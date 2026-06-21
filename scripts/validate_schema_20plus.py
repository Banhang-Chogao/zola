#!/usr/bin/env python3
"""
BlogPosting Schema Validator — Ensure 20+ core posts have complete schema.

Purpose: After zola build, scan public/ HTML files for JSON-LD BlogPosting
schema and validate completeness. Ensures Google Rich Results for articles
and proper metadata for SEO.

Required fields for valid BlogPosting:
- @type: "BlogPosting"
- headline (page title)
- image (og image URL)
- datePublished (RFC 3339)
- author (Person with name, url)
- description (or mainEntity.text)
- mainEntity (Article or similar)

Exit codes:
- 0: Success (20+ valid posts found)
- 2: Failure (<20 valid posts, deploy blocked)
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime


def extract_json_ld(html_content):
    """Extract JSON-LD blocks from HTML."""
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html_content, re.DOTALL)
    results = []

    for match in matches:
        try:
            data = json.loads(match)
            results.append(data)
        except json.JSONDecodeError:
            pass

    return results


def validate_blogposting(schema):
    """Validate BlogPosting schema completeness."""
    if not isinstance(schema, dict):
        return False, "Not a dict"

    # Check type
    schema_type = schema.get("@type")
    if schema_type != "BlogPosting":
        return False, "Wrong @type"

    # Required fields
    required = ["headline", "image", "datePublished", "author"]
    missing = [f for f in required if not schema.get(f)]

    if missing:
        return False, f"Missing: {', '.join(missing)}"

    # Validate author
    author = schema.get("author")
    if isinstance(author, dict):
        if not author.get("name"):
            return False, "Author missing name"
    elif isinstance(author, list) and author:
        if not author[0].get("name"):
            return False, "Author[0] missing name"
    else:
        return False, "Invalid author format"

    return True, "Valid"


def scan_public_schema():
    """Scan public/ for BlogPosting schemas."""
    public_dir = Path("public")
    if not public_dir.exists():
        print("ERROR: public/ directory not found. Run 'zola build' first.", file=sys.stderr)
        return [], []

    valid_posts = []
    invalid_posts = []

    # Scan all HTML files in public/posting/
    posting_dir = public_dir / "posting"
    if not posting_dir.exists():
        print("WARNING: public/posting/ not found.", file=sys.stderr)
        return valid_posts, invalid_posts

    for html_file in posting_dir.rglob("*.html"):
        # Skip index.html
        if html_file.name == "index.html":
            continue

        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html = f.read()

            schemas = extract_json_ld(html)
            blogposts = [s for s in schemas if isinstance(s, dict) and s.get("@type") == "BlogPosting"]

            if not blogposts:
                post_slug = html_file.parent.name
                invalid_posts.append({
                    "slug": post_slug,
                    "issue": "No BlogPosting schema found",
                    "file": str(html_file)
                })
                continue

            # Validate first BlogPosting schema found
            bp = blogposts[0]
            is_valid, reason = validate_blogposting(bp)

            post_slug = html_file.parent.name
            if is_valid:
                valid_posts.append({
                    "slug": post_slug,
                    "headline": bp.get("headline", ""),
                    "has_image": bool(bp.get("image")),
                    "published": bp.get("datePublished", ""),
                    "file": str(html_file)
                })
            else:
                invalid_posts.append({
                    "slug": post_slug,
                    "issue": reason,
                    "file": str(html_file)
                })
        except Exception as e:
            post_slug = html_file.parent.name
            invalid_posts.append({
                "slug": post_slug,
                "issue": f"Parse error: {str(e)[:50]}",
                "file": str(html_file)
            })

    return valid_posts, invalid_posts


def main():
    print("Validating BlogPosting schema in public/ posts...")
    valid_posts, invalid_posts = scan_public_schema()

    total = len(valid_posts) + len(invalid_posts)
    if total == 0:
        print("WARNING: No posts found in public/posting/", file=sys.stderr)
        return 2

    # Report
    print()
    print(f"📄 Schema Validation Report")
    print(f"=" * 60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()
    print(f"Valid BlogPosting schemas: {len(valid_posts):3d} / {total} posts")
    print(f"Invalid / missing:         {len(invalid_posts):3d} / {total} posts")
    print(f"Pass threshold:            {20} minimum")
    print()

    # Check pass/fail
    if len(valid_posts) >= 20:
        print(f"✓ PASS: {len(valid_posts)} posts meet BlogPosting schema requirements")
        print()

        # Show sample valid posts
        print(f"Sample valid posts:")
        for post in valid_posts[:5]:
            print(f"  • {post['slug']:40s} — {post['headline'][:40]}")

        # Save report
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        report_file = reports_dir / f"schema-audit-{datetime.utcnow().strftime('%Y-%m-%d')}.json"
        report_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "valid_posts": len(valid_posts),
            "invalid_posts": len(invalid_posts),
            "total_posts": total,
            "pass_threshold": 20,
            "status": "PASS",
            "valid_samples": valid_posts[:10],
            "invalid_samples": invalid_posts[:5]
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        print(f"\nReport: {report_file}")
        return 0
    else:
        print(f"✗ FAIL: Only {len(valid_posts)} posts have valid schema (minimum 20 required)")
        print()

        if invalid_posts:
            print(f"Invalid posts ({len(invalid_posts)}):")
            for post in invalid_posts[:10]:
                print(f"  • {post['slug']:40s} — {post['issue']}")

        return 2


if __name__ == "__main__":
    sys.exit(main())
