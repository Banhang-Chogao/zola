#!/usr/bin/env python3
"""Unit tests — auto-merge policy (ZERO_BARRIER_AUTOMATION)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auto_merge_policy import (
    PrContext,
    checks_pass,
    evaluate,
    is_dashboard_refresh_pr,
    protected_hits,
)


def _ctx(**kwargs) -> PrContext:
    defaults = {
        "number": 1,
        "title": "chore: refresh Merge Report data",
        "body": "Automated update",
        "head_ref": "chore/merge-report-data",
        "actor": "github-actions[bot]",
        "labels": set(),
        "paths": ["data/merge-report.json"],
        "checks": [
            {"name": "qa-check", "conclusion": "SUCCESS"},
        ],
    }
    defaults.update(kwargs)
    return PrContext(**defaults)


class TestChecksPass(unittest.TestCase):
    def test_qa_check_only(self):
        ok, _ = checks_pass(_ctx())
        self.assertTrue(ok)

    def test_missing_qa_check(self):
        ok, msg = checks_pass(_ctx(checks=[]))
        self.assertFalse(ok)
        self.assertIn("status check", msg.lower())

    def test_failed_qa_check(self):
        ok, msg = checks_pass(
            _ctx(checks=[{"name": "qa-check", "conclusion": "FAILURE"}])
        )
        self.assertFalse(ok)
        self.assertIn("qa-check", msg)


class TestZeroBarrier(unittest.TestCase):
    def test_workflow_change_allowed(self):
        hits = protected_hits(_ctx(paths=[".github/workflows/deploy.yml"]))
        self.assertFalse(hits)

    def test_oauth_title_allowed(self):
        hits = protected_hits(_ctx(title="fix(f-dashboard): restore GitHub OAuth login"))
        self.assertFalse(hits)

    def test_chore_data_auto_merge(self):
        ready, reason, cat = evaluate(_ctx())
        self.assertTrue(ready, reason)
        self.assertEqual(cat, "auto_eligible")
        self.assertIn("ZERO_BARRIER", reason)

    def test_workflow_pr_auto_merge(self):
        ready, reason, cat = evaluate(
            _ctx(
                title="fix(ci): update deploy workflow",
                head_ref="fix/deploy-workflow",
                paths=[".github/workflows/deploy.yml"],
            )
        )
        self.assertTrue(ready, reason)
        self.assertEqual(cat, "auto_eligible")


class TestCategories(unittest.TestCase):
    def test_dashboard_refresh(self):
        self.assertTrue(is_dashboard_refresh_pr(_ctx(title="chore: refresh Build Dashboard data")))

    def test_compliance_autofix(self):
        ready, _, cat = evaluate(
            _ctx(
                title="qa: Compliance Score audit + auto-fix",
                paths=["data/compliance-score.json"],
                compliance_score=97.0,
            )
        )
        self.assertTrue(ready)
        self.assertEqual(cat, "auto_eligible")

    def test_compliance_low_score_still_auto_merge(self):
        ready, reason, cat = evaluate(
            _ctx(
                title="qa: Compliance Score audit + auto-fix",
                paths=["data/compliance-score.json"],
                compliance_score=80.0,
            )
        )
        self.assertTrue(ready, reason)
        self.assertEqual(cat, "auto_eligible")

    def test_no_auto_merge_label_ignored(self):
        ready, reason, cat = evaluate(_ctx(labels={"no-auto-merge"}))
        self.assertTrue(ready, reason)
        self.assertEqual(cat, "auto_eligible")


if __name__ == "__main__":
    unittest.main()