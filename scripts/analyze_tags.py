#!/usr/bin/env python3
"""
Tag Sprawl Audit Script — Analyze tag distribution and identify thin tags.

Purpose: Scan all markdown content files, extract tags, count posts per tag,
and identify candidates for consolidation or deletion (1-post tags, orphans, etc).

Output: reports/tag-sprawl-audit-{ISO_DATE}.csv with detailed tag analysis.

Provides:
- Tags with 1-2 posts (consolidation candidates)
- Orphan tags (listed in taxonomy but no posts)
- Top 50 tags by post count (core tags to retain)
- Tag frequency distribution for SEO health check
"""

import os
import re
import json
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def parse_frontmatter(file_path):
    """Simple TOML/YAML frontmatter parser for Zola markdown files."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract frontmatter (delimited by +++ for TOML)
        if content.startswith("+++"):
            parts = content.split("+++", 2)
            if len(parts) >= 2:
                fm_text = parts[1].strip()
                # Simple tag extraction from TOML: tags = ["tag1", "tag2"]
                tags_match = re.search(r'tags\s*=\s*\[(.*?)\]', fm_text, re.DOTALL)
                if tags_match:
                    tags_str = tags_match.group(1)
                    # Extract quoted strings
                    tags = re.findall(r'"([^"]*)"', tags_str)
                    return {"tags": tags}
        return {"tags": []}
    except Exception as e:
        return {"tags": []}


def scan_content_tags():
    """Scan all markdown files in content/ and extract tags."""
    content_dir = Path("content")
    tags_count = defaultdict(int)
    tag_posts = defaultdict(list)

    # Scan markdown files
    for md_file in content_dir.rglob("*.md"):
        # Skip index files and special pages
        if md_file.name == "_index.md" or md_file.parent.name in ["cms", "shortensea"]:
            continue

        try:
            metadata = parse_frontmatter(md_file)

            # Extract tags from metadata
            tags = metadata.get("tags", [])
            if not tags:
                continue

            # Count tags and track posts
            slug = md_file.stem
            title = md_file.stem

            for tag in tags:
                if tag and tag.strip():  # Skip empty tags
                    tags_count[tag] += 1
                    tag_posts[tag].append({
                        "slug": slug,
                        "title": title,
                        "file": str(md_file)
                    })
        except Exception as e:
            pass  # Silently skip unparseable files

    return tags_count, tag_posts


def generate_report(tags_count, tag_posts):
    """Generate comprehensive tag sprawl analysis."""

    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Generate timestamp
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    report_file = reports_dir / f"tag-sprawl-audit-{date_str}.csv"

    # Categorize tags
    one_post_tags = [t for t, c in tags_count.items() if c == 1]
    two_post_tags = [t for t, c in tags_count.items() if c == 2]
    three_plus_tags = [t for t, c in tags_count.items() if c >= 3]

    # Sort tags by frequency
    sorted_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)
    top_50_tags = sorted_tags[:50]

    # Write CSV report
    with open(report_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "tag",
            "post_count",
            "category",
            "posts_sample",
            "recommendation"
        ])
        writer.writeheader()

        # Write all tags sorted by count
        for i, (tag, count) in enumerate(sorted_tags, 1):
            category = "1-post (thin)" if count == 1 else \
                      "2-post (small)" if count == 2 else \
                      "core" if count >= 5 else \
                      "moderate"

            # Sample posts
            posts = tag_posts[tag][:2]  # First 2 posts
            posts_sample = "; ".join([p["title"] for p in posts])

            # Recommendation
            if count == 1:
                recommendation = "Consider deleting or aliasing to broader tag"
            elif count == 2:
                recommendation = "Monitor; consolidate if related"
            elif count >= 10:
                recommendation = "Core tag — retain"
            else:
                recommendation = "Keep but monitor growth"

            writer.writerow({
                "tag": tag,
                "post_count": count,
                "category": category,
                "posts_sample": posts_sample[:100],  # Truncate for CSV
                "recommendation": recommendation
            })

    # Print summary
    print(f"\n📊 Tag Sprawl Audit Report")
    print(f"=" * 60)
    print(f"Report: {report_file}")
    print(f"Generated: {now.isoformat()}Z")
    print()
    print(f"Total unique tags: {len(tags_count)}")
    print(f"Total posts: {sum(tags_count.values())}")
    print()
    print(f"Tag Distribution:")
    print(f"  • 1-post (thin):     {len(one_post_tags):3d}  ({len(one_post_tags)*100//len(tags_count):2d}%) — candidates for deletion")
    print(f"  • 2-post (small):    {len(two_post_tags):3d}  ({len(two_post_tags)*100//len(tags_count):2d}%) — consider consolidation")
    print(f"  • 3+ posts (core):   {len(three_plus_tags):3d}  ({len(three_plus_tags)*100//len(tags_count):2d}%) — healthy")
    print()
    print(f"Top 10 tags by frequency:")
    for i, (tag, count) in enumerate(top_50_tags[:10], 1):
        print(f"  {i:2d}. {tag:30s} ({count:3d} posts)")
    print()

    # Write summary JSON for dashboard
    summary = {
        "generated_at": now.isoformat() + "Z",
        "total_tags": len(tags_count),
        "total_posts": sum(tags_count.values()),
        "distribution": {
            "one_post": len(one_post_tags),
            "two_post": len(two_post_tags),
            "core_3plus": len(three_plus_tags),
            "core_5plus": len([t for t, c in tags_count.items() if c >= 5])
        },
        "top_50": [{"tag": t, "count": c} for t, c in top_50_tags],
        "thin_tags": sorted(one_post_tags),
        "small_tags": sorted(two_post_tags),
        "health_score": (len(three_plus_tags) * 100) // len(tags_count) if tags_count else 0
    }

    # Save JSON summary
    json_file = reports_dir / f"tag-sprawl-audit-{date_str}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"JSON summary: {json_file}")
    print()

    return summary


if __name__ == "__main__":
    print("Scanning content directory for tags...")
    tags_count, tag_posts = scan_content_tags()

    if not tags_count:
        print("No tags found in content.")
        exit(0)

    summary = generate_report(tags_count, tag_posts)
    print("✓ Tag sprawl audit complete")
