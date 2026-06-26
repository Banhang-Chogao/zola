#!/usr/bin/env python3
"""Unit tests for scripts/gsc_preflight.py — offline gate only (no live API)."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFLIGHT = ROOT / "scripts" / "gsc_preflight.py"


def _load_preflight():
    spec = importlib.util.spec_from_file_location("gsc_preflight", PREFLIGHT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


pf = _load_preflight()


class _EnvGuard:
    """Set GSC_* env for a test, restore afterwards."""

    def __init__(self, **env):
        self.env = env
        self._saved: dict[str, str | None] = {}

    def __enter__(self):
        for k, v in self.env.items():
            self._saved[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class NormalizeTest(unittest.TestCase):
    def test_domain_property_lowercased(self):
        self.assertEqual(
            pf.normalize_property_for_match("sc-domain:SeoMoney.org"),
            "sc-domain:seomoney.org",
        )

    def test_domain_trailing_slash_stripped(self):
        self.assertEqual(
            pf.normalize_property_for_match("sc-domain:seomoney.org/"),
            "sc-domain:seomoney.org",
        )

    def test_url_prefix_is_not_domain(self):
        self.assertNotEqual(
            pf.normalize_property_for_match("https://seomoney.org/"),
            pf.EXPECTED_GSC_PROPERTY,
        )


class IsExpectedTest(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(pf.is_expected_property("sc-domain:seomoney.org"))

    def test_case_insensitive(self):
        self.assertTrue(pf.is_expected_property("sc-domain:SEOMONEY.ORG"))

    def test_url_prefix_rejected(self):
        self.assertFalse(pf.is_expected_property("https://seomoney.org/"))

    def test_other_domain_rejected(self):
        self.assertFalse(pf.is_expected_property("sc-domain:example.com"))

    def test_empty_rejected(self):
        self.assertFalse(pf.is_expected_property(""))


class GateTest(unittest.TestCase):
    def test_gate_passes_on_domain_property(self):
        with _EnvGuard(GSC_PROPERTY_URL="sc-domain:seomoney.org"):
            self.assertTrue(pf.check_property_gate())

    def test_gate_fails_on_url_prefix(self):
        with _EnvGuard(GSC_PROPERTY_URL="https://seomoney.org/"):
            self.assertFalse(pf.check_property_gate())

    def test_gate_fails_when_unset(self):
        with _EnvGuard(GSC_PROPERTY_URL=None):
            self.assertFalse(pf.check_property_gate())


class MainGateOnlyTest(unittest.TestCase):
    def test_main_gate_only_pass(self):
        with _EnvGuard(GSC_PROPERTY_URL="sc-domain:seomoney.org"):
            self.assertEqual(pf.main(["--gate-only"]), 0)

    def test_main_gate_only_fail(self):
        with _EnvGuard(GSC_PROPERTY_URL="https://seomoney.org/"):
            self.assertEqual(pf.main(["--gate-only"]), 2)

    def test_main_require_live_without_creds_fails(self):
        with _EnvGuard(
            GSC_PROPERTY_URL="sc-domain:seomoney.org",
            GSC_REFRESH_TOKEN=None,
            GSC_CLIENT_ID=None,
            GSC_CLIENT_SECRET=None,
        ):
            self.assertEqual(pf.main(["--require-live"]), 2)

    def test_main_skips_live_without_creds(self):
        with _EnvGuard(
            GSC_PROPERTY_URL="sc-domain:seomoney.org",
            GSC_REFRESH_TOKEN=None,
            GSC_CLIENT_ID=None,
            GSC_CLIENT_SECRET=None,
        ):
            self.assertEqual(pf.main([]), 0)


class ConstantsInSyncTest(unittest.TestCase):
    """Inlined constants must match gsc_client (loaded with stubbed google libs)."""

    def test_constants_match_gsc_client(self):
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
            sys.modules.setdefault(name, types.ModuleType(name))
        sys.modules["google.auth.transport.requests"].Request = object
        sys.modules["google.oauth2.credentials"].Credentials = object
        sys.modules["googleapiclient.errors"].HttpError = type("HttpError", (Exception,), {})
        sys.modules["googleapiclient.discovery"].build = lambda *a, **k: None

        client_path = ROOT / "services" / "vipzone" / "gsc_client.py"
        spec = importlib.util.spec_from_file_location("gsc_client_sync", client_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.assertEqual(pf.EXPECTED_GSC_PROPERTY, mod.EXPECTED_GSC_PROPERTY)
        self.assertEqual(pf.EXPECTED_SITEMAP_URL, mod.EXPECTED_SITEMAP_URL)


if __name__ == "__main__":
    unittest.main()
