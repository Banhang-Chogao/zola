#!/usr/bin/env python3
"""
Validate FAQ schema on top 20 high-value posts (ad-report-v2.json).

Exit 0 when all posts have 3–8 FAQ items with q=/a= fields.
Exit 2 when any post missing or thin FAQ (P1 content SEO gate).

Usage:
  python3 scripts/check_faq_top_posts.py
  python3 scripts/check_faq_top_posts.py --stdout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data/ad-report-v2.json"
CONTENT = ROOT / "content"

URL_RE = re.compile(r"https?://[^/]+/(?:zola/)?([^/]+)/([^/]+)/?$")
FAQ_BLOCK_RE = re.compile(r"\[\[extra\.faq\]\]", re.M)
FAQ_Q_RE = re.compile(r"^q\s*=", re.M)
FAQ_A_RE = re.compile(r"^a\s*=", re.M)
BAD_FAQ_RE = re.compile(r"^question\s*=|^answer\s*=", re.M)


def find_post(slug: str, section: str) -> Path | None:
    if section:
        p = CONTENT / section / f"{slug}.md"
        if p.exists():
            return p
    for path in sorted(CONTENT.glob(f"**/{slug}.md")):
        if path.name != "_index.md" and "/pages/" not in path.as_posix():
            return path
    return None


def count_faq(content: str) -> int:
    return len(FAQ_BLOCK_RE.findall(content))


def main() -> int:
    parser = argparse.ArgumentParser(description="FAQ gate for top 20 posts")
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--min", type=int, default=3)
    parser.add_argument("--max", type=int, default=8)
    args = parser.parse_args()

    if not REPORT.exists():
        print(f"Error: {REPORT} not found", file=sys.stderr)
        return 2

    data = json.loads(REPORT.read_text(encoding="utf-8"))
    posts = data.get("top_adsense_candidates", [])[:20]
    failures: list[str] = []

    for i, post in enumerate(posts, 1):
        url = post.get("url", "")
        title = post.get("title", "")[:50]
        m = URL_RE.search(url)
        if not m:
            failures.append(f"[P1] #{i} bad-url: {url}")
            continue
        section, slug = m.group(1), m.group(2)
        path = find_post(slug, section)
        if not path:
            failures.append(f"[P1] #{i} missing-file: {slug} ({url})")
            continue
        text = path.read_text(encoding="utf-8")
        n = count_faq(text)
        if n < args.min or n > args.max:
            failures.append(f"[P1] #{i} faq-count-{n}: {slug} (need {args.min}-{args.max})")
        if BAD_FAQ_RE.search(text):
            failures.append(f"[P1] #{i} bad-faq-fields: {slug} uses question=/answer= (use q=/a=)")
        if n > 0 and (not FAQ_Q_RE.search(text) or not FAQ_A_RE.search(text)):
            failures.append(f"[P1] #{i} invalid-faq-fields: {slug}")

    if args.stdout or failures:
        print("FAQ Top Posts Gate")
        print(f"  posts checked: {len(posts)}")
        print(f"  failures: {len(failures)}")
        for f in failures:
            print(f"  - {f}")

    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())