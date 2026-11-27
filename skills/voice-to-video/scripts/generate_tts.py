#!/usr/bin/env python3
"""Generate per-scene TTS audio and synced SRT subtitles from script.json."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def probe_duration(media_path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        text=True,
    ).strip()
    return round(float(out), 3)


def format_srt_ts(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def split_caption_lines(text: str, max_chars: int = 24) -> list[str]:
    """Split Chinese/English narration at punctuation boundaries first, then wrap long clauses."""
    text = text.strip()
    if not text:
        return []
    punct = set("。！？!?；;，,：:")
    clauses: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in punct:
            clauses.append(buf.strip())
            buf = ""
    if buf.strip():
        clauses.append(buf.strip())

    chunks: list[str] = []
    for clause in clauses:
        if len(clause) <= max_chars:
            if chunks and len(chunks[-1]) + len(clause) <= max_chars and not chunks[-1][-1] in "。！？!?":
                chunks[-1] += clause
            else:
                chunks.append(clause)
        else:
            # Break long clause cleanly
            for i in range(0, len(clause), max_chars):
                part = clause[i : i + max_chars].strip()
                if part:
                    chunks.append(part)
    return chunks


def generate_silent_audio(output_path: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            f"{duration:.3f}",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def synth_edge_tts(text: str, output_path: Path, voice: str, rate: str, pitch: str) -> None:
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))


def estimate_duration(text: str, fallback: float) -> float:
    if fallback and fallback > 0:
        return float(fallback)
    chars = len(text.strip())
    return round(max(2.5, chars / 4.2 + 0.6), 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-scene narration audio and SRT.")
    parser.add_argument("--script", required=True, help="Path to project script.json")
    parser.add_argument(
        "--dry-run-audio",
        action="store_true",
        help="Generate silent placeholder audio tracks instead of calling edge-tts (great for offline testing).",
    )
    parser.add_argument("--padding", type=float, default=0.35, help="Trailing pause per scene (seconds)")
    args = parser.parse_args()

    script_path = Path(args.script).resolve()
    project_dir = script_path.parent
    data = json.loads(script_path.read_text(encoding="utf-8"))

    has_edge_tts = importlib.util.find_spec("edge_tts") is not None
    if not args.dry_run_audio and not has_edge_tts:
        print(
            "Error: edge-tts is not installed.\n"
            "Install it with: uv pip install edge-tts\n"
            "Or run with --dry-run-audio to test visual timing offline.",
            file=sys.stderr,
        )
        return 2

    tts_cfg = data.get("tts", {})
    voice = tts_cfg.get("voice", "zh-CN-YunxiNeural")
    rate = tts_cfg.get("rate", "+0%")
    pitch = tts_cfg.get("pitch", "+0Hz")

    audio_dir = project_dir / "work" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    srt_entries: list[str] = []
    srt_idx = 1
    cursor = 0.0

    for i, scene in enumerate(data.get("scenes", []), start=1):
        sid = str(scene.get("id", f"{i:02d}"))
        narration = str(scene.get("narration", "")).strip()
        existing_audio = str(scene.get("audio_path", "")).strip()

        if existing_audio and (project_dir / existing_audio).exists() and not args.dry_run_audio:
            audio_file = project_dir / existing_audio
            dur = probe_duration(audio_file)
        elif args.dry_run_audio or not narration:
            dur = estimate_duration(narration, float(scene.get("duration", 0)))
            audio_file = audio_dir / f"scene_{sid}.m4a"
            generate_silent_audio(audio_file, dur)
            scene["audio_path"] = str(audio_file.relative_to(project_dir))
        else:
            raw_mp3 = audio_dir / f"scene_{sid}_raw.mp3"
            padded_m4a = audio_dir / f"scene_{sid}.m4a"
            asyncio.run(synth_edge_tts(narration, raw_mp3, voice, rate, pitch))
            # Pad small breathing pause so cuts feel natural
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(raw_mp3),
                    "-af",
                    f"apad=pad_dur={args.padding:.3f}",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    str(padded_m4a),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            dur = probe_duration(padded_m4a)
            audio_file = padded_m4a
            scene["audio_path"] = str(audio_file.relative_to(project_dir))

        scene["duration"] = round(dur, 3)

        # Build proportional SRT chunks for this scene
        chunks = split_caption_lines(narration)
        if chunks:
            usable_dur = max(0.5, dur - (args.padding if not args.dry_run_audio else 0.15))
            total_weight = sum(max(1, len(c)) for c in chunks)
            local_t = cursor
            for c in chunks:
                c_dur = usable_dur * (max(1, len(c)) / total_weight)
                srt_entries.append(str(srt_idx))
                srt_entries.append(f"{format_srt_ts(local_t)} --> {format_srt_ts(local_t + c_dur)}")
                srt_entries.append(c)
                srt_entries.append("")
                srt_idx += 1
                local_t += c_dur

        cursor += dur

    script_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    srt_path = output_dir / "subtitles.srt"
    srt_path.write_text("\n".join(srt_entries), encoding="utf-8")
    print(f"Updated {script_path} (total duration: {cursor:.2f}s) and generated {srt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
