#!/usr/bin/env python3
"""Tests for scripts/check_faq_top_posts.py"""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestFAQTopPostsGate(unittest.TestCase):
    def test_top_posts_have_faq(self):
        result = subprocess.run(
            ["python3", "scripts/check_faq_top_posts.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"FAQ gate failed:\n{result.stdout}\n{result.stderr}",
        )

    def test_add_faq_script_resolves_migrated_paths(self):
        result = subprocess.run(
            ["python3", "scripts/add_faq_schema_top_posts.py", "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Could not extract slug", result.stdout)
        self.assertTrue(
            "Already has" in result.stdout or "Skipped:" in result.stdout,
            "Expected existing FAQ skips for top posts",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)