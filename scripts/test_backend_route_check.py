#!/usr/bin/env python3
"""Tests for scripts/backend_route_check.py — V24 post-deploy route smoke.

Pure / offline assertions (no live network needed):
  * classify() maps status codes → ok / missing(404) / unexpected / unknown.
  * The runner is offline-safe (exit 0) and writes a well-formed report.
  * --strict exits 2 only when a critical route is a real 404 (split-backend).

Run:
    python3 -m unittest scripts.test_backend_route_check -v
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backend_route_check as brc  # noqa: E402


class ClassifyTest(unittest.TestCase):
    def test_200_ok(self):
        self.assertEqual(brc.classify(200, (200,)), "ok")

    def test_auth_gate_ok(self):
        # save-post unauthenticated → 401/403/405 is the *correct* outcome.
        for code in (401, 403, 405):
            self.assertEqual(brc.classify(code, (401, 403, 405)), "ok")

    def test_404_missing(self):
        # The split-backend signature: route exists in repo but 404 in prod.
        self.assertEqual(brc.classify(404, (401, 403, 405)), "missing")
        self.assertEqual(brc.classify(404, (200,)), "missing")

    def test_unexpected(self):
        self.assertEqual(brc.classify(500, (200,)), "unexpected")

    def test_zero_unknown(self):
        self.assertEqual(brc.classify(0, (200,)), "unknown")


class CriticalSpecTest(unittest.TestCase):
    def test_critical_routes_cover_spec(self):
        paths = {p for _n, _m, p, _a in brc.CRITICAL_CHECKS}
        self.assertIn("/health", paths)
        self.assertIn("/gsc/status", paths)
        self.assertIn("/cms/save-post", paths)

    def test_save_post_never_accepts_404(self):
        for name, _m, path, accepted in brc.CRITICAL_CHECKS:
            self.assertNotIn(404, accepted, f"{path} must never accept 404")

    def test_save_post_is_post_and_auth_gated(self):
        spec = {n: (m, p, a) for n, m, p, a in brc.CRITICAL_CHECKS}
        method, path, accepted = spec["cms_save_post"]
        self.assertEqual(method, "POST")
        self.assertEqual(set(accepted), {401, 403, 405})


class OfflineRunTest(unittest.TestCase):
    def test_offline_exit_zero_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "route-status.json"
            with mock.patch.object(brc, "REPORT", report):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = brc.run(["--offline"])
                self.assertEqual(rc, 0)  # offline never gates
                data = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(data["overall"], "offline")
                self.assertEqual(len(data["checks"]), len(brc.CRITICAL_CHECKS))
                for c in data["checks"]:
                    self.assertEqual(c["verdict"], "unknown")

    def test_offline_strict_still_zero(self):
        # No 404 observed (offline) → strict must not fail.
        with mock.patch.object(brc, "REPORT", Path(tempfile.mkdtemp()) / "r.json"):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(brc.run(["--offline", "--strict"]), 0)


class StrictGateTest(unittest.TestCase):
    """Simulate a split-backend (save-post 404) and confirm --strict exits 2."""

    def _fake_probe(self, api, method, path, **kw):
        # Healthy except /cms/save-post which is 404 (route only in visitor-counter).
        if path == "/cms/save-post":
            return 404, ""
        return 403, ""

    def test_strict_fails_on_critical_404(self):
        with mock.patch.object(brc, "probe", self._fake_probe), \
             mock.patch.object(brc, "fetch_health", lambda *a, **k: None), \
             mock.patch.object(brc, "REPORT", Path(tempfile.mkdtemp()) / "r.json"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = brc.run(["--strict", "--api", "https://example.test"])
            self.assertEqual(rc, 2)
            self.assertIn("split-backend", buf.getvalue())

    def test_non_strict_404_still_exit_zero(self):
        with mock.patch.object(brc, "probe", self._fake_probe), \
             mock.patch.object(brc, "fetch_health", lambda *a, **k: None), \
             mock.patch.object(brc, "REPORT", Path(tempfile.mkdtemp()) / "r.json"):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(brc.run(["--api", "https://example.test"]), 0)


if __name__ == "__main__":
    unittest.main()
