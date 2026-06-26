#!/usr/bin/env python3
"""
Normalize root-absolute internal markdown links for GitHub Pages subpath.

On https://banhang-chogao.github.io/zola/, markdown links like ](/baochi/foo/)
resolve to github.io/baochi/foo/ (404). This script prefixes /zola/ so built
HTML hrefs match the deployed base path.

Stdlib only. Idempotent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
SITE_PREFIX = "/zola"

# ](/path) — internal root-absolute markdown links
_MD_LINK_RE = re.compile(r"\]\((/[^)\s\"'#]+)")


def prefix_internal_md_links(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        path = m.group(1)
        if path.startswith(f"{SITE_PREFIX}/") or path == SITE_PREFIX:
            return m.group(0)
        count += 1
        return f"]({SITE_PREFIX}{path}"

    return _MD_LINK_RE.sub(repl, text), count


def main() -> int:
    total_links = 0
    files_changed = 0

    for md in sorted(CONTENT.rglob("*.md")):
        try:
            raw = md.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"skip {md}: {exc}", file=sys.stderr)
            continue
        new, n = prefix_internal_md_links(raw)
        if n:
            md.write_text(new, encoding="utf-8")
            files_changed += 1
            total_links += n
            print(f"  {md.relative_to(REPO)}: {n} link(s)")

    print(f"\nDone: {total_links} link(s) in {files_changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())