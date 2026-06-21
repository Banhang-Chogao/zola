#!/usr/bin/env python3
"""
Old URL Audit — Detect github.io and /zola path references after domain migration.

Purpose: Verify no stale domain references remain after migration to seomoney.org.
Scans:
1. public/sitemap.xml for old domain URLs
2. public/**/*.html for hardcoded old domain links
3. static/ for old CNAME or migration artifacts

Exit codes:
- 0: Success (zero old URLs found or non-blocking report)
- 1: Warning (old URLs found but non-critical)
"""

import re
import json
from pathlib import Path
from datetime import datetime


def scan_sitemap():
    """Scan sitemap.xml for old domain references."""
    stale_urls = []

    sitemap = Path("public/sitemap.xml")
    if not sitemap.exists():
        return stale_urls

    try:
        with open(sitemap, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for old domain patterns in <loc> tags
        patterns = [
            r'github\.io',
            r'/zola/',  # Old path structure
            r'duynguyenlog',
            r'banhang-chogao\.github\.io'
        ]

        for pattern in patterns:
            matches = re.findall(rf'<loc>([^<]*{pattern}[^<]*)</loc>', content)
            stale_urls.extend(matches)

    except Exception as e:
        print(f"Warning: Could not parse sitemap: {e}")

    return stale_urls


def scan_html_files():
    """Scan public/**/*.html for hardcoded old domain links."""
    stale_urls = []

    public_dir = Path("public")
    if not public_dir.exists():
        return stale_urls

    patterns = [
        r'href=["\']https?://[^"\']*github\.io',
        r'href=["\']https?://[^"\']*banhang-chogao',
        r'href=["\'][^"\']*zola["\']',  # Path with /zola/
        r'content=["\']https?://[^"\']*github\.io'
    ]

    html_files = list(public_dir.rglob("*.html"))

    for html_file in html_files:
        try:
            with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    stale_urls.extend([{
                        "url": m,
                        "file": str(html_file.relative_to(public_dir)),
                        "type": "html_attribute"
                    } for m in matches])
        except Exception as e:
            pass

    return stale_urls


def scan_static():
    """Scan static/ for migration artifacts."""
    artifacts = []

    static_dir = Path("static")
    if not static_dir.exists():
        return artifacts

    # Check for old CNAME file
    cname_file = static_dir / "CNAME"
    if cname_file.exists():
        with open(cname_file, "r") as f:
            content = f.read().strip()
            if content and "seomoney.org" not in content:
                artifacts.append({
                    "file": "static/CNAME",
                    "content": content,
                    "issue": "CNAME points to old domain"
                })

    # Check for migration notes or READMEs
    for txt_file in static_dir.glob("*.txt"):
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                if any(p in f.read() for p in ["github.io", "banhang-chogao", "zola"]):
                    artifacts.append({
                        "file": str(txt_file),
                        "issue": "Contains old domain reference"
                    })
        except Exception:
            pass

    return artifacts


def main():
    print("Auditing for old domain references...")
    print()

    sitemap_stale = scan_sitemap()
    html_stale = scan_html_files()
    artifacts = scan_static()

    total_stale = len(sitemap_stale) + len(html_stale) + len(artifacts)

    print(f"🔍 Old URL Audit Report")
    print(f"=" * 60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()
    print(f"Stale URLs in sitemap:  {len(sitemap_stale)}")
    print(f"Stale URLs in HTML:     {len(html_stale)}")
    print(f"Migration artifacts:    {len(artifacts)}")
    print(f"Total stale references: {total_stale}")
    print()

    if total_stale > 0:
        print("⚠️  Old references found:")
        if sitemap_stale:
            print(f"\nSitemap ({len(sitemap_stale)}):")
            for url in sitemap_stale[:5]:
                print(f"  • {url[:80]}")
            if len(sitemap_stale) > 5:
                print(f"  ... and {len(sitemap_stale) - 5} more")

        if html_stale:
            print(f"\nHTML files ({len(html_stale)}):")
            for item in html_stale[:5]:
                print(f"  • {item['file']}: {item['url'][:50]}")
            if len(html_stale) > 5:
                print(f"  ... and {len(html_stale) - 5} more")

        if artifacts:
            print(f"\nArtifacts ({len(artifacts)}):")
            for artifact in artifacts:
                print(f"  • {artifact['file']}: {artifact.get('issue', 'Unknown')}")
    else:
        print("✓ No stale domain references found")

    # Save report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    report_file = reports_dir / f"old-urls-audit-{datetime.utcnow().strftime('%Y-%m-%d')}.json"
    report_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stale_in_sitemap": len(sitemap_stale),
        "stale_in_html": len(html_stale),
        "artifacts": len(artifacts),
        "total_stale": total_stale,
        "status": "CLEAN" if total_stale == 0 else "WARN",
        "samples": {
            "sitemap": sitemap_stale[:3],
            "html": [h for h in html_stale[:3]],
            "artifacts": artifacts
        }
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print()
    print(f"Report: {report_file}")

    return 0 if total_stale == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
