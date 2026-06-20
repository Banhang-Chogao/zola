#!/usr/bin/env python3
"""Test preflight_conflict_check — high-risk detect + dry-run merge (worktree không đổi)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight_conflict_check as pf  # noqa: E402


class HighRiskTest(unittest.TestCase):
    def test_shared_files_flagged(self):
        for p in [
            "CLAUDE.md",
            "README.md",
            "config.toml",
            ".github/workflows/deploy.yml",
            "scripts/autofix_conflicts.py",
            "scripts/vaccine_hotfix.py",
            "templates/base.html",
            "templates/macros/series-nav.html",
            "sass/_footer.scss",
            "static/js/main.js",
            "data/seo-foundation-series.json",
        ]:
            self.assertIsNotNone(pf.high_risk_reason(p), f"{p} phải là high-risk")

    def test_normal_files_not_flagged(self):
        for p in [
            "content/posting/tao-blog-voi-zola.md",
            "content/baochi/tin-moi.md",
            "data/seo-qa-scores.json",
            "sass/_post-nav.scss",
        ]:
            self.assertIsNone(pf.high_risk_reason(p), f"{p} KHÔNG nên là high-risk")


def _run(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


class MergeTreeTest(unittest.TestCase):
    """Dựng repo git tạm: branch + main cùng sửa 1 dòng → conflict thật."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pf-test-")
        self.repo = Path(self.tmp)
        _run(self.repo, "init", "-q", "-b", "main")
        _run(self.repo, "config", "user.email", "t@t.t")
        _run(self.repo, "config", "user.name", "t")
        (self.repo / "CLAUDE.md").write_text("base line\n")
        (self.repo / "untouched.txt").write_text("keep\n")
        _run(self.repo, "add", "-A")
        _run(self.repo, "commit", "-qm", "base")
        # branch sửa CLAUDE.md
        _run(self.repo, "checkout", "-qb", "feature")
        (self.repo / "CLAUDE.md").write_text("feature line\n")
        _run(self.repo, "commit", "-aqm", "feature edit")
        # main sửa CÙNG dòng → conflict
        _run(self.repo, "checkout", "-q", "main")
        (self.repo / "CLAUDE.md").write_text("main line\n")
        _run(self.repo, "commit", "-aqm", "main edit")
        _run(self.repo, "checkout", "-q", "feature")
        self._orig_repo = pf.REPO
        pf.REPO = self.repo

    def tearDown(self):
        pf.REPO = self._orig_repo
        subprocess.run(["rm", "-rf", self.tmp], capture_output=True)

    def test_detects_real_conflict_without_mutating_tree(self):
        before = (self.repo / "CLAUDE.md").read_text()
        clean, files, method = pf.merge_tree_conflicts("main", "HEAD")
        self.assertFalse(clean)
        self.assertIn("CLAUDE.md", files)
        # BẤT BIẾN: working tree KHÔNG đổi sau dry-run.
        self.assertEqual((self.repo / "CLAUDE.md").read_text(), before)
        self.assertEqual(_run(self.repo, "status", "--porcelain").stdout, "")

    def test_analyze_high_risk_blocks(self):
        report = pf.analyze("main", do_fetch=False)
        self.assertEqual(report["risk"], "high")
        self.assertFalse(report["proceed"])
        self.assertIn("CLAUDE.md", report["conflict_files"])

    def test_clean_merge_low_risk(self):
        # feature branch khớp main (no divergent change) → đặt main = feature head
        _run(self.repo, "branch", "-f", "main", "feature")
        report = pf.analyze("main", do_fetch=False)
        self.assertTrue(report["merge_clean"])
        self.assertTrue(report["proceed"])


if __name__ == "__main__":
    unittest.main()
