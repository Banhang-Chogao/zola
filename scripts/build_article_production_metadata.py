#!/usr/bin/env python3
"""
Generate production article metadata with git commit info and sort times.

Scans all article sections (posting, baochi, khoa-hoc, the-gioi, cong-nghe,
du-lich, ngan-hang, bao-hiem, doi-song, the-thao) and generates a JSON file
with metadata including:
- source_path, url, title, slug
- frontmatter_date, last_article_commit_hash, last_article_commit_time
- production_deploy_commit_hash, production_deploy_time
- sort_time (for reliable ordering)

sort_time = last_article_commit_time (when article was last modified)
This ensures articles are ordered by when they were last published/updated,
not just the frontmatter date.
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import re

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
OUTPUT_FILE = Path("data/article-production-metadata.json")


def get_git_commit_time(file_path: str) -> tuple[str, str] | tuple[None, None]:
    """Get last commit hash and time for a file.

    Returns:
        (commit_hash, commit_time_iso) or (None, None) if not in git
    """
    try:
        # Get last commit hash for this file
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%cI", "--", file_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("|")
            if len(parts) == 2:
                commit_hash = parts[0][:8]  # First 8 chars
                commit_time = parts[1]
                return commit_hash, commit_time
    except Exception as e:
        print(f"Warning: Failed to get git info for {file_path}: {e}")

    return None, None


def parse_frontmatter_date(file_path: Path) -> str | None:
    """Extract date from TOML frontmatter.

    Handles both:
    - date = 2026-06-28 (date-only)
    - date = 2026-06-28T18:30:00+07:00 (full ISO)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract date from frontmatter
        match = re.search(r'^date\s*=\s*["\']?([^"\']+)["\']?', content, re.MULTILINE)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Warning: Failed to parse frontmatter for {file_path}: {e}")

    return None


def extract_title_and_slug(file_path: Path) -> tuple[str, str]:
    """Extract title and slug from file."""
    slug = file_path.stem

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract title from frontmatter
        match = re.search(r'^title\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if match:
            return match.group(1), slug
    except Exception as e:
        print(f"Warning: Failed to extract title from {file_path}: {e}")

    return slug.replace("-", " ").title(), slug


def get_section_url(section: str, slug: str) -> str:
    """Generate the production URL for an article."""
    # Special handling for sections
    if section == "posting":
        return f"https://seomoney.org/posting/{slug}/"
    else:
        return f"https://seomoney.org/posts/{slug}/"  # or appropriate path


def build_metadata() -> list[dict]:
    """Scan all article files and build metadata.

    Uses production metadata hierarchy:
    1. production_deployed_at (when commit is deployed to GitHub Pages)
    2. commit_time_fallback (git commit time for last article modification)
    3. frontmatter_fallback (frontmatter date value)

    Since gh CLI unavailable in this environment, production_deployed_at is null.
    Actual deploy time mapping would require GitHub API access to correlate
    commit SHA with successful deploy.yml run completion time.
    """
    articles = []

    for section in ARTICLE_SECTIONS:
        section_dir = CONTENT_DIR / section
        if not section_dir.exists():
            print(f"Warning: Section directory not found: {section_dir}")
            continue

        # Find all .md files except _index.md
        md_files = sorted(section_dir.glob("*.md"))
        md_files = [f for f in md_files if f.name != "_index.md"]

        print(f"Processing {section}: {len(md_files)} articles")

        for md_file in md_files:
            # Get git information
            commit_hash, commit_time = get_git_commit_time(str(md_file))

            # Parse frontmatter
            frontmatter_date = parse_frontmatter_date(md_file)
            title, slug = extract_title_and_slug(md_file)

            # Determine ordering_timestamp and ordering_source using hierarchy
            ordering_timestamp = None
            ordering_source = None

            # Priority 1: production_deployed_at (requires gh CLI mapping—not available)
            production_deployed_at = None

            # Priority 2: commit_time (available from git log)
            if commit_time:
                ordering_timestamp = commit_time
                ordering_source = "commit_time_fallback"
            # Priority 3: frontmatter_date (display metadata)
            elif frontmatter_date:
                ordering_timestamp = frontmatter_date
                ordering_source = "frontmatter_fallback"
            # Priority 4: current time (last resort, should not happen)
            else:
                ordering_timestamp = datetime.now(timezone.utc).isoformat()
                ordering_source = "generated_now"

            article = {
                "source_path": str(md_file.relative_to(Path("."))),
                "canonical_url": get_section_url(section, slug),
                "title": title,
                "section": section,
                "slug": slug,
                "commit_hash": commit_hash,
                "commit_time": commit_time,
                "production_deployed_at": production_deployed_at,
                "ordering_timestamp": ordering_timestamp,
                "ordering_source": ordering_source,
                "frontmatter_date": frontmatter_date,
                "metadata_generated_at": datetime.now(timezone.utc).isoformat(),
            }

            articles.append(article)

    return articles


def main():
    """Main function."""
    print("Building article production metadata...")

    try:
        articles = build_metadata()

        # Sort by ordering_timestamp descending (newest first)
        articles.sort(
            key=lambda a: a.get("ordering_timestamp", ""),
            reverse=True,
        )

        # Create output file
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_articles": len(articles),
            "sections": ARTICLE_SECTIONS,
            "articles": articles,
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"✓ Generated {len(articles)} article metadata entries")
        print(f"✓ Saved to {OUTPUT_FILE}")

        # Show newest article
        if articles:
            newest = articles[0]
            print(f"\n📰 Newest article by ordering timestamp:")
            print(f"   Title: {newest['title']}")
            print(f"   Path: {newest['source_path']}")
            print(f"   Ordering timestamp: {newest['ordering_timestamp']}")
            print(f"   Source: {newest['ordering_source']}")

        return 0

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
