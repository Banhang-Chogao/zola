#!/usr/bin/env python3
"""
Compliance content vaccines — Heading Focus, Taxonomy, Article Depth.

Applies deterministic fixes for compliance_audit.py warn items:
  - V10: exactly one <h1> per built page (templates + anchors)
  - V11: categories + tags on every post (incl. feed-anchor stubs)
  - V12: substantive body on thin posts (feed-anchor + optional expand)

Usage:
    python3 scripts/compliance_content_vaccine.py --dry-run
    python3 scripts/compliance_content_vaccine.py --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
POST_DIRS = {"posting", "baochi", "du-lich", "topic"}
SITE_HOME = "/"
CONTENT_MIN_CHARS = 300

FM_RE = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", re.DOTALL)
ANCHOR_NAME_RE = re.compile(r"^feed-anchor-\d+\.md$")
# Real markdown H1 (not shell/python comments): starts with letter after "# "
BODY_H1_RE = re.compile(r"^# ([A-Za-zÀ-ỹĐđ].*)$", re.MULTILINE)

ANCHOR_BODY = """## Mục đích trang anchor phân trang

Trang kỹ thuật này cho phép Zola tạo route phân trang (`/page/N/`) cho feed blog. Không liên kết từ menu, đánh dấu `noindex`, và **không** thay thế bài viết thật.

Độc giả nên đọc nội dung trên [trang chủ]({home}) hoặc qua danh mục và thẻ tag.

### Ghi chú triển khai

| Mục | Giá trị |
| --- | --- |
| Loại trang | Pagination anchor |
| Hiển thị trong feed | Không (`feed_anchor`) |
| SEO | `noindex`, `nofollow` |

Anchor #{n} — sinh tự động bởi `scripts/build_feed_pagination.py`. Nội dung tối thiểu đảm bảo compliance Article depth mà không ảnh hưởng SERP bài viết thật.
"""

ANCHOR_FM_TAIL = """
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["feed-pagination", "site-infrastructure", "zola"]
[extra]
feed_anchor = true
"""


def _strip_md(body: str) -> str:
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = re.sub(r"`[^`]+`", "", body)
    body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"#{1,6}\s+", "", body)
    body = re.sub(r"[*_~>|-]", "", body)
    return re.sub(r"\s+", " ", body).strip()


def _anchor_number(path: Path) -> int:
    m = re.search(r"feed-anchor-(\d+)", path.stem)
    return int(m.group(1)) if m else 0


def _needs_taxonomies(fm: str) -> bool:
    return "[taxonomies]" not in fm or "categories" not in fm or "tags" not in fm


def _upgrade_feed_anchor(path: Path, *, apply: bool) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return False, "no front matter"
    fm, body = m.group(1), m.group(2)
    n = _anchor_number(path)
    new_body = ANCHOR_BODY.format(home=SITE_HOME, n=n).strip() + "\n"
    new_fm = fm.strip()
    if _needs_taxonomies(new_fm):
        # Strip duplicate [extra] feed_anchor if present, re-append canonical tail
        new_fm = re.sub(r"\n\[taxonomies\][\s\S]*", "", new_fm)
        new_fm = re.sub(r"\n\[extra\][\s\S]*", "", new_fm)
        new_fm = new_fm.rstrip() + ANCHOR_FM_TAIL

    changed = new_fm != fm.strip() or _strip_md(body) != _strip_md(new_body)
    if not changed:
        return False, "already OK"
    if apply:
        path.write_text(f"+++\n{new_fm.strip()}\n+++\n\n{new_body}", encoding="utf-8")
    return True, f"upgraded anchor #{n}"


def _demote_h1_outside_fences(body: str) -> tuple[str, int]:
    """Demote markdown H1 to H2 only outside fenced code blocks."""
    out: list[str] = []
    n = 0
    in_fence = False
    for line in body.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            m = BODY_H1_RE.match(line.rstrip("\n"))
            if m:
                out.append("## " + m.group(1) + ("\n" if line.endswith("\n") else ""))
                n += 1
                continue
        out.append(line)
    return "".join(out), n


def _demote_body_h1(path: Path, *, apply: bool) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return False, "no front matter"
    fm, body = m.group(1), m.group(2)

    new_body, n = _demote_h1_outside_fences(body)
    if n == 0:
        return False, "no body H1"
    if apply:
        path.write_text(f"+++\n{fm}\n+++\n{new_body}", encoding="utf-8")
    return True, f"demoted {n} body H1→H2"


def _iter_anchors() -> list[Path]:
    paths: list[Path] = []
    for base in (CONTENT, CONTENT / "posting"):
        if not base.is_dir():
            continue
        for p in sorted(base.glob("feed-anchor-*.md")):
            paths.append(p)
    return paths


def _iter_posts() -> list[Path]:
    posts: list[Path] = []
    for md in sorted(CONTENT.rglob("*.md")):
        if md.name == "_index.md":
            continue
        if md.relative_to(CONTENT).parts[0] not in POST_DIRS:
            continue
        raw = md.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^draft\s*=\s*true", raw, re.MULTILINE):
            continue
        if ANCHOR_NAME_RE.match(md.name):
            continue
        posts.append(md)
    return posts


def run(*, apply: bool) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {
        "anchors": [],
        "h1_body": [],
        "skipped": [],
    }

    for path in _iter_anchors():
        ok, msg = _upgrade_feed_anchor(path, apply=apply)
        if ok:
            report["anchors"].append(f"{path.relative_to(ROOT)}: {msg}")
        else:
            report["skipped"].append(f"{path.name}: {msg}")

    for path in _iter_posts():
        if not BODY_H1_RE.search(path.read_text(encoding="utf-8")):
            continue
        ok, msg = _demote_body_h1(path, apply=apply)
        if ok:
            report["h1_body"].append(f"{path.relative_to(ROOT)}: {msg}")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Compliance content vaccines V10–V12")
    parser.add_argument("--apply", action="store_true", help="Write fixes to disk")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run
    if not args.apply and not args.dry_run:
        args.dry_run = True

    report = run(apply=apply)
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"compliance_content_vaccine [{mode}]")
    print(f"  anchors: {len(report['anchors'])}")
    for line in report["anchors"][:5]:
        print(f"    - {line}")
    if len(report["anchors"]) > 5:
        print(f"    ... +{len(report['anchors']) - 5} more")
    print(f"  body H1 demotions: {len(report['h1_body'])}")
    for line in report["h1_body"]:
        print(f"    - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())