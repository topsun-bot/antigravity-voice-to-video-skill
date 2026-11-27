#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${1:-$SKILL_DIR/.venv}"

echo "[voice-to-video] Checking ffmpeg..."
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARNING: ffmpeg not found in PATH. Please install ffmpeg first:"
  echo "  macOS:  brew install ffmpeg"
  echo "  Ubuntu: sudo apt-get install -y ffmpeg fonts-noto-cjk"
fi

echo "[voice-to-video] Creating Python venv at: $VENV_DIR"
if command -v uv >/dev/null 2>&1; then
  uv venv "$VENV_DIR"
  uv pip install --python "$VENV_DIR/bin/python" edge-tts pillow
else
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade edge-tts pillow
fi

echo "[voice-to-video] Running environment verification..."
"$VENV_DIR/bin/python" "$SKILL_DIR/scripts/check_env.py"
echo "[voice-to-video] Setup complete!"
