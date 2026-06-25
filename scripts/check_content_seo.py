#!/usr/bin/env python3
"""Kiểm tra SEO front matter + ảnh thiếu alt trong content/*.md (Zola, TOML +++)."""

import re
import sys
import tomllib
from pathlib import Path

CONTENT = Path(__file__).resolve().parent.parent / "content"
FM = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", re.DOTALL)
MD_IMG = re.compile(r"!\[(.*?)\]\([^)]+\)")            # ![alt](url)
HTML_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HAS_ALT = re.compile(r"\balt\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)


def check(path):
    errs = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = FM.match(text)
    if not m:
        return ["thiếu front matter (+++)"]

    try:
        fm = tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError as e:
        return [f"front matter TOML lỗi: {e}"]

    if not str(fm.get("title", "")).strip():
        errs.append("thiếu title")
    if not str(fm.get("description", "")).strip():
        errs.append("thiếu description")

    body = m.group(2)
    for i, alt in enumerate(MD_IMG.findall(body), 1):
        if not alt.strip():
            errs.append(f"ảnh markdown #{i} thiếu alt")
    for i, tag in enumerate(HTML_IMG.findall(body), 1):
        mt = HAS_ALT.search(tag)
        if not mt or not mt.group(2).strip():
            errs.append(f"<img> #{i} thiếu alt")
    return errs


def main():
    bad = 0
    for md in sorted(CONTENT.rglob("*.md")):
        errs = check(md)
        if errs:
            bad += 1
            print(f"✗ {md.relative_to(CONTENT.parent)}")
            for e in errs:
                print(f"    - {e}")
    print(f"\n{'='*50}\n{bad} file lỗi." if bad else "✓ Không có file lỗi.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
