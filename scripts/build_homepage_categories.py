#!/usr/bin/env python3
"""Generate list of real categories used in published posts for homepage filter.

This script scans all post markdown files and extracts unique categories
(excluding synthetic ones like "Tất cả", "Báo chí", "premium").
Output: data/homepage-categories.json
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def extract_categories_from_posts():
    """Scan all posts and extract categories with post counts."""
    content_dir = Path("content")
    categories = defaultdict(int)

    # Include both posting and baochi sections
    for section_dir in ["posting", "baochi"]:
        posts_dir = content_dir / section_dir
        if not posts_dir.exists():
            continue

        for md_file in posts_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue

            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Skip draft posts
            if re.search(r"draft\s*=\s*true", content):
                continue

            # Extract categories from [taxonomies] section
            match = re.search(r"\[taxonomies\].*?categories\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if match:
                cat_str = match.group(1)
                cat_list = [c.strip().strip('"') for c in cat_str.split(",")]

                for cat in cat_list:
                    # Skip synthetic/meta categories
                    if cat.lower() not in ["tất cả", "báo chí", "premium"]:
                        categories[cat] += 1

    return categories

def main():
    categories = extract_categories_from_posts()

    # Sort by post count (descending), then alphabetically
    sorted_categories = sorted(
        categories.items(),
        key=lambda x: (-x[1], x[0])
    )

    # Prepare output
    output = {
        "categories": [
            {"name": cat, "count": count}
            for cat, count in sorted_categories
        ],
        "total_categories": len(sorted_categories),
    }

    # Write to data file
    output_file = Path("data/homepage-categories.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ Generated {output_file}")
    print(f"  Categories: {len(sorted_categories)}")
    for cat, count in sorted_categories:
        print(f"    - {cat}: {count} posts")

if __name__ == "__main__":
    main()
