#!/usr/bin/env python3
"""Tests for GA improvement progress aggregator."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "fetch_ga_improvement_progress",
    ROOT / "scripts" / "fetch_ga_improvement_progress.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class GaImprovementProgressTests(unittest.TestCase):
    def test_build_payload_has_tasks(self):
        payload = mod.build_payload()
        self.assertIn("tasks", payload)
        self.assertEqual(len(payload["tasks"]), 8)
        self.assertIn("summary", payload)
        self.assertIn(payload["summary"]["done"] + payload["summary"]["running"] + payload["summary"]["pending"], range(0, 9))

    def test_task_status_values(self):
        payload = mod.build_payload()
        allowed = {"pending", "running", "done"}
        for task in payload["tasks"]:
            self.assertIn(task["status"], allowed)
            self.assertTrue(task.get("label"))
            self.assertTrue(task.get("detail"))

    def test_pagespeed_running_when_mobile_low(self):
        task = mod._pagespeed_task(
            {"updated_at": "2026-01-01T00:00:00Z", "mobile": {"performance": 65, "lcp": "7s"}, "desktop": {"performance": 98}},
            None,
        )
        self.assertEqual(task["status"], "running")
        self.assertIn("65", task["detail"])

    def test_indexing_done_when_no_broken(self):
        task = mod._indexing_task(
            {"updated_at": "2026-01-01T00:00:00Z", "summary": {"checked": 100, "broken_count": 0, "status": "pass"}},
            None,
        )
        self.assertEqual(task["status"], "done")


if __name__ == "__main__":
    unittest.main()