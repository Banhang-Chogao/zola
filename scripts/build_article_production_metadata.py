#!/usr/bin/env python3
"""
Build article production metadata with deployment-aware ordering.

Problem: Articles currently ordered by frontmatter date, but should be ordered
by production deployment time (when the article was actually deployed).

Solution:
- Read all articles with their frontmatter dates
- Determine deployment time from git commit history (first commit = deploy time)
- Generate pre-sorted JSON files for templates to consume
- Sort by: production_deployed_at > commit_time > frontmatter_date

Output files:
- data/article-production-metadata.json — full metadata with ordering info
- data/articles-sorted-by-production.json — pre-sorted list (templates can iterate)
- data/articles-by-section.json — grouped by section, pre-sorted
"""

import json
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class ArticleMetadata:
    """Article metadata with production ordering info."""
    title: str
    source_path: str  # e.g., "content/posting/example.md"
    canonical_url: str  # e.g., "/posting/example/" or "/khoa-hoc/example/"
    section: str  # e.g., "posting", "khoa-hoc"
    slug: str
    frontmatter_date: Optional[str]  # YYYY-MM-DD from frontmatter
    commit_hash: Optional[str]  # git commit that added/modified file
    commit_time: Optional[str]  # ISO 8601 from git
    production_deployed_at: Optional[str]  # if we track explicit deploys
    ordering_timestamp: str  # ISO 8601 — what we actually sort by
    ordering_source: str  # "production_deploy" | "commit_time" | "frontmatter"

    def ordering_priority(self) -> tuple:
        """Sort key: prefer production deploy time, fallback to commit, then frontmatter."""
        # Convert to ISO strings for comparison (all assumed valid ISO)
        deploy = self.production_deployed_at or ""
        commit = self.commit_time or ""
        frontmatter = self.frontmatter_date or ""

        # Return tuple: (priority, timestamp) where higher priority comes first
        if deploy:
            return (2, deploy)
        if commit:
            return (1, commit)
        if frontmatter:
            return (0, frontmatter)
        return (-1, "")  # No date at all


def parse_frontmatter(content: str) -> dict:
    """Parse TOML frontmatter from markdown file."""
    # Extract TOML between +++ markers
    match = re.match(r'^\+\+\+\n(.*?)\n\+\+\+', content, re.DOTALL)
    if not match:
        return {}

    toml_text = match.group(1)
    metadata = {}

    # Simple TOML parsing (just enough for date and slug)
    for line in toml_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # date = 2026-06-27
        if line.startswith('date = '):
            date_match = re.search(r'date = ["\']?(\d{4}-\d{2}-\d{2})', line)
            if date_match:
                metadata['date'] = date_match.group(1)

        # slug = "example-slug"
        elif line.startswith('slug = '):
            slug_match = re.search(r'slug = ["\']([^"\']+)["\']', line)
            if slug_match:
                metadata['slug'] = slug_match.group(1)

        # title = "Article Title"
        elif line.startswith('title = '):
            title_match = re.search(r'title = ["\']([^"\']+)["\']', line)
            if title_match:
                metadata['title'] = title_match.group(1)

    return metadata


def get_git_commit_info(file_path: str) -> tuple:
    """Get first commit time for a file (when it was created/deployed)."""
    try:
        # Get the oldest commit for this file (first creation)
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%H %aI", "--", file_path],
            capture_output=True,
            text=True,
            cwd="/home/user/zola"
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None, None

        # Get the last line (oldest commit)
        lines = result.stdout.strip().split('\n')
        if not lines:
            return None, None

        # Take the oldest commit (last line)
        oldest = lines[-1]
        parts = oldest.split(' ', 1)
        if len(parts) == 2:
            commit_hash = parts[0]
            commit_time = parts[1]
            return commit_hash, commit_time

        return None, None
    except Exception:
        return None, None


def infer_section_and_url(file_path: str, slug: str) -> tuple:
    """Infer section and canonical URL from file path."""
    # e.g., "content/posting/example.md" -> section="posting", url="/posting/example/"
    # e.g., "content/khoa-hoc/example.md" -> section="khoa-hoc", url="/khoa-hoc/example/"

    parts = file_path.split('/')
    if len(parts) >= 2:
        section = parts[1]  # e.g., "posting"
    else:
        section = "root"

    # Skip content/ directory, skip .md filename
    if section in ("content", "."):
        section = "posting"

    url = f"/{section}/{slug}/"

    return section, url


def build_metadata():
    """Main: scan all articles and build metadata."""
    repo_root = Path("/home/user/zola")
    content_dir = repo_root / "content"

    articles = []

    # Find all markdown files in content/posting, content/khoa-hoc, etc.
    for md_file in content_dir.rglob("*.md"):
        # Skip special pages (_index.md, index.md at root level, admin pages)
        if md_file.name in ("_index.md", "index.md") or "admin" in str(md_file):
            continue
        if "pages" in str(md_file):  # Skip pages/ directory (special pages)
            continue
        if md_file.name.startswith("_"):
            continue

        # Read frontmatter
        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        fm = parse_frontmatter(content)
        if not fm.get('title') or not fm.get('slug'):
            continue

        title = fm['title']
        slug = fm['slug']
        frontmatter_date = fm.get('date')

        # Get git commit info
        relative_path = md_file.relative_to(repo_root)
        commit_hash, commit_time = get_git_commit_info(str(relative_path))

        # Infer section and URL
        section, canonical_url = infer_section_and_url(str(relative_path), slug)

        # Determine ordering timestamp and source
        if commit_time:
            ordering_timestamp = commit_time
            ordering_source = "commit_time"
        elif frontmatter_date:
            # Pad date to ISO format (2026-06-27 -> 2026-06-27T00:00:00Z)
            ordering_timestamp = f"{frontmatter_date}T00:00:00Z"
            ordering_source = "frontmatter"
        else:
            ordering_timestamp = "1970-01-01T00:00:00Z"
            ordering_source = "unknown"

        article = ArticleMetadata(
            title=title,
            source_path=str(relative_path),
            canonical_url=canonical_url,
            section=section,
            slug=slug,
            frontmatter_date=frontmatter_date,
            commit_hash=commit_hash,
            commit_time=commit_time,
            production_deployed_at=None,  # Not tracking explicit deploys yet
            ordering_timestamp=ordering_timestamp,
            ordering_source=ordering_source,
        )

        articles.append(article)

    # Sort by ordering timestamp (newest first)
    articles.sort(key=lambda a: a.ordering_timestamp, reverse=True)

    # Generate output files
    repo_root = Path("/home/user/zola")
    data_dir = repo_root / "data"
    data_dir.mkdir(exist_ok=True)

    # 1. Full metadata (all articles with ordering info)
    metadata_full = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "article_count": len(articles),
        "articles": [asdict(a) for a in articles],
    }

    metadata_file = data_dir / "article-production-metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata_full, f, indent=2)
    print(f"✓ Generated: {metadata_file} ({len(articles)} articles)")

    # 2. Sorted list (minimal, for templates to iterate)
    sorted_list = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(articles),
        "articles": [
            {
                "slug": a.slug,
                "title": a.title,
                "url": a.canonical_url,
                "section": a.section,
                "date": a.ordering_timestamp,
            }
            for a in articles
        ],
    }

    sorted_file = data_dir / "articles-sorted-by-production.json"
    with open(sorted_file, 'w') as f:
        json.dump(sorted_list, f, indent=2)
    print(f"✓ Generated: {sorted_file} (pre-sorted, Tera-safe)")

    # 3. Articles by section
    by_section = {}
    for article in articles:
        if article.section not in by_section:
            by_section[article.section] = []
        by_section[article.section].append({
            "slug": article.slug,
            "title": article.title,
            "url": article.canonical_url,
            "date": article.ordering_timestamp,
        })

    by_section_file = data_dir / "articles-by-section.json"
    with open(by_section_file, 'w') as f:
        json.dump({"sections": by_section}, f, indent=2)
    print(f"✓ Generated: {by_section_file} (grouped, pre-sorted)")

    # 4. Verification report
    print(f"\n=== Article Ordering Verification ===")
    print(f"Total articles: {len(articles)}")
    print(f"Ordering sources:")
    sources = {}
    for a in articles:
        sources[a.ordering_source] = sources.get(a.ordering_source, 0) + 1
    for source, count in sorted(sources.items()):
        print(f"  {source}: {count}")

    # Show newest 5
    print(f"\nNewest 5 articles (by production ordering):")
    for i, a in enumerate(articles[:5], 1):
        print(f"  {i}. {a.title}")
        print(f"     URL: {a.canonical_url}")
        print(f"     Source: {a.ordering_source} ({a.ordering_timestamp})")

    return len(articles)


if __name__ == "__main__":
    count = build_metadata()
    print(f"\n✅ Built metadata for {count} articles")
