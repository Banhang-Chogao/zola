#!/usr/bin/env python3
"""Tests for build_github_activity.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_github_activity.py"

_spec = importlib.util.spec_from_file_location("build_github_activity", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["build_github_activity"] = mod
_spec.loader.exec_module(mod)


class ContributionLevelTest(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(mod.contribution_level(0, 10), 0)

    def test_relative_buckets(self):
        self.assertEqual(mod.contribution_level(1, 8), 1)
        self.assertEqual(mod.contribution_level(3, 8), 2)
        self.assertEqual(mod.contribution_level(5, 8), 3)
        self.assertEqual(mod.contribution_level(8, 8), 4)


class HeatmapWeeksTest(unittest.TestCase):
    def test_week_column_count(self):
        end = date(2026, 6, 18)
        start = end - timedelta(days=364)
        totals = {start.isoformat(): 2, end.isoformat(): 5}
        heatmap = mod.build_heatmap_weeks(start, end, totals)
        self.assertIn("weeks", heatmap)
        self.assertGreaterEqual(len(heatmap["weeks"]), 52)
        self.assertEqual(len(heatmap["weekday_labels"]), 3)

    def test_cells_have_levels(self):
        end = date(2026, 6, 18)
        start = end - timedelta(days=6)
        key = start.isoformat()
        heatmap = mod.build_heatmap_weeks(start, end, {key: 4, end.isoformat(): 1})
        found = False
        for week in heatmap["weeks"]:
            for cell in week["days"]:
                if cell and cell["date"] == key:
                    self.assertEqual(cell["count"], 4)
                    self.assertEqual(cell["level"], 4)
                    found = True
        self.assertTrue(found)


class BreakdownTest(unittest.TestCase):
    def test_percentages_sum_to_100(self):
        end = date(2026, 6, 18)
        start = end - timedelta(days=2)
        counts = mod._empty_day_counts(start, end)
        counts[start.isoformat()]["commits"] = 3
        counts[(start + timedelta(days=1)).isoformat()]["pull_requests"] = 1
        bd = mod._breakdown(counts)
        self.assertEqual(bd["commits"], 3)
        self.assertEqual(bd["pull_requests"], 1)
        self.assertEqual(
            bd["commits_pct"] + bd["pull_requests_pct"] + bd["issues_pct"] + bd["reviews_pct"],
            100,
        )


class BuildActivityTest(unittest.TestCase):
    def test_git_only_payload_shape(self):
        payload = mod.build_activity(use_api=False)
        self.assertIn("total_contributions", payload)
        self.assertIn("heatmap", payload)
        self.assertIn("breakdown", payload)
        self.assertEqual(len(payload["days"]), mod.PERIOD_DAYS)
        self.assertEqual(payload["repository"], mod.REPO)

    def test_write_output_creates_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            orig = mod.OUTPUT
            try:
                mod.OUTPUT = tpath / "github-activity.json"
                payload = mod.build_activity(use_api=False)
                mod.write_output(payload)
                self.assertTrue(mod.OUTPUT.is_file())
                loaded = json.loads(mod.OUTPUT.read_text())
                self.assertEqual(loaded["total_contributions"], payload["total_contributions"])
            finally:
                mod.OUTPUT = orig


if __name__ == "__main__":
    unittest.main()