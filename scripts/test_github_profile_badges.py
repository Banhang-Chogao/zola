#!/usr/bin/env python3
"""Tests for build_github_profile_badges.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_github_profile_badges.py"

_spec = importlib.util.spec_from_file_location("build_github_profile_badges", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["build_github_profile_badges"] = mod
_spec.loader.exec_module(mod)


class DedupeBadgesTest(unittest.TestCase):
    def test_removes_duplicate_ids(self):
        badges = [
            {"id": "pull-shark", "title": "A"},
            {"id": "pull-shark", "title": "B"},
            {"id": "starstruck", "title": "C"},
            {"id": "", "title": "D"},
        ]
        out = mod._dedupe_badges(badges)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["title"], "A")


class RepoMilestoneBadgesTest(unittest.TestCase):
    def test_stars_badge_tier(self):
        badges = mod._repo_milestone_badges({"stargazers_count": 12, "forks_count": 0})
        self.assertEqual(len(badges), 1)
        self.assertEqual(badges[0]["id"], "repo-stars")
        self.assertEqual(badges[0]["tier"], "silver")


class BuildBadgesTest(unittest.TestCase):
    def test_config_only_shape(self):
        payload = mod.build_badges(use_api=False)
        self.assertIn("badges", payload)
        self.assertIn("profile_url", payload)
        self.assertGreater(len(payload["badges"]), 0)
        self.assertEqual(payload["source"], "config")

    def test_no_duplicate_ids_in_output(self):
        payload = mod.build_badges(use_api=False)
        ids = [b["id"] for b in payload["badges"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_write_output_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            orig_out = mod.OUTPUT
            orig_cfg = mod.CONFIG
            try:
                mod.OUTPUT = tpath / "github-profile-badges.json"
                mod.CONFIG = tpath / "config.json"
                mod.CONFIG.write_text(
                    json.dumps({
                        "profile": "test-user",
                        "profile_url": "https://github.com/test-user",
                        "badges": [{"id": "demo", "title": "Demo", "tier": "default"}],
                    }),
                    encoding="utf-8",
                )
                payload = mod.build_badges(use_api=False)
                mod.write_output(payload)
                self.assertTrue(mod.OUTPUT.is_file())
                loaded = json.loads(mod.OUTPUT.read_text())
                self.assertEqual(loaded["badges"][0]["id"], "demo")
            finally:
                mod.OUTPUT = orig_out
                mod.CONFIG = orig_cfg


if __name__ == "__main__":
    unittest.main()