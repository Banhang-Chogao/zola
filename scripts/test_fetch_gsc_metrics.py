#!/usr/bin/env python3
"""Unit tests for scripts/fetch_gsc_metrics.py — no live network calls.

Covers the backend-cache fallback that lets CI build a REAL gsc-metrics.json
snapshot from the blog backend's already-cached bundle when the direct GSC
secrets are absent (operator connected via OAuth on the backend only).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "fetch_gsc_metrics.py"


def _stub_google_modules() -> None:
    """gsc_client imports google-* wheels at module load; stub them for dev tests."""
    for name in (
        "google",
        "google.auth",
        "google.auth.transport",
        "google.auth.transport.requests",
        "google.oauth2",
        "google.oauth2.credentials",
        "googleapiclient",
        "googleapiclient.discovery",
        "googleapiclient.errors",
    ):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
    sys.modules["google.auth.transport.requests"].Request = object
    sys.modules["google.oauth2.credentials"].Credentials = object

    class _HttpError(Exception):
        def __init__(self, status=500):
            self.resp = types.SimpleNamespace(status=status)

    sys.modules["googleapiclient.errors"].HttpError = _HttpError
    sys.modules["googleapiclient.discovery"].build = lambda *a, **k: None


def _load_module():
    _stub_google_modules()
    sys.path.insert(0, str(ROOT / "services" / "vipzone"))
    spec = importlib.util.spec_from_file_location("fetch_gsc_metrics", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()


def _real_bundle(**over):
    base = {
        "connected": True,
        "status": "ok",
        "property": "sc-domain:seomoney.org",
        "impressions": 1234,
        "clicks": 56,
        "ctr": 4.54,
        "avg_position": 12.3,
        "indexed_pages": 200,
        "top_pages": [{"page": "https://seomoney.org/a/", "clicks": 5}],
        "top_queries": [{"query": "seo", "clicks": 3}],
        "trend": {"daily": [{"date": "2026-06-20", "clicks": 5}], "weekly": [], "monthly": []},
    }
    base.update(over)
    return base


class _FakeResp:
    def __init__(self, body: str, status: int = 200):
        self._body = body.encode("utf-8")
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class BundleHasData(unittest.TestCase):
    def test_connected_with_metrics(self):
        self.assertTrue(MOD.bundle_has_data(_real_bundle()))

    def test_disconnected(self):
        self.assertFalse(MOD.bundle_has_data({"connected": False, "status": "not_connected"}))

    def test_connected_but_empty(self):
        empty = {
            "connected": True,
            "impressions": None,
            "clicks": None,
            "indexed_pages": None,
            "top_pages": [],
            "top_queries": [],
            "trend": {"daily": [], "weekly": [], "monthly": []},
        }
        self.assertFalse(MOD.bundle_has_data(empty))

    def test_non_dict(self):
        self.assertFalse(MOD.bundle_has_data(None))


class FetchFromBackend(unittest.TestCase):
    def test_returns_real_bundle(self):
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(json.dumps(_real_bundle()))):
            out = MOD.fetch_from_backend("https://backend.example")
        self.assertIsNotNone(out)
        self.assertEqual(out["clicks"], 56)

    def test_disconnected_backend_returns_none(self):
        payload = {"connected": False, "status": "not_connected"}
        with mock.patch("urllib.request.urlopen", return_value=_FakeResp(json.dumps(payload))):
            self.assertIsNone(MOD.fetch_from_backend("https://backend.example"))

    def test_network_error_returns_none(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("cold start timeout")):
            self.assertIsNone(MOD.fetch_from_backend("https://backend.example"))


class ResolvePayload(unittest.TestCase):
    def test_no_secrets_falls_back_to_backend(self):
        env = {"GSC_BACKEND_URL": "https://backend.example"}  # no direct secrets
        with mock.patch.object(MOD, "fetch_from_backend", return_value=_real_bundle()):
            out = MOD.resolve_payload(env)
        self.assertIsNotNone(out)
        self.assertEqual(out["impressions"], 1234)

    def test_backend_empty_yields_none(self):
        env = {"GSC_BACKEND_URL": "https://backend.example"}
        with mock.patch.object(MOD, "fetch_from_backend", return_value=None):
            self.assertIsNone(MOD.resolve_payload(env))


class MainWrites(unittest.TestCase):
    def _patch_outputs(self, tmp: Path):
        return mock.patch.multiple(
            MOD,
            DATA_OUT=tmp / "data" / "gsc-metrics.json",
            STATIC_OUT=tmp / "static" / "data" / "gsc-metrics.json",
        )

    def test_writes_real_backend_data(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            with self._patch_outputs(tmp), \
                 mock.patch.object(MOD, "resolve_payload", return_value=_real_bundle()):
                self.assertEqual(MOD.main(), 0)
            written = json.loads((tmp / "data" / "gsc-metrics.json").read_text())
            self.assertTrue(written["connected"])
            self.assertEqual(written["clicks"], 56)

    def test_keeps_previous_when_no_data(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            data_out = tmp / "data" / "gsc-metrics.json"
            data_out.parent.mkdir(parents=True)
            data_out.write_text('{"connected": true, "clicks": 99}\n', encoding="utf-8")
            with self._patch_outputs(tmp), \
                 mock.patch.object(MOD, "resolve_payload", return_value=None):
                self.assertEqual(MOD.main(), 0)
            # Previous good snapshot preserved, not overwritten with a placeholder.
            self.assertEqual(json.loads(data_out.read_text())["clicks"], 99)

    def test_seeds_placeholder_when_no_prior_file(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            with self._patch_outputs(tmp), \
                 mock.patch.object(MOD, "resolve_payload", return_value=None):
                self.assertEqual(MOD.main(), 0)
            written = json.loads((tmp / "data" / "gsc-metrics.json").read_text())
            self.assertFalse(written["connected"])
            self.assertEqual(written["status"], "not_connected")


if __name__ == "__main__":
    unittest.main()
