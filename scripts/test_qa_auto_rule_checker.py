"""Tests for qa-auto-rule-checker.py"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SCRIPT = Path(__file__).resolve().parent / "qa-auto-rule-checker.py"
_spec = importlib.util.spec_from_file_location("qa_auto_rule_checker", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["qa_auto_rule_checker"] = mod
_spec.loader.exec_module(mod)


class RuleCheckerTest(unittest.TestCase):
    def test_run_all_scanners_returns_list(self):
        conflicts = mod.run_all_scanners()
        self.assertIsInstance(conflicts, list)
        for c in conflicts:
            self.assertIn(c.severity, mod.SEVERITIES)
            self.assertGreaterEqual(c.confidence, 0.0)
            self.assertLessEqual(c.confidence, 1.0)

    def test_build_report_payload(self):
        conflicts = [
            mod.Conflict(
                id="test",
                category="CLAUDE.md",
                severity="LOW",
                title="Test",
                rule_a="A",
                rule_b="B",
                resolution="Fix",
                confidence=0.5,
            )
        ]
        payload = mod.build_report_payload(
            conflicts, loop_detected=False, loop_reason="", fixes_applied=[]
        )
        self.assertEqual(payload["summary"]["total_conflicts"], 1)
        self.assertEqual(payload["conflicts"][0]["id"], "test")

    def test_render_markdown_contains_title(self):
        payload = {
            "updated_at": "2026-06-18T00:00:00Z",
            "summary": {
                "total_conflicts": 1,
                "by_severity": {"LOW": 1},
                "loop_detected": False,
                "loop_reason": "",
                "fixes_applied": [],
            },
            "conflicts": [
                {
                    "title": "Test conflict",
                    "category": "Test",
                    "severity": "LOW",
                    "confidence": 0.5,
                    "rule_a": "A",
                    "rule_b": "B",
                    "resolution": "R",
                }
            ],
        }
        md = mod.render_markdown(payload)
        self.assertIn("# Rule Conflict Report", md)
        self.assertIn("Test conflict", md)

    def test_detect_pr_loop_from_state(self):
        state = {"fix_attempts": {"CLAUDE.md:claude_x": 5}, "loop_detected": False}
        loop, reason = mod.detect_pr_loop(state)
        self.assertTrue(loop)
        self.assertIn("auto-fix", reason)

    def test_apply_fixes_respects_confidence(self):
        called = []

        def fake_fix():
            called.append(True)
            return True

        fixes = [
            mod.FixAction("x", "low", ["a"], lambda: False, 0.5),
            mod.FixAction("y", "high", ["b"], fake_fix, 0.95),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(mod, "REPORTS_DIR", Path(tmp) / "reports"):
                changed, fixed_ids = mod.apply_fixes(fixes, min_confidence=0.9)
        self.assertEqual(changed, ["b"])
        self.assertEqual(fixed_ids, ["y"])
        self.assertEqual(len(called), 1)

    def test_robots_subpath_not_root_disallow(self):
        robots = "User-agent: *\nAllow: /\nDisallow: /editor/\nDisallow: /data/\n"
        self.assertFalse(mod._robots_disallows_root(robots))

    def test_robots_root_disallow_detected(self):
        robots = "User-agent: *\nDisallow: /\n"
        self.assertTrue(mod._robots_disallows_root(robots))

    def test_write_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(mod, "REPORTS_DIR", root / "reports"), mock.patch.object(
                mod, "REPORT_JSON", root / "reports" / "rule-conflict-report.json"
            ), mock.patch.object(mod, "REPORT_MD", root / "reports" / "rule-conflict-report.md"):
                payload = mod.build_report_payload([], loop_detected=False, loop_reason="", fixes_applied=[])
                mod.write_reports(payload, "# empty\n")
                self.assertTrue((root / "reports" / "rule-conflict-report.json").exists())
                data = json.loads((root / "reports" / "rule-conflict-report.json").read_text())
                self.assertEqual(data["summary"]["total_conflicts"], 0)


if __name__ == "__main__":
    unittest.main()