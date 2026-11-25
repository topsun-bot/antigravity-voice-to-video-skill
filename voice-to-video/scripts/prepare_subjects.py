#!/usr/bin/env python3
"""Subject-consistency reference sheet & scene first-frame keyframe pipeline.

Workflow:
1. Locks recurring characters/props/products into `assets/subjects/<id>.png`.
2. Locks per-scene first frames into `assets/keyframes/scene_<id>.png` while
   explicitly referencing the locked subject sheet(s) and global `style_bible`.
3. Supports three modes:
   - `manifest` (default): outputs `work/subject_manifest.json` with ready-to-use
     prompts for Antigravity's native `image-generator` subagent (zero extra API key).
   - `gemini_api`: concurrently calls Google Gemini Image / Imagen API using GEMINI_API_KEY.
   - `placeholder`: renders annotated visual storyboard placeholders offline for testing.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from check_env import load_dotenv
from render_slide_card import render_card

ASPECT_PRESETS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}


def encode_image_b64(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
    return base64.b64encode(path.read_bytes()).decode("ascii"), mime


def build_manifest(script_path: Path) -> dict:
    project_dir = script_path.parent
    data = json.loads(script_path.read_text(encoding="utf-8"))
    style_bible = str(data.get("style_bible", "")).strip()
    aspect = str(data.get("aspect_ratio", "16:9"))

    subjects_by_id: dict[str, dict] = {}
    subject_tasks: list[dict] = []

    for sub in data.get("subjects", []):
        sid = str(sub["id"])
        rel_path = str(sub.get("reference_image") or f"assets/subjects/{sid}.png")
        abs_path = project_dir / rel_path
        prompt = (
            f"Character & asset consistency reference portrait: {sub.get('description', '')}. "
            f"Clean neutral cinematic lighting, crisp focus, high detail. "
            f"{style_bible}"
        ).strip()
        task = {
            "id": sid,
            "name": sub.get("name", sid),
            "role": sub.get("role", "character"),
            "path": rel_path,
            "abs_path": str(abs_path),
            "exists": abs_path.exists(),
            "aspect_ratio": "1:1" if sub.get("role") == "character" else aspect,
            "prompt": prompt,
        }
        subjects_by_id[sid] = task
        subject_tasks.append(task)

    keyframe_tasks: list[dict] = []
    warnings: list[str] = []

    for idx, scene in enumerate(data.get("scenes", []), start=1):
        sc_id = str(scene.get("id", f"{idx:02d}"))
        visual = scene.get("visual", {})
        if visual.get("type") != "ai_video":
            continue

        ref_ids = list(visual.get("subjects", []))
        if len(ref_ids) > 3:
            warnings.append(
                f"Scene {sc_id} lists {len(ref_ids)} subjects; Google Veo 3.1 supports at most 3 referenceImages. Only the first 3 will be attached."
            )
            ref_ids = ref_ids[:3]

        ref_paths = []
        ref_descriptions = []
        for rid in ref_ids:
            if rid in subjects_by_id:
                ref_paths.append(subjects_by_id[rid]["abs_path"])
                ref_descriptions.append(f"[{rid}: {subjects_by_id[rid]['name']}]")
            else:
                warnings.append(f"Scene {sc_id} references unknown subject id '{rid}'.")

        kf_rel = str(visual.get("first_frame") or f"assets/keyframes/scene_{sc_id}.png")
        kf_abs = project_dir / kf_rel
        base_img_prompt = str(visual.get("image_prompt") or visual.get("video_prompt") or scene.get("narration", ""))
        camera = str(visual.get("camera", "")).strip()
        full_prompt = " ".join(
            p
            for p in [
                base_img_prompt,
                f"Maintain exact visual identity of referenced subjects: {', '.join(ref_descriptions)}." if ref_descriptions else "",
                f"Camera & framing: {camera}." if camera else "",
                f"Global visual style: {style_bible}" if style_bible else "",
                "No text, no watermarks, no subtitles on image.",
            ]
            if p
        )

        keyframe_tasks.append(
            {
                "scene_id": sc_id,
                "label": scene.get("label", f"Scene {sc_id}"),
                "chapter": scene.get("chapter", ""),
                "path": kf_rel,
                "abs_path": str(kf_abs),
                "exists": kf_abs.exists(),
                "aspect_ratio": aspect,
                "subject_ids": ref_ids,
                "reference_images": ref_paths,
                "prompt": full_prompt,
            }
        )

    manifest = {
        "project_dir": str(project_dir),
        "aspect_ratio": aspect,
        "style_bible": style_bible,
        "subjects": subject_tasks,
        "keyframes": keyframe_tasks,
        "missing_subjects": [t["id"] for t in subject_tasks if not t["exists"]],
        "missing_keyframes": [t["scene_id"] for t in keyframe_tasks if not t["exists"]],
        "warnings": warnings,
    }
    out_manifest = project_dir / "work" / "subject_manifest.json"
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def call_gemini_image_api(
    prompt: str,
    output_path: Path,
    reference_paths: list[Path],
    api_key: str,
    model: str = "gemini-2.5-flash-image-preview",
) -> None:
    """Generate a consistency-locked image using Google Gemini multimodal image generation API."""
    parts: list[dict] = []
    for rp in reference_paths[:3]:
        if rp.exists():
            b64, mime = encode_image_b64(rp)
            parts.append({"inlineData": {"mimeType": mime, "data": b64}})
    parts.append({"text": prompt})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_text = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini image API error {e.code}: {err_text[:400]}") from e

    for cand in body.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(base64.b64decode(inline["data"]))
                return
    raise RuntimeError(f"Gemini image API returned no image data for {output_path.name}")


def run_gemini_generation(manifest: dict, force: bool, concurrency: int, model: str) -> None:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for --mode gemini_api.")

    # Phase A: Generate subject sheets first (so keyframes can reference them!)
    sub_jobs = [t for t in manifest["subjects"] if force or not Path(t["abs_path"]).exists()]
    if sub_jobs:
        print(f"[Subjects] Generating {len(sub_jobs)} subject consistency sheets via {model}...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = {
                pool.submit(call_gemini_image_api, t["prompt"], Path(t["abs_path"]), [], api_key, model): t["id"]
                for t in sub_jobs
            }
            for fut in concurrent.futures.as_completed(futs):
                sid = futs[fut]
                fut.result()
                print(f"  ✓ Subject sheet ready: {sid}")

    # Phase B: Generate scene keyframes using locked subject reference images
    kf_jobs = [t for t in manifest["keyframes"] if force or not Path(t["abs_path"]).exists()]
    if kf_jobs:
        print(f"[Keyframes] Generating {len(kf_jobs)} scene first-frames with subject refs...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = {
                pool.submit(
                    call_gemini_image_api,
                    t["prompt"],
                    Path(t["abs_path"]),
                    [Path(p) for p in t["reference_images"]],
                    api_key,
                    model,
                ): t["scene_id"]
                for t in kf_jobs
            }
            for fut in concurrent.futures.as_completed(futs):
                sc_id = futs[fut]
                fut.result()
                print(f"  ✓ Scene keyframe ready: scene_{sc_id}")


def run_placeholder_generation(manifest: dict, force: bool) -> None:
    aspect = manifest.get("aspect_ratio", "16:9")
    w, h = ASPECT_PRESETS.get(aspect, (1920, 1080))
    for idx, t in enumerate(manifest["subjects"], start=1):
        p = Path(t["abs_path"])
        if force or not p.exists():
            render_card(
                output_path=p,
                width=1024,
                height=1024,
                theme="dark",
                accent="#38BDF8",
                badge=f"SUBJECT · {t['id']}",
                title=t["name"],
                subtitle="Subject Consistency Reference Placeholder",
                bullets=[t["prompt"][:90] + "..."],
                scene_index=idx,
                total_scenes=max(1, len(manifest["subjects"])),
            )
    for idx, t in enumerate(manifest["keyframes"], start=1):
        p = Path(t["abs_path"])
        if force or not p.exists():
            render_card(
                output_path=p,
                width=w,
                height=h,
                theme="dark",
                accent="#A78BFA",
                badge=t.get("chapter") or f"KEYFRAME · {t['scene_id']}",
                title=t.get("label", f"Scene {t['scene_id']}"),
                subtitle=f"Subjects: {', '.join(t['subject_ids']) or 'None'}",
                bullets=[t["prompt"][:100] + "..."],
                scene_index=idx,
                total_scenes=max(1, len(manifest["keyframes"])),
            )
    print("Generated offline storyboard placeholders for missing subjects/keyframes.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare subject consistency sheets and scene first-frame keyframes.")
    parser.add_argument("--script", required=True, help="Path to script.json")
    parser.add_argument(
        "--mode",
        choices=["manifest", "gemini_api", "placeholder"],
        default="manifest",
        help="manifest: emit tasks for Antigravity image-generator; gemini_api: call Gemini Image API; placeholder: offline cards",
    )
    parser.add_argument("--model", default="gemini-2.5-flash-image-preview", help="Gemini image model for gemini_api mode")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--force", action="store_true", help="Regenerate even if files exist")
    args = parser.parse_args()

    load_dotenv(Path.cwd())

    script_path = Path(args.script).resolve()
    manifest = build_manifest(script_path)

    if args.mode == "gemini_api":
        run_gemini_generation(manifest, force=args.force, concurrency=args.concurrency, model=args.model)
        manifest = build_manifest(script_path)
    elif args.mode == "placeholder":
        run_placeholder_generation(manifest, force=args.force)
        manifest = build_manifest(script_path)

    print(
        json.dumps(
            {
                "manifest_path": str(script_path.parent / "work" / "subject_manifest.json"),
                "total_subjects": len(manifest["subjects"]),
                "missing_subjects": manifest["missing_subjects"],
                "total_keyframes": len(manifest["keyframes"]),
                "missing_keyframes": manifest["missing_keyframes"],
                "warnings": manifest["warnings"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
