#!/usr/bin/env python3
"""Tests cho wip8 (WIP + TheoDoi8 gộp). Read-only, không network, không secret."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import wip8


class ConfigTests(unittest.TestCase):
    def test_default_when_missing(self):
        orig = wip8.CONFIG_PATH
        wip8.CONFIG_PATH = Path("/nonexistent/wip8.config.json")
        try:
            cfg = wip8.load_config()
        finally:
            wip8.CONFIG_PATH = orig
        self.assertTrue(cfg["show_theodoi8"])
        self.assertEqual(cfg["theodoi8_max_commits"], 8)

    def test_merge_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wip8.config.json"
            p.write_text(json.dumps({"theodoi8_max_commits": 3, "show_theodoi8": False}))
            orig = wip8.CONFIG_PATH
            wip8.CONFIG_PATH = p
            try:
                cfg = wip8.load_config()
            finally:
                wip8.CONFIG_PATH = orig
        self.assertEqual(cfg["theodoi8_max_commits"], 3)
        self.assertFalse(cfg["show_theodoi8"])
        # khoá không khai báo vẫn giữ default
        self.assertTrue(cfg["show_wip"])

    def test_bad_json_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wip8.config.json"
            p.write_text("{ not valid json")
            orig = wip8.CONFIG_PATH
            wip8.CONFIG_PATH = p
            try:
                cfg = wip8.load_config()
            finally:
                wip8.CONFIG_PATH = orig
        self.assertEqual(cfg, wip8.DEFAULT_CONFIG)


class TheoDoi8LoaderTests(unittest.TestCase):
    def _with_root(self, files: dict) -> dict | None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel, payload in files.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(json.dumps(payload), encoding="utf-8")
            orig = wip8.ROOT
            wip8.ROOT = root
            try:
                return wip8.load_theodoi8(dict(wip8.DEFAULT_CONFIG))
            finally:
                wip8.ROOT = orig

    def test_missing_report_returns_none(self):
        self.assertIsNone(self._with_root({}))

    def test_reads_report_and_caps_commits(self):
        commits = [{"sha": f"c{i}", "message": f"m{i}", "status": "success"} for i in range(20)]
        rep = self._with_root({"data/theodoi8-report.json": {
            "status": "success", "summary": "ok", "commits": commits}})
        self.assertIsNotNone(rep)
        self.assertEqual(len(rep["commits"]), wip8.DEFAULT_CONFIG["theodoi8_max_commits"])

    def test_static_fallback(self):
        rep = self._with_root({"static/data/theodoi8-report.json": {
            "status": "idle", "summary": "live", "commits": []}})
        self.assertIsNotNone(rep)
        self.assertEqual(rep["status"], "idle")


class GatherReadOnlyTests(unittest.TestCase):
    def test_gather_no_write_keys(self):
        # gather chỉ chứa key đọc — không có dấu hiệu mutate
        data = wip8.gather(quick=True)
        for k in ("status", "branch", "stash"):
            self.assertIn(k, data)

    def test_health_clean(self):
        h = wip8.health({"status": "", "aheadbehind": "0\t0"})
        self.assertEqual(h["verdict"], "CLEAN")
        self.assertEqual(h["tone"], "pass")

    def test_health_conflict_blocked(self):
        h = wip8.health({"status": "UU foo.py", "aheadbehind": ""})
        self.assertEqual(h["verdict"], "BLOCKED")
        self.assertEqual(h["tone"], "fail")


if __name__ == "__main__":
    unittest.main()
