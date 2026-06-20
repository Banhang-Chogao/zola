#!/usr/bin/env python3
"""
Post-build checker: detect on-site links that would 404 against the canonical base.

The blog is served from https://seomoney.org/ (root domain — no /zola subpath),
so every on-site link in the built HTML must be a valid root-absolute path. This
checker parses real HTML *attributes* (not a raw-text regex), so substrings such
as data-href="/x", xlink:href, or "href":"/x" inside inline JSON can never
masquerade as a link and trip a false positive. It inspects asset URLs
(src / srcset / <link href>) as well, so a missing-prefix asset is not silently
skipped either.

SITE_PREFIX is derived from BASE_URL: at root it is "" (every root-absolute link
is already canonical), and if the site ever moves back under a subpath the same
logic enforces that prefix automatically — no root-domain assumption hardcoded.

Exit 0 if clean, 1 if any bad links found.
Stdlib only.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "public"
BASE_URL = "https://seomoney.org"
SITE_PREFIX = urlparse(BASE_URL).path.rstrip("/")  # "" at root — canonical subpath

SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:", "data:")

# <link rel="…"> values whose href is a real navigable/asset URL we care about.
_ASSET_LINK_RELS = ("stylesheet", "preload", "icon", "manifest")


class LinkParser(HTMLParser):
    """Collect real href/src attribute values from navigational + asset tags.

    Parsing attributes (vs. a regex over raw text) means substrings like
    data-href="/x" or xlink:href never get mistaken for an <a href> link.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("a", "area") and a.get("href"):
            self.links.append(a["href"])
        # src on img/script/source/iframe/audio/video/embed
        src = a.get("src")
        if src:
            self.links.append(src)
        # responsive images: <img/source srcset="url 1x, url2 2x">
        srcset = a.get("srcset")
        if srcset:
            for part in srcset.split(","):
                url = part.strip().split(" ")[0].strip()
                if url:
                    self.links.append(url)
        # <link href> only for asset rels (skip canonical/alternate self-URLs).
        if tag == "link":
            rel = (a.get("rel") or "").lower()
            if a.get("href") and any(r in rel for r in _ASSET_LINK_RELS):
                self.links.append(a["href"])


def _is_bad_href(href: str) -> bool:
    """True if href is an on-site root-absolute link missing the canonical prefix.

    At root (SITE_PREFIX == "") every root-absolute href is already canonical, so
    nothing is flagged; under a subpath the missing-prefix links are caught.
    """
    href = (href or "").strip()
    if not href or any(href.startswith(p) for p in SKIP_PREFIXES):
        return False
    # Absolute or protocol-relative URLs are not "missing-prefix" candidates: an
    # absolute self-URL already carries the base, and cross-origin is out of scope.
    if href.startswith("//") or urlparse(href).scheme:
        return False
    # Only root-absolute paths can 404 from a missing base prefix (skip relative
    # links and the bare "/" home, which prior behaviour also left untouched).
    if not href.startswith("/") or href == "/":
        return False
    # Already correctly under the canonical subpath (always true at root).
    if href == SITE_PREFIX or href.startswith(SITE_PREFIX + "/"):
        return False
    return True


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

        parser = LinkParser()
        try:
            parser.feed(text)
        except Exception:
            continue

        # dedupe, preserve order
        seen: set[str] = set()
        unique: list[str] = []
        for href in parser.links:
            h = href.strip()
            if _is_bad_href(h) and h not in seen:
                seen.add(h)
                unique.append(h)
        if unique:
            bad[str(html.relative_to(REPO))] = unique

    return bad


def main() -> int:
    bad = scan()
    total = sum(len(v) for v in bad.values())
    if not bad:
        print("OK: no internal links missing canonical prefix")
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
