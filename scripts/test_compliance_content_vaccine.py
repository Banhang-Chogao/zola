#!/usr/bin/env python3
"""Tests for compliance_content_vaccine.py."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "compliance_content_vaccine.py"

_spec = importlib.util.spec_from_file_location("compliance_content_vaccine", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["compliance_content_vaccine"] = mod
_spec.loader.exec_module(mod)


class VaccineHelpersTest(unittest.TestCase):
    def test_strip_md_counts_substantive_anchor_body(self):
        body = mod.ANCHOR_BODY.format(home="/", n=1)
        self.assertGreaterEqual(len(mod._strip_md(body)), mod.CONTENT_MIN_CHARS)

    def test_upgrade_feed_anchor_adds_taxonomies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            posting = root / "posting"
            posting.mkdir(parents=True)
            path = posting / "feed-anchor-001.md"
            path.write_text(
                '+++\ntitle = "Feed pagination anchor 1"\ntemplate = "feed-anchor.html"\n'
                "date = 2000-01-01\n[extra]\nfeed_anchor = true\n+++\n",
                encoding="utf-8",
            )
            orig_content = mod.CONTENT
            mod.CONTENT = root
            try:
                ok, _ = mod._upgrade_feed_anchor(path, apply=True)
                self.assertTrue(ok)
                text = path.read_text(encoding="utf-8")
                self.assertIn("[taxonomies]", text)
                self.assertIn("feed-pagination", text)
                self.assertGreaterEqual(len(mod._strip_md(text)), mod.CONTENT_MIN_CHARS)
            finally:
                mod.CONTENT = orig_content

    def test_body_h1_skips_shell_comments(self):
        body = "# 1. Tạo cặp khóa\n"
        self.assertIsNone(mod.BODY_H1_RE.search(body))
        body2 = "# Tiêu đề thật trong body\n"
        self.assertIsNotNone(mod.BODY_H1_RE.search(body2))

    def test_demote_skips_fenced_code(self):
        body = "```python\n# comment in code\n```\n# Real Heading\n"
        new_body, n = mod._demote_h1_outside_fences(body)
        self.assertEqual(n, 1)
        self.assertIn("# comment in code", new_body)
        self.assertIn("## Real Heading", new_body)


if __name__ == "__main__":
    unittest.main()