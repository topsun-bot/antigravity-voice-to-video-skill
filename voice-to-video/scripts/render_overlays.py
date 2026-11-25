#!/usr/bin/env python3
"""Cinematic overlay renderer (chapter badges, rounded subtitle pills, cinema outro cards)."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from render_slide_card import load_font, wrap_text


def render_chapter_badge(
    output_path: Path,
    text: str,
    width: int = 1920,
    height: int = 1080,
    accent_rgb: tuple[int, int, int] = (56, 189, 248),
) -> Path:
    """Render a sleek top-left frosted translucent chapter badge (e.g. PART 01 · 清晨唤醒)."""
    scale = min(width, height) / 1080.0
    font_size = max(18, int(24 * scale))
    font = load_font(font_size, bold=True)

    dummy = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    dot_r = max(4, int(5 * scale))
    pad_l = int(20 * scale)
    pad_r = int(22 * scale)
    pad_y = int(12 * scale)
    gap = int(12 * scale)

    box_w = pad_l + dot_r * 2 + gap + tw + pad_r
    box_h = th + pad_y * 2

    # 2x supersampling for crisp anti-aliased rounded corners
    ss = 2
    img = Image.new("RGBA", (box_w * ss, box_h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = (box_h * ss) // 2
    d.rounded_rectangle(
        (0, 0, box_w * ss - 1, box_h * ss - 1),
        radius=radius,
        fill=(12, 16, 24, 155),
        outline=(255, 255, 255, 55),
        width=max(1, int(1.5 * scale * ss)),
    )

    # Accent dot
    cx = (pad_l + dot_r) * ss
    cy = (box_h // 2) * ss
    r_ss = dot_r * ss
    d.ellipse((cx - r_ss, cy - r_ss, cx + r_ss, cy + r_ss), fill=(*accent_rgb, 240))

    # Draw text at 1x after downsampling shape for sharpest font hinting
    img = img.resize((box_w, box_h), Image.Resampling.LANCZOS)
    d1 = ImageDraw.Draw(img)
    tx = pad_l + dot_r * 2 + gap - bb[0]
    ty = (box_h - th) // 2 - bb[1]
    d1.text((tx, ty), text, font=font, fill=(241, 245, 249, 245))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def render_subtitle_pill(
    output_path: Path,
    text: str,
    video_width: int = 1920,
    video_height: int = 1080,
    font_size: int | None = None,
) -> Path:
    """Render a cinema-style rounded translucent dark pill subtitle bar (matching reference video)."""
    scale = min(video_width, video_height) / 1080.0
    fs = font_size if font_size else max(24, int((40 if video_width >= video_height else 46) * scale))
    font = load_font(fs, bold=False)

    max_text_w = int(video_width * 0.82)
    dummy = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    lines = wrap_text(draw, text.strip(), font, max_text_w)[:2]
    if not lines:
        lines = [""]

    bboxes = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
    line_widths = [bb[2] - bb[0] for bb in bboxes]
    line_heights = [bb[3] - bb[1] for bb in bboxes]
    max_lw = max(line_widths) if line_widths else 10
    line_gap = int(fs * 0.34)
    total_th = sum(line_heights) + line_gap * max(0, len(lines) - 1)

    pad_x = int(34 * scale)
    pad_y = int(16 * scale)
    box_w = max_lw + pad_x * 2
    box_h = total_th + pad_y * 2

    # 2x supersampled rounded translucent pill
    ss = 2
    img = Image.new("RGBA", (box_w * ss, box_h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(min(18 * scale, box_h * 0.38) * ss)
    d.rounded_rectangle(
        (0, 0, box_w * ss - 1, box_h * ss - 1),
        radius=radius,
        fill=(14, 18, 26, 188),
        outline=(255, 255, 255, 26),
        width=max(1, int(1 * scale * ss)),
    )
    img = img.resize((box_w, box_h), Image.Resampling.LANCZOS)

    d1 = ImageDraw.Draw(img)
    cur_y = pad_y
    for ln, bb, lw, lh in zip(lines, bboxes, line_widths, line_heights):
        tx = (box_w - lw) // 2 - bb[0]
        ty = cur_y - bb[1]
        d1.text((tx, ty), ln, font=font, fill=(248, 250, 252, 255))
        cur_y += lh + line_gap

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def render_cinema_outro(
    output_path: Path,
    title: str,
    subtitle: str = "",
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """Render a minimal dark radial-gradient cinema outro card (e.g. 未来呼啸而来·2028)."""
    img = Image.new("RGB", (width, height), (14, 17, 23))
    px = img.load()
    cx, cy = width * 0.5, height * 0.48
    max_r = math.hypot(width * 0.65, height * 0.65)

    # Smooth subtle radial spotlight gradient (computed on downscaled grid for speed)
    small_w, small_h = 320, max(180, int(320 * height / width))
    bg = Image.new("RGB", (small_w, small_h))
    bpx = bg.load()
    scx, scy = small_w * 0.5, small_h * 0.48
    smax = math.hypot(small_w * 0.65, small_h * 0.65)
    for y in range(small_h):
        for x in range(small_w):
            t = min(1.0, math.hypot(x - scx, y - scy) / smax)
            # Center slate-blue charcoal -> deep dark vignette edges
            r = int(34 * (1 - t) + 12 * t)
            g = int(41 * (1 - t) + 15 * t)
            b = int(50 * (1 - t) + 20 * t)
            bpx[x, y] = (r, g, b)
    img = bg.resize((width, height), Image.Resampling.BICUBIC)

    draw = ImageDraw.Draw(img)
    scale = min(width, height) / 1080.0
    font_title = load_font(max(44, int(92 * scale)), bold=True)
    font_sub = load_font(max(24, int(38 * scale)), bold=False)

    tbb = draw.textbbox((0, 0), title, font=font_title)
    tw, th = tbb[2] - tbb[0], tbb[3] - tbb[1]

    if subtitle:
        sbb = draw.textbbox((0, 0), subtitle, font=font_sub)
        sw, sh = sbb[2] - sbb[0], sbb[3] - sbb[1]
        gap = int(42 * scale)
        total_h = th + gap + sh
        top_y = (height - total_h) // 2
        draw.text(
            ((width - tw) // 2 - tbb[0], top_y - tbb[1]),
            title,
            font=font_title,
            fill=(245, 247, 250),
        )
        draw.text(
            ((width - sw) // 2 - sbb[0], top_y + th + gap - sbb[1]),
            subtitle,
            font=font_sub,
            fill=(203, 213, 225),
        )
    else:
        draw.text(
            ((width - tw) // 2 - tbb[0], (height - th) // 2 - tbb[1]),
            title,
            font=font_title,
            fill=(245, 247, 250),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
