#!/usr/bin/env python3
"""
Convert self-hosted TTF fonts to WOFF2 for faster web delivery.

WOFF2 (Brotli-compressed) is ~60-70% smaller than raw TTF and supported by
all modern browsers. We keep the TTF as an @font-face fallback in SCSS, but
browsers download only the WOFF2 — directly cutting the font payload that
competes with LCP on mobile.

Usage:
    python3 scripts/to_woff2.py                 # convert static/fonts/*.ttf
    python3 scripts/to_woff2.py path/to/dir     # convert a specific dir
    python3 scripts/to_woff2.py --force         # re-convert even if woff2 newer

No raster/SVG/WebP logic here — fonts only. Idempotent: skips up-to-date files.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "static" / "fonts"

# Fonts embedded into PDFs via jsPDF (export.js) are fetched as raw .ttf and
# CANNOT use woff2 — skip them so we don't ship dead-weight files.
SKIP_DIRS = {"nokia-pure"}


def convert_one(ttf: Path, force: bool = False) -> tuple[bool, int, int]:
    """Convert a single TTF → WOFF2. Returns (converted, ttf_bytes, woff2_bytes)."""
    from fontTools.ttLib import TTFont

    woff2 = ttf.with_suffix(".woff2")
    ttf_size = ttf.stat().st_size

    if woff2.exists() and not force and woff2.stat().st_mtime >= ttf.stat().st_mtime:
        return (False, ttf_size, woff2.stat().st_size)

    font = TTFont(ttf)
    font.flavor = "woff2"
    font.save(str(woff2))
    return (True, ttf_size, woff2.stat().st_size)


def main(argv: list[str]) -> int:
    force = "--force" in argv
    args = [a for a in argv if not a.startswith("--")]
    target = Path(args[0]) if args else DEFAULT_DIR
    if not target.is_absolute():
        target = ROOT / target

    if not target.exists():
        print(f"❌ Not found: {target}")
        return 1

    if target.is_dir():
        ttfs = sorted(
            t for t in target.rglob("*.ttf")
            if not (SKIP_DIRS & set(t.relative_to(target).parts))
        )
    else:
        ttfs = [target]
    if not ttfs:
        print(f"No .ttf files under {target}")
        return 0

    total_ttf = total_woff2 = 0
    converted = 0
    for ttf in ttfs:
        try:
            did, ttf_b, woff2_b = convert_one(ttf, force=force)
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"  ⚠️  {ttf.name}: {e}")
            continue
        total_ttf += ttf_b
        total_woff2 += woff2_b
        if did:
            converted += 1
            saved = 100 * (1 - woff2_b / ttf_b) if ttf_b else 0
            print(f"  ✓ {ttf.name} → {ttf.with_suffix('.woff2').name}  "
                  f"{ttf_b // 1024}KB → {woff2_b // 1024}KB  (−{saved:.0f}%)")
        else:
            print(f"  · {ttf.name}: woff2 up-to-date (skip)")

    if total_ttf:
        saved = 100 * (1 - total_woff2 / total_ttf)
        print(f"\nConverted {converted}/{len(ttfs)} fonts · "
              f"{total_ttf // 1024}KB TTF → {total_woff2 // 1024}KB WOFF2  (−{saved:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
