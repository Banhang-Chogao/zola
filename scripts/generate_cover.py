#!/usr/bin/env python3
"""Generate owned, branded SEOMONEY editorial cover/placeholder images.

Replaces external stock images (Pixabay) with deterministic, self-owned SVG
covers. No internet, no external/copyrighted assets, no fonts beyond the system
sans stack. Output is **stable** for a given (slug, title, category): re-running
produces byte-identical SVG so rebuilds do not create noisy diffs.

Covers follow the existing convention `static/img/covers/<slug>.svg`; the OG
rasteriser (`scripts/build_og_images.py`) bakes the `.og.webp` twin used for
social/JSON-LD. Cards can render the `.svg` directly.

Fallback chain (resolved in templates/macros/img.html → `img::card_image`):
    1. frontmatter image / cover / thumbnail
    2. first LOCAL inline image in the body (no hotlinking)
    3. generated cover  /img/covers/<slug>.svg   ← this script
    4. category placeholder  /img/placeholders/category-<key>.svg  ← this script
    5. site OG fallback  /img/og/seomoney-og.og.webp

Usage:
    # Rebuild the covers manifest (which slugs already have a cover):
    python3 scripts/generate_cover.py manifest

    # (Re)generate the category placeholder set:
    python3 scripts/generate_cover.py placeholders

    # Generate one owned cover for a post:
    python3 scripts/generate_cover.py post --slug my-post \\
        --title "Tiêu đề bài viết" --category "Công nghệ"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVERS_DIR = ROOT / "static" / "img" / "covers"
PLACEHOLDERS_DIR = ROOT / "static" / "img" / "placeholders"
MANIFEST = ROOT / "data" / "covers-manifest.json"

W, H = 1200, 630

# Category → (gradient top, gradient bottom, accent) — SEOMONEY editorial palette.
# Keys are ASCII slugs; map_category() resolves Vietnamese category names to these.
PALETTES: dict[str, tuple[str, str, str]] = {
    "cong-nghe":     ("#0f2a4a", "#0b1f38", "#4c8dff"),  # Công nghệ — blue
    "ngan-hang":     ("#0b3a2e", "#082a22", "#2fbf8f"),  # Ngân hàng — teal/green
    "du-lich":       ("#3a2410", "#2a1a0b", "#ff9f43"),  # Du lịch — amber
    "am-thuc":       ("#3a1414", "#2a0d0d", "#ff6b6b"),  # Ẩm thực — rose
    "khoa-hoc":      ("#2a1640", "#1d0f2e", "#a06bff"),  # Khoa học — violet
    "hoc-tieng-han": ("#3a103a", "#2a0a2a", "#ff6bd6"),  # Học tiếng Hàn — magenta
    "tai-chinh":     ("#0b3340", "#08252e", "#2fb6bf"),  # Tài chính — cyan
    "default":       ("#1c2532", "#121922", "#7c93ad"),  # neutral slate
}

# Vietnamese / common category name → palette key.
CATEGORY_MAP: dict[str, str] = {
    "công nghệ": "cong-nghe", "cong nghe": "cong-nghe", "tech": "cong-nghe",
    "ngân hàng": "ngan-hang", "ngan hang": "ngan-hang", "banking": "ngan-hang",
    "tài chính": "tai-chinh", "tai chinh": "tai-chinh", "finance": "tai-chinh",
    "du lịch": "du-lich", "du lich": "du-lich", "travel": "du-lich",
    "ẩm thực": "am-thuc", "am thuc": "am-thuc", "food": "am-thuc",
    "khoa học": "khoa-hoc", "khoa hoc": "khoa-hoc", "science": "khoa-hoc",
    "học tiếng hàn": "hoc-tieng-han", "hoc tieng han": "hoc-tieng-han",
}

# Human label shown on category placeholders.
CATEGORY_LABEL: dict[str, str] = {
    "cong-nghe": "Công nghệ",
    "ngan-hang": "Ngân hàng",
    "tai-chinh": "Tài chính",
    "du-lich": "Du lịch",
    "am-thuc": "Ẩm thực",
    "khoa-hoc": "Khoa học",
    "hoc-tieng-han": "Học tiếng Hàn",
    "default": "SEOMONEY",
}


def map_category(name: str) -> str:
    """Resolve a (possibly Vietnamese) category name to a palette key."""
    return CATEGORY_MAP.get((name or "").strip().lower(), "default")


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def wrap_title(title: str, max_chars: int = 22, max_lines: int = 4) -> list[str]:
    """Greedy word-wrap a title into SVG lines (no external text metrics)."""
    words = (title or "").split()
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) <= max_chars or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "…"
    return lines


def render_svg(*, title: str, eyebrow: str, key: str, seed_text: str) -> str:
    """Deterministic 1200×630 branded SVG. Byte-stable per inputs."""
    top, bottom, accent = PALETTES.get(key, PALETTES["default"])
    seed = _seed(seed_text)
    # Deterministic decorative dot grid (subtle, brand-safe geometry — "S-DNA").
    dots = []
    for i in range(36):
        gx = 80 + (i % 9) * 130
        gy = 80 + (i // 9) * 150
        # stable jitter from seed
        jx = ((seed >> (i % 16)) & 0x3) * 6
        r = 2 + ((seed >> (i % 11)) & 0x1) * 2
        op = 0.05 + ((seed >> (i % 7)) & 0x3) * 0.02
        dots.append(
            f'<circle cx="{gx + jx}" cy="{gy}" r="{r}" fill="#ffffff" '
            f'opacity="{op:.2f}"/>'
        )
    dot_grid = "".join(dots)

    title_lines = wrap_title(title) if title else []
    # Title block bottom-anchored above the wordmark.
    line_h = 78
    start_y = 300 - (len(title_lines) - 1) * line_h // 2 if title_lines else 0
    title_tspans = "".join(
        f'<text x="90" y="{start_y + i * line_h}" font-size="68" '
        f'font-weight="800" fill="#ffffff" '
        f'font-family="Inter, \'Helvetica Neue\', Arial, sans-serif" '
        f'letter-spacing="-1.5">{_esc(line)}</text>'
        for i, line in enumerate(title_lines)
    )

    eyebrow_svg = (
        f'<text x="92" y="120" font-size="26" font-weight="700" '
        f'fill="{accent}" letter-spacing="3" '
        f'font-family="Inter, \'Helvetica Neue\', Arial, sans-serif">'
        f'{_esc(eyebrow.upper())}</text>'
        if eyebrow else ""
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{_esc(title or eyebrow)}">'
        f'<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="0.6" y2="1">'
        f'<stop offset="0" stop-color="{top}"/>'
        f'<stop offset="1" stop-color="{bottom}"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
        f'{dot_grid}'
        # left accent bar (S-DNA spine)
        f'<rect x="90" y="78" width="56" height="6" rx="3" fill="{accent}"/>'
        f'{eyebrow_svg}'
        f'{title_tspans}'
        # wordmark + mark, bottom-left
        f'<g transform="translate(90, 548)">'
        f'<rect x="0" y="-26" width="34" height="34" rx="8" fill="none" '
        f'stroke="{accent}" stroke-width="3"/>'
        f'<text x="8" y="0" font-size="26" font-weight="800" fill="{accent}" '
        f'font-family="Inter, Arial, sans-serif">S</text>'
        f'<text x="50" y="0" font-size="30" font-weight="800" fill="#ffffff" '
        f'letter-spacing="0.5" font-family="Inter, Arial, sans-serif">SEOMONEY</text>'
        f'</g>'
        f'<text x="{W - 90}" y="548" text-anchor="end" font-size="22" '
        f'font-weight="600" fill="#ffffff" opacity="0.55" '
        f'font-family="Inter, Arial, sans-serif">seomoney.org</text>'
        f'</svg>\n'
    )


def cmd_post(args: argparse.Namespace) -> None:
    key = map_category(args.category)
    eyebrow = CATEGORY_LABEL.get(key, "SEOMONEY") if args.category else "SEOMONEY"
    svg = render_svg(title=args.title, eyebrow=eyebrow, key=key, seed_text=args.slug)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    out = COVERS_DIR / f"{args.slug}.svg"
    out.write_text(svg, encoding="utf-8")
    print(f"COVER:{out.relative_to(ROOT)} (category={key})")
    cmd_manifest(args)


def cmd_placeholders(args: argparse.Namespace) -> None:
    PLACEHOLDERS_DIR.mkdir(parents=True, exist_ok=True)
    for key, label in CATEGORY_LABEL.items():
        # Placeholder = branded category card, no specific post title.
        title = label if key != "default" else "Bài viết SEOMONEY"
        svg = render_svg(title=title, eyebrow="SEOMONEY", key=key,
                         seed_text=f"placeholder-{key}")
        out = PLACEHOLDERS_DIR / f"category-{key}.svg"
        out.write_text(svg, encoding="utf-8")
        print(f"PLACEHOLDER:{out.relative_to(ROOT)}")


def cmd_manifest(args: argparse.Namespace) -> None:
    """Scan covers dir → manifest of slugs that own a generated/drawn cover."""
    slugs = sorted(p.stem for p in COVERS_DIR.glob("*.svg")) if COVERS_DIR.exists() else []
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps({"slugs": slugs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"MANIFEST:{MANIFEST.relative_to(ROOT)} ({len(slugs)} covers)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate owned SEOMONEY cover images.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_post = sub.add_parser("post", help="Generate one owned cover for a post.")
    p_post.add_argument("--slug", required=True)
    p_post.add_argument("--title", required=True)
    p_post.add_argument("--category", default="")
    p_post.set_defaults(func=cmd_post)

    sub.add_parser("placeholders", help="Generate the category placeholder set.").set_defaults(func=cmd_placeholders)
    sub.add_parser("manifest", help="Rebuild data/covers-manifest.json.").set_defaults(func=cmd_manifest)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
