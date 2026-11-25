#!/usr/bin/env python3
"""One-command full-auto cinematic video pipeline orchestrator (Google-first).

Runs all stages in sequence:
  1. Cost & Google Ultra credit estimation
  2. Subject consistency reference sheets & first-frame keyframes check/generation
  3. TTS narration + synced SRT subtitles (falls back to dry-run audio if edge-tts missing)
  4. Concurrent AI video generation (Google Veo 3.1 Gemini/Vertex -> Google Flow queue -> Ken Burns preview)
  5. Cinema FFmpeg packaging (chapter badges, rounded translucent pill subtitles, outro card, contact sheet)
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


def run_step(title: str, cmd: list[str]) -> None:
    print(f"\n=== {title} ===")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise SystemExit(res.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full-auto voice-to-video cinematic pipeline.")
    parser.add_argument("--script", required=True, help="Path to project script.json")
    parser.add_argument(
        "--subject-mode",
        choices=["manifest", "gemini_api", "placeholder"],
        default="manifest",
        help="How to handle missing subject sheets / keyframes",
    )
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "google_veo_gemini", "google_veo_vertex", "google_flow", "volcengine_seedance", "kenburns"],
    )
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--scenes", default="", help="Only regenerate specific scene IDs (e.g. '02,04')")
    parser.add_argument("--force-video", action="store_true", help="Force regenerate video clips")
    parser.add_argument("--fallback-kenburns", action="store_true", help="Animate keyframes locally if no video API key")
    parser.add_argument("--dry-run-audio", action="store_true", help="Force silent timing placeholders instead of TTS")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    script_path = Path(args.script).resolve()
    py = sys.executable

    run_step("1/5 Pre-flight Cost & Credit Estimate", [py, str(scripts_dir / "generate_videos.py"), "--script", str(script_path), "--estimate-only"])

    run_step(
        "2/5 Subject Consistency Sheets & Keyframes",
        [py, str(scripts_dir / "prepare_subjects.py"), "--script", str(script_path), "--mode", args.subject_mode],
    )

    tts_cmd = [py, str(scripts_dir / "generate_tts.py"), "--script", str(script_path)]
    if args.dry_run_audio or importlib.util.find_spec("edge_tts") is None:
        if not args.dry_run_audio:
            print("Note: edge_tts not installed; using --dry-run-audio timing mode for TTS.")
        tts_cmd.append("--dry-run-audio")
    run_step("3/5 Voiceover & Synced Subtitles", tts_cmd)

    vid_cmd = [
        py,
        str(scripts_dir / "generate_videos.py"),
        "--script",
        str(script_path),
        "--provider",
        args.provider,
        "--concurrency",
        str(args.concurrency),
    ]
    if args.scenes:
        vid_cmd.extend(["--scenes", args.scenes])
    if args.force_video:
        vid_cmd.append("--force")
    if args.fallback_kenburns:
        vid_cmd.append("--fallback-kenburns")
    run_step("4/5 Concurrent AI Video Generation (Google-First)", vid_cmd)

    build_cmd = [py, str(scripts_dir / "build_video.py"), "--script", str(script_path)]
    if args.verbose:
        build_cmd.append("--verbose")
    run_step("5/5 Cinema Packaging, Chapter Badges & Pill Subtitles", build_cmd)

    print("\nPipeline complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
