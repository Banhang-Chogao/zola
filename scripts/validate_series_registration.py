#!/usr/bin/env python3
"""
Validate that all *-series.json files are properly registered in templates.
Prevents V8-class failures where new series causes zola build to fail.

Usage:
  python3 scripts/validate_series_registration.py

Exit codes:
  0: All series registered and syntax valid
  1: Configuration error or warning
  2: Validation failed — unregistered series or syntax error
"""

import json
import re
import sys
from pathlib import Path


def get_series_manifests():
    """Get all *-series.json files from data/"""
    data_dir = Path("data")
    series = {}

    for manifest_file in sorted(data_dir.glob("*-series.json")):
        series_id = manifest_file.stem.replace("-series", "")
        try:
            content = json.loads(manifest_file.read_text())
            series[series_id] = content
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {manifest_file}: {e}")
            return None

    return series


def get_registered_series():
    """Extract registered series from series-listing.html load_data() calls"""
    template_file = Path("templates/macros/series-listing.html")

    if not template_file.exists():
        print(f"❌ Template not found: {template_file}")
        return None

    content = template_file.read_text()
    registered = set()

    # Find all load_data(path="data/...-series.json") calls
    # Pattern: load_data(path="data/SERIES_ID-series.json", ...)
    for match in re.finditer(
        r'load_data\s*\(\s*path\s*=\s*"data/([a-z0-9\-]+)-series\.json"',
        content
    ):
        series_id = match.group(1)
        registered.add(series_id)

    if not registered:
        print(f"⚠️  Could not find any load_data() calls in {template_file}")
        print("   Pattern: load_data(path=\"data/SERIES_ID-series.json\")")
        return set()

    return registered


def check_tera_syntax():
    """Verify correct Tera syntax (from=/to=, NOT old=/new=)"""
    issues = []

    tera_files = [
        "templates/macros/series-listing.html",
        "templates/macros/series-nav.html",
        "templates/page.html",
    ]

    bad_patterns = [
        (r'replace\(\s*old\s*=', "replace(old=...) → use replace(from=... to=...)"),
        (r'replace\(\s*new\s*=', "replace(new=...) → use replace(from=... to=...)"),
        (r'split\(\s*delimiter\s*=', "split(delimiter=...) → use split(pattern=...)"),
    ]

    for template_file_str in tera_files:
        template_file = Path(template_file_str)
        if not template_file.exists():
            continue

        content = template_file.read_text()

        for pattern, msg in bad_patterns:
            if re.search(pattern, content):
                issues.append(f"{template_file}: {msg}")

    return issues


def main():
    print("📋 Validating series template registration...\n")

    # Step 1: Load series manifests
    print("Step 1: Loading series manifests...")
    series_files = get_series_manifests()
    if series_files is None:
        return 2

    if not series_files:
        print("  ℹ️  No series files found (OK if none defined yet)")
    else:
        print(f"  ✓ Found {len(series_files)} series: {sorted(series_files.keys())}")

    # Step 2: Load registered series
    print("\nStep 2: Reading registered series from templates...")
    registered = get_registered_series()
    if registered is None:
        return 2

    print(f"  ✓ Found {len(registered)} registered: {sorted(registered) if registered else '(none)'}")

    # Step 3: Check for unregistered series
    print("\nStep 3: Checking for unregistered series...")
    unregistered = set(series_files.keys()) - registered
    orphaned = registered - set(series_files.keys())

    errors = []

    if unregistered:
        print(f"  ❌ Unregistered series: {sorted(unregistered)}")
        print()
        print("     Fix: Add to templates/macros/series-listing.html manifests[] array:")
        for series_id in sorted(unregistered):
            manifest = series_files[series_id]
            title = manifest.get("title", series_id.replace("-", " ").title())
            print(f"       {{ id: \"{series_id}\", title: \"{title}\" }},")
        errors.append("Unregistered series")

    if orphaned:
        print(f"  ⚠️  Orphaned registrations (no .json file): {sorted(orphaned)}")
        print("     These series are registered but have no manifest file.")
        # Not fatal, but suspicious

    # Step 4: Check Tera syntax
    print("\nStep 4: Checking Tera filter syntax...")
    syntax_issues = check_tera_syntax()
    if syntax_issues:
        for issue in syntax_issues:
            print(f"  ❌ {issue}")
        errors.append("Tera syntax error")
    else:
        print("  ✓ All Tera filters use correct syntax (from=/to=)")

    # Final result
    print()
    if errors:
        print(f"❌ FAILED: {len(errors)} issue(s) found")
        return 2
    else:
        if series_files:
            print(f"✅ SUCCESS: All {len(series_files)} series properly registered with valid syntax")
        else:
            print("✅ OK: No series to validate")
        return 0


if __name__ == "__main__":
    sys.exit(main())
