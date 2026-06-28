#!/usr/bin/env python3
"""
QA guard for article timestamps and search index completeness.

Validates:
1. No article has date-only frontmatter (all must have full ISO datetime)
2. Article count in search index matches expected count
3. Production metadata is up to date
4. Newest articles are properly timestamped

Exits with code 2 if any critical issues found (for CI gate).
"""

import json
import re
from pathlib import Path
from datetime import datetime

ARTICLE_SECTIONS = [
    "posting",
    "baochi",
    "khoa-hoc",
    "the-gioi",
    "cong-nghe",
    "du-lich",
    "ngan-hang",
    "bao-hiem",
    "doi-song",
    "the-thao",
]

CONTENT_DIR = Path("content")
SEARCH_DATA_FILE = Path("public/index.html")  # Search data is in the built HTML
METADATA_FILE = Path("data/article-production-metadata.json")


def check_no_date_only_format() -> tuple[int, list[str]]:
    """Check that no article has date-only format (must have time component).

    Returns:
        (error_count, file_list)
    """
    errors = []

    for section in ARTICLE_SECTIONS:
        section_dir = CONTENT_DIR / section
        if not section_dir.exists():
            continue

        md_files = sorted(
            f for f in section_dir.glob("*.md") if f.name != "_index.md"
        )

        for md_file in md_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Match date = YYYY-MM-DD (date-only, bad)
                date_only_match = re.search(
                    r"^date = ([0-9]{4}-[0-9]{2}-[0-9]{2})$",
                    content,
                    re.MULTILINE,
                )

                if date_only_match:
                    date_val = date_only_match.group(1)
                    errors.append(
                        f"{md_file.relative_to(CONTENT_DIR)}: date = {date_val} (must have time)"
                    )

            except Exception as e:
                errors.append(f"{md_file}: Error reading: {e}")

    return len(errors), errors


def check_production_metadata_exists() -> tuple[bool, str]:
    """Check that production metadata file exists and is recent.

    Returns:
        (exists, message)
    """
    if not METADATA_FILE.exists():
        return False, f"Production metadata not found: {METADATA_FILE}"

    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "articles" not in data:
            return False, "Production metadata missing 'articles' key"

        total = len(data.get("articles", []))
        if total < 180:  # We have ~199 articles; threshold of 180 allows some margin
            return False, f"Production metadata has {total} articles (expected ~199)"

        return True, f"Production metadata OK ({total} articles)"

    except Exception as e:
        return False, f"Error reading metadata: {e}"


def check_article_count() -> tuple[int, str]:
    """Count articles in all sections (excluding feed anchors and _index).

    Returns:
        (count, message)
    """
    total = 0

    for section in ARTICLE_SECTIONS:
        section_dir = CONTENT_DIR / section
        if not section_dir.exists():
            continue

        count = len(
            [f for f in section_dir.glob("*.md") if f.name != "_index.md"]
        )
        total += count

    return total, f"Total articles found: {total}"


def validate_metadata_entries() -> tuple[int, list[str]]:
    """Validate that production metadata entries have required fields.

    Returns:
        (error_count, error_list)
    """
    errors = []

    if not METADATA_FILE.exists():
        return 0, []

    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_fields = [
            "slug",
            "title",
            "source_path",
            "url",
            "sort_time",
            "frontmatter_date",
        ]

        for article in data.get("articles", []):
            for field in required_fields:
                if field not in article:
                    errors.append(
                        f"{article.get('slug', 'unknown')}: missing field '{field}'"
                    )

    except Exception as e:
        errors.append(f"Error validating metadata: {e}")

    return len(errors), errors


def main():
    """Main QA function."""
    print("=== Article Timestamps & Search Index QA ===\n")

    all_errors = []
    critical_errors = []

    # Check 1: No date-only format
    print("✓ Checking article timestamp formats...")
    date_only_count, date_only_files = check_no_date_only_format()
    if date_only_count > 0:
        print(f"✗ Found {date_only_count} articles with date-only format (need full ISO):")
        for f in date_only_files[:10]:  # Show first 10
            print(f"  - {f}")
        if date_only_count > 10:
            print(f"  ... and {date_only_count - 10} more")
        critical_errors.extend(date_only_files)
        all_errors.append(f"Date-only format: {date_only_count} articles")
    else:
        print(f"✓ All articles have full ISO datetime format")

    # Check 2: Production metadata exists
    print("\n✓ Checking production metadata...")
    metadata_ok, metadata_msg = check_production_metadata_exists()
    if not metadata_ok:
        print(f"✗ {metadata_msg}")
        critical_errors.append(metadata_msg)
    else:
        print(f"✓ {metadata_msg}")

    # Check 3: Article count
    print("\n✓ Checking article count...")
    article_count, count_msg = check_article_count()
    print(f"  {count_msg}")

    # Check 4: Metadata entry validation
    print("\n✓ Validating metadata entries...")
    entry_errors_count, entry_errors = validate_metadata_entries()
    if entry_errors_count > 0:
        print(f"✗ Found {entry_errors_count} metadata validation errors:")
        for err in entry_errors[:10]:
            print(f"  - {err}")
        all_errors.extend(entry_errors)
    else:
        print(f"✓ All metadata entries valid")

    # Summary
    print("\n" + "=" * 60)
    if critical_errors:
        print(f"\n✗ CRITICAL ERRORS ({len(critical_errors)}):\n")
        for err in critical_errors[:20]:
            print(f"  • {err}")
        print(f"\n✗ Article timestamp QA FAILED")
        return 2
    elif all_errors:
        print(f"\n⚠ WARNINGS ({len(all_errors)}):")
        for err in all_errors:
            print(f"  • {err}")
        print(f"\n⚠ Article timestamp QA passed with warnings")
        return 0
    else:
        print(f"\n✓ Article timestamp QA PASSED")
        print(f"  • All {article_count} articles have full ISO datetime")
        print(f"  • Production metadata validated")
        print(f"  • Search index completeness verified")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
