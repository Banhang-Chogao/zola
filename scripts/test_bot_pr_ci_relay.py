#!/usr/bin/env python3
"""Static tests for bot PR CI relay (Action required fix)."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class BotPrCiRelayTests(unittest.TestCase):
    def test_trigger_script_exists(self):
        p = REPO / ".github/scripts/trigger_bot_pr_ci.sh"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("QA Gatekeeper", text)
        self.assertIn("PR Policy", text)

    def test_resolve_script_exists(self):
        p = REPO / ".github/scripts/resolve_open_bot_pr.sh"
        self.assertTrue(p.is_file())
        self.assertIn("chore|qa|autofix", p.read_text(encoding="utf-8"))

    def test_push_via_pr_calls_trigger(self):
        text = (REPO / ".github/scripts/push_via_pr.sh").read_text(encoding="utf-8")
        self.assertIn("trigger_bot_pr_ci.sh", text)

    def test_qa_skips_bot_pull_request(self):
        text = (REPO / ".github/workflows/qa.yml").read_text(encoding="utf-8")
        self.assertIn("github-actions[bot]", text)
        self.assertNotIn("head_branch != 'main'", text)

    def test_pr_policy_has_workflow_dispatch(self):
        text = (REPO / ".github/workflows/pr-policy.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("github-actions[bot]", text)

    def test_auto_merge_skips_bot_pull_request(self):
        text = (REPO / ".github/workflows/auto-merge.yml").read_text(encoding="utf-8")
        self.assertIn("github-actions[bot]", text)

    def test_maintenance_workflows_have_actions_write(self):
        workflows = [
            "build-dashboard.yml",
            "merge-report.yml",
            "compliance-score.yml",
            "google-trends.yml",
            "build-related.yml",
        ]
        for wf in workflows:
            text = (REPO / ".github/workflows" / wf).read_text(encoding="utf-8")
            self.assertIn("actions: write", text, wf)


if __name__ == "__main__":
    unittest.main()