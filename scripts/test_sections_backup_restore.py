#!/usr/bin/env python3
"""Smoke tests for backup_sections.py + restore_sections.py.

Run: python3 -m unittest scripts.test_sections_backup_restore -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backup_sections as B  # noqa: E402
import restore_sections as R  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class TestBackup(unittest.TestCase):
    def test_read_frontmatter(self):
        fm = B.read_frontmatter(REPO / "content" / "tools" / "s-dna.md")
        self.assertEqual(fm.get("template"), "s-dna.html")
        self.assertIn("S-DNA", fm.get("title", ""))

    def test_resolve_template_deps_dashboard(self):
        deps = B.resolve_template_deps("f-dashboard.html")
        self.assertIn("templates/f-dashboard.html", deps["templates"])
        self.assertTrue(any(p.endswith("_f-dashboard.scss") for p in deps["scss"]))
        self.assertTrue(deps["js"], "dashboard should have js assets")

    def test_extract_menu_block_balanced(self):
        text = (REPO / "config.toml").read_text(encoding="utf-8")
        block = B.extract_block(text, "menu")
        self.assertTrue(block.startswith("menu = ["))
        self.assertEqual(block.count("["), block.count("]"))

    def test_manifest_shape(self):
        mf = REPO / "sections-backup" / "manifest.json"
        if not mf.exists():
            self.skipTest("run backup_sections.py first")
        m = json.loads(mf.read_text(encoding="utf-8"))
        for key in ("sections", "feature_pages", "posts", "menu_raw", "scss_imports"):
            self.assertIn(key, m)
        self.assertGreater(m["counts"]["feature_pages"], 0)


class TestRestoreHelpers(unittest.TestCase):
    def test_parse_template_field(self):
        blob = b'+++\ntitle = "x"\ntemplate = "calendar.html"\n+++\nbody'
        self.assertEqual(R.parse_template_field(blob), "calendar.html")

    def test_scss_name_from_partial(self):
        self.assertEqual(R.scss_name_from_partial("sass/_calendar.scss"), "calendar")
        self.assertIsNone(R.scss_name_from_partial("templates/calendar.html"))

    def test_match(self):
        fp = {"content_file": "content/tools/calendar.md", "title": "Lịch",
              "template": "calendar.html", "aliases": ["/calendar/"]}
        self.assertTrue(R.match("calendar", fp))
        self.assertTrue(R.match("Lịch", fp))
        self.assertFalse(R.match("dashboard", fp))


if __name__ == "__main__":
    unittest.main()
