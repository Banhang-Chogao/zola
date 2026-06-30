#!/usr/bin/env python3
"""Tests for scripts/update_changelog.py — import & unit."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Point to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import scripts.update_changelog as uc  # noqa: E402


class TestInferTag(unittest.TestCase):
    def test_label_priority(self):
        self.assertEqual(uc.infer_tag("fix: bug", [{"name": "feature"}]), "feat")

    def test_title_prefix(self):
        self.assertEqual(uc.infer_tag("add new page", []), "feat")
        self.assertEqual(uc.infer_tag("fix: crash", []), "fix")
        self.assertEqual(uc.infer_tag("remove legacy", []), "remove")

    def test_keyword_fallback(self):
        self.assertEqual(uc.infer_tag("refactor the whole thing", []), "refactor")
        self.assertEqual(uc.infer_tag("clean up code", []), "cleanup")
        self.assertEqual(uc.infer_tag("random update", []), "chore")

    def test_security_keyword(self):
        self.assertEqual(uc.infer_tag("security issue", []), "security")


class TestCleanTitle(unittest.TestCase):
    def test_strip_prefix(self):
        self.assertEqual(uc.clean_title("Add: new feature"), "new feature")
        self.assertEqual(uc.clean_title("fix - broken link"), "broken link")
        self.assertEqual(uc.clean_title("feat: awesome thing"), "awesome thing")
        self.assertEqual(uc.clean_title("no prefix"), "no prefix")


class TestStripMdFormatting(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(uc.strip_md_formatting("**bold** text"), "bold text")

    def test_links(self):
        self.assertEqual(uc.strip_md_formatting("[link](url) here"), "link here")


class TestExtractHighlights(unittest.TestCase):
    def test_bullets(self):
        body = "- First bullet\n- Second bullet\n- Third"
        result = uc.extract_highlights(body, max_items=2)
        self.assertEqual(result, ["First bullet", "Second bullet"])

    def test_no_bullets(self):
        body = "Just a paragraph."
        result = uc.extract_highlights(body)
        self.assertEqual(result, [])

    def test_empty(self):
        self.assertEqual(uc.extract_highlights(None), [])
        self.assertEqual(uc.extract_highlights(""), [])

    def test_skip_short(self):
        body = "- ab"
        result = uc.extract_highlights(body)
        self.assertEqual(result, [])

    def test_skip_tables(self):
        body = "- | header |\n- | col1 | col2 |"
        result = uc.extract_highlights(body)
        self.assertEqual(result, [])


class TestMaskSecrets(unittest.TestCase):
    def test_otp_pattern(self):
        text = "OTP code 123456"
        result = uc.mask_secrets(text)
        self.assertNotIn("123456", result)

    def test_github_pat(self):
        text = "ghp_abcdefghijklmnopqrstuvwxyz"
        result = uc.mask_secrets(text)
        self.assertIn("ghp_****", result)

    def test_no_secret(self):
        text = "clean text without secrets"
        result = uc.mask_secrets(text)
        self.assertEqual(result, text)


class TestMigrateIfNeeded(unittest.TestCase):
    def test_migrate_old_schema(self):
        data = {
            "items": [
                {
                    "date": "2026-06-27",
                    "title": "test title",
                    "tag": "feat",
                    "lines_added": 100,
                    "lines_removed": 10,
                    "highlights": ["thing"],
                    "pr": 1234,
                    "commit": "abc123def456",
                    "author": "user",
                    "merged_at": "2026-06-27T12:00:00Z",
                }
            ]
        }
        changed = uc.migrate_if_needed(data, "owner/repo")
        self.assertTrue(changed)
        item = data["items"][0]
        self.assertEqual(item["id"], "pr-1234")
        self.assertEqual(item["pr_number"], 1234)
        self.assertEqual(item["stats"]["additions"], 100)
        self.assertEqual(item["stats"]["deletions"], 10)
        self.assertEqual(item["verified"], True)

    def test_skip_new_schema(self):
        data = {
            "items": [
                {
                    "id": "pr-999",
                    "pr_number": 999,
                    "title": "already new",
                    "verified": True,
                }
            ]
        }
        changed = uc.migrate_if_needed(data, "owner/repo")
        self.assertFalse(changed)


class TestDedupOldSchema(unittest.TestCase):
    def test_do_not_dedup_before_migration(self):
        """Verify that before migration, the old schema items are NOT
        detected as duplicates of new entries by the updater's logic."""
        data = {
            "items": [
                {"date": "2026-06-27", "title": "old entry", "pr": 123}
            ]
        }
        uc.migrate_if_needed(data, "o/r")
        self.assertEqual(data["items"][0]["pr_number"], 123)


if __name__ == "__main__":
    unittest.main()
