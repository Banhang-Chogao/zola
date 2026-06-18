#!/usr/bin/env python3
"""Tests for scripts/vaccine_autofixer.py (Vaccine V11 engine)."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaccine_autofixer as va  # noqa: E402


class TestVaccineRegistry(unittest.TestCase):
    def test_parses_vaccine_blocks(self):
        md = (
            "intro\n"
            "#### V1 — build-related: HuggingFace 401\n"
            "- **Dấu hiệu:** log `snapshot_download` báo `401`.\n"
            "- **FIXER:** dùng `org/model` đầy đủ.\n\n"
            "#### V2 — slack-notify: sai input\n"
            "- **Dấu hiệu:** Missing input.\n"
            "- **FIXER:** cú pháp v3.\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(md)
            path = fh.name
        try:
            vaccines = va.load_vaccines(path)
        finally:
            os.unlink(path)
        self.assertEqual([v["code"] for v in vaccines], ["V1", "V2"])
        self.assertIn("HuggingFace", vaccines[0]["title"])
        self.assertTrue(vaccines[0]["signature"])
        self.assertTrue(vaccines[0]["fixer"])

    def test_real_claude_md_has_vaccines(self):
        vaccines = va.load_vaccines()
        codes = {v["code"] for v in vaccines}
        # Library ships at least V1..V7.
        self.assertTrue({"V1", "V7"}.issubset(codes), codes)


class TestNextScheduledRun(unittest.TestCase):
    def test_next_run_is_0600_ict_future(self):
        base = datetime(2026, 6, 18, 9, 0, tzinfo=va.TZ)  # 09:00 → next day 06:00
        nxt = va.next_scheduled_run(base)
        self.assertEqual((nxt.hour, nxt.minute), (6, 0))
        self.assertEqual(nxt.date(), (base + timedelta(days=1)).date())

    def test_before_0600_same_day(self):
        base = datetime(2026, 6, 18, 3, 0, tzinfo=va.TZ)
        nxt = va.next_scheduled_run(base)
        self.assertEqual(nxt.date(), base.date())
        self.assertEqual(nxt.hour, 6)


class TestLock(unittest.TestCase):
    def test_active_lock_blocks(self):
        now = datetime(2026, 6, 18, 6, 0, tzinfo=va.TZ)
        state = {"running": True, "started_at": now.isoformat()}
        self.assertTrue(va.lock_is_active(state, now + timedelta(minutes=5)))

    def test_stale_lock_ignored(self):
        now = datetime(2026, 6, 18, 6, 0, tzinfo=va.TZ)
        state = {"running": True, "started_at": now.isoformat()}
        self.assertFalse(va.lock_is_active(state, now + timedelta(minutes=45)))

    def test_no_lock_when_not_running(self):
        self.assertFalse(va.lock_is_active({"running": False}, datetime.now(va.TZ)))


class TestReportShape(unittest.TestCase):
    def test_dry_run_report_has_required_fields(self):
        report = va.run(trigger="manual", dry_run=True, skip_build=True)
        for key in ("trigger", "last_run", "next_scheduled_run", "matched_vaccines",
                    "fixed_count", "qa_result", "build_result", "production_status",
                    "status"):
            self.assertIn(key, report)
        self.assertEqual(report["status"], "dry-run")
        # dry-run must not claim any fixes
        self.assertEqual(report["fixed_count"], 0)
        json.dumps(report)  # serializable


if __name__ == "__main__":
    unittest.main()
