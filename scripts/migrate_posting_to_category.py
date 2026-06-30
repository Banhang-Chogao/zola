#!/usr/bin/env python3
"""Migrate posts from content/posting/ to category-based directories.

Usage:
  # Preview what would happen (dry run)
  python3 scripts/migrate_posting_to_category.py

  # Migrate a specific post
  python3 scripts/migrate_posting_to_category.py --slug an-khuya-sai-gon

  # Migrate all posts (one at a time, use when ready)
  python3 scripts/migrate_posting_to_category.py --all

The script reads the post's categories from TOML frontmatter and moves it to
the appropriate category directory, adding an alias for the old /posting/ URL.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTING_DIR = REPO_ROOT / "content" / "posting"

CATEGORY_DIR_MAP = {
    "Công nghệ": "cong-nghe",
    "Ngân hàng": "ngan-hang",
    "Du lịch": "du-lich",
    "Khoa học": "khoa-hoc",
    "Ẩm thực": "am-thuc",
    "Học tiếng Hàn": "hoc-tieng-han",
    "SEO": "seo",
    "Thế giới": "the-gioi",
    "Thể thao": "the-thao",
    "Bảo hiểm": "bao-hiem",
    "Điện ảnh": "dien-anh",
    "Đời sống": "doi-song",
    "Kiến thức": "kien-thuc",
    "World cup 2026": "world-cup-2026",
    "Linh tinh": "linh-tinh",
}


def parse_frontmatter(content: str) -> dict:
    """Extract TOML frontmatter from markdown content."""
    match = re.match(r'^\+\+\+\n(.+?)\n\+\+\+', content, re.DOTALL)
    if not match:
        return {}
    toml_text = match.group(1)
    meta = {}
    categories = None
    in_extra = False
    for line in toml_text.split('\n'):
        if line.strip() == '[extra]':
            in_extra = True
        elif line.strip().startswith('['):
            in_extra = False

        if line.strip().startswith('categories = '):
            raw = line.strip()
            raw = raw.replace('categories = ', '').strip()
            if raw.startswith('[') and raw.endswith(']'):
                raw = raw[1:-1]
                cats = []
                for item in re.findall(r'"([^"]*)"', raw):
                    cats.append(item)
                categories = cats
        elif line.strip().startswith('slug = '):
            val = line.strip().replace('slug = ', '').strip('"\' ')
            meta['slug'] = val
    meta['categories'] = categories or []
    return meta


def get_target_dir(categories: list) -> str | None:
    """Determine the target category directory from the post's categories."""
    seen_tat_ca = False
    for cat in categories:
        if cat == "Tất cả":
            seen_tat_ca = True
            continue
        if cat == "premium":
            continue
        if cat == "Series":
            continue
        if cat == "Báo chí":
            continue
        if cat in CATEGORY_DIR_MAP:
            dir_slug = CATEGORY_DIR_MAP[cat]
            return dir_slug
    if categories and not seen_tat_ca and len(categories) > 0:
        cat = categories[0]
        if cat in CATEGORY_DIR_MAP:
            return CATEGORY_DIR_MAP[cat]
    return None


def has_extra_series(content: str) -> bool:
    """Check if the post belongs to a series."""
    return 'series = "' in content or "series = '" in content


def update_aliases(content: str, slug: str) -> str:
    """Add /posting/slug/ alias to frontmatter if not already present."""
    old_alias = f'"/posting/{slug}/"'
    if old_alias in content:
        return content
    alias_line = f'  "{old_alias[1:-1]}",'
    aliases_match = re.search(r'^aliases\s*=\s*\[(.+?)\]', content, re.MULTILINE | re.DOTALL)
    if aliases_match:
        aliases_block = aliases_match.group(0)
        if aliases_block.strip().endswith(']'):
            new_block = aliases_block.rstrip()
            if new_block[-1] == ']':
                new_block = new_block[:-1].rstrip() + ',\n  '
                new_block += f'"{old_alias[1:-1]}"\n]'
                content = content.replace(aliases_match.group(0), new_block)
    else:
        date_line = re.search(r'^date\s*=\s*\S+', content, re.MULTILINE)
        if date_line:
            end = date_line.end()
            insert = f'\naliases = ["{old_alias[1:-1]}"]'
            content = content[:end] + insert + content[end:]
    return content


def migrate_post(slug: str, dry_run: bool = False) -> None:
    """Migrate a single post from posting/ to its category directory."""
    src = POSTING_DIR / f"{slug}.md"
    if not src.exists():
        print(f"  ❌ Not found: content/posting/{slug}.md")
        return

    content = src.read_text(encoding='utf-8')
    meta = parse_frontmatter(content)
    categories = meta.get('categories', [])

    if not categories:
        print(f"  ⚠️  No categories for {slug}, skipping")
        return

    target_dir_slug = get_target_dir(categories)
    if not target_dir_slug:
        cat_names = ', '.join(categories)
        print(f"  ⚠️  No mapping for categories [{cat_names}] in {slug}, skipping")
        return

    target_dir = REPO_ROOT / "content" / target_dir_slug
    target_file = target_dir / f"{slug}.md"

    if target_file.exists():
        print(f"  ⚠️  Already exists: {target_dir_slug}/{slug}.md, skipping")
        return

    updated = update_aliases(content, slug)
    os.makedirs(target_dir, exist_ok=True)

    _index = target_dir / "_index.md"
    if not _index.exists():
        title = next((k for k, v in CATEGORY_DIR_MAP.items() if v == target_dir_slug), target_dir_slug)
        _index.write_text(f'+++\ntitle = "{title}"\nsort_by = "date"\npaginate_by = 10\ntemplate = "section.html"\n+++\n', encoding='utf-8')
        if dry_run:
            print(f"  📄 Would create {target_dir_slug}/_index.md")

    if dry_run:
        print(f"  🔄 Would move: posting/{slug}.md → {target_dir_slug}/{slug}.md")
        return

    target_file.write_text(updated, encoding='utf-8')
    src.unlink()
    print(f"  ✅ Moved: posting/{slug}.md → {target_dir_slug}/{slug}.md")


def main():
    parser = argparse.ArgumentParser(description="Migrate posts from content/posting/ to category directories")
    parser.add_argument('--slug', type=str, help='Migrate a specific post by slug')
    parser.add_argument('--all', action='store_true', help='Migrate all posts in content/posting/')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Preview without making changes (default)')
    parser.add_argument('--apply', action='store_true', help='Actually apply changes (override dry-run)')
    args = parser.parse_args()

    dry_run = not args.apply

    if args.slug:
        migrate_post(args.slug, dry_run=dry_run)
        return

    if args.all:
        posting_files = sorted(POSTING_DIR.glob("*.md"))
        print(f"Found {len(posting_files)} posts in content/posting/")
        for f in posting_files:
            slug = f.stem
            if slug == "_index":
                continue
            migrate_post(slug, dry_run=dry_run)
        return

    parser.print_help()
    print("\nExamples:")
    print("  python3 scripts/migrate_posting_to_category.py --slug an-khuya-sai-gon --apply")
    print("  python3 scripts/migrate_posting_to_category.py --all --apply")


if __name__ == "__main__":
    main()
