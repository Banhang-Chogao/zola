#!/usr/bin/env python3
"""Tests for compliance internal link audit + draft scoring purge."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compliance_audit
import compliance_fix


class ComplianceLinkAuditTest(unittest.TestCase):
    def test_link_report_in_audit_result(self) -> None:
        if not compliance_audit.PUBLIC.is_dir():
            self.skipTest("public/ missing — run zola build first")
        result = compliance_audit.run_audit()
        self.assertIn("categories", result)
        report = result.get("link_report", {})
        self.assertIn("summary", report)
        self.assertIn("links", report)
        self.assertEqual(report["summary"]["broken_count"], 0)

    def test_internal_links_item_has_broken_list_when_warn(self) -> None:
        if not compliance_audit.PUBLIC.is_dir():
            self.skipTest("public/ missing")
        result = compliance_audit.run_audit()
        links_cat = next(c for c in result["categories"] if c["id"] == "links")
        item = next(i for i in links_cat["items"] if i["label"] == "Internal links")
        if item["status"] == "pass":
            self.assertNotIn("broken", item)
        else:
            self.assertIn("broken", item)
            self.assertGreater(len(item["broken"]), 0)


class DraftScoringPurgeTest(unittest.TestCase):
    def test_purge_draft_slug_from_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            scores_path = data / "scores.json"
            scores_path.write_text(
                json.dumps([
                    {"slug": "published-post", "title": "OK"},
                    {"slug": "draft-post", "title": "Draft"},
                ]) + "\n",
                encoding="utf-8",
            )
            related_path = data / "related.json"
            related_path.write_text(
                json.dumps({
                    "draft-post": [{"slug": "published-post", "score": 0.5}],
                    "published-post": [{"slug": "draft-post", "score": 0.5}],
                }) + "\n",
                encoding="utf-8",
            )
            compliance_fix.SCORES_FILE = scores_path
            compliance_fix.RELATED_FILE = related_path
            changed = compliance_fix._purge_draft_from_scoring_data({"draft-post"})
            self.assertTrue(changed)
            scores = json.loads(scores_path.read_text())
            self.assertEqual([s["slug"] for s in scores], ["published-post"])
            related = json.loads(related_path.read_text())
            self.assertNotIn("draft-post", related)
            self.assertEqual(related["published-post"], [])


if __name__ == "__main__":
    unittest.main()