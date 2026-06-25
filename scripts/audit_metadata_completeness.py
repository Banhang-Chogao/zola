#!/usr/bin/env python3
"""
Audit metadata completeness for all posting files.

Scans all .md files in content/posting/ for:
- Title (10-65 chars)
- Description (50-160 chars)
- Date
- Categories
- SEO keyword
- Thumbnail/OG image

Outputs: data/audit-metadata.json
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT_FILE = ROOT / "data" / "audit-metadata.json"


def _extract_frontmatter(content: str) -> dict[str, Any]:
    """Extract TOML frontmatter from markdown."""
    match = re.match(r'^\+\+\+\n(.*?)\n\+\+\+', content, re.DOTALL)
    if not match:
        return {}

    fm_text = match.group(1)
    result = {}

    # Simple TOML parsing (no heavy deps)
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Handle title, description, date
        if line.startswith('title'):
            match = re.search(r'= ["\'](.+?)["\']', line)
            if match:
                result['title'] = match.group(1)
        elif line.startswith('description'):
            match = re.search(r'= ["\'](.+?)["\']', line)
            if match:
                result['description'] = match.group(1)
        elif line.startswith('date'):
            match = re.search(r'= (.+)', line)
            if match:
                result['date'] = match.group(1).strip()
        elif line.startswith('seo_keyword'):
            match = re.search(r'= ["\'](.+?)["\']', line)
            if match:
                result['seo_keyword'] = match.group(1)
        elif line.startswith('thumbnail'):
            match = re.search(r'= ["\'](.+?)["\']', line)
            if match:
                result['thumbnail'] = match.group(1)

    # Handle categories
    if '[taxonomies]' in fm_text:
        cat_match = re.search(r'categories\s*=\s*\[(.*?)\]', fm_text, re.DOTALL)
        if cat_match:
            cats_str = cat_match.group(1)
            cats = [c.strip().strip('"\'') for c in cats_str.split(',') if c.strip()]
            result['categories'] = cats

    return result


def _audit_file(file_path: Path) -> dict[str, Any]:
    """Audit a single markdown file."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return {'slug': file_path.stem, 'error': str(e)}

    fm = _extract_frontmatter(content)
    slug = file_path.stem

    issues = []

    # Check title
    title = fm.get('title', '')
    if not title:
        issues.append('missing_title')
    elif len(title) > 65:
        issues.append(f'title_too_long_{len(title)}')
    elif len(title) < 10:
        issues.append(f'title_too_short_{len(title)}')

    # Check description
    desc = fm.get('description', '')
    if not desc:
        issues.append('missing_description')
    elif len(desc) > 160:
        issues.append(f'description_too_long_{len(desc)}')
    elif len(desc) < 50:
        issues.append(f'description_too_short_{len(desc)}')

    # Check date
    if not fm.get('date'):
        issues.append('missing_date')

    # Check categories
    cats = fm.get('categories', [])
    if not cats:
        issues.append('missing_categories')
    elif 'Tất cả' not in cats:
        issues.append('missing_tat_ca_category')

    # Check SEO keyword
    if not fm.get('seo_keyword'):
        issues.append('missing_seo_keyword')

    # Check thumbnail
    if not fm.get('thumbnail'):
        issues.append('missing_thumbnail')

    return {
        'slug': slug,
        'file': str(file_path.relative_to(ROOT)),
        'issues': issues,
        'metadata': {
            'title': title,
            'description': desc,
            'date': fm.get('date'),
            'categories': cats,
            'seo_keyword': fm.get('seo_keyword'),
            'thumbnail': fm.get('thumbnail')
        }
    }


def main():
    """Run audit."""
    if not CONTENT_DIR.exists():
        print(f"Content dir not found: {CONTENT_DIR}")
        return 1

    # Find all posting .md files
    files = sorted(CONTENT_DIR.glob('*.md'))
    print(f"Scanning {len(files)} posting files...")

    results = []
    for f in files:
        result = _audit_file(f)
        results.append(result)
        if result.get('issues'):
            print(f"  ⚠️  {result['slug']}: {len(result['issues'])} issues")

    # Categorize by issue type
    by_issue = {}
    critical = []

    for result in results:
        if 'error' in result:
            if 'error' not in by_issue:
                by_issue['error'] = []
            by_issue['error'].append(result['slug'])
            critical.append(result)
            continue

        for issue in result['issues']:
            if issue not in by_issue:
                by_issue[issue] = []
            by_issue[issue].append(result['slug'])
            critical.append(result)

    # Generate report
    report = {
        'audit_at': datetime.now(timezone.utc).isoformat(),
        'total_files': len(files),
        'files_with_issues': len([r for r in results if r.get('issues')]),
        'by_issue': by_issue,
        'critical_issues': critical[:20],  # First 20
        'summary': {
            'missing_title': len(by_issue.get('missing_title', [])),
            'missing_description': len(by_issue.get('missing_description', [])),
            'missing_date': len(by_issue.get('missing_date', [])),
            'missing_categories': len(by_issue.get('missing_categories', [])),
            'missing_seo_keyword': len(by_issue.get('missing_seo_keyword', [])),
            'missing_thumbnail': len(by_issue.get('missing_thumbnail', [])),
        }
    }

    OUTPUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n✓ Report written to {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"  Total files: {report['total_files']}")
    print(f"  Files with issues: {report['files_with_issues']}")
    print(f"  Summary: {report['summary']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
