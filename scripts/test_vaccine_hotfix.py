#!/usr/bin/env python3
"""Tests for scripts/vaccine_hotfix.py (the Vaccine Hotfix engine)."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaccine_hotfix as vh  # noqa: E402


class TestBranchNaming(unittest.TestCase):
    def test_prefix_and_slug(self):
        self.assertEqual(vh.hotfix_branch("qa-123"), "vaccine-hotfix/qa-123")
        self.assertEqual(vh.hotfix_branch("PR #87 / build"), "vaccine-hotfix/pr-87-build")
        self.assertTrue(vh.hotfix_branch("").endswith("/unknown"))

    def test_never_touches_main(self):
        # Every computed branch lives under the dedicated namespace.
        for issue in ("qa-1", "deploy-99", "weird///id", ""):
            self.assertTrue(vh.hotfix_branch(issue).startswith("vaccine-hotfix/"))


class TestTriggers(unittest.TestCase):
    def test_five_triggers(self):
        self.assertEqual(
            set(vh.TRIGGERS),
            {"build_fail", "deploy_fail", "auto_merge_blocked",
             "merge_conflict", "required_checks_fail"},
        )


class TestRequiredChecks(unittest.TestCase):
    def test_reads_policy(self):
        rc = vh.required_checks({"required_checks": {"QA Gatekeeper": ["qa-check", "QA Gatekeeper"]}})
        self.assertIn("qa-check", rc)

    def test_default_when_empty(self):
        self.assertEqual(vh.required_checks({}), ["qa-check"])

    def test_real_policy_has_qa_check(self):
        self.assertIn("qa-check", vh.required_checks())


class TestContentSafety(unittest.TestCase):
    def test_content_protected(self):
        self.assertTrue(vh.is_protected_path("content/posting/x.md"))
        self.assertTrue(vh.is_protected_path("private_content/premium-001.md"))
        self.assertTrue(vh.is_protected_path("data/korean-30day-series.json"))
        self.assertTrue(vh.is_protected_path("data/categories.json"))

    def test_generated_data_not_protected(self):
        # CI-regenerated data is safe to overwrite (not user content).
        self.assertFalse(vh.is_protected_path("data/references.json"))
        self.assertFalse(vh.is_protected_path("data/seo-qa-scores.json"))

    def test_conflict_strategy_keeps_content(self):
        # Reuses autofix_conflicts: content/* must resolve to the PR side, never dropped.
        import autofix_conflicts as afc
        self.assertEqual(afc.classify("content/posting/x.md"), "pr")
        self.assertEqual(afc.classify("data/korean-30day-series.json"), "manual")


class TestPrecheck(unittest.TestCase):
    def setUp(self):
        self.audit = vh.audit_rules()

    def test_safe_to_run(self):
        self.assertTrue(self.audit["safe_to_run"])

    def test_covers_all_rule_areas(self):
        blob = " ".join(self.audit["guarantees"]).lower()
        for needle in ("qa gatekeeper", "merge delegated", "deploy", "branch protection"):
            self.assertIn(needle, blob)

    def test_required_checks_present(self):
        self.assertIn("qa-check", self.audit["required_checks"])

    def test_never_bypasses_or_force_pushes(self):
        # The audit must always assert these invariants somewhere.
        blob = " ".join(self.audit["guarantees"]).lower()
        self.assertIn("never pushes", blob.replace("force-pushes", "pushes"))

    def test_protected_paths_listed(self):
        self.assertIn("content/", self.audit["protected_paths"])
        self.assertIn("private_content/", self.audit["protected_paths"])


class TestConflictResolutionPolicy(unittest.TestCase):
    """When a manual-approval gate exists, keep it — do not bypass."""

    def test_manual_approval_conflict_keeps_gate(self):
        # Simulate a manual gate by pointing the engine at a temp workflows dir.
        with tempfile.TemporaryDirectory() as d:
            wf = Path(d) / "workflows"
            wf.mkdir()
            (wf / "pr-approval.yml").write_text("name: manual-approval\n", encoding="utf-8")
            orig = vh.WORKFLOWS
            vh.WORKFLOWS = str(wf)
            try:
                audit = vh.audit_rules()
            finally:
                vh.WORKFLOWS = orig
        manual = [c for c in audit["conflicts"] if c["rule"] == "manual-approval"]
        self.assertTrue(manual, "manual-approval conflict should be detected")
        self.assertIn("keep the gate", manual[0]["resolution"].lower())
        # A detected conflict must NOT stop the hotfix from running (fix is always safe).
        self.assertTrue(audit["safe_to_run"])


class TestLock(unittest.TestCase):
    def test_active_lock_blocks(self):
        now = datetime(2026, 6, 20, 6, 0, tzinfo=vh.TZ)
        state = {"running": True, "started_at": now.isoformat()}
        self.assertTrue(vh.lock_is_active(state, now + timedelta(minutes=5)))

    def test_stale_lock_ignored(self):
        now = datetime(2026, 6, 20, 6, 0, tzinfo=vh.TZ)
        state = {"running": True, "started_at": now.isoformat()}
        self.assertFalse(vh.lock_is_active(state, now + timedelta(minutes=45)))


class TestAntiLoop(unittest.TestCase):
    def setUp(self):
        self._orig = vh.STATE_PATH
        self._tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self._tmp.close()
        vh.STATE_PATH = self._tmp.name

    def tearDown(self):
        vh.STATE_PATH = self._orig
        os.unlink(self._tmp.name)

    def test_bump_and_detect(self):
        for _ in range(vh.LOOP_THRESHOLD):
            vh.bump_attempt("qa-7")
        looped, reason = vh.loop_detected("qa-7")
        self.assertTrue(looped)
        self.assertIn("escalate", reason)

    def test_clear_resets(self):
        vh.bump_attempt("qa-8")
        vh.clear_attempt("qa-8")
        looped, _ = vh.loop_detected("qa-8")
        self.assertFalse(looped)

    def test_lock_preserves_attempts(self):
        vh.bump_attempt("qa-9")
        now = datetime.now(vh.TZ)
        self.assertTrue(vh.acquire_lock("build_fail", "qa-9", now))
        # Acquiring the lock must not wipe the anti-loop counter.
        self.assertEqual(vh.read_state().get("fix_attempts", {}).get("qa-9"), 1)


class TestDiagnose(unittest.TestCase):
    def test_merge_conflict_pattern(self):
        d = vh.diagnose("CONFLICT (content): Merge conflict in data/x.json\n<<<<<<< HEAD")
        self.assertEqual(d["pattern_id"], "MERGE_CONFLICT")
        self.assertGreaterEqual(d["confidence"], 70)

    def test_empty_log_is_safe(self):
        d = vh.diagnose("")
        self.assertIn("root_cause", d)


class TestReportShape(unittest.TestCase):
    def _report(self, status="ok", files=None, dry_run=False):
        now = datetime.now(vh.TZ)
        return vh.build_report(
            trigger="build_fail", issue_id="qa-1", branch="vaccine-hotfix/qa-1",
            audit=vh.audit_rules(),
            diagnosis={"root_cause": "x", "confidence": 80, "pattern_id": "ZOLA_BUILD"},
            fix={"actions": [], "files_changed": files or [], "manual_review": False},
            checks={"qa": {"passed": True}, "build": {"passed": True},
                    "tests": {"passed": True}, "passed": True},
            attempts=1, status=status, dry_run=dry_run, started=now, finished=now)

    def test_required_fields(self):
        r = self._report()
        for key in ("report_name", "rule", "trigger", "issue_id", "branch", "pr_url",
                    "precheck", "root_cause", "files_changed", "checks_result",
                    "auto_merge", "deploy_status", "status"):
            self.assertIn(key, r)

    def test_report_name_and_guarantees(self):
        r = self._report()
        self.assertEqual(r["report_name"], "Autofixer_report_by Vacxin")
        self.assertTrue(r["auto_merge"]["merges_only_when_required_checks_pass"])
        self.assertFalse(r["auto_merge"]["force_push_main"])

    def test_deploy_status_variants(self):
        self.assertIn("deploy-on-merge", self._report(status="ok", files=["a.py"])["deploy_status"])
        self.assertIn("no-op", self._report(status="ok", files=[])["deploy_status"])
        self.assertIn("manual review", self._report(status="escalate")["deploy_status"])

    def test_save_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            orig = vh.REPORT_PATH
            vh.REPORT_PATH = os.path.join(d, "report.json")
            try:
                vh.save_report(self._report(files=["a.py"]))
                vh.save_report(self._report(files=["b.py"]))
                data = json.loads(Path(vh.REPORT_PATH).read_text(encoding="utf-8"))
            finally:
                vh.REPORT_PATH = orig
        self.assertEqual(len(data["history"]), 2)
        self.assertEqual(data["latest"]["files_changed"], 1)
        self.assertEqual(data["report_name"], "Autofixer_report_by Vacxin")


class TestEscalationRun(unittest.TestCase):
    """A looping issue escalates without attempting more fixes."""

    def setUp(self):
        self._orig_state, self._orig_report = vh.STATE_PATH, vh.REPORT_PATH
        self._d = tempfile.TemporaryDirectory()
        vh.STATE_PATH = os.path.join(self._d.name, "state.json")
        vh.REPORT_PATH = os.path.join(self._d.name, "report.json")

    def tearDown(self):
        vh.STATE_PATH, vh.REPORT_PATH = self._orig_state, self._orig_report
        self._d.cleanup()

    def test_escalates_after_threshold(self):
        for _ in range(vh.LOOP_THRESHOLD):
            vh.bump_attempt("pr-5")
        report = vh.run(trigger="merge_conflict", issue_id="pr-5",
                        branch_hint="feature/x", dry_run=False, skip_build=True,
                        skip_tests=True)
        self.assertEqual(report["status"], "escalate")
        self.assertTrue(report["manual_review"])
        # Escalation must never claim a deploy.
        self.assertIn("manual review", report["deploy_status"])


if __name__ == "__main__":
    unittest.main()
