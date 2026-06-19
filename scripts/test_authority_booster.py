#!/usr/bin/env python3
"""Tests for authority-booster.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOSTER = ROOT / "authority-booster.py"

_spec = importlib.util.spec_from_file_location("authority_booster", BOOSTER)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(mod)


class TrustScoreTest(unittest.TestCase):
    def test_trust_bounded(self):
        posts = [
            {
                "eeat_score": 80,
                "internal_link_count": 4,
                "external_link_count": 2,
                "thin": False,
                "topic_keys": ["ngan-hang"],
                "date": "2026-01-01",
                "updated": "2026-06-01",
            }
        ]
        trust = mod._trust_score(posts, [], None)
        self.assertGreater(trust["score"], 0)
        self.assertLessEqual(trust["score"], 100)
        self.assertIn("label", trust)

    def test_category_authority_has_pillars(self):
        posts = [
            {
                "topic_keys": ["tieng-han"],
                "eeat_score": 70,
                "word_count": 1200,
                "series": "x",
            },
            {
                "topic_keys": ["tieng-han"],
                "eeat_score": 65,
                "word_count": 900,
                "series": None,
            },
        ]
        cats = mod._category_authority(posts)
        han = next(c for c in cats if c["slug"] == "tieng-han")
        self.assertEqual(han["coverage"], 2)
        self.assertGreater(han["score"], 0)


class BuildReportTest(unittest.TestCase):
    def test_build_report_keys(self):
        payload, _ = mod.build_report(force_full=True)
        for key in (
            "trust_score",
            "category_authority",
            "topical_gaps",
            "authority_forecast",
            "internal_link_suggestions",
            "backlink_opportunities",
        ):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()