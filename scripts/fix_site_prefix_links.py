#!/usr/bin/env python3
"""
Normalize root-absolute internal markdown links for GitHub Pages subpath.

On https://banhang-chogao.github.io/zola/, markdown links like ](/baochi/foo/)
resolve to github.io/baochi/foo/ (404). This script prefixes /zola/ so built
HTML hrefs match the deployed base path.

VACCINE (migration safety): links that appear INSIDE code spans — fenced ```
blocks or inline `code` — are documentation, not real links. Rewriting them
would corrupt code examples (and they never produce a 404). They are detected
via link_utils.code_span_ranges and left untouched. Every other root-absolute
internal link is prefixed so it cannot 404 after deploy.

Stdlib only. Idempotent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link_utils import code_span_ranges, in_ranges

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
SITE_PREFIX = "/zola"

# ](/path) — internal root-absolute markdown links
_MD_LINK_RE = re.compile(r"\]\((/[^)\s\"'#]+)")


def prefix_internal_md_links(text: str) -> tuple[str, int]:
    count = 0
    code_ranges = code_span_ranges(text)

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        # Never touch links inside code spans — they are examples, not links.
        if in_ranges(m.start(), code_ranges):
            return m.group(0)
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