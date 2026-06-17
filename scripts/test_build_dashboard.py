"""Tests for Build Dashboard status mapping and 5-minute history."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "fetch_build_dashboard",
    ROOT / "scripts" / "fetch_build_dashboard.py",
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules["fetch_build_dashboard"] = mod
spec.loader.exec_module(mod)


class TestNormalizeStatus(unittest.TestCase):
    def test_success(self):
        self.assertEqual(mod.normalize_status("success", "completed"), "success")

    def test_cancelled_not_failed(self):
        self.assertEqual(mod.normalize_status("cancelled", "completed"), "cancelled")
        self.assertFalse(mod.is_build_error("cancelled"))

    def test_failure_is_error(self):
        self.assertEqual(mod.normalize_status("failure", "completed"), "failed")
        self.assertTrue(mod.is_build_error("failed"))

    def test_in_progress(self):
        self.assertEqual(mod.normalize_status(None, "in_progress"), "in_progress")

    def test_skipped(self):
        self.assertEqual(mod.normalize_status("skipped", "completed"), "skipped")
        self.assertFalse(mod.is_build_error("skipped"))


class TestCancelDetection(unittest.TestCase):
    def test_superseding_run_detected(self):
        older = {
            "id": 1,
            "run_number": 387,
            "run_started_at": "2026-06-17T16:23:58Z",
            "created_at": "2026-06-17T16:23:58Z",
        }
        newer = {
            "id": 2,
            "run_number": 388,
            "run_started_at": "2026-06-17T16:24:00Z",
            "created_at": "2026-06-17T16:24:00Z",
        }
        reason, cause = mod.analyze_cancel_cause_vi(older, [older, newer], "deploy.yml")
        self.assertEqual(reason, "concurrency")
        self.assertIn("Build #388", cause)

    def test_build_388_superseded_by_389(self):
        run388 = {
            "id": 27703753708,
            "run_number": 388,
            "run_started_at": "2026-06-17T16:24:00Z",
        }
        run389 = {
            "id": 27703862889,
            "run_number": 389,
            "run_started_at": "2026-06-17T16:25:48Z",
        }
        reason, cause = mod.analyze_cancel_cause_vi(
            run388, [run388, run389], "deploy.yml",
        )
        self.assertEqual(reason, "concurrency")
        self.assertIn("Build #389", cause)


class TestBuildHistory(unittest.TestCase):
    def _snap(self, deploy_status="success", qa_status="success"):
        return {
            "deploy.yml": {
                "id": 1,
                "run_number": 10,
                "status_normalized": deploy_status,
                "gh_status": "completed",
            },
            "qa.yml": {
                "id": 2,
                "run_number": 20,
                "status_normalized": qa_status,
                "gh_status": "completed",
            },
        }

    def _stats(self):
        return {
            "total": 2,
            "success": 2,
            "failure": 0,
            "cancelled": 0,
            "skipped": 0,
            "in_progress": 0,
        }

    def test_append_on_status_change(self):
        t0 = datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)
        h = mod.append_history(
            [],
            now=t0,
            stats=self._stats(),
            snapshot=self._snap(),
        )
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["type"], "change")

        t1 = datetime(2026, 6, 18, 12, 5, tzinfo=timezone.utc)
        h2 = mod.append_history(
            h,
            now=t1,
            stats={**self._stats(), "in_progress": 1},
            snapshot=self._snap(deploy_status="in_progress"),
        )
        self.assertEqual(len(h2), 2)
        self.assertEqual(h2[-1]["type"], "change")

    def test_skip_duplicate_within_5_minutes(self):
        t0 = datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)
        snap = self._snap()
        h = mod.append_history([], now=t0, stats=self._stats(), snapshot=snap)
        t1 = datetime(2026, 6, 18, 12, 3, tzinfo=timezone.utc)
        h2 = mod.append_history(h, now=t1, stats=self._stats(), snapshot=snap)
        self.assertEqual(len(h2), 1)

    def test_checkpoint_after_one_hour_unchanged(self):
        t0 = datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)
        snap = self._snap()
        h = mod.append_history([], now=t0, stats=self._stats(), snapshot=snap)
        t1 = datetime(2026, 6, 18, 13, 5, tzinfo=timezone.utc)
        h2 = mod.append_history(h, now=t1, stats=self._stats(), snapshot=snap)
        self.assertEqual(len(h2), 2)
        self.assertEqual(h2[-1]["type"], "checkpoint")

    def test_workflow_snapshot_picks_latest_per_workflow(self):
        builds = [
            {"workflow_file": "deploy.yml", "id": 99, "run_number": 9,
             "status_normalized": "in_progress", "started_at": "2026-06-18T12:00:00Z"},
            {"workflow_file": "deploy.yml", "id": 88, "run_number": 8,
             "status_normalized": "success", "started_at": "2026-06-18T11:00:00Z"},
            {"workflow_file": "qa.yml", "id": 77, "run_number": 7,
             "status_normalized": "success", "started_at": "2026-06-18T12:00:00Z"},
        ]
        snap = mod._workflow_snapshot(builds)
        self.assertEqual(snap["deploy.yml"]["id"], 99)
        self.assertEqual(snap["qa.yml"]["id"], 77)


if __name__ == "__main__":
    unittest.main()