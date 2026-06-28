#!/usr/bin/env python3
"""
Backfill article timestamps from date-only to full ISO datetime format.

This script converts all articles from:
    date = 2026-06-28        (date-only, bad)
to:
    date = 2026-06-28T00:00:00+07:00  (full ISO, good)

It uses git commit time as the source of truth when available.
For articles without git history, uses safe fallback (T00:00:00+07:00).

Supports both --dry-run (preview) and --apply (commit changes).
"""

import subprocess
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta

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
TZ_GMT7 = timezone(timedelta(hours=7))


def get_git_commit_time_for_file(file_path: str) -> str | None:
    """Get last commit time for a file as ISO datetime."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", file_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return None


def convert_date_only_to_datetime(date_only: str, commit_time: str | None) -> str:
    """Convert date-only string to full ISO datetime.

    If commit_time is available, parse it to preserve the actual commit time.
    Otherwise, use T00:00:00+07:00 as safe fallback.
    """
    # Try to use commit time if available
    if commit_time:
        # commit_time format: 2026-06-28T18:30:45+07:00
        try:
            dt = datetime.fromisoformat(commit_time)
            return dt.isoformat()
        except Exception:
            pass

    # Fallback: use T00:00:00+07:00
    try:
        date_obj = datetime.strptime(date_only, "%Y-%m-%d")
        # Create datetime in GMT+7
        dt_gmt7 = date_obj.replace(tzinfo=TZ_GMT7)
        return dt_gmt7.isoformat()
    except Exception:
        # If parsing fails, just append T00:00:00+07:00
        return f"{date_only}T00:00:00+07:00"


def process_article_file(file_path: Path, dry_run: bool = True) -> tuple[bool, str]:
    """Process a single article file.

    Returns:
        (changed, message)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Check if file has date-only format
        date_only_match = re.search(
            r"^date = ([0-9]{4}-[0-9]{2}-[0-9]{2})$",
            original_content,
            re.MULTILINE,
        )

        if not date_only_match:
            return False, f"Already has full timestamp or no date"

        date_only = date_only_match.group(1)

        # Get git commit time
        commit_time = get_git_commit_time_for_file(str(file_path))

        # Convert to datetime
        new_datetime = convert_date_only_to_datetime(date_only, commit_time)

        # Replace in content
        new_content = original_content.replace(
            f"date = {date_only}",
            f'date = {new_datetime}',
        )

        if dry_run:
            return True, f"Would convert: {date_only} → {new_datetime}"

        # Apply the change
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True, f"Converted: {date_only} → {new_datetime}"

    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Main function."""
    import sys

    dry_run = "--apply" not in sys.argv
    mode = "DRY RUN" if dry_run else "APPLY"

    print(f"=== Article Timestamp Backfill ({mode}) ===\n")

    total_changed = 0
    total_processed = 0

    for section in ARTICLE_SECTIONS:
        section_dir = CONTENT_DIR / section
        if not section_dir.exists():
            continue

        md_files = sorted(
            f for f in section_dir.glob("*.md") if f.name != "_index.md"
        )

        if not md_files:
            continue

        print(f"\n📁 {section.upper()}: {len(md_files)} articles")

        for md_file in md_files:
            total_processed += 1
            changed, message = process_article_file(md_file, dry_run=dry_run)

            if changed:
                print(f"  ✓ {md_file.name}: {message}")
                total_changed += 1
            else:
                print(f"  - {md_file.name}: {message}")

    print(f"\n{'=' * 60}")
    print(f"Total: {total_changed} changed / {total_processed} processed")

    if dry_run:
        print(f"\n✓ Dry run completed. Use --apply flag to commit changes.")
    else:
        print(f"\n✓ {total_changed} articles updated with full timestamps!")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
