#!/usr/bin/env python3
"""Prepare any local video for Google Flow Omni 1.2 Flash Video-to-Video (Character Swap / Motion Transfer).

Splits the source video into H.264 720p@24fps chunks (default 15s, matching Omni 1.2 Flash's max edit length),
extracts the exact unbroken master audio track (`input/master_audio.m4a`), and writes a ready-to-assemble
`script.json` that re-muxes the original unbroken audio onto the edited 1080p/4K output clips.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path


def probe_video(path: Path) -> dict:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    data = json.loads(out)
    dur = float(data["format"]["duration"])
    v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    return {
        "duration": dur,
        "width": int(v_stream.get("width", 1920)),
        "height": int(v_stream.get("height", 1080)),
        "has_audio": has_audio,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Split a local video into 15s H.264 chunks + master audio for Flow V2V editing.")
    parser.add_argument("--input", required=True, help="Path to local source video")
    parser.add_argument("--project-dir", required=True, help="Target project directory (e.g. projects/my-v2v)")
    parser.add_argument("--chunk-seconds", type=float, default=15.0, help="Chunk duration in seconds (max 15s for Omni 1.2 Flash)")
    parser.add_argument("--resolution", choices=["1080p", "4k"], default="1080p", help="Final output resolution")
    parser.add_argument("--edit-prompt", default="", help="Default video-to-video edit prompt recorded in script.json")
    parser.add_argument(
        "--keep-segment-audio",
        action="store_true",
        help="Keep audio inside sliced segments (NOT recommended for Google Flow V2V: vocals/speech trigger Flow's speech_edit policy block; master_audio.m4a is already extracted separately).",
    )
    parser.add_argument(
        "--no-storyboard-sheets",
        action="store_true",
        help="Skip generating tiled storyboard contact sheets (work/storyboard_ref/sheet_*.jpg) for visual scene/lighting analysis.",
    )
    args = parser.parse_args()

    src = Path(args.input).resolve()
    if not src.exists():
        print(f"Error: source video not found: {src}", file=sys.stderr)
        return 1

    proj = Path(args.project_dir).resolve()
    in_dir = proj / "input"
    seg_dir = proj / "assets" / "source_segments"
    gen_dir = proj / "work" / "generated_videos"
    in_dir.mkdir(parents=True, exist_ok=True)
    seg_dir.mkdir(parents=True, exist_ok=True)
    gen_dir.mkdir(parents=True, exist_ok=True)

    meta = probe_video(src)
    total_dur = meta["duration"]
    aspect = "9:16" if meta["height"] > meta["width"] else "16:9"
    scale_vf = "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2" if aspect == "9:16" else "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"

    # 1. Extract unbroken master audio track
    master_audio_rel = ""
    if meta["has_audio"]:
        master_audio = in_dir / "master_audio.m4a"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-vn",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(master_audio),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
        master_audio_rel = "input/master_audio.m4a"

    # 2. Split into exact <=15s H.264 720p@24fps chunks (fast upload + universal browser/Flow compatibility)
    chunk_s = max(3.0, min(15.0, float(args.chunk_seconds)))
    count = math.ceil(total_dur / chunk_s)
    scenes: list[dict] = []
    seg_paths: list[str] = []

    for i in range(count):
        start_t = round(i * chunk_s, 3)
        dur = round(min(chunk_s, total_dur - start_t), 3)
        if dur < 1.0:
            break
        sid = f"{i + 1:02d}"
        seg_out = seg_dir / f"seg_{sid}.mp4"
        audio_args = (
            ["-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k"]
            if args.keep_segment_audio
            else ["-an"]
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{start_t:.3f}",
                "-t",
                f"{dur:.3f}",
                "-i",
                str(src),
                "-vf",
                f"{scale_vf},fps=24,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                *audio_args,
                "-movflags",
                "+faststart",
                str(seg_out),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
        seg_paths.append(str(seg_out))
        scenes.append(
            {
                "id": sid,
                "label": f"Segment {sid} ({start_t:.0f}s-{start_t+dur:.0f}s)",
                "duration": dur,
                "transition": "cut",
                "visual": {
                    "type": "ai_video",
                    "source_segment": f"assets/source_segments/seg_{sid}.mp4",
                    "generated_video": f"work/generated_videos/seg_{sid}.mp4",
                    "video_prompt": args.edit_prompt,
                    "keep_audio": False,
                    "auto_fit": True,
                },
            }
        )

    storyboard_sheets: list[str] = []
    if not args.no_storyboard_sheets and scenes:
        try:
            from PIL import Image, ImageDraw

            ref_dir = proj / "work" / "storyboard_ref"
            ref_dir.mkdir(parents=True, exist_ok=True)
            cell_w, cell_h = (240, 426) if aspect == "9:16" else (426, 240)
            for g_start in range(0, len(scenes), 5):
                batch = scenes[g_start : g_start + 5]
                sheet = Image.new("RGB", (cell_w * 3, cell_h * len(batch)), (15, 15, 18))
                draw = ImageDraw.Draw(sheet)
                for r, sc in enumerate(batch):
                    idx = g_start + r + 1
                    mp4 = seg_dir / f"seg_{idx:02d}.mp4"
                    d = float(sc["duration"])
                    times = [max(0.2, d * 0.14), max(0.4, d * 0.50), max(0.6, d * 0.86)]
                    for c, t in enumerate(times):
                        tmp = ref_dir / f"_s{idx:02d}_{c}.jpg"
                        subprocess.run(
                            [
                                "ffmpeg",
                                "-y",
                                "-ss",
                                f"{t:.2f}",
                                "-i",
                                str(mp4),
                                "-frames:v",
                                "1",
                                "-vf",
                                f"scale={cell_w}:{cell_h}:force_original_aspect_ratio=decrease,pad={cell_w}:{cell_h}:(ow-iw)/2:(oh-ih)/2",
                                str(tmp),
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=True,
                        )
                        sheet.paste(Image.open(tmp), (c * cell_w, r * cell_h))
                        tmp.unlink(missing_ok=True)
                        abs_t = (idx - 1) * chunk_s + t
                        mm, ss = divmod(int(abs_t), 60)
                        label = f"SEG {idx:02d} ({mm:02d}:{ss:02d})"
                        draw.rectangle([c * cell_w + 6, r * cell_h + 6, c * cell_w + 150, r * cell_h + 28], fill=(0, 0, 0))
                        draw.text((c * cell_w + 12, r * cell_h + 10), label, fill=(255, 255, 120))
                g_end = g_start + len(batch)
                sheet_path = ref_dir / f"sheet_{g_start + 1:02d}_{g_end:02d}.jpg"
                sheet.save(sheet_path, quality=88)
                storyboard_sheets.append(str(sheet_path))
        except ImportError:
            pass

    script_data = {
        "project_name": proj.name,
        "title": src.stem,
        "aspect_ratio": aspect,
        "output_resolution": args.resolution,
        "fps": 24,
        "theme": "dark",
        "production": {
            "mode": "reference_storyboard_omni_flow",
            "video_provider": "google_flow",
            "output_resolution": args.resolution,
            "source_video": str(src),
            "chunk_seconds": chunk_s,
        },
        "tts": {"enabled": False},
        "bgm": {"path": master_audio_rel, "volume": 1.0, "replace_audio": True},
        "subtitles": {"enabled": False},
        "scenes": scenes,
    }
    script_path = proj / "script.json"
    script_path.write_text(json.dumps(script_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "project_dir": str(proj),
                "script_json": str(script_path),
                "master_audio": str(proj / master_audio_rel) if master_audio_rel else "",
                "total_duration_sec": round(total_dur, 2),
                "segment_count": len(scenes),
                "segments_dir": str(seg_dir),
                "segments": seg_paths,
                "storyboard_sheets": storyboard_sheets,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
