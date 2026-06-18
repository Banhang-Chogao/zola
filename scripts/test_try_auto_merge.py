#!/usr/bin/env python3
"""Tests for try_auto_merge bot blocking."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "try_auto_merge.py"

_spec = importlib.util.spec_from_file_location("try_auto_merge", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["try_auto_merge"] = mod
_spec.loader.exec_module(mod)


class BlockedBotTest(unittest.TestCase):
    def test_dependabot_actor_blocked(self):
        pr = {"user": {"login": "dependabot[bot]"}}
        blocked, reason = mod.is_blocked_bot(pr, {})
        self.assertTrue(blocked)
        self.assertIn("dependabot", reason)

    def test_renovate_branch_blocked(self):
        pr = {"user": {"login": "someone"}, "head": {"ref": "renovate/actions-abc"}}
        blocked, _ = mod.is_blocked_bot(pr, {})
        self.assertTrue(blocked)

    def test_feature_branch_allowed(self):
        pr = {"user": {"login": "Banhang-Chogao"}, "head": {"ref": "feature/foo"}}
        blocked, _ = mod.is_blocked_bot(pr, {})
        self.assertFalse(blocked)

    def test_is_eligible_rejects_dependabot(self):
        pr = {
            "draft": False,
            "state": "open",
            "base": {"ref": "main"},
            "user": {"login": "dependabot[bot]"},
            "head": {"ref": "dependabot/github_actions-foo"},
            "labels": [],
        }
        ok, reason = mod.is_eligible(pr, {})
        self.assertFalse(ok)
        self.assertIn("dependabot", reason)


if __name__ == "__main__":
    unittest.main()