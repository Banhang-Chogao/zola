#!/usr/bin/env python3
"""Unit tests for scripts/wd_heartbeat_stats.py."""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wd_heartbeat_stats as wd  # noqa: E402


NOW = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


def run(conclusion: str, day: str, sha: str = "abc1234", dur: int = 100) -> dict:
    return {
        "conclusion": conclusion,
        "status": "completed",
        "createdAt": f"{day}T09:00:00Z",
        "headSha": sha,
        "duration_s": dur,
    }


class NormalizeTests(unittest.TestCase):
    def test_normalize_gh_schema(self):
        out = wd.normalize_run(run("success", "2026-06-24"))
        self.assertEqual(out["conclusion"], "success")
        self.assertEqual(out["sha"], "abc1234")
        self.assertEqual(out["created_at"].year, 2026)

    def test_normalize_deploy_monitor_schema(self):
        out = wd.normalize_run(
            {"conclusion": "failure", "created_at": "2026-06-24T04:50:28Z", "sha_short": "7c2a614", "duration_s": 1380}
        )
        self.assertEqual(out["conclusion"], "failure")
        self.assertEqual(out["sha"], "7c2a614")
        self.assertEqual(out["duration_s"], 1380)

    def test_normalize_missing_timestamp_drops(self):
        self.assertIsNone(wd.normalize_run({"conclusion": "success"}))

    def test_parse_ts_handles_offset_and_z(self):
        self.assertIsNotNone(wd._parse_ts("2026-06-24T09:00:00Z"))
        self.assertIsNotNone(wd._parse_ts("2026-06-24T09:00:00+00:00"))
        self.assertIsNone(wd._parse_ts("not-a-date"))


class AggregateTests(unittest.TestCase):
    def setUp(self):
        raw = [
            run("success", "2026-06-24"),
            run("success", "2026-06-24"),
            run("failure", "2026-06-24"),
            run("cancelled", "2026-06-24"),
            run("success", "2026-06-20"),
        ]
        self.runs = [wd.normalize_run(r) for r in raw]
        self.stats = wd.aggregate(self.runs, NOW)

    def test_totals_exclude_cancelled(self):
        t = self.stats["totals"]
        self.assertEqual(t["success"], 3)
        self.assertEqual(t["failed"], 1)
        self.assertEqual(t["cancelled"], 1)
        self.assertEqual(t["total"], 4)  # success + failed only

    def test_success_rate(self):
        # 3 success / (3 success + 1 failed) = 75%
        self.assertEqual(self.stats["totals"]["success_rate_pct"], 75)

    def test_heatmap_has_full_window(self):
        days = self.stats["heatmap"]["days"]
        self.assertEqual(len(days), wd.WINDOW_DAYS)
        # days sorted ascending, last day == today
        self.assertEqual(days[-1]["date"], "2026-06-25")
        self.assertEqual(days[0]["date"], "2026-05-27")

    def test_heatmap_busy_day_counts(self):
        days = {d["date"]: d for d in self.stats["heatmap"]["days"]}
        # cancelled excluded → 3 charted on the 24th (2 success + 1 failed)
        self.assertEqual(days["2026-06-24"]["count"], 3)
        self.assertEqual(days["2026-06-24"]["success"], 2)
        self.assertEqual(days["2026-06-24"]["failed"], 1)
        self.assertEqual(days["2026-06-20"]["count"], 1)
        self.assertEqual(self.stats["heatmap"]["max"], 3)

    def test_heatmap_levels_scale(self):
        days = {d["date"]: d for d in self.stats["heatmap"]["days"]}
        self.assertEqual(days["2026-06-24"]["level"], 4)  # busiest
        self.assertGreaterEqual(days["2026-06-20"]["level"], 1)
        self.assertEqual(days["2026-06-01"]["level"], 0)  # empty day

    def test_last_deploy_is_most_recent(self):
        last = self.stats["last_deploy"]
        self.assertEqual(last["at"], "2026-06-24T09:00:00Z")
        self.assertIn(last["status"], {"success", "failed"})


class PayloadTests(unittest.TestCase):
    def test_pending_when_no_completed_runs(self):
        payload = wd.build_payload([], NOW)
        self.assertFalse(payload["configured"])
        self.assertEqual(payload["totals"]["total"], 0)
        self.assertEqual(len(payload["heatmap"]["days"]), wd.WINDOW_DAYS)
        self.assertIn("pending_reason", payload)

    def test_pending_when_only_queued(self):
        # runs without a conclusion (in-progress) must not fabricate stats
        raw = [{"status": "in_progress", "createdAt": "2026-06-24T09:00:00Z"}]
        payload = wd.build_payload(raw, NOW)
        self.assertFalse(payload["configured"])

    def test_configured_payload_shape(self):
        payload = wd.build_payload([run("success", "2026-06-24")], NOW)
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["window_days"], wd.WINDOW_DAYS)
        self.assertEqual(payload["totals"]["success"], 1)
        self.assertIsNotNone(payload["last_deploy"])

    def test_no_division_by_zero(self):
        payload = wd.build_payload([run("cancelled", "2026-06-24")], NOW)
        # only cancelled → no counted runs → pending, rate 0, no crash
        self.assertEqual(payload["totals"]["success_rate_pct"], 0)


if __name__ == "__main__":
    unittest.main()
