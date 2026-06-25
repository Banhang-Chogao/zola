#!/usr/bin/env python3
"""Unit tests cho scripts/request_indexing.py — không gọi mạng.

Kiểm các hàm thuần: candidate pool từ content, lọc indexable, deep-link GSC,
phân loại coverage→indexed, parse arg. Không đụng GSC API (graceful path).
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "request_indexing.py"


def _load():
    spec = importlib.util.spec_from_file_location("request_indexing", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["request_indexing"] = mod
    spec.loader.exec_module(mod)
    return mod


ri = _load()


class TestBaseUrl(unittest.TestCase):
    def test_base_url(self):
        self.assertEqual(ri.read_base_url(), "https://seomoney.org")

    def test_property_default(self):
        self.assertEqual(ri.gsc_property(), "sc-domain:seomoney.org")


class TestIndexable(unittest.TestCase):
    def test_public_post_is_indexable(self):
        self.assertTrue(ri._is_indexable({"title": "x"}))

    def test_draft_excluded(self):
        self.assertFalse(ri._is_indexable({"draft": True}))

    def test_noindex_excluded(self):
        self.assertFalse(ri._is_indexable({"extra": {"noindex": True}}))

    def test_premium_extra_excluded(self):
        self.assertFalse(ri._is_indexable({"extra": {"premium": True}}))

    def test_premium_category_excluded(self):
        self.assertFalse(ri._is_indexable({"taxonomies": {"categories": ["premium", "Công nghệ"]}}))


class TestCandidates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = "https://seomoney.org"
        cls.cands = ri.build_candidates(cls.base)

    def test_nonempty(self):
        self.assertGreater(len(self.cands), 100)

    def test_all_under_base_and_sections(self):
        for c in self.cands:
            self.assertTrue(c["url"].startswith(self.base + "/"))
            self.assertIn(c["section"], ri.POST_SECTIONS)
            self.assertTrue(c["url"].endswith("/"))

    def test_sorted_by_score_desc(self):
        scores = [c["score"] for c in self.cands]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_no_premium_in_pool(self):
        # bài premium đã bị loại → không URL nào trỏ tới slug premium đã biết
        urls = {c["url"] for c in self.cands}
        # pool chỉ gồm posting/baochi
        self.assertTrue(all("/posting/" in u or "/baochi/" in u for u in urls))


class TestInspectClassification(unittest.TestCase):
    def test_indexed_states_membership(self):
        self.assertIn("submitted and indexed", ri.INDEXED_STATES)
        self.assertIn("indexed, not submitted in sitemap", ri.INDEXED_STATES)
        self.assertNotIn("crawled - currently not indexed", ri.INDEXED_STATES)


class TestDeepLink(unittest.TestCase):
    def test_inspect_link(self):
        link = ri.gsc_inspect_link("https://seomoney.org/posting/abc/", "sc-domain:seomoney.org")
        self.assertIn("search.google.com/search-console/inspect", link)
        self.assertIn("resource_id=sc-domain%3Aseomoney.org", link)
        self.assertIn("id=https%3A%2F%2Fseomoney.org%2Fposting%2Fabc%2F", link)


class TestArgParse(unittest.TestCase):
    def test_argint_default(self):
        old = sys.argv
        try:
            sys.argv = ["x"]
            self.assertEqual(ri._argint("--shortlist", 12), 12)
            sys.argv = ["x", "--shortlist", "7"]
            self.assertEqual(ri._argint("--shortlist", 12), 7)
            sys.argv = ["x", "--shortlist", "notint"]
            self.assertEqual(ri._argint("--shortlist", 12), 12)
        finally:
            sys.argv = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
