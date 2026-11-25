#!/usr/bin/env python3
"""Programmatic FFmpeg cinema video editor & packager driven by script.json.

Supports:
  - visual.type: "ai_video" | "video" | "image" | "card" | "outro_card"
  - Per-scene top-left translucent chapter badge ("PART 01 · ...")
  - Cinema rounded translucent dark pill subtitles (`subtitles.style = "cinema_pill"`)
    or classic ASS outline subtitles (`subtitles.style = "ass"`)
  - Auto BGM ducking + EBU R128 loudness normalization
  - Storyboard contact sheet + per-scene midpoint frames for visual QC
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from render_overlays import render_chapter_badge, render_cinema_outro, render_subtitle_pill
from render_slide_card import hex_to_rgb, render_card

ASPECT_PRESETS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}


def run_ffmpeg(cmd: list[str], verbose: bool = False) -> None:
    if verbose:
        print("Running:", " ".join(cmd))
    res = subprocess.run(
        cmd,
        stdout=None if verbose else subprocess.DEVNULL,
        stderr=None if verbose else subprocess.PIPE,
        text=True,
    )
    if res.returncode != 0:
        if not verbose and res.stderr:
            print(res.stderr, file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed with exit code {res.returncode}")


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def remove_silence(
    input_path: Path, output_path: Path, silence_db: float = -32.0, min_silence: float = 0.45, pad: float = 0.08
) -> None:
    """Detect silent spans via FFmpeg silencedetect and keep only active speech segments."""
    total_dur = probe_duration(input_path)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(input_path),
            "-af",
            f"silencedetect=noise={silence_db}dB:d={min_silence}",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    starts = [float(m) for m in re.findall(r"silence_start:\s*([0-9.]+)", proc.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([0-9.]+)", proc.stderr)]
    if len(ends) < len(starts):
        ends.append(total_dur)

    keep: list[tuple[float, float]] = []
    cur = 0.0
    for s_start, s_end in zip(starts, ends):
        seg_end = min(total_dur, s_start + pad)
        if seg_end - cur > 0.15:
            keep.append((max(0.0, cur), seg_end))
        cur = max(0.0, s_end - pad)
    if total_dur - cur > 0.15:
        keep.append((cur, total_dur))

    if not keep:
        raise RuntimeError("No active speech segments detected; try adjusting --silence-db.")

    v_filters = []
    a_filters = []
    concat_inputs = []
    for idx, (s, e) in enumerate(keep):
        v_filters.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{idx}]")
        a_filters.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{idx}]")
        concat_inputs.append(f"[v{idx}][a{idx}]")

    filter_complex = ";".join(
        v_filters + a_filters + [f"{''.join(concat_inputs)}concat=n={len(keep)}:v=1:a=1[vout][aout]"]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(output_path),
        ]
    )
    new_dur = probe_duration(output_path)
    print(f"Silence removed: {total_dur:.2f}s -> {new_dur:.2f}s ({len(keep)} kept segments) -> {output_path}")


def parse_srt_cues(srt_path: Path) -> list[dict]:
    def to_sec(ts: str) -> float:
        h, m, rest = ts.strip().split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    raw = srt_path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\n\s*\n", raw) if raw else []
    cues: list[dict] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_s, end_s = [p.strip() for p in lines[1].split("-->")]
        cues.append({"start": to_sec(start_s), "end": to_sec(end_s), "text": " ".join(lines[2:])})
    return cues


def srt_to_ass(srt_path: Path, ass_path: Path, width: int, height: int, sub_cfg: dict) -> None:
    font_name = sub_cfg.get("font_name", "Noto Sans CJK SC")
    font_size = int(sub_cfg.get("font_size", 44 if width >= height else 50))
    margin_v = int(sub_cfg.get("margin_v", 54 if width >= height else 120))
    margin_lr = int(width * 0.06)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00101828,&H90000000,1,0,0,0,100,100,0,0,1,3,1,2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def to_ass_ts(srt_ts: str) -> str:
        h, m, rest = srt_ts.strip().split(":")
        s, ms = rest.split(",")
        cs = int(ms) // 10
        return f"{int(h)}:{m}:{s}.{cs:02d}"

    raw = srt_path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\n\s*\n", raw) if raw else []
    events: list[str] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_s, end_s = [p.strip() for p in lines[1].split("-->")]
        text = "\\N".join(lines[2:]).replace("{", "(").replace("}", ")")
        events.append(f"Dialogue: 0,{to_ass_ts(start_s)},{to_ass_ts(end_s)},Default,,0,0,0,,{text}")

    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def burn_cinema_pill_subtitles(
    input_mp4: Path,
    output_mp4: Path,
    srt_path: Path,
    work_dir: Path,
    width: int,
    height: int,
    sub_cfg: dict,
    bgm_file: Path | None,
    bgm_vol: float,
    verbose: bool,
) -> None:
    """Burn rounded translucent dark pill subtitles (reference cinema style) using PNG overlays."""
    cues = parse_srt_cues(srt_path)
    if not cues:
        raise ValueError("Empty SRT cues")

    # Guard against excessively long filter graphs on 20-min videos
    if len(cues) > 90:
        ass_path = work_dir / "subtitles.ass"
        srt_to_ass(srt_path, ass_path, width, height, sub_cfg)
        burn_ass_subtitles(input_mp4, output_mp4, ass_path, bgm_file, bgm_vol, verbose)
        return

    pill_dir = work_dir / "subtitle_pills"
    pill_dir.mkdir(parents=True, exist_ok=True)
    font_size = int(sub_cfg.get("font_size", 40 if width >= height else 46))
    margin_v = int(sub_cfg.get("margin_v", 46 if width >= height else 120))

    cmd = ["ffmpeg", "-y", "-i", str(input_mp4)]
    bgm_idx: int | None = None
    if bgm_file and bgm_file.exists():
        cmd.extend(["-stream_loop", "-1", "-i", str(bgm_file)])
        bgm_idx = 1

    pill_inputs_start = 2 if bgm_idx is not None else 1
    filter_steps: list[str] = []
    cur_v = "0:v"

    for i, cue in enumerate(cues):
        png_path = pill_dir / f"cue_{i:04d}.png"
        render_subtitle_pill(png_path, cue["text"], video_width=width, video_height=height, font_size=font_size)
        cmd.extend(["-i", str(png_path)])
        in_idx = pill_inputs_start + i
        next_v = f"vsub{i}"
        s_t = max(0.0, cue["start"])
        e_t = max(s_t + 0.05, cue["end"])
        filter_steps.append(
            f"[{cur_v}][{in_idx}:v]overlay=x=(W-w)/2:y=H-h-{margin_v}:enable='between(t,{s_t:.3f},{e_t:.3f})'[{next_v}]"
        )
        cur_v = next_v

    if bgm_idx is not None:
        filter_steps.append(
            f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[vo];"
            f"[{bgm_idx}:a]volume={bgm_vol:.3f}[bgm];"
            f"[vo][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        audio_map = "[aout]"
    else:
        audio_map = "0:a:0"

    fc_script = work_dir / "pill_subs_filter.txt"
    fc_script.write_text(";\n".join(filter_steps) + "\n", encoding="utf-8")

    cmd.extend(
        [
            "-filter_complex_script",
            str(fc_script),
            "-map",
            f"[{cur_v}]",
            "-map",
            audio_map,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_mp4),
        ]
    )
    run_ffmpeg(cmd, verbose=verbose)


def burn_ass_subtitles(
    input_mp4: Path,
    output_mp4: Path,
    ass_path: Path | None,
    bgm_file: Path | None,
    bgm_vol: float,
    verbose: bool,
) -> None:
    cmd = ["ffmpeg", "-y", "-i", str(input_mp4)]
    has_bgm = bool(bgm_file and bgm_file.exists())
    if has_bgm:
        cmd.extend(["-stream_loop", "-1", "-i", str(bgm_file)])

    v_filter = f"ass='{escape_filter_path(ass_path)}'" if ass_path else None
    if has_bgm:
        a_filter = (
            f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[vo];"
            f"[1:a]volume={bgm_vol:.3f}[bgm];"
            f"[vo][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        if v_filter:
            cmd.extend(["-filter_complex", f"[0:v]{v_filter}[vout];{a_filter}", "-map", "[vout]", "-map", "[aout]"])
        else:
            cmd.extend(["-filter_complex", a_filter, "-map", "0:v:0", "-map", "[aout]"])
    else:
        if v_filter:
            cmd.extend(["-vf", v_filter])
        cmd.extend(["-map", "0:v:0", "-map", "0:a:0"])

    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_mp4),
        ]
    )
    run_ffmpeg(cmd, verbose=verbose)


def apply_chapter_badge_if_needed(
    raw_clip: Path,
    final_clip: Path,
    chapter_text: str,
    accent_hex: str,
    work_dir: Path,
    sid: str,
    width: int,
    height: int,
    verbose: bool,
) -> Path:
    if not chapter_text.strip():
        return raw_clip
    badge_png = work_dir / "badges" / f"badge_{sid}.png"
    render_chapter_badge(
        badge_png,
        text=chapter_text.strip(),
        width=width,
        height=height,
        accent_rgb=hex_to_rgb(accent_hex, (56, 189, 248)),
    )
    scale = min(width, height) / 1080.0
    pad_x = int(38 * scale)
    pad_y = int(30 * scale)
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw_clip),
            "-i",
            str(badge_png),
            "-filter_complex",
            f"[0:v][1:v]overlay=x={pad_x}:y={pad_y}:format=auto[vout]",
            "-map",
            "[vout]",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(final_clip),
        ],
        verbose=verbose,
    )
    return final_clip


def render_scene_clip(
    scene: dict,
    scene_idx: int,
    total_scenes: int,
    project_dir: Path,
    work_dir: Path,
    width: int,
    height: int,
    fps: int,
    default_theme: str,
    verbose: bool,
) -> Path:
    sid = str(scene.get("id", f"{scene_idx:02d}"))
    dur = float(scene.get("duration", 4.0))
    visual = scene.get("visual", {})
    vtype = visual.get("type", "card")
    raw_clip = work_dir / "clips" / f"scene_{sid}_raw.mp4"
    out_clip = work_dir / "clips" / f"scene_{sid}.mp4"
    raw_clip.parent.mkdir(parents=True, exist_ok=True)

    audio_rel = str(scene.get("audio_path", "")).strip()
    audio_file = (project_dir / audio_rel) if audio_rel else None
    if not audio_file or not audio_file.exists():
        audio_file = work_dir / "audio" / f"scene_{sid}_silence.m4a"
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo",
                "-t",
                f"{dur:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(audio_file),
            ],
            verbose=verbose,
        )

    # Resolve ai_video -> generated_video mp4 (or gracefully fall back to first_frame image)
    if vtype == "ai_video":
        gen_rel = str(visual.get("generated_video") or f"work/generated_videos/scene_{sid}.mp4")
        gen_path = project_dir / gen_rel
        if gen_path.exists():
            vtype = "video"
            visual = {**visual, "path": gen_rel, "start": 0.0, "auto_fit": True}
        elif visual.get("first_frame") and (project_dir / visual["first_frame"]).exists():
            vtype = "image"
            visual = {**visual, "path": visual["first_frame"], "zoom": True}
        else:
            raise FileNotFoundError(
                f"Scene {sid} (ai_video) has neither generated_video '{gen_rel}' nor first_frame."
            )

    if vtype == "outro_card":
        outro_png = work_dir / "cards" / f"scene_{sid}_outro.png"
        render_cinema_outro(
            output_path=outro_png,
            title=str(visual.get("title", "")),
            subtitle=str(visual.get("subtitle", "")),
            width=width,
            height=height,
        )
        fade_out_st = max(0.2, dur - 0.6)
        vf = f"scale={width}:{height},fade=t=in:st=0:d=0.45,fade=t=out:st={fade_out_st:.3f}:d=0.55,format=yuv420p"
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-framerate",
                str(fps),
                "-i",
                str(outro_png),
                "-i",
                str(audio_file),
                "-t",
                f"{dur:.3f}",
                "-vf",
                vf,
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-b:a",
                "160k",
                "-shortest",
                str(raw_clip),
            ],
            verbose=verbose,
        )
    elif vtype == "card":
        card_png = work_dir / "cards" / f"scene_{sid}.png"
        render_card(
            output_path=card_png,
            width=width,
            height=height,
            theme=visual.get("theme", default_theme),
            accent=visual.get("accent", "#38BDF8"),
            badge=str(scene.get("label", f"SCENE {sid}")),
            title=str(visual.get("title", scene.get("label", f"分镜 {sid}"))),
            subtitle=str(visual.get("subtitle", "")),
            bullets=list(visual.get("bullets", [])),
            scene_index=scene_idx,
            total_scenes=total_scenes,
        )
        vf = f"scale={width}:{height},fade=t=in:st=0:d=0.25,format=yuv420p"
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-framerate",
                str(fps),
                "-i",
                str(card_png),
                "-i",
                str(audio_file),
                "-t",
                f"{dur:.3f}",
                "-vf",
                vf,
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-b:a",
                "160k",
                "-shortest",
                str(raw_clip),
            ],
            verbose=verbose,
        )
    elif vtype == "image":
        img_path = project_dir / str(visual["path"])
        if not img_path.exists():
            raise FileNotFoundError(f"Scene {sid} image not found: {img_path}")
        frames = max(1, int(round(dur * fps)))
        if visual.get("zoom", True):
            vf = (
                f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
                f"crop={width*2}:{height*2},"
                f"zoompan=z='min(zoom+0.00055,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames}:s={width}x{height}:fps={fps},"
                f"fade=t=in:st=0:d=0.2,format=yuv420p"
            )
        else:
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fade=t=in:st=0:d=0.2,format=yuv420p"
            )
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(img_path),
                "-i",
                str(audio_file),
                "-t",
                f"{dur:.3f}",
                "-vf",
                vf,
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-b:a",
                "160k",
                "-shortest",
                str(raw_clip),
            ],
            verbose=verbose,
        )
    elif vtype == "video":
        vid_path = project_dir / str(visual["path"])
        if not vid_path.exists():
            raise FileNotFoundError(f"Scene {sid} video not found: {vid_path}")
        start = float(visual.get("start", 0.0))
        keep_audio = bool(visual.get("keep_audio", False))
        src_dur = probe_duration(vid_path)
        avail = max(0.5, src_dur - start)

        # Auto-fit AI clip length to narration duration smoothly
        stream_loop_args: list[str] = []
        pts_filter = ""
        if visual.get("auto_fit") and avail < dur - 0.15:
            ratio = dur / avail
            if ratio <= 1.35:
                pts_filter = f"setpts={ratio:.4f}*PTS,"
            else:
                stream_loop_args = ["-stream_loop", "-1"]

        fade_in = "fade=t=in:st=0:d=0.18," if scene_idx > 1 else "fade=t=in:st=0:d=0.3,"
        vf = (
            f"{pts_filter}scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},{fade_in}format=yuv420p"
        )
        cmd = ["ffmpeg", "-y", *stream_loop_args, "-ss", f"{start:.3f}", "-i", str(vid_path), "-i", str(audio_file), "-t", f"{dur:.3f}"]
        if keep_audio:
            cmd.extend(
                [
                    "-filter_complex",
                    f"[0:v]{vf}[vout];[0:a]volume=0.25[bg];[1:a]volume=1.0[vo];[bg][vo]amix=inputs=2:duration=shortest[aout]",
                    "-map",
                    "[vout]",
                    "-map",
                    "[aout]",
                ]
            )
        else:
            cmd.extend(["-vf", vf, "-map", "0:v:0", "-map", "1:a:0"])
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-b:a",
                "160k",
                "-shortest",
                str(raw_clip),
            ]
        )
        run_ffmpeg(cmd, verbose=verbose)
    else:
        raise ValueError(f"Unsupported visual.type '{vtype}' in scene {sid}")

    chapter = str(scene.get("chapter", "")).strip()
    accent = str(visual.get("accent", "#38BDF8"))
    if chapter and vtype != "outro_card":
        return apply_chapter_badge_if_needed(raw_clip, out_clip, chapter, accent, work_dir, sid, width, height, verbose)
    raw_clip.replace(out_clip)
    return out_clip


def build_contact_sheet(frame_paths: list[Path], output_path: Path) -> None:
    if not frame_paths:
        return
    from PIL import Image

    cols = min(3, len(frame_paths))
    rows = math.ceil(len(frame_paths) / cols)
    tw, th = 640, 360
    sample = Image.open(frame_paths[0])
    if sample.height > sample.width:
        tw, th = 360, 640
    sheet = Image.new("RGB", (cols * tw, rows * th), (12, 16, 24))
    for i, fp in enumerate(frame_paths):
        im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        r, c = divmod(i, cols)
        sheet.paste(im, (c * tw, r * th))
    sheet.save(output_path, "JPEG", quality=88)


def build_from_script(script_path: Path, verbose: bool = False) -> None:
    project_dir = script_path.parent
    data = json.loads(script_path.read_text(encoding="utf-8"))
    aspect = data.get("aspect_ratio", "16:9")
    width, height = ASPECT_PRESETS.get(aspect, (1920, 1080))
    fps = int(data.get("fps", 24))
    theme = data.get("theme", "dark")
    scenes = data.get("scenes", [])
    if not scenes:
        raise ValueError("script.json contains no scenes.")

    work_dir = project_dir / "work"
    output_dir = project_dir / "output"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    clip_paths: list[Path] = []
    for idx, scene in enumerate(scenes, start=1):
        clip = render_scene_clip(
            scene=scene,
            scene_idx=idx,
            total_scenes=len(scenes),
            project_dir=project_dir,
            work_dir=work_dir,
            width=width,
            height=height,
            fps=fps,
            default_theme=theme,
            verbose=verbose,
        )
        clip_paths.append(clip)

    concat_file = work_dir / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths) + "\n", encoding="utf-8")
    merged_mp4 = work_dir / "merged.mp4"
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-b:a",
            "160k",
            str(merged_mp4),
        ],
        verbose=verbose,
    )

    bgm_cfg = data.get("bgm", {})
    bgm_rel = str(bgm_cfg.get("path", "")).strip()
    bgm_file = (project_dir / bgm_rel) if bgm_rel else None
    if bgm_file and not bgm_file.exists():
        bgm_file = None
    bgm_vol = float(bgm_cfg.get("volume", 0.14))

    sub_cfg = data.get("subtitles", {})
    srt_path = output_dir / "subtitles.srt"
    burn_subs = bool(sub_cfg.get("enabled", True) and srt_path.exists() and srt_path.stat().st_size > 0)
    sub_style = str(sub_cfg.get("style", "cinema_pill")).lower()
    final_mp4 = output_dir / "final.mp4"

    if burn_subs and sub_style == "cinema_pill":
        burn_cinema_pill_subtitles(
            input_mp4=merged_mp4,
            output_mp4=final_mp4,
            srt_path=srt_path,
            work_dir=work_dir,
            width=width,
            height=height,
            sub_cfg=sub_cfg,
            bgm_file=bgm_file,
            bgm_vol=bgm_vol,
            verbose=verbose,
        )
    else:
        ass_path = work_dir / "subtitles.ass"
        if burn_subs:
            srt_to_ass(srt_path, ass_path, width, height, sub_cfg)
        burn_ass_subtitles(
            input_mp4=merged_mp4,
            output_mp4=final_mp4,
            ass_path=ass_path if burn_subs else None,
            bgm_file=bgm_file,
            bgm_vol=bgm_vol,
            verbose=verbose,
        )

    # Extract midpoint preview frames + unified storyboard contact sheet
    preview_dir = output_dir / "preview_frames"
    preview_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: list[Path] = []
    cursor = 0.0
    for idx, scene in enumerate(scenes, start=1):
        sid = str(scene.get("id", f"{idx:02d}"))
        dur = float(scene.get("duration", 4.0))
        mid = cursor + min(dur * 0.5, max(0.3, dur - 0.2))
        frame_out = preview_dir / f"scene_{sid}.png"
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{mid:.3f}",
                "-i",
                str(final_mp4),
                "-frames:v",
                "1",
                str(frame_out),
            ],
            verbose=verbose,
        )
        frame_paths.append(frame_out)
        cursor += dur

    contact_sheet = preview_dir / "contact_sheet.jpg"
    build_contact_sheet(frame_paths, contact_sheet)

    total_final = probe_duration(final_mp4)
    print(f"Rendered final video: {final_mp4} ({total_final:.2f}s, {width}x{height}@{fps}fps)")
    print(f"Preview frames & contact sheet: {contact_sheet}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build cinema video from script.json or remove silence.")
    parser.add_argument("--script", help="Path to project script.json")
    parser.add_argument("--remove-silence", help="Path to raw talking-head video for silence removal")
    parser.add_argument("--output", help="Output path when using --remove-silence")
    parser.add_argument("--silence-db", type=float, default=-32.0)
    parser.add_argument("--min-silence", type=float, default=0.45)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.remove_silence:
        if not args.output:
            print("Error: --output is required with --remove-silence", file=sys.stderr)
            return 1
        remove_silence(
            Path(args.remove_silence).resolve(),
            Path(args.output).resolve(),
            silence_db=args.silence_db,
            min_silence=args.min_silence,
        )
        return 0

    if not args.script:
        print("Error: provide --script <path/to/script.json> or --remove-silence <video>", file=sys.stderr)
        return 1

    build_from_script(Path(args.script).resolve(), verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
