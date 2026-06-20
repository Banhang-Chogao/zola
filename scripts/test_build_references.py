#!/usr/bin/env python3
"""Regression tests for scripts/build_references.py link extraction.

Guards the V14 / V10-LINKS class: example links written inside `code spans` or
fenced ``` blocks must NEVER be harvested as real reference links (which would
emit a 404 anchor like /posting/slug/ into the references block).

Run: python3 -m unittest scripts.test_build_references -v
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_references as br  # noqa: E402


class ExtractLinksCodeSpanTest(unittest.TestCase):
    def test_real_link_is_extracted(self):
        urls = [u for _, u in br.extract_links("See [guide](/posting/real-post/) here.")]
        self.assertIn("/posting/real-post/", urls)

    def test_inline_code_example_is_ignored(self):
        # The exact PR #557 bug: an example markdown link inside a code span.
        body = "Link kiểu `[text](/posting/slug/)` trong markdown bypass build check."
        urls = [u for _, u in br.extract_links(body)]
        self.assertNotIn("/posting/slug/", urls)

    def test_fenced_block_example_is_ignored(self):
        body = "Ví dụ:\n```md\n[x](/posting/fake/)\n```\nvà [thật](/posting/ok/) ngoài."
        urls = [u for _, u in br.extract_links(body)]
        self.assertNotIn("/posting/fake/", urls)
        self.assertIn("/posting/ok/", urls)

    def test_html_anchor_outside_code_extracted(self):
        urls = [u for _, u in br.extract_links('<a href="/posting/html-post/">x</a>')]
        self.assertIn("/posting/html-post/", urls)


if __name__ == "__main__":
    unittest.main()
