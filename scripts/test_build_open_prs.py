#!/usr/bin/env python3
"""Unit tests for build_open_prs sanitize/summarize logic (network-free, no gh).

Covers the Open PR Monitor invariants:
  * only whitelisted fields survive sanitization (no raw author object / secrets);
  * statusCheckRollup is bucketed into pass/fail/pending with a stable overall state;
  * updatedAt is rendered in GMT+7 dd/mm/yyyy per the repo timezone rule;
  * malformed input degrades to [] / skipped rows, never raises;
  * the output is newest-updated first and capped at the 10-PR limit.

Run: python3 -m unittest scripts.test_build_open_prs -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_open_prs as bop  # noqa: E402


def _pr(number=1, updated="2026-06-21T01:14:20Z", rollup=None, **kw):
    base = {
        "number": number,
        "title": kw.get("title", "feat: a thing"),
        "headRefName": kw.get("headRefName", "claude/foo"),
        "baseRefName": kw.get("baseRefName", "main"),
        "url": kw.get("url", f"https://github.com/Banhang-Chogao/zola/pull/{number}"),
        "author": kw.get("author", {"login": "banhang-chogao", "is_bot": False}),
        "updatedAt": updated,
        "mergeable": kw.get("mergeable", "MERGEABLE"),
        "reviewDecision": kw.get("reviewDecision", "REVIEW_REQUIRED"),
        "statusCheckRollup": rollup if rollup is not None else [],
    }
    return base


class SummarizeChecksTest(unittest.TestCase):
    def test_empty_rollup_is_none_state(self):
        s = bop.summarize_checks([])
        self.assertEqual(s["state"], "none")
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["summary"], "Chưa có kiểm tra CI")

    def test_all_success(self):
        roll = [
            {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"__typename": "StatusContext", "state": "SUCCESS"},
        ]
        s = bop.summarize_checks(roll)
        self.assertEqual(s["state"], "success")
        self.assertEqual((s["passed"], s["failed"], s["pending"]), (2, 0, 0))

    def test_failure_dominates(self):
        roll = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
            {"status": "IN_PROGRESS", "conclusion": None},
        ]
        s = bop.summarize_checks(roll)
        self.assertEqual(s["state"], "failure")
        self.assertEqual((s["passed"], s["failed"], s["pending"]), (1, 1, 1))

    def test_pending_when_no_failure_but_inflight(self):
        roll = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "QUEUED", "conclusion": None},
        ]
        s = bop.summarize_checks(roll)
        self.assertEqual(s["state"], "pending")
        self.assertEqual(s["pending"], 1)

    def test_skipped_and_neutral_count_as_pass(self):
        roll = [
            {"status": "COMPLETED", "conclusion": "SKIPPED"},
            {"status": "COMPLETED", "conclusion": "NEUTRAL"},
        ]
        s = bop.summarize_checks(roll)
        self.assertEqual(s["state"], "success")
        self.assertEqual(s["passed"], 2)

    def test_statuscontext_pending_and_error(self):
        roll = [
            {"__typename": "StatusContext", "state": "PENDING"},
            {"__typename": "StatusContext", "state": "ERROR"},
        ]
        s = bop.summarize_checks(roll)
        self.assertEqual(s["state"], "failure")
        self.assertEqual((s["failed"], s["pending"]), (1, 1))

    def test_garbage_items_do_not_raise(self):
        s = bop.summarize_checks([None, "x", 5, {"weird": 1}])
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["pending"], 4)


class SanitizePrTest(unittest.TestCase):
    def test_only_whitelisted_fields(self):
        pr = _pr(number=601)
        pr["author"] = {"login": "banhang-chogao", "id": "SECRET", "name": "X"}
        pr["secretToken"] = "ghp_should_not_survive"
        out = bop.sanitize_pr(pr)
        self.assertEqual(
            set(out.keys()),
            {"number", "title", "head", "base", "url", "author",
             "updated_at", "updated_display", "mergeable", "review_decision", "checks"},
        )
        # author flattened to login only; no raw object / id leaks.
        self.assertEqual(out["author"], "banhang-chogao")
        self.assertNotIn("secretToken", out)
        self.assertNotIn("ghp_", json_dump(out))

    def test_branch_and_number_mapping(self):
        out = bop.sanitize_pr(_pr(number=42, headRefName="fix/bar", baseRefName="main"))
        self.assertEqual(out["number"], 42)
        self.assertEqual(out["head"], "fix/bar")
        self.assertEqual(out["base"], "main")

    def test_updated_display_is_gmt7_vietnamese(self):
        # 01:14 UTC → 08:14 GMT+7, dd/mm/yyyy.
        out = bop.sanitize_pr(_pr(updated="2026-06-21T01:14:20Z"))
        self.assertEqual(out["updated_display"], "08:14 21/06/2026")

    def test_long_title_truncated(self):
        out = bop.sanitize_pr(_pr(title="x" * 300))
        self.assertLessEqual(len(out["title"]), 160)
        self.assertTrue(out["title"].endswith("…"))

    def test_missing_number_skipped(self):
        self.assertIsNone(bop.sanitize_pr({"title": "no number"}))
        self.assertIsNone(bop.sanitize_pr("not a dict"))

    def test_missing_author_is_empty_string(self):
        pr = _pr()
        pr["author"] = None
        out = bop.sanitize_pr(pr)
        self.assertEqual(out["author"], "")


class SanitizePrsTest(unittest.TestCase):
    def test_non_list_input_returns_empty(self):
        self.assertEqual(bop.sanitize_prs(None), [])
        self.assertEqual(bop.sanitize_prs({"not": "a list"}), [])

    def test_sorted_newest_first(self):
        raw = [
            _pr(number=1, updated="2026-06-20T00:00:00Z"),
            _pr(number=2, updated="2026-06-21T00:00:00Z"),
            _pr(number=3, updated="2026-06-19T00:00:00Z"),
        ]
        out = bop.sanitize_prs(raw)
        self.assertEqual([p["number"] for p in out], [2, 1, 3])

    def test_capped_at_limit(self):
        raw = [_pr(number=n, updated=f"2026-06-{(n % 28) + 1:02d}T00:00:00Z") for n in range(25)]
        out = bop.sanitize_prs(raw)
        self.assertEqual(len(out), bop.LIMIT)

    def test_garbage_rows_dropped(self):
        out = bop.sanitize_prs([_pr(number=1), None, {"no": "number"}, 7])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["number"], 1)


def json_dump(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
