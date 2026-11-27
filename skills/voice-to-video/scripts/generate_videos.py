#!/usr/bin/env python3
"""Concurrent multi-engine AI video orchestrator (Google-first priority).

Priority order in `auto` mode:
  1. google_veo_gemini  -> Official Gemini API Veo 3.1 (:predictLongRunning + up to 3 referenceImages)
  2. google_veo_vertex  -> Official Vertex AI Veo 3.1 (gcloud auth)
  3. google_flow        -> Exports batch queue for Google Flow Ultra (10,000 monthly credits)
  4. volcengine_seedance / kling / runway -> Optional backup REST providers
  5. kenburns           -> Zero-cost cinematic Ken Burns animation from locked first-frame keyframes

Features:
  - ThreadPoolExecutor concurrent dispatch & async job polling
  - Thread-safe checkpointing (`work/video_jobs.json`) for zero-waste resume
  - Pre-flight cost & credit estimator (`--estimate-only`)
  - Single-scene regeneration (`--scenes 02,05 --force`) for fast boss revisions
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from check_env import detect_gcloud_auth, load_dotenv

STATE_LOCK = threading.Lock()

# Approximate reference pricing (used for pre-flight budget estimation)
VEO_API_PRICE_PER_SEC_NO_AUDIO = {"lite": 0.04, "fast": 0.10, "quality": 0.20}
VEO_API_PRICE_PER_SEC_AUDIO = {"lite": 0.07, "fast": 0.20, "quality": 0.40}
FLOW_ULTRA_CREDITS_PER_CLIP = {"lite": 5, "fast": 10, "quality": 100}


def encode_file_b64(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
    return base64.b64encode(path.read_bytes()).decode("ascii"), mime


def http_json(url: str, headers: dict[str, str], payload: dict | None = None, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} from {url}: {err_body[:500]}") from e


def download_binary(url: str, headers: dict[str, str], dest: Path, timeout: int = 180) -> None:
    req = urllib.request.Request(url, headers=headers, method="GET")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as fp:
        shutil.copyfileobj(resp, fp)


def resolve_provider(requested: str) -> str:
    req = requested.strip().lower()
    if req and req != "auto":
        return req
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "google_veo_gemini"
    if os.environ.get("GOOGLE_CLOUD_PROJECT") and detect_gcloud_auth():
        return "google_veo_vertex"
    if os.environ.get("VOLCENGINE_API_KEY"):
        return "volcengine_seedance"
    if os.environ.get("RUNWAYML_API_SECRET"):
        return "runway"
    return "google_flow"


def select_veo_model(tier: str) -> str:
    t = tier.lower()
    if t == "lite":
        return os.environ.get("VEO_MODEL_LITE", "veo-3.1-lite-generate-preview")
    if t == "quality":
        return os.environ.get("VEO_MODEL_QUALITY", "veo-3.1-generate-preview")
    return os.environ.get("VEO_MODEL_FAST", "veo-3.1-fast-generate-preview")


def build_scene_prompt(scene: dict, style_bible: str) -> str:
    visual = scene.get("visual", {})
    parts = [
        str(visual.get("video_prompt") or visual.get("image_prompt") or scene.get("narration", "")).strip(),
        f"Camera movement: {visual['camera']}." if visual.get("camera") else "",
        f"Style: {style_bible}." if style_bible else "",
        "Smooth natural cinematic motion, no distorted text, no watermarks, no embedded subtitles.",
    ]
    return " ".join(p for p in parts if p)


def collect_reference_images(scene: dict, subjects_map: dict[str, Path], project_dir: Path) -> list[Path]:
    visual = scene.get("visual", {})
    refs: list[Path] = []
    for sid in list(visual.get("subjects", []))[:3]:
        p = subjects_map.get(sid)
        if p and p.exists():
            refs.append(p)
    return refs


def extract_veo_video_bytes_or_uri(op_response: dict) -> tuple[bytes | None, str | None]:
    resp = op_response.get("response", {})
    # Gemini API structure: response.generateVideoResponse.generatedSamples[0].video.uri
    gvr = resp.get("generateVideoResponse", {})
    samples = gvr.get("generatedSamples", [])
    if samples:
        vid = samples[0].get("video", {})
        if vid.get("bytesBase64Encoded"):
            return base64.b64decode(vid["bytesBase64Encoded"]), None
        if vid.get("uri"):
            return None, str(vid["uri"])
    # Vertex AI structure: response.videos[0]
    videos = resp.get("videos", [])
    if videos:
        v0 = videos[0]
        if v0.get("bytesBase64Encoded"):
            return base64.b64decode(v0["bytesBase64Encoded"]), None
        if v0.get("gcsUri"):
            return None, str(v0["gcsUri"])
    return None, None


def generate_via_google_veo(
    scene: dict,
    out_path: Path,
    project_dir: Path,
    subjects_map: dict[str, Path],
    style_bible: str,
    aspect_ratio: str,
    prod_cfg: dict,
    use_vertex: bool = False,
    poll_interval: int = 8,
    max_wait_sec: int = 420,
) -> dict:
    visual = scene.get("visual", {})
    tier = str(visual.get("tier") or prod_cfg.get("veo_tier", "fast")).lower()
    model = select_veo_model(tier)
    resolution = str(prod_cfg.get("resolution", "720p"))
    dur_raw = float(scene.get("duration", 6.0))
    # Veo 3.1 typically supports 4, 6, or 8 second clips; snap cleanly
    clip_sec = 8 if dur_raw > 6.2 else (6 if dur_raw > 4.2 else 4)
    prompt = build_scene_prompt(scene, style_bible)

    instance: dict = {"prompt": prompt}

    # Optional first-frame image-to-video conditioning
    kf_rel = str(visual.get("first_frame", "")).strip()
    kf_path = (project_dir / kf_rel) if kf_rel else None
    refs = collect_reference_images(scene, subjects_map, project_dir)

    # Veo 3.1 rule: attach up to 3 subject referenceImages for character/prop consistency
    # If referenceImages are present and aspect is 16:9, attach referenceImages; else attach first-frame image.
    if refs and aspect_ratio == "16:9":
        instance["referenceImages"] = []
        for rp in refs[:3]:
            b64, mime = encode_file_b64(rp)
            instance["referenceImages"].append(
                {
                    "referenceType": "asset",
                    "image": {"bytesBase64Encoded": b64, "mimeType": mime},
                }
            )
    elif kf_path and kf_path.exists():
        b64, mime = encode_file_b64(kf_path)
        instance["image"] = {"bytesBase64Encoded": b64, "mimeType": mime}

    params: dict = {
        "sampleCount": 1,
        "resolution": resolution,
        "aspectRatio": aspect_ratio,
        "durationSeconds": clip_sec,
    }
    if use_vertex:
        params["personGeneration"] = "allow_all"

    payload = {"instances": [instance], "parameters": params}

    if use_vertex:
        project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base = f"https://{location}-aiplatform.googleapis.com/v1"
        submit_url = f"{base}/projects/{project_id}/locations/{location}/publishers/google/models/{model}:predictLongRunning"
        op = http_json(submit_url, headers=headers, payload=payload)
        op_name = op["name"]
        poll_url = f"{base}/projects/{project_id}/locations/{location}/publishers/google/models/{model}:fetchPredictOperation"
        deadline = time.time() + max_wait_sec
        while time.time() < deadline:
            status = http_json(poll_url, headers=headers, payload={"operationName": op_name})
            if status.get("done"):
                if status.get("error"):
                    raise RuntimeError(f"Vertex Veo failed: {status['error']}")
                raw_bytes, uri = extract_veo_video_bytes_or_uri(status)
                if raw_bytes:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(raw_bytes)
                    return {"provider": "google_veo_vertex", "model": model, "duration_requested": clip_sec}
                if uri and uri.startswith("gs://"):
                    subprocess.run(["gsutil", "cp", uri, str(out_path)], check=True)
                    return {"provider": "google_veo_vertex", "model": model, "duration_requested": clip_sec}
                raise RuntimeError(f"Vertex Veo completed without downloadable video: {status}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Vertex Veo timed out after {max_wait_sec}s (op={op_name})")
    else:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        base = "https://generativelanguage.googleapis.com/v1beta"
        submit_url = f"{base}/models/{model}:predictLongRunning"
        op = http_json(submit_url, headers=headers, payload=payload)
        op_name = op["name"]
        poll_url = f"{base}/{op_name}"
        deadline = time.time() + max_wait_sec
        while time.time() < deadline:
            status = http_json(poll_url, headers={"x-goog-api-key": api_key})
            if status.get("done"):
                if status.get("error"):
                    raise RuntimeError(f"Gemini Veo failed: {status['error']}")
                raw_bytes, uri = extract_veo_video_bytes_or_uri(status)
                if raw_bytes:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(raw_bytes)
                    return {"provider": "google_veo_gemini", "model": model, "duration_requested": clip_sec}
                if uri:
                    download_binary(uri, headers={"x-goog-api-key": api_key}, dest=out_path)
                    return {"provider": "google_veo_gemini", "model": model, "duration_requested": clip_sec}
                raise RuntimeError(f"Gemini Veo completed without video URI: {status}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Gemini Veo timed out after {max_wait_sec}s (op={op_name})")


def generate_via_volcengine_seedance(
    scene: dict,
    out_path: Path,
    project_dir: Path,
    style_bible: str,
    aspect_ratio: str,
    poll_interval: int = 8,
    max_wait_sec: int = 420,
) -> dict:
    """Optional backup adapter for Volcengine Ark / Jimeng Seedance Video API."""
    api_key = os.environ["VOLCENGINE_API_KEY"]
    base_url = os.environ.get("VOLCENGINE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
    model = os.environ.get("VOLCENGINE_SEEDANCE_MODEL", "doubao-seedance-1-0-pro-250528")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    visual = scene.get("visual", {})
    prompt = build_scene_prompt(scene, style_bible)
    content: list[dict] = [{"type": "text", "text": f"{prompt} --ratio {aspect_ratio}"}]
    kf_rel = str(visual.get("first_frame", "")).strip()
    kf_path = (project_dir / kf_rel) if kf_rel else None
    if kf_path and kf_path.exists():
        b64, mime = encode_file_b64(kf_path)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    created = http_json(f"{base_url}/contents/generations/tasks", headers=headers, payload={"model": model, "content": content})
    task_id = created["id"]
    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        st = http_json(f"{base_url}/contents/generations/tasks/{task_id}", headers=headers)
        state = str(st.get("status", "")).lower()
        if state in ("succeeded", "completed"):
            video_url = st.get("content", {}).get("video_url") or st.get("output", {}).get("video_url")
            if not video_url:
                raise RuntimeError(f"Seedance task {task_id} succeeded without video_url: {st}")
            download_binary(video_url, headers={}, dest=out_path)
            return {"provider": "volcengine_seedance", "model": model, "task_id": task_id}
        if state in ("failed", "canceled", "cancelled"):
            raise RuntimeError(f"Seedance task {task_id} failed: {st}")
        time.sleep(poll_interval)
    raise TimeoutError(f"Seedance task {task_id} timed out")


def generate_via_kenburns_fallback(
    scene: dict,
    out_path: Path,
    project_dir: Path,
    aspect_ratio: str,
    fps: int = 24,
) -> dict:
    """Zero-cost local fallback: smooth cinema Ken Burns camera motion from first-frame keyframe."""
    visual = scene.get("visual", {})
    kf_rel = str(visual.get("first_frame", "")).strip()
    kf_path = (project_dir / kf_rel) if kf_rel else None
    if not kf_path or not kf_path.exists():
        raise FileNotFoundError(
            f"Scene {scene.get('id')} missing first_frame '{kf_rel}'. Run prepare_subjects.py first."
        )

    size_map = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
    w, h = size_map.get(aspect_ratio, (1920, 1080))
    dur = max(3.0, float(scene.get("duration", 5.5)))
    frames = max(1, int(round(dur * fps)))

    # Alternate subtle dolly-in / subtle pan motion across scenes for natural film pacing
    sid_num = int("".join(ch for ch in str(scene.get("id", "1")) if ch.isdigit()) or "1")
    if sid_num % 2 == 1:
        zoom_expr = "min(zoom+0.00055,1.08)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        zoom_expr = "if(eq(on,1),1.08,max(zoom-0.00055,1.0))"
        x_expr = "iw/2-(iw/zoom/2)+on*0.25"
        y_expr = "ih/2-(ih/zoom/2)"

    vf = (
        f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
        f"crop={w*2}:{h*2},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={w}x{h}:fps={fps},"
        f"format=yuv420p"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(kf_path),
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
            "-an",
            str(out_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    return {"provider": "kenburns_fallback", "source_keyframe": kf_rel, "duration": dur}


def export_google_flow_queue(script_path: Path, data: dict, subjects_map: dict[str, Path]) -> dict:
    """Export structured queue for Google Flow Ultra (10,000 monthly credits, half-price Veo Fast/Lite)."""
    project_dir = script_path.parent
    style_bible = str(data.get("style_bible", ""))
    prod_cfg = data.get("production", {})
    default_tier = str(prod_cfg.get("veo_tier", "fast")).lower()

    items: list[dict] = []
    md_lines = [
        f"# Google Flow (Ultra 积分池) 批量生成任务清单 — {data.get('title', '')}",
        "",
        "将下列镜头依次提交至 **Google Flow (`https://flow.google.com`)**（可由 Antigravity `browser` 子智能体在已登录的 Google AI Ultra 账号中辅助执行），下载成片后保存到对应目标路径，再运行 `build_video.py` 一键合片。",
        "",
    ]
    total_credits = 0
    for idx, sc in enumerate(data.get("scenes", []), start=1):
        visual = sc.get("visual", {})
        if visual.get("type") != "ai_video":
            continue
        sid = str(sc.get("id", f"{idx:02d}"))
        tier = str(visual.get("tier") or default_tier).lower()
        credits = FLOW_ULTRA_CREDITS_PER_CLIP.get(tier, 10)
        total_credits += credits
        out_rel = str(visual.get("generated_video") or f"work/generated_videos/scene_{sid}.mp4")
        refs = [str(p) for p in collect_reference_images(sc, subjects_map, project_dir)]
        prompt = build_scene_prompt(sc, style_bible)
        item = {
            "scene_id": sid,
            "tier": tier,
            "estimated_ultra_credits": credits,
            "reference_images": refs,
            "first_frame": str(project_dir / visual["first_frame"]) if visual.get("first_frame") else "",
            "prompt": prompt,
            "target_video_path": str(project_dir / out_rel),
            "already_exists": (project_dir / out_rel).exists(),
        }
        items.append(item)
        md_lines.extend(
            [
                f"## 镜头 {sid} ({sc.get('label', '')}) — 推荐档位: `Veo {tier.upper()}` (~{credits} Ultra 积分)",
                f"- **目标保存路径**: `{out_rel}`",
                f"- **参考主体图**: {', '.join(refs) if refs else '无'}",
                f"- **视频提示词**:",
                f"  > {prompt}",
                "",
            ]
        )

    queue_json = project_dir / "work" / "google_flow_queue.json"
    queue_md = project_dir / "work" / "google_flow_prompts.md"
    queue_json.parent.mkdir(parents=True, exist_ok=True)
    queue_json.write_text(json.dumps({"total_ultra_credits_est": total_credits, "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    queue_md.write_text("\n".join(md_lines), encoding="utf-8")
    return {"queue_json": str(queue_json), "queue_md": str(queue_md), "total_ultra_credits_est": total_credits, "clip_count": len(items)}


def estimate_cost(data: dict) -> dict:
    prod = data.get("production", {})
    default_tier = str(prod.get("veo_tier", "fast")).lower()
    with_audio = bool(prod.get("generate_audio", False))
    out_res = str(data.get("output_resolution") or prod.get("output_resolution") or "1080p").lower()
    price_table = VEO_API_PRICE_PER_SEC_AUDIO if with_audio else VEO_API_PRICE_PER_SEC_NO_AUDIO

    clips = 0
    total_sec = 0.0
    api_usd = 0.0
    flow_ultra_credits = 0
    for sc in data.get("scenes", []):
        v = sc.get("visual", {})
        if v.get("type") != "ai_video":
            continue
        clips += 1
        dur = float(sc.get("duration", 6.0))
        clip_sec = 8 if dur > 6.2 else (6 if dur > 4.2 else 4)
        tier = str(v.get("tier") or default_tier).lower()
        total_sec += clip_sec
        api_usd += clip_sec * price_table.get(tier, 0.10)
        flow_ultra_credits += FLOW_ULTRA_CREDITS_PER_CLIP.get(tier, 10)

    flow_4k_upscale_extra = clips * 50
    return {
        "ai_video_scenes": clips,
        "estimated_generated_seconds": total_sec,
        "target_output_resolution": out_res,
        "audio_enabled_in_video_model": with_audio,
        "google_flow_ultra_credits_est": {
            "single_pass": flow_ultra_credits,
            "1080p_free_upscale_single_pass": flow_ultra_credits,
            "1080p_with_1_5x_retries": int(round(flow_ultra_credits * 1.5)),
            "4k_upscale_extra": flow_4k_upscale_extra,
            "4k_total_single_pass": flow_ultra_credits + flow_4k_upscale_extra,
            "pct_of_10000_monthly_ultra_1080p": round(flow_ultra_credits / 10000 * 100, 2),
            "pct_of_10000_monthly_ultra_4k": round((flow_ultra_credits + flow_4k_upscale_extra) / 10000 * 100, 2),
        },
        "google_veo_api_usd_est": {
            "single_pass": round(api_usd, 2),
            "with_1_5x_retries": round(api_usd * 1.5, 2),
        },
    }


def save_job_state(state_path: Path, state: dict) -> None:
    with STATE_LOCK:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrent AI video generator (Google-first).")
    parser.add_argument("--script", required=True, help="Path to script.json")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "google_veo_gemini", "google_veo_vertex", "google_flow", "volcengine_seedance", "kenburns"],
    )
    parser.add_argument("--concurrency", type=int, default=0, help="Override MAX_CONCURRENCY (default from script/env or 4)")
    parser.add_argument("--retries", type=int, default=2, help="Max retries per failed scene")
    parser.add_argument("--scenes", default="", help="Comma-separated scene IDs to process (e.g. '01,03')")
    parser.add_argument("--force", action="store_true", help="Regenerate even if target MP4 already exists")
    parser.add_argument("--fallback-kenburns", action="store_true", help="If no live API key, render Ken Burns preview clips")
    parser.add_argument("--estimate-only", action="store_true", help="Print cost & Ultra credit estimate without generating")
    args = parser.parse_args()

    load_dotenv(Path.cwd())

    script_path = Path(args.script).resolve()
    project_dir = script_path.parent
    data = json.loads(script_path.read_text(encoding="utf-8"))
    prod_cfg = data.get("production", {})
    style_bible = str(data.get("style_bible", ""))
    aspect_ratio = str(data.get("aspect_ratio", "16:9"))
    fps = int(data.get("fps", 24))

    est = estimate_cost(data)
    if args.estimate_only:
        print(json.dumps(est, ensure_ascii=False, indent=2))
        return 0

    provider_req = args.provider if args.provider != "auto" else str(prod_cfg.get("video_provider") or os.environ.get("GOOGLE_VIDEO_BACKEND", "auto"))
    provider = resolve_provider(provider_req)
    if provider == "google_flow" and args.fallback_kenburns:
        provider = "kenburns"

    subjects_map: dict[str, Path] = {}
    for sub in data.get("subjects", []):
        rel = str(sub.get("reference_image") or f"assets/subjects/{sub['id']}.png")
        subjects_map[str(sub["id"])] = project_dir / rel

    # Always export Google Flow queue if provider is google_flow
    if provider == "google_flow":
        info = export_google_flow_queue(script_path, data, subjects_map)
        print(
            json.dumps(
                {
                    "provider": "google_flow",
                    "status": "queue_exported",
                    "note": "未检测到 GEMINI_API_KEY / Vertex 凭据，已导出 Google Flow (Ultra 10,000 积分池) 批量任务清单。也可加 --fallback-kenburns 先行离线预览，或在 .env 填入 GEMINI_API_KEY 走全自动并发 API。",
                    **info,
                    "estimate": est,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    only_ids = {s.strip() for s in args.scenes.split(",") if s.strip()}
    concurrency = args.concurrency or int(prod_cfg.get("max_concurrency") or os.environ.get("MAX_CONCURRENCY", "4"))

    state_path = project_dir / "work" / "video_jobs.json"
    job_state: dict = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"scenes": {}}

    tasks: list[tuple[dict, Path, str]] = []
    for idx, sc in enumerate(data.get("scenes", []), start=1):
        v = sc.get("visual", {})
        if v.get("type") != "ai_video":
            continue
        sid = str(sc.get("id", f"{idx:02d}"))
        if only_ids and sid not in only_ids:
            continue
        out_rel = str(v.get("generated_video") or f"work/generated_videos/scene_{sid}.mp4")
        v["generated_video"] = out_rel
        out_path = project_dir / out_rel
        if out_path.exists() and not args.force:
            job_state["scenes"][sid] = {"status": "cached", "path": out_rel}
            continue
        tasks.append((sc, out_path, sid))

    print(f"[Video Engine] Provider={provider} | Concurrency={concurrency} | Pending={len(tasks)} | Est={est['google_veo_api_usd_est']['single_pass']} USD / {est['google_flow_ultra_credits_est']['single_pass']} Flow credits")

    def worker(sc: dict, out_path: Path, sid: str) -> dict:
        last_err: Exception | None = None
        for attempt in range(1, args.retries + 2):
            try:
                job_state["scenes"][sid] = {"status": "running", "attempt": attempt, "provider": provider}
                save_job_state(state_path, job_state)
                if provider == "google_veo_gemini":
                    meta = generate_via_google_veo(sc, out_path, project_dir, subjects_map, style_bible, aspect_ratio, prod_cfg, use_vertex=False)
                elif provider == "google_veo_vertex":
                    meta = generate_via_google_veo(sc, out_path, project_dir, subjects_map, style_bible, aspect_ratio, prod_cfg, use_vertex=True)
                elif provider == "volcengine_seedance":
                    meta = generate_via_volcengine_seedance(sc, out_path, project_dir, style_bible, aspect_ratio)
                elif provider == "kenburns":
                    meta = generate_via_kenburns_fallback(sc, out_path, project_dir, aspect_ratio, fps=fps)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
                job_state["scenes"][sid] = {"status": "done", "path": str(out_path.relative_to(project_dir)), **meta}
                save_job_state(state_path, job_state)
                return {"scene_id": sid, "ok": True, **meta}
            except Exception as exc:
                last_err = exc
                if attempt <= args.retries:
                    time.sleep(min(20, 3 * attempt))
        job_state["scenes"][sid] = {"status": "failed", "error": str(last_err)}
        save_job_state(state_path, job_state)
        return {"scene_id": sid, "ok": False, "error": str(last_err)}

    results: list[dict] = []
    if tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = [pool.submit(worker, sc, out_p, sid) for sc, out_p, sid in tasks]
            for fut in concurrent.futures.as_completed(futs):
                res = fut.result()
                results.append(res)
                tag = "✓" if res["ok"] else "✗"
                print(f"  {tag} Scene {res['scene_id']}: {'done' if res['ok'] else res.get('error')}")

    # Persist updated generated_video paths back into script.json
    script_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save_job_state(state_path, job_state)

    failed = [r for r in results if not r["ok"]]
    if failed:
        print(f"Completed with {len(failed)} failed scene(s). See {state_path}", file=sys.stderr)
        return 1
    print(f"All requested video scenes ready. State saved to {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
