#!/usr/bin/env python3
"""
Post-build checker: detect internal hrefs missing GitHub Pages /zola/ prefix.

Scans public/*.html for href="/..." that would 404 on
https://banhang-chogao.github.io/zola/ (browser resolves to github.io root).

Exit 0 if clean, 1 if any bad links found.
Stdlib only.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "public"
SITE_PREFIX = "/zola"
BASE_URL = "https://banhang-chogao.github.io/zola"

# href="/foo" but not href="/zola/..." or href="//..."
_BAD_HREF_RE = re.compile(
    r"""href=["'](/(?!zola/)[^"'#?]+)["']""",
    re.IGNORECASE,
)

SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:", "data:")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def _is_bad_href(href: str) -> bool:
    href = href.strip()
    if not href or any(href.startswith(p) for p in SKIP_PREFIXES):
        return False
    if href.startswith(BASE_URL):
        return False
    if href.startswith(SITE_PREFIX + "/") or href == SITE_PREFIX + "/":
        return False
    if href.startswith("/"):
        return True
    return False


def scan() -> dict[str, list[str]]:
    """Return {html_file: [bad_href, ...]}."""
    bad: dict[str, list[str]] = {}
    if not PUBLIC.is_dir():
        return bad

    for html in sorted(PUBLIC.rglob("*.html")):
        try:
            text = html.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        found: list[str] = []
        for m in _BAD_HREF_RE.finditer(text):
            href = m.group(1)
            if _is_bad_href(href):
                found.append(href)
        # dedupe preserve order
        seen: set[str] = set()
        unique = []
        for h in found:
            if h not in seen:
                seen.add(h)
                unique.append(h)
        if unique:
            bad[str(html.relative_to(REPO))] = unique

    return bad


def main() -> int:
    bad = scan()
    total = sum(len(v) for v in bad.values())
    if not bad:
        print("OK: no internal links missing /zola/ prefix")
        return 0

    print(f"FAIL: {total} bad href(s) in {len(bad)} file(s)\n")
    for path, hrefs in sorted(bad.items()):
        print(f"  {path}")
        for h in hrefs[:10]:
            print(f"    - {h}")
        if len(hrefs) > 10:
            print(f"    ... +{len(hrefs) - 10} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())