"""Regression checks for dynamic homepage article discovery."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "templates/index.html").read_text(encoding="utf-8")


def test_homepage_discovers_root_subsections_dynamically():
    assert "for subsection_path in section.subsections" in INDEX
    assert "get_section(path=subsection_path)" in INDEX
    assert 'get_section(path="posting/_index.md")' not in INDEX
    assert 'get_section(path="baochi/_index.md")' not in INDEX


def test_homepage_filters_non_articles_and_explicitly_hidden_pages():
    assert "child_section.extra.skip_feed" in INDEX
    assert "page.title and page.date" in INDEX
    assert "page.extra.feed_anchor" in INDEX
    assert "page.extra.hide_from_home" in INDEX


def test_static_pages_section_is_explicitly_excluded():
    front_matter = (ROOT / "content/pages/_index.md").read_text(encoding="utf-8")
    assert "skip_feed = true" in front_matter
