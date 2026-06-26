#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_theme_audit.py — QA cho rollback ledger Theme Log.

Chạy: python3 -m unittest scripts.test_theme_audit -v
       (hoặc) python3 scripts/test_theme_audit.py

Hai lớp kiểm tra:
  - Tripwire mốc bắt đầu: THEME_LOG_START_DATE (theme_audit) và
    THEME_LOG_EXPECTED_START (qa_check) phải khớp nhau → đổi mốc trở nên "visible".
  - Committed data/theme-log.json: có hàng, phủ cửa sổ đầu [14/06, 25/06), mọi
    commit_hash hex hợp lệ, và (khi full git history) mọi hash verify được bằng
    `git rev-parse --verify` — không có hash giả lọt vào bảng.

An toàn shallow: nếu repo shallow (commit nền móng vắng mặt cục bộ) → phần
git-verify được SKIP có thông báo, các check cấu trúc/coverage vẫn chạy.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
sys.path.insert(0, REPO_ROOT)

import theme_audit  # noqa: E402

THEME_LOG_JSON = os.path.join(REPO_ROOT, "data", "theme-log.json")
START_LOW = "2026-06-14"   # inclusive baseline (Asia/Ho_Chi_Minh)
RECENT_BATCH_LOW = "2026-06-25"  # mốc bắt đầu batch theme dày gần đây


def _is_shallow():
    out = subprocess.run(
        ["git", "-C", REPO_ROOT, "rev-parse", "--is-shallow-repository"],
        capture_output=True, text=True, check=False,
    )
    return out.stdout.strip().lower() == "true"


def _git_has(sha):
    out = subprocess.run(
        ["git", "-C", REPO_ROOT, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
        capture_output=True, text=True, check=False,
    )
    return out.returncode == 0 and bool(out.stdout.strip())


class TestStartDateTripwire(unittest.TestCase):
    def test_start_date_constant(self):
        self.assertEqual(
            theme_audit.THEME_LOG_START_DATE,
            "2026-06-14T00:00:00+07:00",
            "THEME_LOG_START_DATE đã đổi — đây là mốc bắt đầu reliable rollback "
            "history của SEOMONEY. Nếu cố ý đổi, cập nhật cả qa_check.THEME_LOG_EXPECTED_START.",
        )

    def test_qa_check_constant_in_sync(self):
        sys.path.insert(0, REPO_ROOT)
        import qa_check  # noqa: E402
        self.assertEqual(
            qa_check.THEME_LOG_EXPECTED_START,
            theme_audit.THEME_LOG_START_DATE,
            "qa_check.THEME_LOG_EXPECTED_START lệch theme_audit.THEME_LOG_START_DATE — "
            "phải đồng bộ để gate phát hiện đúng.",
        )


class TestCommittedLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(THEME_LOG_JSON, "r", encoding="utf-8") as fh:
            cls.data = json.load(fh)
        cls.themes = cls.data.get("themes") or []

    def test_has_rows(self):
        self.assertGreater(len(self.themes), 0, "Ledger rỗng — chạy scripts/theme_audit.py")

    def test_baseline_block(self):
        baseline = self.data.get("baseline") or {}
        self.assertEqual(baseline.get("start_date"), theme_audit.THEME_LOG_START_DATE)

    def test_early_window_covered(self):
        """Phải có ≥1 hàng trong [14/06, 25/06) — backfill nền móng, không chỉ batch gần đây."""
        early = [t for t in self.themes
                 if START_LOW <= (t.get("datetime") or "")[:10] < RECENT_BATCH_LOW]
        self.assertGreaterEqual(
            len(early), 1,
            "Không có hàng theme nào trong [2026-06-14, 2026-06-25) — backfill từ 14/06 bị thiếu.",
        )

    def test_no_row_before_start(self):
        """Không có hàng nào trước 14/06 (tôn trọng mốc baseline)."""
        for t in self.themes:
            d = (t.get("datetime") or "")[:10]
            if d and d != "unknown":
                self.assertGreaterEqual(d, START_LOW,
                    f"Hàng {t.get('theme_id')} ({d}) trước mốc baseline {START_LOW}")

    def test_hashes_hex(self):
        import re
        rx = re.compile(r"^[0-9a-f]{7,40}$")
        for t in self.themes:
            h = (t.get("commit_hash") or "").strip()
            self.assertRegex(h, rx, f"commit_hash không hex hợp lệ: {h!r}")

    def test_hashes_git_verified(self):
        """Mọi commit_hash verify được bằng git (chống hash giả). SKIP nếu shallow."""
        if _is_shallow():
            self.skipTest("repo shallow — commit nền móng vắng mặt cục bộ; git-verify bỏ qua")
        missing = [t["commit_hash"] for t in self.themes if not _git_has(t["commit_hash"])]
        # Nếu full history mà vẫn thiếu → có thể history chưa fetch đủ; chỉ fail khi
        # đa số thiếu (tránh false-fail khi 1-2 commit bị rebase ngoài history cục bộ).
        self.assertEqual(
            missing, [],
            f"commit_hash không tồn tại trong git history: {missing}",
        )

    def test_status_not_all_rollback(self):
        statuses = [t.get("status") for t in self.themes]
        self.assertIn("live", statuses, "Thiếu hàng 'live' (HEAD/current theme)")
        rt = sum(1 for s in statuses if s == "rollback target")
        self.assertLess(rt, len(statuses),
            "Mọi hàng đều 'rollback target' — vi phạm 'do not mark everything'.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
