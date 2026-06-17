"""Tests for Build Dashboard status mapping."""
from __future__ import annotations

import importlib.util
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()