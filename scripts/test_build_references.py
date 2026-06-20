"""
Regression tests for build_references.py code-span-safe URL extraction.

Root cause (PR #551): build_references.py used raw LINK_MD_RE on the full
markdown body, extracting URLs from inside backtick code spans (e.g.
`[text](/posting/slug/)`) as real references.  Those end up in
data/references.json, get rendered as <a> tags, and trigger 404 failures
in qa-404-checker.py.

Fix: extract_links() now delegates to link_utils.extract_link_pairs(), which
masks code spans (fenced + inline backtick) before running the regex.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Allow running as `python3 scripts/test_build_references.py`
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_references import extract_links


class CodeSpanSafeExtractionTest(unittest.TestCase):
    """URL extraction must NOT read through code spans."""

    def test_inline_code_span_url_excluded(self):
        """URL inside a single-backtick span must not be extracted."""
        body = "Example: `[tên bài](/posting/slug/)` — plain text."
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertNotIn("/posting/slug/", urls, "URL inside backtick must be ignored")

    def test_inline_code_span_http_url_excluded(self):
        """Absolute URL inside backtick code span must not be extracted."""
        body = "Run `curl https://example.com/api` to fetch data."
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertNotIn("https://example.com/api", urls,
                         "Absolute URL inside backtick must be ignored")

    def test_fenced_code_block_url_excluded(self):
        """Link inside a fenced code block must not be extracted."""
        body = (
            "Normal prose.\n"
            "```\n"
            "[text](/posting/slug/)\n"
            "```\n"
            "After block."
        )
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertNotIn("/posting/slug/", urls, "URL inside fenced block must be ignored")

    def test_posting_slug_placeholder_excluded(self):
        """The exact /posting/slug/ pattern that broke PR #551 must not be extracted."""
        # Reproduces the bai-hoc-xay-he-thong... line 56 content pattern
        body = (
            "Zola không validate dangling markdown links tại build time — "
            "nó chỉ check Zola's own `@/` refs. "
            "Link kiểu `[text](/posting/slug/)` trong markdown hoàn toàn bypass build check."
        )
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertNotIn("/posting/slug/", urls,
                         "Exact PR #551 case: /posting/slug/ in backtick must be ignored")

    def test_real_prose_link_extracted(self):
        """A real markdown link in prose (not inside code) must still be extracted."""
        body = "See the [bài viết liên quan](/posting/real-article/) for details."
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertIn("/posting/real-article/", urls, "Real prose link must be extracted")

    def test_real_external_link_extracted(self):
        """A real external markdown link in prose must be extracted."""
        body = "Đọc thêm tại [Google Search Central](https://developers.google.com/search)."
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertIn("https://developers.google.com/search", urls,
                      "Real external link must be extracted")

    def test_html_anchor_extracted(self):
        """An HTML <a href> in prose must be extracted."""
        body = 'Visit <a href="https://web.dev">web.dev</a> for performance tips.'
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertIn("https://web.dev", urls, "HTML anchor link must be extracted")

    def test_anchor_text_preserved(self):
        """Anchor text of a real link must be captured alongside the URL."""
        body = "See the [hướng dẫn chi tiết](/posting/huong-dan/) đây."
        pairs = extract_links(body)
        self.assertTrue(
            any(text == "hướng dẫn chi tiết" and url == "/posting/huong-dan/"
                for text, url in pairs),
            "Anchor text must match extracted URL pair"
        )

    def test_mixed_code_and_prose(self):
        """Code-span URL excluded, prose URL extracted in the same body."""
        body = (
            "Xem `[example](/posting/slug/)` rồi đọc "
            "[bài thật](/posting/real-article/) để biết thêm."
        )
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertNotIn("/posting/slug/", urls, "Code-span URL must be excluded")
        self.assertIn("/posting/real-article/", urls, "Prose URL must be included")

    def test_image_link_excluded(self):
        """Image links (![...](url)) must not be extracted (negative lookahead on !)."""
        body = "![placeholder](/img/placeholder/placeholder.svg) text [link](/posting/a/)"
        pairs = extract_links(body)
        urls = [url for _, url in pairs]
        self.assertNotIn("/img/placeholder/placeholder.svg", urls,
                         "Image markdown must not be treated as a link")
        self.assertIn("/posting/a/", urls, "Regular link after image must be extracted")

    def test_empty_body(self):
        """Empty string returns empty list without error."""
        self.assertEqual(extract_links(""), [])

    def test_no_links(self):
        """Plain text without links returns empty list."""
        self.assertEqual(extract_links("This has no links at all."), [])


if __name__ == "__main__":
    unittest.main()
