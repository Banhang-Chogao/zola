#!/usr/bin/env python3
"""
Audit internal linking quality across all posts.

Identifies:
- Posts with <3 internal links (weak)
- Posts with 3-8 links (optimal)
- Posts with >8 links (over-linked)
- Orphaned posts with no links to/from them
- Weak link pairs (low semantic relevance)

Outputs: data/audit-internal-links.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT_FILE = ROOT / "data" / "audit-internal-links.json"


def _extract_links_from_markdown(content: str) -> list[str]:
    """Extract internal links from markdown content."""
    links = []

    # Match markdown links: [text](/url)
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, url in md_links:
        # Normalize URL (remove /zola prefix, trailing slash)
        url = url.strip()
        if url.startswith('/zola/'):
            url = url[5:]  # Remove /zola prefix
        if url.startswith('/posting/'):
            slug = url[9:].rstrip('/')
            if slug and slug != 'index':
                links.append(slug)

    return links


def _get_post_metadata(file_path: Path) -> dict[str, Any]:
    """Extract slug, title, categories, tags from post."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return {}

    slug = file_path.stem
    result = {'slug': slug}

    # Extract title
    title_match = re.search(r'title\s*=\s*["\']([^"\']+)["\']', content)
    if title_match:
        result['title'] = title_match.group(1)

    # Extract categories
    cat_match = re.search(r'categories\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if cat_match:
        cats_str = cat_match.group(1)
        cats = [c.strip().strip('"\'') for c in cats_str.split(',') if c.strip()]
        result['categories'] = cats

    # Extract tags
    tag_match = re.search(r'tags\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if tag_match:
        tags_str = tag_match.group(1)
        tags = [t.strip().strip('"\'') for t in tags_str.split(',') if t.strip()]
        result['tags'] = tags

    return result


def _calculate_link_strength(slug1_meta: dict, slug2_meta: dict) -> float:
    """Calculate link strength between two posts (0-1)."""
    score = 0.0

    # Same category (strong signal)
    cats1 = set(slug1_meta.get('categories', []))
    cats2 = set(slug2_meta.get('categories', []))
    if cats1 & cats2:
        score += 0.4
        # Bonus if category is more specific than "Tất cả"
        specific_overlap = (cats1 - {'Tất cả'}) & (cats2 - {'Tất cả'})
        if specific_overlap:
            score += 0.1

    # Tag overlap (medium signal)
    tags1 = set(slug1_meta.get('tags', []))
    tags2 = set(slug2_meta.get('tags', []))
    tag_overlap = len(tags1 & tags2)
    if tag_overlap > 0:
        overlap_ratio = tag_overlap / (len(tags1) + len(tags2) - tag_overlap)
        score += overlap_ratio * 0.3

    return min(score, 1.0)


def main():
    """Run audit."""
    if not CONTENT_DIR.exists():
        print(f"Content dir not found: {CONTENT_DIR}")
        return 1

    # Load all posts
    files = [f for f in CONTENT_DIR.glob('*.md') if f.name != '_index.md']
    print(f"Scanning {len(files)} posts...")

    posts_by_slug = {}
    for f in files:
        meta = _get_post_metadata(f)
        if meta:
            posts_by_slug[meta['slug']] = meta

    # For each post, extract links
    links_from = defaultdict(set)  # slug -> set of linked slugs
    links_to = defaultdict(set)    # slug -> set of linking slugs

    for f in files:
        slug = f.stem
        try:
            content = f.read_text(encoding='utf-8')
            links = _extract_links_from_markdown(content)
            links_from[slug].update(links)
            for target_slug in links:
                links_to[target_slug].add(slug)
        except Exception as e:
            print(f"  Error reading {slug}: {e}")

    # Categorize posts by link count
    posts_by_link_count = {
        'weak': [],      # 0-2 links
        'optimal': [],   # 3-8 links
        'over_linked': [] # 9+ links
    }

    for slug in posts_by_slug.keys():
        count = len(links_from[slug])
        if count < 3:
            posts_by_link_count['weak'].append({'slug': slug, 'link_count': count})
        elif count <= 8:
            posts_by_link_count['optimal'].append({'slug': slug, 'link_count': count})
        else:
            posts_by_link_count['over_linked'].append({'slug': slug, 'link_count': count})

    # Find orphaned posts (no inlinks, few outlinks)
    orphaned = []
    for slug in posts_by_slug.keys():
        inlink_count = len(links_to[slug])
        outlink_count = len(links_from[slug])
        if inlink_count == 0 and outlink_count < 2:
            orphaned.append({
                'slug': slug,
                'title': posts_by_slug[slug].get('title', slug),
                'inlinks': 0,
                'outlinks': outlink_count
            })

    # Find weak pairs: posts that should be linked but aren't (high semantic similarity, low strength)
    weak_pairs = []
    for slug1 in posts_by_slug.keys():
        for slug2 in posts_by_slug.keys():
            if slug1 >= slug2:
                continue  # Avoid duplicates and self-pairs

            # Check if already linked
            if slug2 in links_from[slug1] or slug1 in links_from[slug2]:
                continue

            # Calculate link strength
            strength = _calculate_link_strength(posts_by_slug[slug1], posts_by_slug[slug2])

            # If strength is high but not linked, it's a weak pair
            if strength > 0.4:
                weak_pairs.append({
                    'from_slug': slug1,
                    'from_title': posts_by_slug[slug1].get('title', slug1),
                    'to_slug': slug2,
                    'to_title': posts_by_slug[slug2].get('title', slug2),
                    'strength': round(strength, 2),
                    'reason': f"High category/tag overlap but not linked"
                })

    # Sort weak pairs by strength (descending)
    weak_pairs.sort(key=lambda x: x['strength'], reverse=True)

    # Generate report
    report = {
        'audit_at': datetime.now(timezone.utc).isoformat(),
        'total_posts': len(posts_by_slug),
        'by_link_count': {
            'weak_0_2': len(posts_by_link_count['weak']),
            'optimal_3_8': len(posts_by_link_count['optimal']),
            'over_linked_9plus': len(posts_by_link_count['over_linked'])
        },
        'posts_by_link_count': posts_by_link_count,
        'orphaned_posts_count': len(orphaned),
        'orphaned_posts': orphaned[:10],
        'weak_pairs_count': len(weak_pairs),
        'weak_pairs_sample': weak_pairs[:20]
    }

    OUTPUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n✓ Report written to {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"  Total posts: {report['total_posts']}")
    print(f"  Weak (0-2 links): {report['by_link_count']['weak_0_2']}")
    print(f"  Optimal (3-8 links): {report['by_link_count']['optimal_3_8']}")
    print(f"  Over-linked (9+ links): {report['by_link_count']['over_linked_9plus']}")
    print(f"  Weak pairs identified: {report['weak_pairs_count']}")
    print(f"  Orphaned posts: {report['orphaned_posts_count']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
