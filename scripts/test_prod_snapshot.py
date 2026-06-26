#!/usr/bin/env python3
"""Tests for build_prod_snapshot drift logic."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_prod_snapshot",
    ROOT / "scripts" / "build_prod_snapshot.py",
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_drift = _mod._drift
_short = _mod._short


class ProdSnapshotDriftTests(unittest.TestCase):
    def test_green_when_aligned(self):
        sha = "a" * 40
        d = _drift(sha, sha, sha, {"summary": {"prod_status": "green", "deploying": False}})
        self.assertEqual(d["status"], "green")
        self.assertFalse(d["main_ahead_of_deploy"])

    def test_yellow_main_ahead(self):
        main = "a" * 40
        deploy = "b" * 40
        d = _drift(main, deploy, main, {"summary": {"prod_status": "green", "deploying": False}})
        self.assertEqual(d["status"], "yellow")
        self.assertTrue(d["main_ahead_of_deploy"])

    def test_red_on_deploy_failure(self):
        d = _drift("a" * 40, "b" * 40, None, {"summary": {"prod_status": "red", "deploying": False}})
        self.assertEqual(d["status"], "red")

    def test_short_sha(self):
        self.assertEqual(_short("fb432dbd8304321b28a47629cdfbb31a0a037497"), "fb432db")


if __name__ == "__main__":
    unittest.main()