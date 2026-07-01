#!/usr/bin/env python3
"""Tests for scripts/check_adsense_viewability.py"""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestAdSenseViewability(unittest.TestCase):
    def test_placeholder_mode_passes(self):
        result = subprocess.run(
            ["python3", "scripts/check_adsense_viewability.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("enabled: False", result.stdout)
        self.assertIn("homepage_max_slots: 3", result.stdout)

    def test_homepage_template_slot_cap(self):
        result = subprocess.run(
            ["python3", "scripts/check_adsense_viewability.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotIn("homepage-too-many-slots", result.stdout)

    def test_detects_missing_slots_when_enabled(self):
        config = ROOT / "config.toml"
        original = config.read_text(encoding="utf-8")
        patched = original.replace(
            "[extra.ads]\nenabled = false",
            "[extra.ads]\nenabled = true",
            1,
        )
        try:
            config.write_text(patched, encoding="utf-8")
            result = subprocess.run(
                ["python3", "scripts/check_adsense_viewability.py"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing-publisher-id", result.stdout)
        finally:
            config.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)