#!/usr/bin/env python3
"""Generate social-preview-native OG image cards (1200×640 PNG) for articles.

Layout: white card on neutral bg, thumbnail image on top, "seomoney.org" label +
article title in white bottom panel. Category placeholders as fallback.

Usage:
    python3 scripts/generate_og_images.py                    # generate missing
    python3 scripts/generate_og_images.py --force            # regenerate all
    python3 scripts/generate_og_images.py --skip-build-check  # no zola build verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("✗ Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent

CONTENT_DIR = REPO_ROOT / "content"
POSTING_DIR = CONTENT_DIR / "posting"
BAOCHI_DIR = CONTENT_DIR / "baochi"
STATIC_DIR = REPO_ROOT / "static"
OG_DIR = STATIC_DIR / "og" / "generated"
PLACEHOLDER_DIR = STATIC_DIR / "og" / "placeholders"
CATEGORY_MAP_FILE = REPO_ROOT / "data" / "category-map.json"
MANIFEST_FILE = REPO_ROOT / "data" / "og-image-manifest.json"

IMG_WIDTH = 1200
IMG_HEIGHT = 640
OUTPUT_FORMAT = "PNG"

PLACEHOLDER_COLORS = {
    "cong-nghe": "#2563eb",
    "ngan-hang": "#059669",
    "tai-chinh": "#d97706",
    "du-lich": "#0891b2",
    "khoa-hoc": "#7c3aed",
    "doi-song": "#db2777",
    "am-thuc": "#ea580c",
    "bao-chi": "#4b5563",
    "bao-hiem": "#0e7490",
    "giao-duc": "#6366f1",
    "hoc-tieng-han": "#be123c",
    "seo": "#ca8a04",
    "ai-webops": "#0f766e",
    "dien-anh": "#9333ea",
    "the-gioi": "#1d4ed8",
    "the-thao": "#16a34a",
    "default": "#374151",
}

FONT_BOLD_PATH = REPO_ROOT / "static" / "fonts" / "EricssonHilda-Bold.ttf"
FONT_MEDIUM_PATH = REPO_ROOT / "static" / "fonts" / "EricssonHilda-Medium.ttf"

TITLE_FONT_SIZE = 42
LABEL_FONT_SIZE = 16
PANEL_HEIGHT = 160


def load_category_map() -> dict:
    if CATEGORY_MAP_FILE.exists():
        return json.loads(CATEGORY_MAP_FILE.read_text())
    return {}


def get_first_category(page_path: Path) -> str:
    text = page_path.read_text(encoding="utf-8")
    m = re.search(r"categories\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if m:
        cats_raw = m.group(1)
        cats = re.findall(r'"(.+?)"', cats_raw)
        cats = [c for c in cats if c != "Tất cả"]
        if cats:
            return cats[0]
    return "default"


def get_article_title(page_path: Path) -> str:
    text = page_path.read_text(encoding="utf-8")
    m = re.search(r"^title\s*=\s*\"(.+?)\"", text, re.MULTILINE)
    if m:
        return m.group(1)
    return "SEOMONEY Blog"


def get_page_slug(page_path: Path) -> str:
    text = page_path.read_text(encoding="utf-8")
    m = re.search(r"^slug\s*=\s*\"(.+?)\"", text, re.MULTILINE)
    if m:
        return m.group(1)
    return page_path.stem


def get_page_thumbnail(page_path: Path) -> str | None:
    text = page_path.read_text(encoding="utf-8")
    m = re.search(r"thumbnail\s*=\s*\"(.+?)\"", text)
    if m:
        val = m.group(1)
        if "/img/placeholder/" not in val:
            return val
    return None


def get_page_image(page_path: Path) -> str | None:
    text = page_path.read_text(encoding="utf-8")
    m = re.search(r'^(?:image|cover)\s*=\s*"(.+?)"', text, re.MULTILINE)
    if m:
        return m.group(1)
    return None


def find_thumbnail_path(thumb_ref: str) -> Path | None:
    if thumb_ref.startswith("/"):
        thumb_ref = thumb_ref.lstrip("/")
    for candidate in [STATIC_DIR / thumb_ref, REPO_ROOT / thumb_ref]:
        if candidate.exists():
            return candidate
    if thumb_ref.endswith(".svg"):
        og_twin = thumb_ref.replace(".svg", ".og.webp")
        for candidate in [STATIC_DIR / og_twin, REPO_ROOT / og_twin]:
            if candidate.exists():
                return candidate
    return None


def make_placeholder(category: str, size: tuple[int, int]) -> Image.Image:
    color = PLACEHOLDER_COLORS.get(category, PLACEHOLDER_COLORS["default"])
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    label = category.replace("-", " ").title() if category != "default" else "SEOMONEY"
    try:
        font = ImageFont.truetype(str(FONT_MEDIUM_PATH), 28)
    except (OSError, IOError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size[0] - tw) // 2
    y = (size[1] - th) // 2
    draw.text((x, y), label, fill="white", font=font)
    return img


def load_thumbnail(page_path: Path) -> Image.Image | None:
    thumb_ref = get_page_thumbnail(page_path)
    if not thumb_ref:
        thumb_ref = get_page_image(page_path)
    if thumb_ref:
        tp = find_thumbnail_path(thumb_ref)
        if tp and tp.exists():
            try:
                im = Image.open(tp).convert("RGB")
                return im
            except Exception:
                pass
    return None


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        bbox = font.getbbox(test)
        tw = bbox[2] - bbox[0]
        if tw <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def generate_card(
    title: str,
    category: str,
    output_path: Path,
    thumbnail: Image.Image | None = None,
) -> None:
    canvas = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), "#f3f4f6")

    # Thumbnail area (top 480px)
    thumb_area_height = IMG_HEIGHT - PANEL_HEIGHT
    if thumbnail:
        thumb = thumbnail.copy()
        thumb_ratio = max(
            IMG_WIDTH / thumb.width,
            thumb_area_height / thumb.height,
        )
        new_w = int(thumb.width * thumb_ratio)
        new_h = int(thumb.height * thumb_ratio)
        thumb = thumb.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - IMG_WIDTH) // 2
        top = (new_h - thumb_area_height) // 2
        thumb = thumb.crop((left, top, left + IMG_WIDTH, top + thumb_area_height))
        canvas.paste(thumb, (0, 0))
    else:
        ph = make_placeholder(category, (IMG_WIDTH, thumb_area_height))
        canvas.paste(ph, (0, 0))

    # Bottom panel (white, 160px)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, thumb_area_height), (IMG_WIDTH, IMG_HEIGHT)], fill="white")

    # "seomoney.org" label in bottom-left
    try:
        label_font = ImageFont.truetype(str(FONT_MEDIUM_PATH), LABEL_FONT_SIZE)
    except (OSError, IOError):
        label_font = ImageFont.load_default()
    draw.text(
        (32, thumb_area_height + 14),
        "seomoney.org",
        fill="#6b7280",
        font=label_font,
    )

    # Title in bottom panel
    try:
        title_font = ImageFont.truetype(str(FONT_BOLD_PATH), TITLE_FONT_SIZE)
    except (OSError, IOError):
        try:
            title_font = ImageFont.truetype(str(FONT_MEDIUM_PATH), TITLE_FONT_SIZE)
        except (OSError, IOError):
            title_font = ImageFont.load_default()

    max_title_width = IMG_WIDTH - 64
    lines = wrap_text(title, title_font, max_title_width)
    # Max 2 lines
    lines = lines[:2]
    line_y = thumb_area_height + 42
    for line in lines:
        draw.text((32, line_y), line, fill="#111827", font=title_font)
        line_y += TITLE_FONT_SIZE + 6

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), format=OUTPUT_FORMAT)


def content_hash(page_path: Path) -> str:
    text = page_path.read_bytes()
    return hashlib.sha256(text).hexdigest()[:16]


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


def generate_all(force: bool = False) -> int:
    pages: list[Path] = []
    for d in [POSTING_DIR, BAOCHI_DIR]:
        if d.exists():
            pages.extend(sorted(d.glob("*.md")))

    manifest = {} if force else load_manifest()
    generated = 0
    skipped = 0
    errors = 0

    for fp in pages:
        slug = get_page_slug(fp)
        out_path = OG_DIR / f"{slug}.png"
        ch = content_hash(fp)

        # Skip if already generated and content unchanged
        if not force and out_path.exists():
            entry = manifest.get(slug, {})
            if entry.get("hash") == ch:
                skipped += 1
                continue

        try:
            title = get_article_title(fp)
            category = get_first_category(fp)
            thumb = load_thumbnail(fp)
            generate_card(title, category, out_path, thumbnail=thumb)
            manifest[slug] = {
                "hash": ch,
                "title": title,
                "slug": slug,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            generated += 1
            print(f"  ✓ {slug}.png")
        except Exception as e:
            print(f"  ✗ {fp.name}: {e}")
            errors += 1

    save_manifest(manifest)

    print(f"\nDone: {generated} generated, {skipped} skipped, {errors} errors")
    return 0 if errors == 0 else 1


def generate_placeholders() -> int:
    PLACEHOLDER_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for cat, color in PLACEHOLDER_COLORS.items():
        out_path = PLACEHOLDER_DIR / f"{cat}.png"
        if out_path.exists():
            continue
        img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT - 160), color)
        draw = ImageDraw.Draw(img)
        label = cat.replace("-", " ").title()
        try:
            font = ImageFont.truetype(str(FONT_MEDIUM_PATH), 32)
        except (OSError, IOError):
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (IMG_WIDTH - tw) // 2
        y = ((IMG_HEIGHT - 160) - th) // 2
        draw.text((x, y), label, fill="white", font=font)
        img.save(str(out_path), format=OUTPUT_FORMAT)
        count += 1
        print(f"  ✓ placeholder/{cat}.png")
    print(f"Placeholders: {count} generated")
    return 0


def generate_fallback() -> int:
    out_path = STATIC_DIR / "img" / "seomoney-og.png"
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), "#1f2937")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(FONT_BOLD_PATH), 56)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype(str(FONT_MEDIUM_PATH), 56)
        except (OSError, IOError):
            font = ImageFont.load_default()
    label = "SEOMONEY"
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (IMG_WIDTH - tw) // 2
    y = (IMG_HEIGHT - th) // 2 - 20
    draw.text((x, y), label, fill="white", font=font)
    try:
        sub_font = ImageFont.truetype(str(FONT_MEDIUM_PATH), 22)
    except (OSError, IOError):
        sub_font = ImageFont.load_default()
    sub = "seomoney.org"
    bbox2 = draw.textbbox((0, 0), sub, font=sub_font)
    sw = bbox2[2] - bbox2[0]
    draw.text(((IMG_WIDTH - sw) // 2, y + 70), sub, fill="#9ca3af", font=sub_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), format=OUTPUT_FORMAT)
    print(f"  ✓ static/img/seomoney-og.png")
    return 0


def check_images() -> int:
    missing: list[str] = []
    # Check fallback exists
    if not (STATIC_DIR / "img" / "seomoney-og.png").exists():
        missing.append("static/img/seomoney-og.png")
    # Check at least some generated images
    gen_count = len(list(OG_DIR.glob("*.png")))
    if gen_count == 0:
        print("⚠ No generated OG images found")
    if missing:
        print(f"Missing: {', '.join(missing)}")
        return 1
    print(f"OK: fallback present, {gen_count} generated images")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OG social-preview cards")
    parser.add_argument("--force", action="store_true", help="Regenerate all")
    parser.add_argument(
        "--skip-placeholders", action="store_true", help="Skip placeholder generation"
    )
    parser.add_argument(
        "--skip-fallback", action="store_true", help="Skip fallback generation"
    )
    parser.add_argument("--check", action="store_true", help="Check images exist")
    args = parser.parse_args()

    if args.check:
        return check_images()

    rc = 0

    if not args.skip_placeholders:
        print("Generating placeholders...")
        rc |= generate_placeholders()

    if not args.skip_fallback:
        print("Generating fallback...")
        rc |= generate_fallback()

    print("Generating OG cards...")
    rc |= generate_all(force=args.force)

    return rc


if __name__ == "__main__":
    sys.exit(main())
