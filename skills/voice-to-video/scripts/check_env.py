#!/usr/bin/env python3
"""Environment & Google-first video engine checker for voice-to-video-studio."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def load_dotenv(start_dir: Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from CWD or nearest parent .env without external deps."""
    candidates: list[Path] = [Path.cwd() / ".env"]
    if start_dir is not None:
        candidates.append(start_dir / ".env")
    # Walk up from script location safely (works in both workspace .agents/skills and global ~/.gemini/config/skills)
    cur = Path(__file__).resolve().parent
    for _ in range(5):
        candidates.append(cur / ".env")
        if cur.parent == cur:
            break
        cur = cur.parent

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            for raw in candidate.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ and val:
                    os.environ[key] = val
            break


def check_binary(name: str) -> dict:
    path = shutil.which(name)
    return {"available": bool(path), "path": path or ""}


def check_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def find_cjk_font() -> str:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    try:
        out = subprocess.check_output(
            ["fc-list", ":lang=zh", "file"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            font_path = line.split(":")[0].strip()
            if font_path and Path(font_path).exists():
                return font_path
    except Exception:
        pass
    return ""


def detect_gcloud_auth() -> bool:
    if not shutil.which("gcloud"):
        return False
    try:
        out = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
        return bool(out)
    except Exception:
        return False


def main() -> int:
    load_dotenv(Path.cwd())

    has_gemini_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_vertex = bool(os.environ.get("GOOGLE_CLOUD_PROJECT")) and detect_gcloud_auth()
    has_volc = bool(os.environ.get("VOLCENGINE_API_KEY"))
    has_kling = bool(os.environ.get("KLING_ACCESS_KEY"))
    has_runway = bool(os.environ.get("RUNWAYML_API_SECRET"))

    forced_backend = os.environ.get("GOOGLE_VIDEO_BACKEND", "auto").strip().lower()
    if forced_backend == "google_flow":
        active_engine = "google_flow_ultra"
    elif forced_backend and forced_backend != "auto":
        active_engine = forced_backend
    elif has_gemini_key:
        active_engine = "google_veo_gemini"
    elif has_vertex:
        active_engine = "google_veo_vertex"
    elif has_volc:
        active_engine = "volcengine_seedance"
    elif has_kling:
        active_engine = "kling"
    elif has_runway:
        active_engine = "runway"
    else:
        active_engine = "google_flow_ultra"

    report = {
        "required": {
            "python3": {"available": True, "version": sys.version.split()[0]},
            "ffmpeg": check_binary("ffmpeg"),
            "ffprobe": check_binary("ffprobe"),
            "pillow": {"available": check_module("PIL")},
        },
        "video_engines": {
            "recommended_active": active_engine,
            "google_veo_gemini": {
                "configured": has_gemini_key,
                "env_var": "GEMINI_API_KEY",
                "priority": 1,
                "note": "Google 官方 Gemini API Veo 3.1（支持主体一致性 referenceImages + 并发 API）",
            },
            "google_veo_vertex": {
                "configured": has_vertex,
                "env_var": "GOOGLE_CLOUD_PROJECT + gcloud auth",
                "priority": 2,
                "note": "Google Cloud Vertex AI 企业账单通道",
            },
            "google_flow_ultra": {
                "configured": True,
                "priority": 3,
                "note": "可通过导出 Flow 任务队列 + Antigravity 浏览器配合 Google AI Ultra 10,000 积分池使用",
            },
            "volcengine_seedance": {"configured": has_volc, "env_var": "VOLCENGINE_API_KEY", "priority": 4},
            "kling": {"configured": has_kling, "env_var": "KLING_ACCESS_KEY", "priority": 5},
            "runway": {"configured": has_runway, "env_var": "RUNWAYML_API_SECRET", "priority": 6},
        },
        "voice_and_audio": {
            "edge_tts": {"available": check_module("edge_tts"), "purpose": "免费高质量中文配音"},
            "faster_whisper": {"available": check_module("faster_whisper"), "purpose": "本地快速录音转文字"},
            "boss_voice_clone_fish": {"configured": bool(os.environ.get("FISH_AUDIO_API_KEY"))},
            "boss_voice_clone_elevenlabs": {"configured": bool(os.environ.get("ELEVENLABS_API_KEY"))},
        },
        "cjk_font": find_cjk_font(),
    }

    missing_required = [k for k, v in report["required"].items() if not v.get("available")]
    report["ready_for_core_pipeline"] = len(missing_required) == 0
    report["missing_required"] = missing_required

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_core_pipeline"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
