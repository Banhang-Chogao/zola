#!/usr/bin/env python3
"""
Strip legacy /zola prefix from internal links after apex-domain migration.

When config.toml base_url is https://seomoney.org (no /zola subpath), markdown
and static assets must not link to /zola/... — those 404 on production and fail
check_internal_links.py after zola build.

Usage:
    python3 scripts/fix_stale_zola_links.py --dry-run
    python3 scripts/fix_stale_zola_links.py --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from site_link_prefix import (
    LEGACY_GHP_PREFIX,
    read_base_url,
    runtime_prefix,
    strip_stale_zola_path,
    uses_legacy_zola_prefix,
)

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
STATIC = REPO / "static"

# ](path) and ![alt](path) — root-absolute internal only
_MD_ROOT_LINK = re.compile(
    r"(\]\(|\!\[[^\]]*\]\()(/zola(?:/[^)\s\"']*)?)(\))",
    re.IGNORECASE,
)
_HTML_HREF = re.compile(r"""href=(["'])(/zola(?:/[^"'#?]*)?)\1""", re.IGNORECASE)
_JS_ZOLA_HOME = re.compile(
    r"""(location\.href\s*=\s*["'])(/zola/?)(["'])""",
    re.IGNORECASE,
)

SCAN_GLOBS = [
    (CONTENT, "**/*.md"),
    (STATIC / "converter", "**/*.html"),
    (STATIC / "js", "admin-*.js"),
    (STATIC / "js", "admin-countdown.js"),
]


def _fix_markdown(text: str) -> tuple[str, int]:
    changes = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal changes
        prefix, path, suffix = m.group(1), m.group(2), m.group(3)
        new_path = strip_stale_zola_path(path)
        if new_path != path:
            changes += 1
            return f"{prefix}{new_path}{suffix}"
        return m.group(0)

    return _MD_ROOT_LINK.sub(repl, text), changes


def _fix_html(text: str) -> tuple[str, int]:
    changes = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal changes
        quote, path = m.group(1), m.group(2)
        new_path = strip_stale_zola_path(path)
        if new_path != path:
            changes += 1
            return f'href={quote}{new_path}{quote}'
        return m.group(0)

    return _HTML_HREF.sub(repl, text), changes


def _fix_js(text: str) -> tuple[str, int]:
    changes = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal changes
        lead, path, tail = m.group(1), m.group(2), m.group(3)
        new_path = strip_stale_zola_path(path if path.endswith("/") else path + "/")
        if new_path != path:
            changes += 1
            return f"{lead}{new_path}{tail}"
        return m.group(0)

    return _JS_ZOLA_HOME.sub(repl, text), changes


def fix_file(path: Path, *, apply: bool) -> int:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return 0

    if path.suffix == ".md":
        new, n = _fix_markdown(raw)
    elif path.suffix == ".html":
        new, n = _fix_html(raw)
    elif path.suffix == ".js":
        new, n = _fix_js(raw)
    else:
        return 0

    if n and apply:
        path.write_text(new, encoding="utf-8")
    return n


def iter_targets() -> list[Path]:
    out: list[Path] = []
    for base, pattern in SCAN_GLOBS:
        if not base.is_dir():
            continue
        out.extend(sorted(base.glob(pattern)))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write fixes to disk")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run

    base = read_base_url()
    prefix = runtime_prefix()
    if uses_legacy_zola_prefix():
        print(f"OK: base_url={base} uses {LEGACY_GHP_PREFIX} — no stale-prefix strip needed")
        return 0

    total_files = 0
    total_links = 0
    touched: list[str] = []

    for path in iter_targets():
        n = fix_file(path, apply=apply)
        if n:
            total_files += 1
            total_links += n
            touched.append(f"{path.relative_to(REPO)} ({n})")

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"{mode}: runtime prefix '{prefix or '/'}' (base_url={base})")
    if not touched:
        print("OK: no stale /zola internal links found")
        return 0

    print(f"{'Fixed' if apply else 'Would fix'} {total_links} link(s) in {total_files} file(s):")
    for line in touched[:40]:
        print(f"  - {line}")
    if len(touched) > 40:
        print(f"  ... +{len(touched) - 40} more files")
    return 0 if apply or total_links == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())