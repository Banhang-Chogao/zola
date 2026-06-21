"""Tests for footer countdown config shape."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "footer-countdown.json"
DISPLAY_MODES = {"days", "days_hours_minutes", "full"}


class FooterCountdownConfigTest(unittest.TestCase):
    def test_config_file_exists_and_valid_json(self):
        self.assertTrue(CONFIG_PATH.exists(), "data/footer-countdown.json missing")
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)

    def test_required_keys(self):
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for key in (
            "enabled",
            "title",
            "targetDate",
            "targetTime",
            "timezone",
            "displayMode",
            "footerTextPrefix",
            "footerTextSuffix",
        ):
            self.assertIn(key, data, f"missing key: {key}")

    def test_display_mode_enum(self):
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertIn(data["displayMode"], DISPLAY_MODES)

    def test_date_format_when_enabled(self):
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("enabled"):
            self.assertRegex(data["targetDate"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertRegex(data["targetTime"], r"^\d{2}:\d{2}$")
            self.assertTrue(data["title"].strip())


class FooterCountdownDualFormatTest(unittest.TestCase):
    """Regression: dual-counter uses total hours + minute remainder."""

    def test_remaining_parts_math(self):
        sec = 128 * 86400 + 42 * 60 + 18 * 3600 + 7  # 128d + 18h + 42m + 7s
        days = sec // 86400
        total_hours = sec // 3600
        minutes = (sec % 3600) // 60
        seconds = sec % 60
        self.assertEqual(days, 128)
        self.assertEqual(total_hours, 128 * 24 + 18)
        self.assertEqual(minutes, 42)
        self.assertEqual(seconds, 7)

    def test_footer_js_uses_dual_markup_and_seconds(self):
        js = (ROOT / "static/js/footer-countdown.js").read_text(encoding="utf-8")
        self.assertIn("footer-countdown__dual", js)
        self.assertIn("totalHours", js)
        self.assertIn("seconds", js)
        self.assertIn("GIÂY", js)
        self.assertIn("displayMode", js)
        self.assertIn("tickMs()", js)
        self.assertIn("1000", js)


if __name__ == "__main__":
    unittest.main()