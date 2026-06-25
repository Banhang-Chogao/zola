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


def _run(sha, status, conclusion=None, started_ago_s=0, dur_s=0, title="t", run_number=None):
    started = NOW - timedelta(seconds=started_ago_s)
    updated = started + timedelta(seconds=dur_s)
    return {
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "display_title": title,
        "run_number": run_number,
        "html_url": f"https://github.com/x/y/actions/runs/{run_number}" if run_number else None,
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
        for k in ("checked_at", "ok", "stale", "summary", "pending", "expired", "recent", "feed"):
            self.assertIn(k, rep)
        for k in ("prod_status", "pending_count", "expired_count", "deploying", "avg_deploy_s",
                  "running_runs", "last_success_run", "superseded_failures", "status_line"):
            self.assertIn(k, rep["summary"])


class FeedTableTest(unittest.TestCase):
    """The `theodoi8 deploy` table feed: run numbers, ordering, superseded, status line."""

    def _scenario(self):
        # Mirrors the canonical image: newest #872 in-flight; #871/#870/#869 success;
        # #868/#867 cancelled; #866/#865 failure (superseded by #869–#871); #864 success.
        return [
            _run("c6eb2a9", "in_progress", title="merge origin/main → deploy", run_number=872, started_ago_s=200),
            _run("b98e4e0", "completed", "success", title="Build & deploy Zola site", run_number=871, started_ago_s=900, dur_s=600),
            _run("dd1119b", "completed", "success", title="feat(adsense): hotfix readiness", run_number=870, started_ago_s=1500, dur_s=600),
            _run("24b6780", "completed", "success", title="feat(premium): paywall visa Hàn", run_number=869, started_ago_s=2100, dur_s=600),
            _run("a00601c", "completed", "cancelled", title="fix(gsc)", run_number=868, started_ago_s=2700, dur_s=110),
            _run("800f2e6", "completed", "cancelled", title="redesign(editor) S-DNA", run_number=867, started_ago_s=3300, dur_s=200),
            _run("175c44b", "completed", "failure", title="docs: V22 vaccine", run_number=866, started_ago_s=3900, dur_s=630),
            _run("f3ea06b", "completed", "failure", title="fix(editor)", run_number=865, started_ago_s=4500, dur_s=900),
            _run("e308532", "completed", "success", title="merge deploy", run_number=864, started_ago_s=6300, dur_s=1100),
        ]

    def test_feed_newest_first_with_run_numbers_and_urls(self):
        rep = fdm.build_report_from_runs(self._scenario(), now=NOW)
        feed = rep["feed"]
        self.assertEqual([f["run_number"] for f in feed][:3], [872, 871, 870])
        head = feed[0]
        self.assertEqual(head["sha_short"], "c6eb2a9")
        self.assertEqual(head["state"], "running")
        self.assertEqual(head["icon"], "🔄")
        self.assertIn("/commit/c6eb2a9", head["commit_url"])
        self.assertTrue(head["run_url"])

    def test_failures_superseded_by_later_success(self):
        rep = fdm.build_report_from_runs(self._scenario(), now=NOW)
        by_rn = {f["run_number"]: f for f in rep["feed"]}
        # 866 & 865 failed but 869–871 succeeded later → superseded.
        self.assertTrue(by_rn[866]["superseded"])
        self.assertTrue(by_rn[865]["superseded"])
        # A success is never "superseded".
        self.assertFalse(by_rn[871]["superseded"])
        self.assertEqual(sorted(rep["summary"]["superseded_failures"]), [865, 866])

    def test_status_line_pieces(self):
        s = fdm.build_report_from_runs(self._scenario(), now=NOW)["summary"]
        self.assertEqual(s["running_runs"], [872])
        self.assertEqual(s["last_success_run"], 871)
        self.assertEqual(s["last_success_sha_short"], "b98e4e0")
        line = s["status_line"]
        self.assertIn("🔄 #872 đang chạy", line)
        self.assertIn("✅ last success #871", line)
        self.assertIn("đã superseded", line)

    def test_no_run_numbers_degrades_gracefully(self):
        # Older API payloads / tests without run_number must not crash.
        rep = fdm.build_report_from_runs([_run("ZZZ", "completed", "success", dur_s=100)], now=NOW)
        self.assertEqual(rep["feed"][0]["run_number"], None)
        self.assertEqual(rep["summary"]["running_runs"], [])
        self.assertEqual(rep["summary"]["last_success_run"], None)
        self.assertEqual(rep["summary"]["status_line"], "")


if __name__ == "__main__":
    unittest.main()
