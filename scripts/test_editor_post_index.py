#!/usr/bin/env python3
"""Test Editor post index includes all posts from posting/ and baochi/ sections."""

import json
from pathlib import Path
from unittest.mock import Mock
import sys

def count_actual_posts():
    """Count actual .md files (excluding _index.md and drafts)."""
    content_dir = Path("content")
    all_posts = []

    for section_dir in ["posting", "baochi"]:
        posts_dir = content_dir / section_dir
        if not posts_dir.exists():
            continue

        for md_file in posts_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue
            all_posts.append((section_dir, md_file.name))

    return all_posts

def count_editor_metadata():
    """Count posts in the baked metadata by parsing editor.html."""
    editor_html = Path("templates/editor.html")
    with open(editor_html, "r", encoding="utf-8") as f:
        content = f.read()

    # The template contains Tera syntax, so we just verify it includes baochi posts
    # Look for the key parts of the template update
    has_posting_section = "posting_section" in content
    has_baochi_section = "baochi_section" in content
    has_concat = "concat(with=baochi_section.pages)" in content

    return {
        "has_posting_section": has_posting_section,
        "has_baochi_section": has_baochi_section,
        "has_concat": has_concat,
    }

def test_editor_includes_baochi():
    """Test that editor template includes baochi posts."""
    metadata = count_editor_metadata()

    print("Testing Editor post index...")
    assert metadata["has_posting_section"], "Missing posting_section variable"
    assert metadata["has_baochi_section"], "Missing baochi_section variable"
    assert metadata["has_concat"], "Missing concat to combine sections"
    print("✓ Editor template includes both posting/ and baochi/ sections")

def test_categories_file_generated():
    """Test that homepage-categories.json exists and has categories."""
    cat_file = Path("data/homepage-categories.json")
    assert cat_file.exists(), "data/homepage-categories.json not found"

    with open(cat_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "categories" in data, "Missing 'categories' key"
    assert len(data["categories"]) > 0, "No categories found"

    # Verify no synthetic categories
    cat_names = [c["name"] for c in data["categories"]]
    assert "Tất cả" not in cat_names, "Should not include 'Tất cả'"
    assert "Báo chí" not in cat_names, "Should not include 'Báo chí'"
    assert "premium" not in cat_names, "Should not include 'premium'"

    print(f"✓ Homepage categories file exists with {len(cat_names)} real categories")
    print(f"  Categories: {', '.join(cat_names)}")

def test_baochi_article_in_editor():
    """Test that baochi articles are included in editor metadata loop."""
    editor_html = Path("templates/editor.html")
    with open(editor_html, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify the template loops through all_posts
    assert "all_posts" in content, "Template should use all_posts variable"
    assert "for page in all_posts" in content, "Template should loop through all_posts"

    print("✓ Editor template loops through all_posts (posting + baochi)")

def test_homepage_uses_dynamic_categories():
    """Test that homepage template uses dynamic categories data."""
    index_html = Path("templates/index.html")
    with open(index_html, "r", encoding="utf-8") as f:
        content = f.read()

    assert "homepage_categories" in content, "Should load homepage-categories.json"
    assert "for cat_item in homepage_categories.categories" in content, "Should loop categories"
    assert 'data-filter-category="{{ cat_item.name }}"' in content, "Should use dynamic category name"

    print("✓ Homepage template uses dynamic categories data")

def main():
    try:
        test_editor_includes_baochi()
        test_categories_file_generated()
        test_baochi_article_in_editor()
        test_homepage_uses_dynamic_categories()

        print("\n✓ All tests passed!")
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
