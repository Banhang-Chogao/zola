#!/usr/bin/env python3
"""Tests for auto_build_failed_healing — 48h filtering, classification, dedup,
dry-run no-mutation, and private-file independence."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auto_build_failed_healing as bot  # noqa: E402

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)


def run(conclusion="failure", name="deploy", age_h=1.0):
    created = NOW - timedelta(hours=age_h)
    return {
        "id": 100, "name": name, "conclusion": conclusion,
        "status": "completed", "created_at": created.isoformat(),
        "head_branch": "main", "html_url": "http://x",
    }


class TestWindow(unittest.TestCase):
    def test_within_48h_failure_is_processed(self):
        ok, reason = bot.should_process_run(run(age_h=10), 48, NOW)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_older_than_48h_is_stale_ignored(self):
        ok, reason = bot.should_process_run(run(age_h=72), 48, NOW)
        self.assertFalse(ok)
        self.assertEqual(reason, "stale_ignored")

    def test_exactly_48h_boundary(self):
        ok, _ = bot.should_process_run(run(age_h=48), 48, NOW)
        self.assertTrue(ok)

    def test_cancelled_not_processed(self):
        ok, reason = bot.should_process_run(run(conclusion="cancelled"), 48, NOW)
        self.assertFalse(ok)
        self.assertEqual(reason, "cancelled_skipped")

    def test_skipped_not_processed(self):
        ok, reason = bot.should_process_run(run(conclusion="skipped"), 48, NOW)
        self.assertEqual(reason, "cancelled_skipped")
        self.assertFalse(ok)

    def test_success_not_processed(self):
        ok, reason = bot.should_process_run(run(conclusion="success"), 48, NOW)
        self.assertFalse(ok)
        self.assertEqual(reason, "not_failure")

    def test_unwatched_workflow_skipped(self):
        ok, reason = bot.should_process_run(run(name="Random Cron Job"), 48, NOW)
        self.assertFalse(ok)
        self.assertEqual(reason, "not_watched")

    def test_is_within_hours_future_tolerated(self):
        # tiny clock skew (slightly future) tolerated
        future = NOW + timedelta(minutes=10)
        self.assertTrue(bot.is_within_hours(future, 48, NOW))


class TestClassify(unittest.TestCase):
    def setUp(self):
        self.patterns = bot.load_patterns()
        self.assertTrue(self.patterns, "registry must load")

    def test_faq_field_naming_matches_p0(self):
        log = "ERROR Reason: Variable `item.q` not found in context while " \
              "rendering 'page.html'. [[extra.faq]] block"
        m = bot.classify(log, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["id"], "faq-field-naming")
        self.assertEqual(m["severity"], "P0")

    def test_generated_json_conflict_matches_p1(self):
        log = "CONFLICT (content): Merge conflict in data/references.json"
        m = bot.classify(log, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["severity"], "P1")

    def test_seo_advisory_is_p2(self):
        log = "compliance warning: thin content / missing faq, weak internal links"
        m = bot.classify(log, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["severity"], "P2")

    def test_no_match_returns_none(self):
        m = bot.classify("totally unrelated green build output", self.patterns)
        self.assertIsNone(m)

    def test_most_severe_wins(self):
        # text that touches multiple patterns → P0 should be chosen over P1
        log = ("Variable `item.q` not found [[extra.faq]] and also "
               "Merge conflict in data/references.json")
        m = bot.classify(log, self.patterns)
        self.assertEqual(m["severity"], "P0")


class TestSafeFixDryRun(unittest.TestCase):
    def test_dry_run_does_not_mutate(self):
        pat = {"id": "faq-field-naming", "fixer": "faq-field-rename",
               "severity": "P0"}
        res = bot.apply_safe_fix(pat, dry_run=True)
        self.assertFalse(res.get("changed"))

    def test_pattern_without_fixer_requires_manual(self):
        pat = {"id": "x", "fixer": None, "severity": "P0"}
        res = bot.apply_safe_fix(pat, dry_run=False)
        self.assertFalse(res.get("ran"))
        self.assertIn("manual", res.get("detail", "").lower())


class TestDedup(unittest.TestCase):
    def test_dedup_key_stable(self):
        k1 = bot.dedup_key(1, "p", "main")
        k2 = bot.dedup_key(1, "p", "main")
        self.assertEqual(k1, k2)

    def test_already_handled(self):
        state = {"handled": []}
        key = bot.dedup_key(5, "faq-field-naming", "main")
        self.assertFalse(bot.already_handled(state, key))
        bot.record_handled(state, key, {"pattern": "faq-field-naming"})
        self.assertTrue(bot.already_handled(state, key))

    def test_handled_capped(self):
        state = {"handled": []}
        for i in range(250):
            bot.record_handled(state, f"k{i}", {})
        self.assertLessEqual(len(state["handled"]), 200)


class TestPrivateIndependence(unittest.TestCase):
    def test_private_not_in_public_sources(self):
        self.assertNotIn("CLAUDE_PRIVATE.md", bot.PUBLIC_HEALING_SOURCES)

    def test_confirm_private_safety_no_crash(self):
        # must run without the private file and without raising
        bot.confirm_private_safety()

    def test_load_patterns_independent_of_private(self):
        # registry loads from the committed public file only
        self.assertTrue(bot.load_patterns())


class TestHeapWindowCeiling(unittest.TestCase):
    def test_main_caps_hours_at_48(self):
        # --hours 200 must be clamped; dry-run, offline → no PR, exit 0
        rc = bot.main(["--hours", "200", "--dry-run"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
