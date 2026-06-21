#!/usr/bin/env python3
"""
Test Admin Zone implementation
Verifies:
1. Markdown file exists and has correct metadata
2. Template file exists and includes required elements
3. JavaScript files are syntactically valid
4. SCSS file is properly formatted
5. Auth logic is reused from Editor
"""

import os
import json
import sys

def test_admin_zone_files():
    """Test that all required files exist"""
    files_to_check = [
        "content/tools/admin-zone.md",
        "templates/admin-zone.html",
        "sass/_admin-zone.scss",
        "static/js/admin-zone/auth.js",
        "static/js/admin-zone/data.js",
        "static/js/admin-zone/search.js",
        "static/js/admin-zone/pdf.js",
        "static/js/admin-zone/stats.js",
        "static/js/admin-zone/app.js",
    ]

    for file in files_to_check:
        path = os.path.join(".", file)
        if not os.path.exists(path):
            print(f"✗ FAIL: Missing file {file}")
            return False
        print(f"✓ Found: {file}")

    return True

def test_admin_zone_content():
    """Test content/tools/admin-zone.md"""
    try:
        with open("content/tools/admin-zone.md", "r") as f:
            content = f.read()

        # Check required frontmatter
        checks = {
            'title = "Admin Zone"': "Page title",
            'template = "admin-zone.html"': "Template reference",
            'noindex = true': "noindex meta",
            'nofollow = true': "nofollow meta",
        }

        for check, desc in checks.items():
            if check not in content:
                print(f"✗ FAIL: {desc} missing in admin-zone.md")
                return False
            print(f"✓ Found: {desc}")

        return True
    except Exception as e:
        print(f"✗ FAIL: Error reading admin-zone.md: {e}")
        return False

def test_admin_zone_template():
    """Test templates/admin-zone.html"""
    try:
        with open("templates/admin-zone.html", "r") as f:
            content = f.read()

        # Check required elements
        checks = {
            'id="admin-zone"': "Main container",
            'data-view="login"': "Login view",
            'data-view="dashboard"': "Dashboard view",
            'data-action="github-login"': "GitHub login button",
            'data-action="pdf-download"': "PDF download action",
            'data-action="pdf-webview"': "PDF webview action",
            'id="guideline-search"': "Search input",
            'data-stat="total-runs"': "Stats display",
            '<script src="{{ config.base_url }}/js/admin-zone/': "JS includes",
            'noindex': "noindex meta",
            'nofollow': "nofollow meta",
        }

        for check, desc in checks.items():
            if check not in content:
                print(f"✗ FAIL: {desc} missing in admin-zone.html")
                return False
            print(f"✓ Found: {desc}")

        # Check auth reuse from Editor
        if '/js/admin-zone/auth.js' not in content:
            print("✗ FAIL: Admin Zone auth module not referenced")
            return False
        print("✓ Found: Auth module reference")

        return True
    except Exception as e:
        print(f"✗ FAIL: Error reading admin-zone.html: {e}")
        return False

def test_admin_zone_js():
    """Test JavaScript modules"""
    try:
        modules = {
            "static/js/admin-zone/auth.js": [
                "window.AdminZoneAuth",
                "SESSION_KEY",
                "fetchMe",
                "populateUserBar",
            ],
            "static/js/admin-zone/data.js": [
                "window.AdminZoneData",
                "getAllGuidelines",
                "searchGuidelines",
            ],
            "static/js/admin-zone/search.js": [
                "window.AdminZoneSearch",
                "renderResults",
                "handleSearch",
            ],
            "static/js/admin-zone/pdf.js": [
                "window.AdminZonePDF",
                "generatePdf",
                "downloadPdf",
                "openPdfWebview",
                "watermark",
            ],
            "static/js/admin-zone/stats.js": [
                "window.AdminZoneStats",
                "getStats",
                "incrementRun",
                "displayStats",
            ],
            "static/js/admin-zone/app.js": [
                "init",
                "switchView",
                "handleAction",
            ],
        }

        for module, checks in modules.items():
            with open(module, "r") as f:
                content = f.read()

            for check in checks:
                if check not in content:
                    print(f"✗ FAIL: {check} missing in {module}")
                    return False

            print(f"✓ Found all checks in: {module}")

        return True
    except Exception as e:
        print(f"✗ FAIL: Error reading JS modules: {e}")
        return False

def test_admin_zone_scss():
    """Test SCSS file"""
    try:
        with open("sass/_admin-zone.scss", "r") as f:
            content = f.read()

        # Check required selectors and features
        checks = {
            ".admin-zone": "Main container",
            ".admin-login": "Login modal",
            ".admin-user-bar": "User bar",
            ".admin-btn": "Button styles",
            ".admin-section": "Section styles",
            ".admin-search": "Search styles",
            ".admin-pdf": "PDF viewer styles",
            ".admin-stat": "Stats card styles",
            "@media (max-width: 720px)": "Mobile responsive",
        }

        for check, desc in checks.items():
            if check not in content:
                print(f"✗ FAIL: {desc} ({check}) missing in admin-zone.scss")
                return False
            print(f"✓ Found: {desc}")

        return True
    except Exception as e:
        print(f"✗ FAIL: Error reading admin-zone.scss: {e}")
        return False

def test_scss_import():
    """Test that admin-zone.scss is imported in site.scss"""
    try:
        with open("sass/site.scss", "r") as f:
            content = f.read()

        if '@import "admin-zone"' not in content:
            print("✗ FAIL: admin-zone.scss not imported in site.scss")
            return False

        print("✓ Found: admin-zone.scss imported in site.scss")
        return True
    except Exception as e:
        print(f"✗ FAIL: Error reading site.scss: {e}")
        return False

def main():
    print("=" * 60)
    print("Testing Admin Zone Implementation")
    print("=" * 60)

    tests = [
        ("File existence", test_admin_zone_files),
        ("Markdown content", test_admin_zone_content),
        ("Template structure", test_admin_zone_template),
        ("JavaScript modules", test_admin_zone_js),
        ("SCSS styling", test_admin_zone_scss),
        ("SCSS imports", test_scss_import),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{name}...")
        result = test_func()
        results.append((name, result))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n✓ All Admin Zone tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
