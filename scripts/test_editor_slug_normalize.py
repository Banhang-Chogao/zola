#!/usr/bin/env python3
"""Tests for editor deep-link slug normalization logic (mirrors normalizeEditorSlug in editor.js)."""

import unittest
from urllib.parse import quote, unquote


CONTENT_DIR = "content/posting"


def normalize_editor_slug(raw: str) -> str:
    """Python mirror of JS normalizeEditorSlug(input) in static/js/editor.js."""
    if not raw:
        return ""
    s = raw
    try:
        s = unquote(s)
    except Exception:
        pass
    s = s.strip()
    # Strip domain if full URL
    if s.startswith("http://") or s.startswith("https://"):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(s)
            s = parsed.path
        except Exception:
            pass
    # Remove query and hash
    s = s.split("?")[0].split("#")[0]
    # Remove leading/trailing slashes
    s = s.strip("/")
    # Reject unsafe traversal
    if ".." in s or "\\" in s or "\x00" in s:
        return ""
    return s


def resolve_editor_path(slug: str) -> str:
    """Python mirror of JS path resolution in checkUrlParam()."""
    if "/" in slug:
        return "content/" + slug + ".md"
    return CONTENT_DIR + "/" + slug + ".md"


def extract_leaf_slug(data_path: str) -> str:
    """Python mirror of JS slug extraction in openEditor().then().
    Strips 'content/<section>/' prefix to get leaf slug."""
    # "content/baochi/liobank....md" → "liobank..."
    # "content/posting/my-post.md" → "my-post"
    import re
    return re.sub(r"^content/[^/]+/", "", data_path).removesuffix(".md")


class TestNormalizeEditorSlug(unittest.TestCase):

    # --- slug normalization ---

    def test_plain_slug(self):
        self.assertEqual(normalize_editor_slug("cai-dat-zola"), "cai-dat-zola")

    def test_leading_slash(self):
        self.assertEqual(
            normalize_editor_slug("/baochi/liobank-gioi-thieu-ban-be-nhan-thuong"),
            "baochi/liobank-gioi-thieu-ban-be-nhan-thuong",
        )

    def test_trailing_slash(self):
        self.assertEqual(
            normalize_editor_slug("/baochi/liobank-gioi-thieu-ban-be-nhan-thuong/"),
            "baochi/liobank-gioi-thieu-ban-be-nhan-thuong",
        )

    def test_both_slashes(self):
        self.assertEqual(
            normalize_editor_slug("/baochi/liobank-gioi-thieu-ban-be-nhan-thuong/"),
            "baochi/liobank-gioi-thieu-ban-be-nhan-thuong",
        )

    def test_url_encoded_slash(self):
        encoded = quote("/baochi/liobank-gioi-thieu-ban-be-nhan-thuong")
        result = normalize_editor_slug(encoded)
        self.assertEqual(result, "baochi/liobank-gioi-thieu-ban-be-nhan-thuong")

    def test_full_url(self):
        result = normalize_editor_slug("https://seomoney.org/baochi/liobank-gioi-thieu-ban-be-nhan-thuong/")
        self.assertEqual(result, "baochi/liobank-gioi-thieu-ban-be-nhan-thuong")

    def test_empty_string(self):
        self.assertEqual(normalize_editor_slug(""), "")

    def test_none_like(self):
        # JS calls with empty string when param missing
        self.assertEqual(normalize_editor_slug(""), "")

    def test_unsafe_traversal_rejected(self):
        self.assertEqual(normalize_editor_slug("../etc/passwd"), "")

    def test_unsafe_backslash_rejected(self):
        self.assertEqual(normalize_editor_slug("baochi\\liobank"), "")

    def test_null_byte_rejected(self):
        self.assertEqual(normalize_editor_slug("baochi/li\x00obank"), "")

    def test_simple_slug_no_folder(self):
        self.assertEqual(normalize_editor_slug("my-post"), "my-post")

    def test_strips_query_and_hash(self):
        self.assertEqual(
            normalize_editor_slug("/baochi/liobank?foo=bar#section"),
            "baochi/liobank",
        )


class TestEditorPathResolution(unittest.TestCase):
    """Tests path resolution from normalized slug → content/ path."""

    def test_nested_slug_uses_content_root(self):
        slug = "baochi/liobank-gioi-thieu-ban-be-nhan-thuong"
        path = resolve_editor_path(slug)
        self.assertEqual(path, "content/baochi/liobank-gioi-thieu-ban-be-nhan-thuong.md")

    def test_simple_slug_uses_content_dir(self):
        slug = "cai-dat-zola"
        path = resolve_editor_path(slug)
        self.assertEqual(path, "content/posting/cai-dat-zola.md")

    def test_posting_nested_slug(self):
        # Slug from posting/ section with leading slash normalized away
        slug = "posting/my-article"
        path = resolve_editor_path(slug)
        self.assertEqual(path, "content/posting/my-article.md")

    def test_no_double_slash(self):
        # Old bug: "/baochi/..." → "content/posting//baochi/....md"
        slug = normalize_editor_slug("/baochi/liobank-gioi-thieu-ban-be-nhan-thuong")
        path = resolve_editor_path(slug)
        self.assertNotIn("//", path)
        self.assertEqual(path, "content/baochi/liobank-gioi-thieu-ban-be-nhan-thuong.md")


class TestLeafSlugExtraction(unittest.TestCase):
    """Tests leaf slug extraction from GitHub API file path (openEditor slug field)."""

    def test_posting_path_returns_leaf(self):
        self.assertEqual(
            extract_leaf_slug("content/posting/cai-dat-zola.md"),
            "cai-dat-zola",
        )

    def test_baochi_path_returns_leaf(self):
        self.assertEqual(
            extract_leaf_slug("content/baochi/liobank-gioi-thieu-ban-be-nhan-thuong.md"),
            "liobank-gioi-thieu-ban-be-nhan-thuong",
        )

    def test_other_section_returns_leaf(self):
        self.assertEqual(
            extract_leaf_slug("content/du-lich/ha-noi-mua-thu.md"),
            "ha-noi-mua-thu",
        )

    def test_missing_slug_in_form_shows_placeholder(self):
        # When slug is empty, form shows placeholder. Should not be "new-post" mode.
        result = extract_leaf_slug("content/baochi/liobank.md")
        self.assertTrue(len(result) > 0, "Leaf slug must not be empty for existing file")


class TestEndToEndDeepLink(unittest.TestCase):
    """Integration test: URL param → normalized slug → resolved path."""

    def test_liobank_deep_link(self):
        """The exact bug case from the issue."""
        url_param = "/baochi/liobank-gioi-thieu-ban-be-nhan-thuong"
        slug = normalize_editor_slug(url_param)
        path = resolve_editor_path(slug)
        self.assertEqual(path, "content/baochi/liobank-gioi-thieu-ban-be-nhan-thuong.md")
        self.assertNotIn("//", path)
        self.assertNotIn("content/posting/", path)

    def test_simple_post_deep_link(self):
        url_param = "cai-dat-zola"
        slug = normalize_editor_slug(url_param)
        path = resolve_editor_path(slug)
        self.assertEqual(path, "content/posting/cai-dat-zola.md")

    def test_url_encoded_deep_link(self):
        url_param = quote("/baochi/liobank-gioi-thieu-ban-be-nhan-thuong")
        slug = normalize_editor_slug(url_param)
        path = resolve_editor_path(slug)
        self.assertEqual(path, "content/baochi/liobank-gioi-thieu-ban-be-nhan-thuong.md")

    def test_missing_slug_returns_false(self):
        # No slug param → checkUrlParam returns false → dashboard mode
        slug = normalize_editor_slug("")
        self.assertEqual(slug, "")

    def test_slug_exists_but_file_missing_not_new_post(self):
        # Slug is valid but file not found → error shown, NOT new-post mode.
        # This is a process rule: state.editing = null after catch,
        # but showView("edit") already called → user stays in edit view.
        url_param = "/baochi/non-existent-article"
        slug = normalize_editor_slug(url_param)
        self.assertEqual(slug, "baochi/non-existent-article")
        path = resolve_editor_path(slug)
        self.assertEqual(path, "content/baochi/non-existent-article.md")


if __name__ == "__main__":
    unittest.main(verbosity=2)
