#!/usr/bin/env python3
"""Static tests for bot PR CI relay (no workflow approval gate)."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class BotPrCiRelayTests(unittest.TestCase):
    def test_pr_policy_removed(self):
        self.assertFalse(
            (REPO / ".github/workflows/pr-policy.yml").exists(),
            "pr-policy.yml must be deleted",
        )

    def test_no_pull_request_triggers(self):
        """pull_request on bot PRs causes 'workflows awaiting approval' UI."""
        import re

        for wf in (REPO / ".github/workflows").glob("*.yml"):
            text = wf.read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"^  pull_request:\s*$", text, re.MULTILINE),
                f"{wf.name} must not use pull_request trigger",
            )

    def test_qa_uses_push_trigger(self):
        text = (REPO / ".github/workflows/qa.yml").read_text(encoding="utf-8")
        self.assertIn("push:", text)
        self.assertIn("workflow_dispatch:", text)

    def test_trigger_script_dispatches_qa_and_auto_merge(self):
        text = (REPO / ".github/scripts/trigger_bot_pr_ci.sh").read_text(encoding="utf-8")
        self.assertIn("QA Gatekeeper", text)
        self.assertIn("Auto Merge PRs", text)
        self.assertNotIn("PR Policy", text)

    def test_resolve_script_exists(self):
        p = REPO / ".github/scripts/resolve_open_bot_pr.sh"
        self.assertTrue(p.is_file())
        self.assertIn("chore|qa|autofix", p.read_text(encoding="utf-8"))

    def test_push_via_pr_calls_trigger(self):
        text = (REPO / ".github/scripts/push_via_pr.sh").read_text(encoding="utf-8")
        self.assertIn("trigger_bot_pr_ci.sh", text)

    def test_resolve_open_bot_pr_uses_gh_author_field(self):
        text = (REPO / ".github/scripts/resolve_open_bot_pr.sh").read_text(encoding="utf-8")
        self.assertIn("author", text)
        self.assertIn(".author.login // .user.login", text)

    def test_auto_merge_uses_workflow_run_not_pull_request(self):
        text = (REPO / ".github/workflows/auto-merge.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_run:", text)
        self.assertIn("QA Gatekeeper", text)

    def test_changelog_triggers_on_push_main(self):
        text = (REPO / ".github/workflows/changelog-update.yml").read_text(encoding="utf-8")
        self.assertIn("branches: [main]", text)

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