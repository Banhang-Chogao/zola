#!/usr/bin/env python3
"""
Generate invisible pagination anchor pages so Zola creates /page/N/ routes.

Homepage (content/_index.md, paginate_by=10) and blog listing (posting/_index.md)
slice a merged feed in templates — anchors only control pager count, not content.
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PER_PAGE = 10

# Non-index markdown pages already in each section (exclude feed-anchor-*.md).
ROOT_STATIC_PAGES = {
    "bao-cao-tong-ket.md",
    "branding-guideline.md",
    "font.md",
    "prompt-support.md",
    "scoring.md",
    "seo-bang-vang.md",
    "timer.md",
}

ANCHOR_TEMPLATE = """+++
title = "Feed pagination anchor {n}"
template = "feed-anchor.html"
date = 2000-01-01
weight = 9000
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["feed-pagination", "site-infrastructure", "zola"]
[extra]
feed_anchor = true
+++

## Mục đích trang anchor phân trang

Trang kỹ thuật này cho phép Zola tạo route phân trang (`/page/N/`) cho feed blog. Không liên kết từ menu, đánh dấu `noindex`, và **không** thay thế bài viết thật.

Độc giả nên đọc nội dung trên [trang chủ](/zola/) hoặc qua danh mục và thẻ tag.

### Ghi chú triển khai

| Mục | Giá trị |
| --- | --- |
| Loại trang | Pagination anchor |
| Hiển thị trong feed | Không (`feed_anchor`) |
| SEO | `noindex`, `nofollow` |

Anchor #{n} — sinh tự động bởi `scripts/build_feed_pagination.py`. Nội dung tối thiểu đảm bảo compliance Article depth mà không ảnh hưởng SERP bài viết thật.

"""


def is_real_post(path: Path) -> bool:
    name = path.name
    if name.startswith("_") or name.startswith("feed-anchor-"):
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return "draft = true" not in text and "draft=true" not in text


def count_published_posts() -> int:
    paths = glob.glob(str(ROOT / "content" / "posting" / "*.md"))
    paths += glob.glob(str(ROOT / "content" / "baochi" / "*.md"))
    return sum(1 for p in paths if is_real_post(Path(p)))


def feed_page_count(post_count: int) -> int:
    if post_count <= 0:
        return 1
    return (post_count + PER_PAGE - 1) // PER_PAGE


def min_section_pages_for_pagers(pagers: int) -> int:
    if pagers <= 1:
        return 0
    return (pagers - 1) * PER_PAGE + 1


def existing_anchors(section_dir: Path) -> list[Path]:
    return sorted(section_dir.glob("feed-anchor-*.md"))


def count_posting_pages() -> int:
    return sum(
        1
        for p in glob.glob(str(ROOT / "content" / "posting" / "*.md"))
        if not Path(p).name.startswith("_") and not Path(p).name.startswith("feed-anchor-")
    )


def existing_root_static_pages() -> int:
    return len(ROOT_STATIC_PAGES)


def write_anchors(section_dir: Path, needed: int) -> tuple[int, int]:
    section_dir.mkdir(parents=True, exist_ok=True)
    current = existing_anchors(section_dir)
    if needed <= 0:
        for path in current:
            path.unlink()
        return 0, len(current)

    if len(current) > needed:
        for path in current[needed:]:
            path.unlink()
        current = current[:needed]

    created = 0
    for i in range(len(current), needed):
        out = section_dir / f"feed-anchor-{i + 1:03d}.md"
        out.write_text(ANCHOR_TEMPLATE.format(n=i + 1), encoding="utf-8")
        created += 1
    return created, needed


def main() -> int:
    post_count = count_published_posts()
    pagers = feed_page_count(post_count)

    root_dir = ROOT / "content"
    posting_dir = ROOT / "content" / "posting"

    root_existing = existing_root_static_pages()
    posting_existing = count_posting_pages()
    min_pages = min_section_pages_for_pagers(pagers)

    root_needed = max(0, min_pages - root_existing)
    posting_needed = max(0, min_pages - posting_existing)

    root_created, root_total = write_anchors(root_dir, root_needed)
    post_created, post_total = write_anchors(posting_dir, posting_needed)

    print(
        f"feed-pagination: {post_count} posts → {pagers} page(s); "
        f"home anchors {root_total} (+{root_created}), "
        f"posting anchors {post_total} (+{post_created})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())