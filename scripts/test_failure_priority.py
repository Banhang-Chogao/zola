"""Validate the Failure Priority Policy triage engine.

CLAUDE.md → "## Failure Priority Policy":
- Fix only REQUIRED failures on the LATEST HEAD first.
- Order: secrets/security > merge conflict > build/syntax > QA/vaccine >
  links > runtime route/API > SEO/AdSense > UI.
- Ignore stale failures (older commits) and report-only workflows.
"""
from __future__ import annotations

import unittest

from scripts.failure_priority import (
    Failure,
    FailureTier,
    build_plan,
    classify,
    is_report_only,
    is_stale,
    triage,
)

HEAD = "abc123def456"
OLD = "0000deadbeef0"


def _f(**kw) -> Failure:
    return Failure.from_dict(kw)


class ClassifyTest(unittest.TestCase):
    def test_pattern_id_takes_precedence(self):
        self.assertEqual(classify(_f(pattern_id="MERGE_CONFLICT")), FailureTier.MERGE_CONFLICT)
        self.assertEqual(classify(_f(pattern_id="ZOLA_BUILD")), FailureTier.BUILD)
        self.assertEqual(classify(_f(pattern_id="BROKEN_LINK")), FailureTier.LINKS)
        self.assertEqual(classify(_f(pattern_id="WORKFLOW_PERMISSION")), FailureTier.SECURITY)

    def test_keyword_fallback(self):
        self.assertEqual(classify(_f(log="gitleaks found a secret token")), FailureTier.SECURITY)
        self.assertEqual(classify(_f(log="CONFLICT (content): merge conflict in x")), FailureTier.MERGE_CONFLICT)
        self.assertEqual(classify(_f(log="Failed to build the site")), FailureTier.BUILD)
        self.assertEqual(classify(_f(check="qa-check", log="vaccine detector FAIL")), FailureTier.QA_VACCINE)
        self.assertEqual(classify(_f(log="3 internal broken links")), FailureTier.LINKS)
        self.assertEqual(classify(_f(log="GET /cms/save-post returned 404")), FailureTier.RUNTIME)
        self.assertEqual(classify(_f(log="missing meta description for SEO")), FailureTier.SEO)
        self.assertEqual(classify(_f(log="responsive css layout broken")), FailureTier.UI)

    def test_unknown(self):
        self.assertEqual(classify(_f(log="something totally unrelated")), FailureTier.UNKNOWN)


class StaleTest(unittest.TestCase):
    def test_old_commit_is_stale(self):
        self.assertTrue(is_stale(_f(head_sha=OLD), HEAD))

    def test_head_commit_not_stale(self):
        self.assertFalse(is_stale(_f(head_sha=HEAD), HEAD))

    def test_unknown_sha_not_dropped(self):
        # We never silently drop a failure we cannot date.
        self.assertFalse(is_stale(_f(head_sha=""), HEAD))
        self.assertFalse(is_stale(_f(head_sha=OLD), ""))


class ReportOnlyTest(unittest.TestCase):
    def test_observer_workflows_are_report_only(self):
        for wf in ("perf-audit", "build-dashboard", "vaccine-autofixer", "qa-rule-checker", "ga-vacxin"):
            self.assertTrue(is_report_only(_f(workflow=wf)), wf)

    def test_qa_gate_is_not_report_only(self):
        self.assertFalse(is_report_only(_f(workflow="qa", check="qa-check")))
        self.assertFalse(is_report_only(_f(workflow="deploy")))
        self.assertFalse(is_report_only(_f(workflow="qa-404-checker")))

    def test_required_check_overrides_report_only(self):
        # Even if the workflow name matched a report-only set, an explicit
        # required check name keeps it actionable.
        self.assertFalse(is_report_only(_f(workflow="perf-audit", check="qa-check")))


class TriageOrderingTest(unittest.TestCase):
    def test_full_ladder_order(self):
        failures = [
            _f(workflow="ui-x", log="css layout", head_sha=HEAD),
            _f(workflow="seo-x", log="adsense schema", head_sha=HEAD),
            _f(workflow="api-x", log="backend /api 500", head_sha=HEAD),
            _f(workflow="links-x", log="internal broken 404", head_sha=HEAD),
            _f(workflow="qa", check="qa-check", log="vaccine FAIL", head_sha=HEAD),
            _f(workflow="build-x", log="Failed to build the site", head_sha=HEAD),
            _f(workflow="merge-x", log="merge conflict", head_sha=HEAD),
            _f(workflow="sec-x", log="secret token leak", head_sha=HEAD),
        ]
        ordered = triage(failures, HEAD)
        tiers = [f.tier for f in ordered]
        self.assertEqual(tiers, sorted(tiers))
        self.assertEqual(ordered[0].tier, FailureTier.SECURITY)
        self.assertEqual(ordered[-1].tier, FailureTier.UI)

    def test_stale_dropped_from_plan(self):
        failures = [
            _f(workflow="build-x", log="Failed to build the site", head_sha=OLD),
            _f(workflow="qa", check="qa-check", log="vaccine FAIL", head_sha=HEAD),
        ]
        ordered = triage(failures, HEAD)
        self.assertEqual(len(ordered), 1)
        self.assertEqual(ordered[0].tier, FailureTier.QA_VACCINE)

    def test_report_only_dropped(self):
        failures = [
            _f(workflow="perf-audit", log="Failed to build", head_sha=HEAD),
            _f(workflow="qa", check="qa-check", log="qa fail", head_sha=HEAD),
        ]
        ordered = triage(failures, HEAD)
        self.assertEqual([f.workflow for f in ordered], ["qa"])

    def test_passing_checks_not_actionable(self):
        failures = [
            _f(workflow="qa", check="qa-check", conclusion="success", head_sha=HEAD),
        ]
        self.assertEqual(triage(failures, HEAD), [])

    def test_stable_within_tier(self):
        failures = [
            _f(workflow="build-a", log="Failed to build", head_sha=HEAD),
            _f(workflow="build-b", log="SyntaxError", head_sha=HEAD),
        ]
        ordered = triage(failures, HEAD)
        self.assertEqual([f.workflow for f in ordered], ["build-a", "build-b"])


class BuildPlanTest(unittest.TestCase):
    def test_plan_shape_and_fix_first(self):
        raw = [
            {"workflow": "ui-x", "log": "css", "head_sha": HEAD},
            {"workflow": "merge-x", "log": "merge conflict", "head_sha": HEAD},
            {"workflow": "perf-audit", "log": "Failed to build", "head_sha": HEAD},
            {"workflow": "build-x", "log": "Failed to build", "head_sha": OLD},
        ]
        plan = build_plan(raw, HEAD)
        self.assertEqual(plan["fix_first"]["tier"], "MERGE_CONFLICT")
        self.assertEqual(plan["summary"]["actionable"], 2)  # merge + ui
        reasons = {d["dropped_reason"] for d in plan["dropped"]}
        self.assertIn("report-only workflow", reasons)
        self.assertIn("stale (older than HEAD)", reasons)

    def test_empty_input_safe(self):
        plan = build_plan([], HEAD)
        self.assertIsNone(plan["fix_first"])
        self.assertEqual(plan["summary"]["total"], 0)

    def test_malformed_items_ignored(self):
        plan = build_plan(["not-a-dict", {"workflow": "qa", "check": "qa-check", "log": "fail", "head_sha": HEAD}], HEAD)
        self.assertEqual(plan["summary"]["actionable"], 1)


if __name__ == "__main__":
    unittest.main()
