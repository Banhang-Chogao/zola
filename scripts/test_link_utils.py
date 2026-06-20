#!/usr/bin/env python3
"""Tests for scripts/link_utils.py — the migration + regex safety vaccine.

Run: python3 -m unittest scripts.test_link_utils -v

Covers the V9 success criteria:
  * 0 skipped internal /zola/ links
  * regex handles markdown + punctuation edge cases
  * code spans unaffected
  * migration tool never rewrites links inside code spans
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import link_utils as L
import fix_site_prefix_links as FIX


class TestClassification(unittest.TestCase):
    def test_zola_paths_always_internal(self):
        # The core bug: /zola/* must NEVER be treated as external/skip.
        for url in ("/zola/foo/", "/zola/posting/bar/", "/zola/x#sec", "/zola/y?q=1"):
            self.assertTrue(L.is_internal(url), url)
            self.assertEqual(L.classify(url), "internal", url)
            self.assertEqual(L.validate(url), "KEEP_INTERNAL", url)
            self.assertFalse(L.is_external(url), url)

    def test_root_and_relative_paths_internal(self):
        for url in ("/foo/", "/", "@/posting/x.md", "./sibling/", "../up/"):
            self.assertEqual(L.classify(url), "internal", url)

    def test_external_urls(self):
        for url in ("http://e.com/a", "https://e.com/b", "//cdn.example/c"):
            self.assertEqual(L.classify(url), "external", url)
            self.assertEqual(L.validate(url), "VALIDATE_EXTERNAL", url)
        self.assertTrue(L.is_external("https://e.com"))

    def test_skip_schemes(self):
        for url in ("#frag", "mailto:a@b.com", "tel:+84", "javascript:void(0)", ""):
            self.assertEqual(L.classify(url), "skip", url)
            self.assertEqual(L.validate(url), "SKIP", url)

    def test_no_host_required_for_internal(self):
        # Host substring must never gate an internal decision.
        self.assertTrue(L.is_internal("/zola/no-host-here/"))
        self.assertEqual(L.classify("/zola/no-host-here/"), "internal")


class TestCleanUrl(unittest.TestCase):
    def test_trailing_prose_punctuation(self):
        self.assertEqual(L.clean_url("https://e.com/a."), "https://e.com/a")
        self.assertEqual(L.clean_url("https://e.com/a,"), "https://e.com/a")
        self.assertEqual(L.clean_url("/zola/x/!"), "/zola/x/")

    def test_angle_wrapped(self):
        self.assertEqual(L.clean_url("<https://e.com/a>"), "https://e.com/a")

    def test_keeps_trailing_slash_and_internal_path(self):
        self.assertEqual(L.clean_url("/zola/foo/"), "/zola/foo/")


class TestCodeSpans(unittest.TestCase):
    def test_inline_code_masked(self):
        text = "real [a](/zola/a) and `[b](/zola/b)` code"
        urls = L.extract_urls(text)
        self.assertIn("/zola/a", urls)
        self.assertNotIn("/zola/b", urls)  # inside inline code → ignored

    def test_fenced_block_masked(self):
        text = "[a](/zola/a)\n```\n[b](/zola/b)\n```\n[c](/zola/c)"
        urls = L.extract_urls(text)
        self.assertEqual(urls.count("/zola/a"), 1)
        self.assertEqual(urls.count("/zola/c"), 1)
        self.assertNotIn("/zola/b", urls)

    def test_ranges_cover_code(self):
        text = "x `code` y"
        ranges = L.code_span_ranges(text)
        self.assertTrue(any(s <= text.index("code") < e for s, e in ranges))

    def test_mask_preserves_length(self):
        text = "a `bb` c"
        self.assertEqual(len(L.mask_code_spans(text)), len(text))


class TestExtraction(unittest.TestCase):
    def test_markdown_link_with_title(self):
        urls = L.extract_urls('[t](/zola/x "Title")')
        self.assertEqual(urls, ["/zola/x"])

    def test_image_links_excluded(self):
        urls = L.extract_urls("![alt](/zola/img.webp) [t](/zola/post/)")
        self.assertEqual(urls, ["/zola/post/"])

    def test_html_anchor(self):
        urls = L.extract_urls('<a href="/zola/x/">x</a> <a href="https://e.com">e</a>')
        self.assertEqual(urls, ["/zola/x/", "https://e.com"])

    def test_link_pairs(self):
        pairs = L.extract_link_pairs("[Anchor](/zola/x/)")
        self.assertEqual(pairs, [("Anchor", "/zola/x/")])

    def test_bare_urls_punctuation(self):
        text = "see https://e.com/a, and /zola/foo/."
        urls = L.extract_bare_urls(text)
        self.assertIn("https://e.com/a", urls)
        self.assertIn("/zola/foo/", urls)

    def test_process_keeps_internal_drops_skip(self):
        text = "[a](/zola/a) [m](mailto:x@y.z) [e](https://e.com)"
        kept = L.process(text)
        self.assertIn("/zola/a", kept)
        self.assertIn("https://e.com", kept)
        self.assertNotIn("mailto:x@y.z", kept)

    def test_empty_and_garbage(self):
        self.assertEqual(L.extract_urls(""), [])
        self.assertEqual(L.extract_urls(None), [])  # type: ignore[arg-type]


class TestMigrationToolCodeSafe(unittest.TestCase):
    def test_prefixes_real_links(self):
        out, n = FIX.prefix_internal_md_links("[a](/posting/x/)")
        self.assertEqual(out, "[a](/zola/posting/x/)")
        self.assertEqual(n, 1)

    def test_idempotent(self):
        out, n = FIX.prefix_internal_md_links("[a](/zola/posting/x/)")
        self.assertEqual(n, 0)
        self.assertEqual(out, "[a](/zola/posting/x/)")

    def test_does_not_touch_inline_code(self):
        src = "real [a](/posting/x/) and `[b](/posting/y/)`"
        out, n = FIX.prefix_internal_md_links(src)
        self.assertIn("[a](/zola/posting/x/)", out)
        self.assertIn("`[b](/posting/y/)`", out)  # code untouched
        self.assertEqual(n, 1)

    def test_does_not_touch_fenced_block(self):
        src = "[a](/posting/x/)\n```\n[b](/posting/y/)\n```\n"
        out, n = FIX.prefix_internal_md_links(src)
        self.assertIn("[a](/zola/posting/x/)", out)
        self.assertIn("[b](/posting/y/)", out)  # unchanged inside fence
        self.assertNotIn("/zola/posting/y/", out)
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
