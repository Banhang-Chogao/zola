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

def test_homepage_is_blog_feed():
    """Verify homepage is a paginated post feed, not a discovery landing page."""
    index_html = Path("templates/index.html")
    with open(index_html, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'class="post-list"' in content, "Should render post-list feed"
    assert "home-discovery" not in content, "Should not use discovery landing layout"
    assert "home-economist" not in content, "Should not use economist landing layout"
    assert "for subsection_path in section.subsections" in content, "Should discover article sections dynamically"

    print("✓ Homepage is a dynamic blog feed at canonical root")

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
        test_homepage_is_blog_feed()
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
