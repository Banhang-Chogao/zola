#!/usr/bin/env python3
"""Unit tests for fetch_deploy_monitor.build_report_from_runs (network-free).

Covers the deploy_monitor_vaccine invariants:
  * a genuinely in-flight deploy → pending + prod_status "yellow" + ETA;
  * a non-terminal run past the TTL → EXPIRED ghost, NOT pending, stale flagged
    (so the published snapshot never freezes a finished commit as "deploying");
  * a non-terminal run whose commit already deployed → expired (already_deployed);
  * deploy state is sourced ONLY from deploy.yml (WORKFLOW_FILE invariant).

Run: python3 -m unittest scripts.test_fetch_deploy_monitor -v
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_deploy_monitor as fdm  # noqa: E402

NOW = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _run(sha, status, conclusion=None, started_ago_s=0, dur_s=0, title="t"):
    started = NOW - timedelta(seconds=started_ago_s)
    updated = started + timedelta(seconds=dur_s)
    return {
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "display_title": title,
        "run_started_at": _iso(started),
        "created_at": _iso(started),
        "updated_at": _iso(updated),
    }


class BuildReportTest(unittest.TestCase):
    def test_workflow_source_is_deploy_only(self):
        self.assertEqual(fdm.WORKFLOW_FILE, "deploy.yml")
        # Report workflows are documented as background checks, never a source.
        for w in ("merge-report.yml", "build-failure-handler.yml", "qa-rule-checker.yml"):
            self.assertIn(w, fdm.TELEMETRY_WORKFLOWS)

    def test_fresh_inflight_is_pending_yellow_with_eta(self):
        runs = [
            _run("AAA", "in_progress", started_ago_s=300, title="feat in flight"),
            _run("BBB", "completed", "success", started_ago_s=1800, dur_s=600),
        ]
        rep = fdm.build_report_from_runs(runs, now=NOW)
        self.assertEqual(rep["summary"]["prod_status"], "yellow")
        self.assertTrue(rep["summary"]["deploying"])
        self.assertEqual(rep["summary"]["pending_count"], 1)
        self.assertEqual(rep["summary"]["expired_count"], 0)
        self.assertEqual(rep["pending"][0]["sha_short"], "AAA"[:7])
        # avg deploy = 600s, waited 300s → ETA ~300s.
        self.assertEqual(rep["pending"][0]["eta_s"], 300)
        self.assertFalse(rep["stale"])

    def test_ghost_inflight_past_ttl_is_expired_not_deploying(self):
        # In_progress for 4000s (> 2700 TTL) → abandoned/superseded ghost.
        runs = [
            _run("CCC", "in_progress", started_ago_s=4000, title="stuck deploy"),
            _run("BBB", "completed", "success", started_ago_s=5000, dur_s=600),
        ]
        rep = fdm.build_report_from_runs(runs, now=NOW)
        self.assertEqual(rep["summary"]["pending_count"], 0)
        self.assertEqual(rep["summary"]["expired_count"], 1)
        self.assertFalse(rep["summary"]["deploying"])
        # An expired ghost must NOT drive "yellow"; last success → green.
        self.assertEqual(rep["summary"]["prod_status"], "green")
        self.assertTrue(rep["stale"])
        self.assertEqual(rep["expired"][0]["expired_reason"], "ttl")

    def test_already_deployed_commit_is_not_pending(self):
        # DDD has a fresh in_progress run AND a completed success run → deployed.
        runs = [
            _run("DDD", "in_progress", started_ago_s=120, title="superseded rerun"),
            _run("DDD", "completed", "success", started_ago_s=1800, dur_s=500),
        ]
        rep = fdm.build_report_from_runs(runs, now=NOW)
        self.assertEqual(rep["summary"]["pending_count"], 0)
        self.assertEqual(rep["summary"]["expired_count"], 1)
        self.assertEqual(rep["expired"][0]["expired_reason"], "already_deployed")
        self.assertEqual(rep["summary"]["prod_status"], "green")

    def test_latest_failure_is_red(self):
        runs = [_run("EEE", "completed", "failure", started_ago_s=600, dur_s=200)]
        rep = fdm.build_report_from_runs(runs, now=NOW)
        self.assertEqual(rep["summary"]["prod_status"], "red")
        self.assertEqual(rep["summary"]["pending_count"], 0)

    def test_all_green_when_latest_success_no_pending(self):
        runs = [
            _run("FFF", "completed", "success", started_ago_s=300, dur_s=300),
            _run("GGG", "completed", "success", started_ago_s=3600, dur_s=400),
        ]
        rep = fdm.build_report_from_runs(runs, now=NOW)
        self.assertEqual(rep["summary"]["prod_status"], "green")
        self.assertFalse(rep["summary"]["deploying"])
        self.assertFalse(rep["stale"])
        self.assertEqual(rep["summary"]["prod_commit_short"], "FFF"[:7])

    def test_schema_keys_present(self):
        rep = fdm.build_report_from_runs([_run("HHH", "completed", "success", dur_s=100)], now=NOW)
        for k in ("checked_at", "ok", "stale", "summary", "pending", "expired", "recent"):
            self.assertIn(k, rep)
        for k in ("prod_status", "pending_count", "expired_count", "deploying", "avg_deploy_s"):
            self.assertIn(k, rep["summary"])


if __name__ == "__main__":
    unittest.main()
