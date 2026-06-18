#!/usr/bin/env python3
"""Tests for build_google_rank.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_google_rank.py"

_spec = importlib.util.spec_from_file_location("build_google_rank", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["build_google_rank"] = mod
_spec.loader.exec_module(mod)


class GoogleRankTest(unittest.TestCase):
    def test_level_top_tier(self):
        lvl = mod._level(91)
        self.assertEqual(lvl["name"], "Top Tier")
        self.assertEqual(lvl["emoji"], "🏆")

    def test_level_new_site(self):
        lvl = mod._level(5)
        self.assertEqual(lvl["name"], "New Site")

    def test_compute_returns_required_fields(self):
        payload = mod.compute_rank()
        self.assertIn("score", payload)
        self.assertGreaterEqual(payload["score"], 0)
        self.assertLessEqual(payload["score"], 100)
        self.assertIn("level", payload)
        self.assertIn("details", payload)
        self.assertIn("articles", payload["details"])
        self.assertIn("tooltip", payload)

    def test_write_outputs_creates_files(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            orig_data = mod.DATA
            orig_static = mod.STATIC_DATA
            try:
                mod.DATA = tpath / "data"
                mod.STATIC_DATA = tpath / "static" / "data"
                payload = mod.compute_rank()
                mod.write_outputs(payload)
                self.assertTrue((mod.DATA / "google-rank.json").is_file())
                self.assertTrue((mod.STATIC_DATA / "google-rank.json").is_file())
                loaded = json.loads((mod.DATA / "google-rank.json").read_text())
                self.assertEqual(loaded["score"], payload["score"])
            finally:
                mod.DATA = orig_data
                mod.STATIC_DATA = orig_static


if __name__ == "__main__":
    unittest.main()