#!/usr/bin/env python3
"""Render clean high-resolution Chinese/English storyboard cards via Pillow."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def find_cjk_font(bold: bool = True) -> str:
    bold_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
    ]
    reg_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for path in (bold_candidates if bold else reg_candidates):
        if Path(path).exists():
            return path
    try:
        out = subprocess.check_output(
            ["fc-list", ":lang=zh", "file"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            p = line.split(":")[0].strip()
            if p and Path(p).exists():
                return p
    except Exception:
        pass
    return ""


def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = find_cjk_font(bold=bold)
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def hex_to_rgb(hex_color: str, default: tuple[int, int, int] = (56, 189, 248)) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 6:
        try:
            return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            pass
    return default


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph:
            lines.append("")
            continue
        cur = ""
        for ch in paragraph:
            test = cur + ch
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def render_card(
    output_path: Path,
    width: int,
    height: int,
    theme: str,
    accent: str,
    badge: str,
    title: str,
    subtitle: str,
    bullets: list[str],
    scene_index: int,
    total_scenes: int,
) -> None:
    is_dark = theme != "light"
    bg_top = (10, 15, 30) if is_dark else (248, 250, 252)
    bg_bot = (20, 30, 54) if is_dark else (226, 232, 240)
    fg_main = (248, 250, 252) if is_dark else (15, 23, 42)
    fg_sub = (148, 163, 184) if is_dark else (71, 85, 105)
    card_bg = (26, 37, 64) if is_dark else (255, 255, 255)
    card_border = (51, 65, 98) if is_dark else (203, 213, 225)
    acc_rgb = hex_to_rgb(accent)

    img = Image.new("RGB", (width, height), bg_top)
    draw = ImageDraw.Draw(img)

    # Vertical background gradient
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(bg_top[0] + (bg_bot[0] - bg_top[0]) * t)
        g = int(bg_top[1] + (bg_bot[1] - bg_top[1]) * t)
        b = int(bg_top[2] + (bg_bot[2] - bg_top[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Subtle decorative glow circle top-right
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    rad = int(min(width, height) * 0.45)
    gdraw.ellipse(
        (width - rad, -rad // 2, width + rad // 2, rad),
        fill=(acc_rgb[0], acc_rgb[1], acc_rgb[2], 32 if is_dark else 24),
    )
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    is_vertical = height > width
    pad_x = int(width * (0.08 if not is_vertical else 0.09))
    pad_top = int(height * (0.11 if not is_vertical else 0.14))
    content_w = width - pad_x * 2

    # Fonts scaled to resolution
    scale = min(width, height) / 1080.0
    font_badge = load_font(max(20, int(26 * scale)), bold=True)
    font_title = load_font(max(40, int((76 if not is_vertical else 68) * scale)), bold=True)
    font_sub = load_font(max(26, int(36 * scale)), bold=False)
    font_bullet = load_font(max(24, int(34 * scale)), bold=False)

    y = pad_top

    # Scene badge pill
    if badge:
        badge_text = f"{badge.upper()}"
        bb = draw.textbbox((0, 0), badge_text, font=font_badge)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        bw = tw + int(44 * scale)
        bh = th + int(24 * scale)
        draw.rounded_rectangle(
            (pad_x, y, pad_x + bw, y + bh),
            radius=int(bh / 2),
            fill=acc_rgb,
        )
        badge_fg = (10, 15, 30) if sum(acc_rgb) > 360 else (255, 255, 255)
        tx = pad_x + (bw - tw) // 2 - bb[0]
        ty = y + (bh - th) // 2 - bb[1]
        draw.text((tx, ty), badge_text, font=font_badge, fill=badge_fg)
        y += bh + int(34 * scale)

    # Left accent bar + title
    title_lines = wrap_text(draw, title, font_title, content_w - int(28 * scale))
    line_h_title = int(font_title.size * 1.24) if hasattr(font_title, "size") else 80
    bar_h = max(line_h_title, len(title_lines) * line_h_title)
    draw.rounded_rectangle(
        (pad_x, y + int(8 * scale), pad_x + int(10 * scale), y + bar_h - int(6 * scale)),
        radius=5,
        fill=acc_rgb,
    )
    for line in title_lines:
        draw.text((pad_x + int(30 * scale), y), line, font=font_title, fill=fg_main)
        y += line_h_title

    y += int(16 * scale)

    # Subtitle
    if subtitle:
        sub_lines = wrap_text(draw, subtitle, font_sub, content_w)
        line_h_sub = int(font_sub.size * 1.38) if hasattr(font_sub, "size") else 46
        for line in sub_lines:
            draw.text((pad_x + int(30 * scale), y), line, font=font_sub, fill=fg_sub)
            y += line_h_sub
        y += int(30 * scale)

    # Bullet container card
    if bullets:
        box_top = y
        box_pad_x = int(38 * scale)
        box_pad_y = int(30 * scale)
        line_h_b = int(font_bullet.size * 1.42) if hasattr(font_bullet, "size") else 46
        rendered_bullets: list[list[str]] = []
        total_lines = 0
        for b in bullets:
            wrapped = wrap_text(draw, b, font_bullet, content_w - box_pad_x * 2 - int(40 * scale))
            rendered_bullets.append(wrapped)
            total_lines += len(wrapped)

        box_h = box_pad_y * 2 + total_lines * line_h_b + max(0, len(bullets) - 1) * int(18 * scale)
        # Keep safe bottom margin for subtitles
        safe_bottom = height - int(height * (0.18 if not is_vertical else 0.22))
        box_bottom = min(box_top + box_h, safe_bottom)

        draw.rounded_rectangle(
            (pad_x, box_top, pad_x + content_w, box_bottom),
            radius=int(24 * scale),
            fill=card_bg,
            outline=card_border,
            width=2,
        )

        by = box_top + box_pad_y
        for wrapped in rendered_bullets:
            if by + line_h_b > box_bottom - int(10 * scale):
                break
            dot_r = int(8 * scale)
            dot_cy = by + int(line_h_b * 0.45)
            draw.ellipse(
                (pad_x + box_pad_x, dot_cy - dot_r, pad_x + box_pad_x + dot_r * 2, dot_cy + dot_r),
                fill=acc_rgb,
            )
            for idx_l, line in enumerate(wrapped):
                if by + line_h_b > box_bottom - int(8 * scale):
                    break
                draw.text(
                    (pad_x + box_pad_x + int(34 * scale), by),
                    line,
                    font=font_bullet,
                    fill=fg_main if idx_l == 0 else fg_sub,
                )
                by += line_h_b
            by += int(16 * scale)

    # Top progress bar
    if total_scenes > 0:
        progress_w = int(width * (scene_index / total_scenes))
        draw.rectangle((0, 0, width, max(6, int(8 * scale))), fill=card_border)
        draw.rectangle((0, 0, progress_w, max(6, int(8 * scale))), fill=acc_rgb)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a storyboard slide card PNG.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--theme", default="dark")
    parser.add_argument("--accent", default="#38BDF8")
    parser.add_argument("--badge", default="")
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--bullets-json", default="[]")
    parser.add_argument("--scene-index", type=int, default=1)
    parser.add_argument("--total-scenes", type=int, default=1)
    args = parser.parse_args()

    render_card(
        output_path=Path(args.output),
        width=args.width,
        height=args.height,
        theme=args.theme,
        accent=args.accent,
        badge=args.badge,
        title=args.title,
        subtitle=args.subtitle,
        bullets=json.loads(args.bullets_json),
        scene_index=args.scene_index,
        total_scenes=args.total_scenes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
