#!/usr/bin/env python3
"""
Verify that built public HTML contains no fake/manual ad placeholder text.
Exit code: 0 if clean, 1 if fake placeholders found.
"""
import os
import re
import sys
from pathlib import Path

# Fake ad placeholder patterns to detect
FAKE_AD_PATTERNS = [
    "Đặt banner quảng cáo",
    "Khu vực này sẽ hiển thị quảng cáo",
    "adsense placeholder",
    "ad placeholder",
    "manual ad",
    "sponsored placeholder",
    "Nhấp để về trang chủ",
    "banner quảng cáo của bạn tại đây",
]

def check_file(file_path):
    """Check a single HTML file for fake ad placeholders."""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for pattern in FAKE_AD_PATTERNS:
                if pattern.lower() in content.lower():
                    # Count occurrences
                    count = content.lower().count(pattern.lower())
                    issues.append((pattern, count))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    return issues

def main():
    public_dir = Path("public")
    if not public_dir.exists():
        print("❌ Error: public/ directory not found. Run 'zola build' first.", file=sys.stderr)
        return 1

    found_issues = False
    issue_map = {}

    # Scan all HTML files in public/
    for html_file in public_dir.rglob("*.html"):
        issues = check_file(html_file)
        if issues:
            found_issues = True
            relative_path = html_file.relative_to(public_dir)
            for pattern, count in issues:
                if pattern not in issue_map:
                    issue_map[pattern] = []
                issue_map[pattern].append((str(relative_path), count))

    if found_issues:
        print("❌ Found fake ad placeholders in public HTML:\n")
        for pattern, locations in issue_map.items():
            print(f"  Pattern: '{pattern}'")
            for path, count in locations:
                print(f"    - {path} ({count} occurrence{'s' if count > 1 else ''})")
        print()
        return 1
    else:
        print("✅ No fake ad placeholders found in public HTML")
        return 0

if __name__ == "__main__":
    sys.exit(main())
