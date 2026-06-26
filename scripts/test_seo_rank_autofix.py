#!/usr/bin/env python3
"""Tests for seo-rank-autofix.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "seo-rank-autofix.py"

_spec = importlib.util.spec_from_file_location("seo_rank_autofix", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["seo_rank_autofix"] = mod
_spec.loader.exec_module(mod)


class AutofixHelpersTest(unittest.TestCase):
    def test_contribution_level_strip_md(self):
        text = "**Hello** [link](/zola/posting/x/)"
        self.assertIn("Hello", mod._strip_md(text))

    def test_excerpt_truncates(self):
        body = "A" * 200
        ex = mod._excerpt(body, max_len=160)
        self.assertLessEqual(len(ex), 161)

    def test_priority_order(self):
        self.assertLess(
            mod.ISSUE_PRIORITY.index("broken_internal_link"),
            mod.ISSUE_PRIORITY.index("missing_meta_description"),
        )


class AutofixScanTest(unittest.TestCase):
    def test_scan_only_returns_report(self):
        payload = mod.run_scan(apply=False, dry_run=True)
        self.assertIn("progressPercent", payload)
        self.assertIn("scoreBefore", payload)
        self.assertIn("items", payload)
        self.assertIn("statusLabel", payload)

    def test_write_report_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            orig_data = mod.DATA
            orig_static = mod.STATIC_DATA
            orig_report = mod.REPORT_FILE
            try:
                mod.DATA = tpath / "data"
                mod.STATIC_DATA = tpath / "static" / "data"
                mod.REPORT_FILE = mod.DATA / "seo-rank-autofix-report.json"
                payload = mod.run_scan(apply=False, dry_run=True)
                mod.write_report(payload)
                self.assertTrue(mod.REPORT_FILE.is_file())
                self.assertTrue((mod.STATIC_DATA / "seo-rank-autofix-report.json").is_file())
                loaded = json.loads(mod.REPORT_FILE.read_text())
                self.assertEqual(loaded["scoreBefore"], payload["scoreBefore"])
            finally:
                mod.DATA = orig_data
                mod.STATIC_DATA = orig_static
                mod.REPORT_FILE = orig_report


class AutofixFixTest(unittest.TestCase):
    def test_fix_broken_privacy_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            posting = tpath / "posting"
            posting.mkdir(parents=True)
            md = posting / "sample.md"
            md.write_text(
                '+++\n'
                'title = "Test"\n'
                'description = "A long enough meta description for SEO testing purposes here."\n'
                'date = 2026-06-18\n'
                '+++\n\n'
                'See [privacy](/zola/pages/privacy/) for details.\n',
                encoding="utf-8",
            )
            orig_content = mod.CONTENT
            orig_scan = mod.SCAN_DIRS
            try:
                mod.CONTENT = tpath
                mod.SCAN_DIRS = (posting,)
                doc = mod._parse_article(md)
                assert doc
                issue = mod.Issue(
                    "broken_internal_link", "content/posting/sample.md",
                    detail="/zola/pages/privacy/|/zola/privacy/",
                )
                ok, _ = mod._apply_fix(doc, issue, {})
                self.assertTrue(ok)
                self.assertIn("/zola/privacy/", md.read_text())
            finally:
                mod.CONTENT = orig_content
                mod.SCAN_DIRS = orig_scan


if __name__ == "__main__":
    unittest.main()