#!/usr/bin/env python3
"""Tests for scripts/check_cwv_hygiene.py"""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestCWVHygiene(unittest.TestCase):
    def test_gate_passes_on_clean_repo(self):
        result = subprocess.run(
            ["python3", "scripts/check_cwv_hygiene.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_detects_google_fonts_in_base(self):
        base = ROOT / "templates/base.html"
        original = base.read_text(encoding="utf-8")
        try:
            base.write_text(
                original + '\n<link href="https://fonts.googleapis.com/css2?family=Inter">\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                ["python3", "scripts/check_cwv_hygiene.py"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("google-fonts-stylesheet", result.stdout)
        finally:
            base.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)