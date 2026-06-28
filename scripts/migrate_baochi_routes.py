#!/usr/bin/env python3
"""
Migrate baochi posts to their real content sections based on primary category.

Baochi is source metadata only (bb-generated), not a public URL section.
This script moves content/baochi/*.md posts to content/<real-category>/
and adds /baochi/<slug>/ aliases for backward compatibility.

Usage:
  python3 scripts/migrate_baochi_routes.py --dry-run
  python3 scripts/migrate_baochi_routes.py --apply
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Category mapping: content category → target section
CATEGORY_TO_SECTION = {
    "Khoa học": "khoa-hoc",
    "Ngân hàng": "ngan-hang",
    "Tài chính": "tai-chinh",
    "Công nghệ": "cong-nghe",
    "Du lịch": "du-lich",
    "Thể thao": "the-thao",
    "Đời sống": "doi-song",
    "Bảo hiểm": "bao-hiem",
    "SEO": "seo",
    "AI": "ai",
    "Học tiếng Hàn": "hoc-tieng-han",
    "Thế giới": "the-gioi",
    "Ẩm thực": "am-thuc",
    "Điện ảnh": "dien-anh",
}

# Categories to skip when determining primary category
SKIP_CATEGORIES = {"Tất cả", "Premium", "Báo chí", "Kiến thức"}

# Fallback category when confidence is low
FALLBACK_SECTION = "doi-song"
FALLBACK_CATEGORY = "Đời sống"


def extract_frontmatter(content: str) -> Tuple[str, Dict, str]:
    """Extract TOML frontmatter from markdown file."""
    match = re.match(r'^\+\+\+\n(.*?)\n\+\+\+\n(.*)', content, re.DOTALL)
    if not match:
        raise ValueError("Invalid frontmatter format")

    frontmatter_str = match.group(1)
    body = match.group(2)

    # Simple TOML parser for our specific use case
    frontmatter = {}
    current_key = None
    current_list = None

    for line in frontmatter_str.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Array detection: [taxonomies]
        if line.startswith('[') and line.endswith(']'):
            current_key = line.strip('[]')
            frontmatter[current_key] = {}
            current_list = None
            continue

        # Array element: categories = [...]
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            if current_key:
                # We're inside [taxonomies] or [extra]
                frontmatter[current_key][key] = value
            else:
                frontmatter[key] = value
            current_list = None

    return frontmatter_str, frontmatter, body


def get_categories_from_frontmatter(frontmatter: Dict) -> List[str]:
    """Extract category list from parsed frontmatter."""
    taxonomies = frontmatter.get('taxonomies', {})
    categories_str = taxonomies.get('categories', '[]')

    # Parse array string
    try:
        # Remove [ and ], split by comma, strip quotes
        categories_str = categories_str.strip('[]')
        categories = [c.strip().strip('"').strip("'") for c in categories_str.split(',')]
        return [c for c in categories if c]  # Remove empty strings
    except Exception:
        return []


def determine_target_section(categories: List[str]) -> Tuple[str, str, float]:
    """
    Determine target section based on primary category.

    Returns: (section_slug, primary_category, confidence)
    - Skips non-content categories (Tất cả, Premium, Báo chí, Kiến thức)
    - Returns first real category found
    - Falls back to Đời sống if no real category
    """
    for category in categories:
        if category in SKIP_CATEGORIES:
            continue

        if category in CATEGORY_TO_SECTION:
            return CATEGORY_TO_SECTION[category], category, 0.95

    # Fallback
    return FALLBACK_SECTION, FALLBACK_CATEGORY, 0.50


def add_alias_to_frontmatter(frontmatter_str: str, slug: str) -> str:
    """Add /baochi/<slug>/ alias to frontmatter."""
    alias_line = f'aliases = ["/baochi/{slug}/"]'

    # Check if aliases already exist
    if 'aliases' in frontmatter_str:
        # Find and replace existing aliases
        pattern = r'aliases\s*=\s*\[(.*?)\]'
        match = re.search(pattern, frontmatter_str)
        if match:
            existing_aliases = match.group(1)
            old_baochi_alias = f'"/baochi/{slug}/"'
            if old_baochi_alias not in existing_aliases:
                new_aliases = f'aliases = [{existing_aliases}, {old_baochi_alias}]'
            else:
                new_aliases = f'aliases = [{existing_aliases}]'
            frontmatter_str = re.sub(pattern, new_aliases, frontmatter_str)
    else:
        # Add new aliases line before closing +++
        frontmatter_str = frontmatter_str.rstrip() + f'\n{alias_line}'

    return frontmatter_str


def ensure_section_exists(section: str) -> None:
    """Ensure target section folder exists with _index.md if needed."""
    section_path = Path("content") / section
    section_path.mkdir(parents=True, exist_ok=True)

    index_file = section_path / "_index.md"
    if not index_file.exists():
        # Create basic _index.md
        index_content = f"""+++
title = "{section.replace('-', ' ').title()}"
sort_by = "date"
paginate_by = 10
template = "section.html"
+++
"""
        index_file.write_text(index_content, encoding='utf-8')
        print(f"  Created _index.md for {section}/")


def migrate_post(
    source_file: Path,
    slug: str,
    target_section: str,
    dry_run: bool = False
) -> Dict:
    """
    Migrate a single post from content/baochi/ to target section.

    Returns: migration result dict
    """
    result = {
        "slug": slug,
        "source": str(source_file),
        "status": "unknown",
        "error": None,
        "target_section": target_section,
    }

    try:
        # Read source file
        content = source_file.read_text(encoding='utf-8')
        frontmatter_str, frontmatter, body = extract_frontmatter(content)

        # Extract categories
        categories = get_categories_from_frontmatter(frontmatter)
        target_section_name, primary_category, confidence = determine_target_section(categories)

        result["target_section"] = target_section_name
        result["primary_category"] = primary_category
        result["confidence"] = confidence
        result["original_categories"] = categories

        # Ensure source metadata preserved
        if confidence < 0.65:
            result["fallback_reason"] = f"Low confidence ({confidence:.2f}), no clear category"

        # Add alias
        frontmatter_str = add_alias_to_frontmatter(frontmatter_str, slug)

        # Build new file content
        new_content = f"+++\n{frontmatter_str}\n+++\n{body}"

        # Target path
        target_file = Path("content") / target_section_name / f"{slug}.md"
        result["target"] = str(target_file)

        # Check if file already exists
        if target_file.exists():
            result["status"] = "exists"
            result["error"] = f"Target file already exists: {target_file}"
            return result

        # Perform migration
        if not dry_run:
            ensure_section_exists(target_section_name)
            target_file.write_text(new_content, encoding='utf-8')
            source_file.unlink()  # Delete source
            result["status"] = "migrated"
        else:
            result["status"] = "ready"

        return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate baochi posts to real sections")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply migrations")

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        return

    # Scan content/baochi/ for .md files (skip _index.md)
    baochi_path = Path("content/baochi")
    if not baochi_path.exists():
        print("✗ content/baochi/ not found")
        return

    posts = sorted([
        f for f in baochi_path.glob("*.md")
        if f.name != "_index.md"
    ])

    print(f"Found {len(posts)} posts in content/baochi/")
    print()

    results = []
    for post_file in posts:
        slug = post_file.stem
        print(f"Processing: {slug}...", end=" ")

        result = migrate_post(post_file, slug, "", dry_run=True)
        results.append(result)

        if result["status"] == "error":
            print(f"✗ ERROR: {result['error']}")
        else:
            section = result["target_section"]
            category = result.get("primary_category", "?")
            confidence = result.get("confidence", 0)
            status = "→" if args.apply else "↪"
            print(f"{status} {section}/ ({category}, {confidence:.0%})")

        # Actually migrate if --apply
        if args.apply and result["status"] in ("ready", "unknown"):
            result = migrate_post(post_file, slug, "", dry_run=False)
            if result["status"] == "migrated":
                print(f"  ✓ Migrated to {result['target']}")
            elif result["status"] != "migrated":
                print(f"  ✗ {result['status']}: {result['error']}")

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    by_status = {}
    by_section = {}

    for result in results:
        status = result["status"]
        by_status[status] = by_status.get(status, 0) + 1

        section = result.get("target_section", "unknown")
        if section not in by_section:
            by_section[section] = []
        by_section[section].append(result)

    print(f"Total posts: {len(results)}")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")

    print()
    print("By section:")
    for section in sorted(by_section.keys()):
        posts = by_section[section]
        print(f"  {section}/: {len(posts)} posts")

    # Generate migration report
    if args.apply or args.dry_run:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_dir = Path("reports/baochi-route-migration")
        report_dir.mkdir(parents=True, exist_ok=True)

        # JSON report
        json_report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": args.dry_run,
            "posts_processed": len(results),
            "summary": by_status,
            "by_section": {
                section: [
                    {
                        "slug": r["slug"],
                        "status": r["status"],
                        "primary_category": r.get("primary_category"),
                        "confidence": r.get("confidence"),
                        "original_categories": r.get("original_categories", []),
                    }
                    for r in posts
                ]
                for section, posts in by_section.items()
            },
        }

        json_file = report_dir / f"report-{timestamp}.json"
        json_file.write_text(json.dumps(json_report, indent=2, ensure_ascii=False), encoding='utf-8')

        print()
        print(f"📊 Report saved: {json_file}")


if __name__ == "__main__":
    main()
