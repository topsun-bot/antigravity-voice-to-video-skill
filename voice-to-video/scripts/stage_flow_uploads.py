#!/usr/bin/env python3
"""Stage subject sheets & first-frame keyframes into browser_sandbox/uploads for Google Flow."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy project subject reference images and scene keyframes into browser_sandbox/uploads/ with clean single-segment filenames."
    )
    parser.add_argument("--script", required=True, help="Path to project script.json")
    parser.add_argument(
        "--uploads-dir",
        required=True,
        help="Target <Artifact Directory Path>/browser_sandbox/uploads directory",
    )
    args = parser.parse_args()

    script_path = Path(args.script).resolve()
    project_dir = script_path.parent
    data = json.loads(script_path.read_text(encoding="utf-8"))

    uploads_dir = Path(args.uploads_dir).resolve()
    uploads_dir.mkdir(parents=True, exist_ok=True)

    staged: dict[str, list[dict]] = {"subjects": [], "keyframes": []}

    for sub in data.get("subjects", []):
        sid = str(sub["id"])
        rel = str(sub.get("reference_image") or f"assets/subjects/{sid}.png")
        src = project_dir / rel
        if src.exists():
            fname = f"subject_{sid}{src.suffix.lower()}"
            shutil.copy2(src, uploads_dir / fname)
            staged["subjects"].append({"id": sid, "upload_filename": fname, "source": str(src)})

    for idx, sc in enumerate(data.get("scenes", []), start=1):
        v = sc.get("visual", {})
        if v.get("type") != "ai_video":
            continue
        sid = str(sc.get("id", f"{idx:02d}"))
        kf_rel = str(v.get("first_frame") or f"assets/keyframes/scene_{sid}.png")
        src = project_dir / kf_rel
        if src.exists():
            fname = f"keyframe_scene_{sid}{src.suffix.lower()}"
            shutil.copy2(src, uploads_dir / fname)
            staged["keyframes"].append({"scene_id": sid, "upload_filename": fname, "source": str(src)})

    print(json.dumps({"uploads_dir": str(uploads_dir), **staged}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
