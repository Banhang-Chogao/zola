#!/usr/bin/env python3
"""Test search configuration for CSE scope and homepage categories."""

from pathlib import Path
import sys

def test_cse_configuration():
    """Verify CSE is configured to search only seomoney.org."""
    config = Path("config.toml")
    with open(config, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for CSE configuration
    assert "google_cse_cx" in content, "Missing google_cse_cx configuration"
    assert 'google_cse_cx = "533c848cb0eb14de2"' in content, "CSE CX value should be configured"

    print("✓ CSE is configured in config.toml")

def test_cse_siteSearch_in_editor():
    """Verify editor.js adds site:seomoney.org to CSE queries."""
    editor_js = Path("static/js/editor.js")
    with open(editor_js, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for site:seomoney.org restriction
    assert "site:seomoney.org" in content, "Should add site:seomoney.org to CSE queries"
    assert "cse.google.com/cse?cx=" in content, "Should use Google CSE"

    print("✓ Editor adds site:seomoney.org restriction to CSE queries")

def test_homepage_uses_real_categories():
    """Verify homepage uses dynamically generated categories."""
    index_html = Path("templates/index.html")
    with open(index_html, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for dynamic category loading
    assert "homepage-categories.json" in content, "Should load homepage-categories.json"
    assert "homepage_categories" in content, "Should use homepage_categories variable"
    assert "for cat_item in homepage_categories.categories" in content, "Should loop through categories"

    # Verify no hardcoded "AI WebOps" or "case-study"
    # (these were in the original hardcoded list but don't exist as real categories)
    lines = content.split('\n')
    in_topics_section = False
    hardcoded_bad_cats = ["AI WebOps", "case-study", "Tài chính cá nhân"]

    for i, line in enumerate(lines):
        if 'id="home-filter-panel"' in line or 'class="home-discovery__topics"' in line:
            in_topics_section = True

        if in_topics_section and 'for cat_item in homepage_categories' in line:
            # Now we're in the dynamic section, OK
            break

        if in_topics_section and any(cat in line for cat in hardcoded_bad_cats):
            # Check if it's in the fallback section (which is OK for backwards compat)
            if "else:" not in lines[max(0, i-10):i] and "fallback" not in "".join(lines[max(0, i-5):i]):
                raise AssertionError(f"Found hardcoded category '{[c for c in hardcoded_bad_cats if c in line][0]}' in main filter")

    print("✓ Homepage filter uses real categories from data/homepage-categories.json")

def test_categories_exclude_synthetic():
    """Verify homepage-categories.json doesn't include synthetic categories."""
    import json

    cat_file = Path("data/homepage-categories.json")
    with open(cat_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    cat_names = [c["name"] for c in data["categories"]]

    synthetic = ["Tất cả", "Báo chí", "premium"]
    for syn in synthetic:
        assert syn not in cat_names, f"Should exclude '{syn}' from categories"

    print(f"✓ Categories exclude synthetic labels: {synthetic}")

def main():
    try:
        test_cse_configuration()
        test_cse_siteSearch_in_editor()
        test_homepage_uses_real_categories()
        test_categories_exclude_synthetic()

        print("\n✓ All search configuration tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
