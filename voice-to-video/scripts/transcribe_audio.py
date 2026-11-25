#!/usr/bin/env python3
"""Transcribe local voice memos or raw footage into TXT, SRT, and JSON."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path


def format_srt_ts(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_outputs(segments: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    full_text = "\n".join(s["text"].strip() for s in segments if s["text"].strip())
    (out_dir / "transcript.txt").write_text(full_text + "\n", encoding="utf-8")

    srt_lines: list[str] = []
    for idx, seg in enumerate(segments, start=1):
        text = seg["text"].strip()
        if not text:
            continue
        srt_lines.append(str(idx))
        srt_lines.append(f"{format_srt_ts(seg['start'])} --> {format_srt_ts(seg['end'])}")
        srt_lines.append(text)
        srt_lines.append("")
    (out_dir / "transcript.srt").write_text("\n".join(srt_lines), encoding="utf-8")

    payload = {"segments": segments, "text": full_text}
    (out_dir / "transcript.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def transcribe_with_faster_whisper(audio_path: Path, model_size: str, language: str | None) -> list[dict]:
    from faster_whisper import WhisperModel  # type: ignore

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    seg_iter, _info = model.transcribe(str(audio_path), language=language or None, vad_filter=True)
    return [
        {"start": round(float(s.start), 3), "end": round(float(s.end), 3), "text": s.text.strip()}
        for s in seg_iter
    ]


def transcribe_with_openai_whisper(audio_path: Path, model_size: str, language: str | None) -> list[dict]:
    import whisper  # type: ignore

    model = whisper.load_model(model_size)
    kwargs = {"language": language} if language else {}
    result = model.transcribe(str(audio_path), **kwargs)
    return [
        {"start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3), "text": s["text"].strip()}
        for s in result.get("segments", [])
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe audio/video into text + timestamps.")
    parser.add_argument("--input", required=True, help="Path to audio or video file")
    parser.add_argument("--output-dir", required=True, help="Directory to write transcript files")
    parser.add_argument("--model", default="small", help="Whisper model size (tiny/base/small/medium)")
    parser.add_argument("--language", default="zh", help="Language code, e.g. zh, en, or empty for auto")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    out_dir = Path(args.output_dir).resolve()
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    lang = args.language.strip() or None

    if importlib.util.find_spec("faster_whisper") is not None:
        segments = transcribe_with_faster_whisper(input_path, args.model, lang)
        write_outputs(segments, out_dir)
        print(f"Transcribed {len(segments)} segments via faster-whisper -> {out_dir}")
        return 0

    if importlib.util.find_spec("whisper") is not None:
        segments = transcribe_with_openai_whisper(input_path, args.model, lang)
        write_outputs(segments, out_dir)
        print(f"Transcribed {len(segments)} segments via openai-whisper -> {out_dir}")
        return 0

    whisper_cli = shutil.which("whisper")
    if whisper_cli:
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [whisper_cli, str(input_path), "--model", args.model, "--output_dir", str(out_dir)]
        if lang:
            cmd.extend(["--language", lang])
        subprocess.run(cmd, check=True)
        print(f"Transcribed via whisper CLI -> {out_dir}")
        return 0

    print(
        "No local Whisper backend found.\n"
        "Install faster-whisper with:\n"
        "  uv pip install faster-whisper\n"
        "Or use Antigravity's native voice input (/voice dictate or /voice live), "
        "or pass the audio file directly to Antigravity for multimodal transcription.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
