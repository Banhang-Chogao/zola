#!/usr/bin/env python3
"""
Audit Editor post index for completeness.

Compares:
1. All article markdown files in content/**/*.md
2. All posts with date >= 2026-06-27 (recent posts)
3. Posts currently shown in Editor (baked metadata in template)

Generates report showing missing posts and metadata gaps.
"""
import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Repo root
REPO_ROOT = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "content"
EDITOR_TEMPLATE = REPO_ROOT / "templates" / "editor.html"
EDITOR_PUBLIC = REPO_ROOT / "public" / "editor" / "index.html"  # Baked metadata from build output

# Sections that should be included in Editor
# (based on templates/editor.html article scan)
EDITOR_SECTIONS = {"posting", "baochi", "khoa-hoc", "the-gioi", "cong-nghe", "du-lich", "ngan-hang", "bao-hiem", "doi-song", "the-thao"}

# Sections that are NOT articles (should be skipped)
SKIP_SECTIONS = {
    "admin", "admin-author", "admin-countdown", "editor",
    "insights", "stats", "pages", "tools",  # Pages, tools, admin (usually not articles)
    "changelog", "archive"  # Special sections
}

# All content sections (should be discovered, not hardcoded)
def discover_sections():
    """Discover all sections in content/"""
    sections = set()
    if CONTENT_DIR.exists():
        for item in CONTENT_DIR.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                sections.add(item.name)
    return sorted(sections)


def parse_toml_date(date_str):
    """Parse TOML date string (ISO 8601)."""
    try:
        if isinstance(date_str, str):
            # Remove timezone info if present
            date_str = date_str.split("+")[0].split("-")[:-1]
            if len(date_str) > 1:
                date_str = "-".join(date_str)
            else:
                date_str = date_str[0]
            return datetime.fromisoformat(date_str.strip('"')).date()
    except Exception:
        pass
    return None


def extract_frontmatter(content):
    """Extract frontmatter from markdown file."""
    fm_match = re.match(r'^\+\+\+\n([\s\S]*?)\n\+\+\+', content)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)
    fm = {
        "title": "",
        "date": None,
        "categories": [],
        "tags": [],
        "draft": False,
    }

    section = "root"
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line == "[taxonomies]":
            section = "taxonomies"
            continue
        elif line == "[extra]":
            section = "extra"
            continue

        if "=" not in line:
            continue

        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()

        # Parse value
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip('"\'') for v in val[1:-1].split(",")]
        elif val == "true":
            val = True
        elif val == "false":
            val = False

        if section == "root":
            if key == "title":
                fm["title"] = val
            elif key == "date":
                fm["date"] = parse_toml_date(val)
            elif key == "draft":
                fm["draft"] = val
        elif section == "taxonomies":
            if key == "categories" and isinstance(val, list):
                fm["categories"] = val
            elif key == "tags" and isinstance(val, list):
                fm["tags"] = val
        elif section == "extra":
            if key == "draft":
                fm["draft"] = val

    return fm


def scan_article_files():
    """Scan all article markdown files."""
    articles = []

    if not CONTENT_DIR.exists():
        return articles

    for md_file in CONTENT_DIR.rglob("*.md"):
        if md_file.name == "_index.md" or md_file.name.startswith("_"):
            continue

        section = md_file.parent.name
        slug = md_file.stem

        try:
            content = md_file.read_text(encoding="utf-8")
            fm = extract_frontmatter(content)

            if not fm:
                continue

            articles.append({
                "slug": slug,
                "section": section,
                "path": str(md_file.relative_to(REPO_ROOT)),
                "title": fm.get("title", ""),
                "date": fm.get("date"),
                "categories": fm.get("categories", []),
                "tags": fm.get("tags", []),
                "draft": fm.get("draft", False),
            })
        except Exception as e:
            print(f"Error parsing {md_file}: {e}", file=sys.stderr)

    return articles


def extract_baked_metadata():
    """Extract baked metadata from editor.html (public build output preferred)."""
    baked = []

    # Try public build output first (has actual baked data), then fallback to template
    files_to_try = [EDITOR_PUBLIC, EDITOR_TEMPLATE]

    for filepath in files_to_try:
        if not filepath.exists():
            continue

        try:
            content = filepath.read_text(encoding="utf-8")

            # Find the posts-metadata script block
            match = re.search(
                r'<script type="application/json" id="posts-metadata">(.*?)</script>',
                content,
                re.DOTALL
            )
            if match:
                json_text = match.group(1)
                # Clean up whitespace while preserving JSON structure
                json_text = re.sub(r'\s+', ' ', json_text).strip()
                if json_text and json_text != '[ ]':
                    try:
                        baked = json.loads(json_text)
                        if baked:  # Successfully parsed non-empty data
                            return baked
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            continue

    return baked


def main():
    """Main audit routine."""
    print("=" * 80)
    print("SEOMONEY EDITOR POST INDEX AUDIT")
    print("=" * 80)
    print()

    # Discover all sections
    all_sections = discover_sections()
    print(f"All sections found: {all_sections}")
    print(f"Editor sections (hardcoded): {sorted(EDITOR_SECTIONS)}")
    print(f"Skip sections: {sorted(SKIP_SECTIONS)}")
    print()

    # Scan all articles
    articles = scan_article_files()
    print(f"Total articles found: {len(articles)}")

    # Group by section
    articles_by_section = defaultdict(list)
    for a in articles:
        articles_by_section[a["section"]].append(a)

    print("\nArticles by section:")
    for section in sorted(articles_by_section.keys()):
        count = len(articles_by_section[section])
        print(f"  {section}: {count}")

    # Get baked metadata
    baked = extract_baked_metadata()
    baked_slugs = {b.get("slug") for b in baked if b.get("slug")}

    print(f"\nBaked metadata in editor.html: {len(baked)} posts")
    print(f"Unique slugs in baked metadata: {len(baked_slugs)}")

    # Recent posts (>= 2026-06-27)
    recent_cutoff = datetime(2026, 6, 27).date()
    recent_articles = [a for a in articles if a.get("date") and a["date"] >= recent_cutoff]
    recent_articles_sorted = sorted(recent_articles, key=lambda x: x["date"], reverse=True)

    print(f"\nRecent articles (date >= {recent_cutoff}): {len(recent_articles)}")
    for a in recent_articles_sorted:
        print(f"  {a['date']} | {a['section']:15} | {a['slug']:50} | {a['title']}")

    # Check which recent articles are in Editor
    missing_from_editor = []
    for a in recent_articles:
        if a["slug"] not in baked_slugs:
            missing_from_editor.append(a)

    print(f"\n⚠️ Recent articles NOT in Editor baked metadata: {len(missing_from_editor)}")
    for a in sorted(missing_from_editor, key=lambda x: x["date"], reverse=True):
        section_status = "SKIP" if a["section"] in SKIP_SECTIONS else "NOT LOADED"
        status = "DRAFT" if a["draft"] else section_status
        print(f"  {a['date']} | {status:15} | {a['section']:15} | {a['slug']:50}")

    # Check sections not included in Editor
    missing_sections = set()
    for a in articles:
        if a["section"] not in EDITOR_SECTIONS and a["section"] not in SKIP_SECTIONS:
            missing_sections.add(a["section"])

    print(f"\n⚠️ Content sections NOT scanned by Editor template: {len(missing_sections)}")
    for section in sorted(missing_sections):
        count = len(articles_by_section[section])
        drafts = sum(1 for a in articles_by_section[section] if a["draft"])
        published = count - drafts
        print(f"  {section:20} | {published} published + {drafts} draft")

    # Specific checks
    print("\n" + "=" * 80)
    print("SPECIFIC CHECKS")
    print("=" * 80)

    # Check codon article
    codon = next((a for a in articles if "codon" in a["slug"]), None)
    if codon:
        in_editor = codon["slug"] in baked_slugs
        print(f"\n✓ Codon article found: {codon['path']}")
        print(f"  Date: {codon['date']}, Section: {codon['section']}")
        print(f"  In Editor: {'YES' if in_editor else 'NO'}")
        if not in_editor:
            print(f"  Reason: Section '{codon['section']}' not in EDITOR_SECTIONS")
    else:
        print("\n✗ Codon article NOT found")

    # Check Hubble article
    hubble = next((a for a in articles if "hubble" in a["slug"]), None)
    if hubble:
        in_editor = hubble["slug"] in baked_slugs
        print(f"\n✓ Hubble article found: {hubble['path']}")
        print(f"  Date: {hubble['date']}, Section: {hubble['section']}")
        print(f"  In Editor: {'YES' if in_editor else 'NO'}")
        if not in_editor:
            print(f"  Reason: Not in baked metadata (cache issue or build stale)")
    else:
        print("\n✗ Hubble article NOT found")

    # Generate report JSON
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_articles": len(articles),
        "total_baked": len(baked),
        "recent_articles": len(recent_articles),
        "missing_from_editor": len(missing_from_editor),
        "missing_sections": list(sorted(missing_sections)),
        "missing_articles": [
            {
                "slug": a["slug"],
                "section": a["section"],
                "date": a["date"].isoformat() if a["date"] else None,
                "title": a["title"],
                "path": a["path"],
                "reason": "SKIP" if a["section"] in SKIP_SECTIONS else f"Section not in EDITOR_SECTIONS"
            }
            for a in sorted(missing_from_editor, key=lambda x: x["date"], reverse=True)
        ],
        "recent_articles_list": [
            {
                "slug": a["slug"],
                "section": a["section"],
                "date": a["date"].isoformat() if a["date"] else None,
                "title": a["title"],
                "path": a["path"],
                "in_editor": a["slug"] in baked_slugs,
            }
            for a in recent_articles_sorted
        ]
    }

    report_path = REPO_ROOT / "data" / "editor-recent-posts-audit.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"\n✓ Report saved to {report_path.relative_to(REPO_ROOT)}")

    return 0 if not missing_from_editor else 1


if __name__ == "__main__":
    sys.exit(main())
