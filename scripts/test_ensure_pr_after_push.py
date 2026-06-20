#!/usr/bin/env python3
"""Tests for ensure_pr_after_push pure helpers (no network)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "ensure_pr_after_push.py"

_spec = importlib.util.spec_from_file_location("ensure_pr_after_push", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["ensure_pr_after_push"] = mod
_spec.loader.exec_module(mod)


class BranchEligibleTest(unittest.TestCase):
    def test_claude_branch_eligible(self):
        ok, _ = mod.branch_eligible("claude/foo-bar", {})
        self.assertTrue(ok)

    def test_codex_branch_eligible(self):
        ok, _ = mod.branch_eligible("codex/x", {})
        self.assertTrue(ok)

    def test_vaccine_hotfix_eligible(self):
        ok, _ = mod.branch_eligible("vaccine-hotfix/deploy-1", {})
        self.assertTrue(ok)

    def test_main_never_eligible(self):
        ok, reason = mod.branch_eligible("main", {})
        self.assertFalse(ok)
        self.assertIn("main", reason)

    def test_unknown_prefix_rejected(self):
        ok, _ = mod.branch_eligible("random-branch", {})
        self.assertFalse(ok)

    def test_force_overrides(self):
        ok, _ = mod.branch_eligible("random-branch", {}, force=True)
        self.assertTrue(ok)

    def test_policy_prefixes_merged(self):
        ok, _ = mod.branch_eligible("experiment/x", {"auto_eligible_branch_prefixes": ["experiment/"]})
        self.assertTrue(ok)
        # Defaults still honoured even when policy provides its own list.
        ok2, _ = mod.branch_eligible("claude/y", {"auto_eligible_branch_prefixes": ["experiment/"]})
        self.assertTrue(ok2)


class TitleBodyTest(unittest.TestCase):
    def test_title_includes_branch(self):
        t = mod.build_pr_title("claude/foo", "feat: add thing")
        self.assertIn("claude/foo", t)
        self.assertIn("feat: add thing", t)

    def test_title_fallback_without_subject(self):
        t = mod.build_pr_title("codex/bar", "")
        self.assertIn("bar", t)
        self.assertIn("codex/bar", t)

    def test_body_has_required_sections(self):
        files = [{"filename": "a.py", "additions": 3, "deletions": 1, "status": "modified"}]
        body = mod.build_pr_body("claude/foo", "did stuff", files, "success", "qa-check success")
        for marker in ("## Summary", "## Changed files", "## QA / Build status", "## Rollback note"):
            self.assertIn(marker, body)
        self.assertIn("a.py", body)
        self.assertIn("green", body)

    def test_body_qa_failure_icon(self):
        body = mod.build_pr_body("claude/foo", "", [], "failure", "qa-check kết luận: failure")
        self.assertIn("failed", body)


class SummaryTest(unittest.TestCase):
    def test_single_commit(self):
        commits = [{"commit": {"message": "fix: one thing\n\nbody"}}]
        self.assertEqual(mod.summarize_commits(commits), "fix: one thing")

    def test_multiple_commits_bulleted(self):
        commits = [
            {"commit": {"message": "a"}},
            {"commit": {"message": "b"}},
        ]
        out = mod.summarize_commits(commits)
        self.assertIn("- a", out)
        self.assertIn("- b", out)

    def test_empty(self):
        self.assertEqual(mod.summarize_commits([]), "")


class TaskNameTest(unittest.TestCase):
    def test_strips_prefix(self):
        self.assertEqual(mod.task_name_from_branch("claude/zero-barrier"), "zero-barrier")

    def test_no_slash(self):
        self.assertEqual(mod.task_name_from_branch("hotfix"), "hotfix")


if __name__ == "__main__":
    unittest.main()
