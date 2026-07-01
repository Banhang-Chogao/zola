#!/usr/bin/env python3
"""
Core Web Vitals hygiene gate — report-only (P2), exit 2 on P0 regressions.

Checks:
  - base.html must NOT load Google Fonts stylesheet (LCP blocker)
  - Hilda theme must use self-hosted Ericsson Hilda (not Inter)
  - site.scss must NOT import dead homepage partials (CSS bloat)
  - base.html must preload Ericsson Hilda WOFF2 (font subsetting)

Usage:
  python3 scripts/check_cwv_hygiene.py
  python3 scripts/check_cwv_hygiene.py --stdout
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

P0_PATTERNS = [
    (
        "google-fonts-stylesheet",
        ROOT / "templates/base.html",
        re.compile(r"fonts\.googleapis\.com/css2"),
        "Remove Google Fonts stylesheet from base.html (use self-hosted Ericsson Hilda)",
    ),
    (
        "hilda-inter-fallback",
        ROOT / "sass/_hilda-fonts.scss",
        re.compile(r"--hilda-font-family:\s*'Inter'"),
        "Set --hilda-font-family to 'Ericsson Hilda' in _hilda-fonts.scss",
    ),
]

DEAD_SCSS_IMPORTS = ("home-momo", "home-discovery", "home-magazine", "home-economist")

REQUIRED_PATTERNS = [
    (
        "hilda-woff2-preload",
        ROOT / "templates/base.html",
        re.compile(r"EricssonHilda-Medium\.woff2"),
        "Preload EricssonHilda-Medium.woff2 in base.html head script",
    ),
    (
        "hilda-bold-preload",
        ROOT / "templates/base.html",
        re.compile(r"EricssonHilda-Bold\.woff2"),
        "Preload EricssonHilda-Bold.woff2 in base.html head script",
    ),
]


def check_p0() -> list[str]:
    errors: list[str] = []
    for name, path, pattern, hint in P0_PATTERNS:
        if not path.exists():
            errors.append(f"[P0] {name}: missing file {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            errors.append(f"[P0] {name}: {hint}")
    return errors


def check_dead_scss() -> list[str]:
    path = ROOT / "sass/site.scss"
    if not path.exists():
        return [f"[P0] site-scss-missing: {path} not found"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for partial in DEAD_SCSS_IMPORTS:
        if re.search(rf'@import\s+"{re.escape(partial)}"', text):
            errors.append(
                f"[P0] dead-scss-{partial}: remove @import \"{partial}\" from site.scss"
            )
    return errors


def check_required() -> list[str]:
    warnings: list[str] = []
    for name, path, pattern, hint in REQUIRED_PATTERNS:
        if not path.exists():
            warnings.append(f"[P1] {name}: missing file {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if not pattern.search(text):
            warnings.append(f"[P1] {name}: {hint}")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="CWV hygiene gate (fonts + CSS trim)")
    parser.add_argument("--stdout", action="store_true", help="Print summary to stdout")
    args = parser.parse_args()

    p0 = check_p0() + check_dead_scss()
    p1 = check_required()

    if args.stdout or p0 or p1:
        print("CWV Hygiene Report")
        print(f"  P0 blockers: {len(p0)}")
        print(f"  P1 warnings: {len(p1)}")
        for line in p0 + p1:
            print(f"  - {line}")

    if p0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())