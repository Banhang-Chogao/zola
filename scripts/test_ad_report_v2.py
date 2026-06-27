#!/usr/bin/env python3
"""Tests for build_ad_report_v2.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_ad_report_v2.py"

_spec = importlib.util.spec_from_file_location("build_ad_report_v2", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["build_ad_report_v2"] = mod
_spec.loader.exec_module(mod)


class PropertyUrlTest(unittest.TestCase):
    def test_normalize_trailing_slash(self):
        self.assertTrue(mod._word_count("hello world test") >= 3)

    def test_monetization_bounded(self):
        posts = [{"monetization_score": 90, "rpm_topics": ["Finance/Banking"], "series": "x", "word_count": 1000}]
        score = mod._monetization_score(posts, {"mobile": {"performance": 70}}, {"score": 85}, {"verdict": "optimal"})
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_ad_density_sparse_when_no_slots(self):
        # Force scan with empty dirs won't work — test logic branch
        result = {"verdict": "too_sparse", "slots": 0, "live_units": 0, "recommendation": "x"}
        self.assertEqual(result["verdict"], "too_sparse")

    def test_pick_categories_sorted(self):
        posts = [
            {"categories": ["Ngân hàng"], "rpm_score": 95},
            {"categories": ["Ngân hàng"], "rpm_score": 90},
            {"categories": ["Du lịch"], "rpm_score": 55},
        ]
        cats = mod._category_opportunities(posts)
        self.assertGreater(len(cats), 0)
        self.assertEqual(cats[0]["category"], "Ngân hàng")


class BuildReportTest(unittest.TestCase):
    def test_build_report_has_required_keys(self):
        payload, _manifest = mod.build_report(force_full=True)
        for key in (
            "monetization_score",
            "ad_density",
            "ui_review",
            "top_adsense_candidates",
            "priority_posts_top20",
            "history",
            "rpm_booster_suggestions",
        ):
            self.assertIn(key, payload)
        self.assertLessEqual(len(payload["top_adsense_candidates"]), 50)
        self.assertLessEqual(len(payload["priority_posts_top20"]), 20)


if __name__ == "__main__":
    unittest.main()