#!/usr/bin/env python3
"""Regression: pagination hrefs must use /page/N/, never /zolapage/."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
BAD = re.compile(r"zolapage/", re.I)
GOOD_HOME = re.compile(r"/page/\d+/")


class PaginationUrlBuildTest(unittest.TestCase):
    def test_macro_exists(self):
        macro = ROOT / "templates/macros/pagination.html"
        self.assertTrue(macro.exists())
        text = macro.read_text(encoding="utf-8")
        self.assertIn("ending_with", text)
        self.assertIn("page/{{ page_num }}", text)

    def test_index_uses_pager_macro(self):
        html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
        self.assertIn("macros/pagination.html", html)
        self.assertIn("pager::page_href", html)
        self.assertNotIn('config.base_url }}page/', html)

    def test_section_uses_pager_macro(self):
        html = (ROOT / "templates/section.html").read_text(encoding="utf-8")
        self.assertIn("pager::page_href", html)
        self.assertNotIn('section.permalink }}page/', html)


class PaginationPublicOutputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PUBLIC.is_dir():
            raise unittest.SkipTest("public/ missing — run zola build first")

    def test_no_zolapage_in_public_html(self):
        offenders = []
        for path in PUBLIC.rglob("*.html"):
            if BAD.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(path.relative_to(PUBLIC)))
        self.assertEqual(offenders, [], f"broken pagination in: {offenders}")

    def test_homepage_page2_link(self):
        index = (PUBLIC / "index.html").read_text(encoding="utf-8")
        # Zola HTML-escapes slashes in href (&#x2F;)
        self.assertIn("zola", index)
        self.assertIn("page/2/", index)
        self.assertNotIn("zolapage", index.lower())


if __name__ == "__main__":
    unittest.main()