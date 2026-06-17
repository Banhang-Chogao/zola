"""Tests for merge report helpers."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "fetch_merge_report",
    ROOT / "scripts" / "fetch_merge_report.py",
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules["fetch_merge_report"] = mod
spec.loader.exec_module(mod)


class TestClassifyChangeType(unittest.TestCase):
    def test_fix(self):
        self.assertEqual(mod.classify_change_type("fix(dashboard): cancelled"), "fix")

    def test_feature(self):
        self.assertEqual(
            mod.classify_change_type("Feature/adsense foundation", "feature/adsense"),
            "feature",
        )

    def test_chore(self):
        self.assertEqual(mod.classify_change_type("chore: refresh data"), "chore")


class TestSummarizeVi(unittest.TestCase):
    def test_from_body(self):
        body = "## Mục tiêu\n\nKhởi tạo AdSense series."
        self.assertIn("AdSense", mod.summarize_vi("Title", body))


if __name__ == "__main__":
    unittest.main()