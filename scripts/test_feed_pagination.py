#!/usr/bin/env python3
"""Tests for build_feed_pagination.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_feed_pagination.py"

_spec = importlib.util.spec_from_file_location("build_feed_pagination", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["build_feed_pagination"] = mod
_spec.loader.exec_module(mod)


class FeedPaginationTest(unittest.TestCase):
    def test_feed_page_count(self):
        self.assertEqual(mod.feed_page_count(0), 1)
        self.assertEqual(mod.feed_page_count(1), 1)
        self.assertEqual(mod.feed_page_count(10), 1)
        self.assertEqual(mod.feed_page_count(11), 2)
        self.assertEqual(mod.feed_page_count(97), 10)

    def test_min_section_pages(self):
        self.assertEqual(mod.min_section_pages_for_pagers(1), 0)
        self.assertEqual(mod.min_section_pages_for_pagers(2), 11)
        self.assertEqual(mod.min_section_pages_for_pagers(10), 91)

    def test_is_real_post_skips_anchor_and_draft(self):
        self.assertFalse(mod.is_real_post(ROOT / "content/posting/feed-anchor-001.md"))
        draft = ROOT / "content/baochi/bi-kip-xin-visa-han-quoc-5-nam-de.md"
        if draft.is_file():
            self.assertFalse(mod.is_real_post(draft))


if __name__ == "__main__":
    unittest.main()