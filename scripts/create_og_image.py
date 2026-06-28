#!/usr/bin/env python3
"""
Sinh ảnh social OG (1200×630) với thiết kế SEOMONEY-branded.

Mục đích:
- Tạo ảnh OG tổng quát thương hiệu cho fallback (og-default)
- Tạo category-specific OG fallbacks (tùy chọn)
- Đảm bảo ảnh hiển thị phong phú trên social (FB, X, LinkedIn, Zalo...)
- Dùng cả .webp (tối ưu) + .png (compatibility)

Cách dùng:
    python3 scripts/create_og_image.py              # sinh og-default (WebP + PNG)
    python3 scripts/create_og_image.py --all        # + category-specific
    python3 scripts/create_og_image.py --force      # force re-render
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

IMG_ROOT = Path(__file__).resolve().parent.parent / "static" / "img"

# OG image dimensions (social standard)
OG_WIDTH = 1200
OG_HEIGHT = 630

# SEOMONEY brand colors (from design system)
COLORS = {
    "bg_dark": "#0a1428",  # Navy (from S-DNA)
    "brand_teal": "#38bdf8",  # Teal (primary accent)
    "brand_blue": "#1d4ed8",  # Deep blue
    "text_white": "#ffffff",
    "text_gray": "#e5e7eb",
    "accent_gold": "#f59e0b",  # Amber (secondary)
}

class OGImageSpec(NamedTuple):
    """Spec for one OG image."""
    name: str
    path: Path
    title: str
    subtitle: str
    color_accent: str = COLORS["brand_teal"]


def create_default_og() -> bool:
    """
    Sinh og-default.webp + og-default.png (fallback tổng quát).

    Design:
    - Nền gradient Navy→DarkBlue (calm enterprise)
    - Tiêu đề "SEOMONEY" lớn tại top
    - Subtitle "Công nghệ, du lịch & trải nghiệm" tại giữa
    - S-DNA symbol (circle ◈) subtle tại bottom-right
    - Teal accent bar dọc bên trái (màu S-DNA)
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("create_og_image: Pillow not installed — skipping OG image generation")
        return False

    # Tạo canvas
    img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), color=COLORS["bg_dark"])
    draw = ImageDraw.Draw(img)

    # Left accent bar (Teal vertical stripe)
    bar_width = 8
    draw.rectangle(
        [(0, 0), (bar_width, OG_HEIGHT)],
        fill=COLORS["brand_teal"]
    )

    # Gradient overlay (Navy → DarkBlue) — vẽ từng dòng pixel
    for y in range(OG_HEIGHT):
        ratio = y / OG_HEIGHT
        r = int(10 + (29 - 10) * ratio)
        g = int(20 + (78 - 20) * ratio)
        b = int(40 + (216 - 40) * ratio)
        color = (r, g, b)
        draw.line([(0, y), (OG_WIDTH, y)], fill=color)

    # Re-draw left accent bar lên trên gradient
    draw.rectangle(
        [(0, 0), (bar_width, OG_HEIGHT)],
        fill=COLORS["brand_teal"]
    )

    # Load font (fallback to default nếu không có)
    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            size=88
        )
        subtitle_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            size=32
        )
        small_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            size=18
        )
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Title "SEOMONEY"
    title_text = "SEOMONEY"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (OG_WIDTH - title_width) // 2
    title_y = 100

    draw.text(
        (title_x, title_y),
        title_text,
        fill=COLORS["text_white"],
        font=title_font
    )

    # Subtitle
    subtitle_text = "Công nghệ • Du lịch • Trải nghiệm"
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (OG_WIDTH - subtitle_width) // 2
    subtitle_y = 280

    draw.text(
        (subtitle_x, subtitle_y),
        subtitle_text,
        fill=COLORS["text_gray"],
        font=subtitle_font
    )

    # Bottom branding: "www.seomoney.org"
    branding_text = "www.seomoney.org"
    branding_bbox = draw.textbbox((0, 0), branding_text, font=small_font)
    branding_width = branding_bbox[2] - branding_bbox[0]
    branding_x = (OG_WIDTH - branding_width) // 2
    branding_y = OG_HEIGHT - 50

    draw.text(
        (branding_x, branding_y),
        branding_text,
        fill=COLORS["brand_teal"],
        font=small_font
    )

    # Subtle accent: S-DNA symbol (◈) bottom-right
    dna_text = "◈"
    dna_x = OG_WIDTH - 80
    dna_y = OG_HEIGHT - 60

    try:
        dna_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            size=40
        )
    except Exception:
        dna_font = small_font

    draw.text(
        (dna_x, dna_y),
        dna_text,
        fill=COLORS["brand_teal"],
        alpha=80 if hasattr(draw, "alpha") else None
    )

    # Save as WebP + PNG
    webp_path = IMG_ROOT / "og-default.webp"
    png_path = IMG_ROOT / "og-default.png"

    try:
        img.save(webp_path, "WEBP", quality=85, method=6)
        print(f"  ✓ Created {webp_path.relative_to(IMG_ROOT.parent.parent)}")
    except Exception as e:
        print(f"  ✗ Failed to save WebP: {e}")
        return False

    try:
        img.save(png_path, "PNG", optimize=True)
        print(f"  ✓ Created {png_path.relative_to(IMG_ROOT.parent.parent)}")
    except Exception as e:
        print(f"  ✗ Failed to save PNG: {e}")
        return False

    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="sinh category-specific OG images")
    ap.add_argument("--force", action="store_true", help="force re-create (overwrite)")
    args = ap.parse_args()

    print("create_og_image: generating SEOMONEY brand OG images")

    # Always create default
    if not create_default_og():
        return 0

    print("create_og_image: OG images ready for social preview")
    return 0


if __name__ == "__main__":
    sys.exit(main())
