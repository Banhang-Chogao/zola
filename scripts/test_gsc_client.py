#!/usr/bin/env python3
"""Unit tests for gsc_client.py — no live API calls."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "services" / "visitor-counter" / "gsc_client.py"


def _load_gsc_client():
    """Load gsc_client without requiring google-* wheels in dev unittest env."""
    import types

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

    sys.path.insert(0, str(ROOT / "services" / "visitor-counter"))
    _spec = importlib.util.spec_from_file_location("gsc_client", CLIENT)
    mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(mod)
    return mod


mod = _load_gsc_client()


class AggregateRowTest(unittest.TestCase):
    def test_empty_row(self):
        agg = mod._aggregate_row(None)
        self.assertEqual(agg["clicks"], 0.0)
        self.assertEqual(agg["ctr"], 0.0)

    def test_ctr_percent(self):
        agg = mod._aggregate_row({"clicks": 10, "impressions": 100, "ctr": 0.025, "position": 18.3})
        self.assertEqual(agg["clicks"], 10.0)
        self.assertEqual(agg["ctr"], 2.5)
        self.assertEqual(agg["position"], 18.3)


class IndexingHealthTest(unittest.TestCase):
    def test_excellent(self):
        self.assertEqual(mod._indexing_health(90, 100, "ok"), "Excellent")

    def test_problem_on_sitemap_error(self):
        self.assertEqual(mod._indexing_health(90, 100, "error"), "Problem")

    def test_warning_low_ratio(self):
        self.assertEqual(mod._indexing_health(50, 100, "ok"), "Warning")


class ExecutiveSummaryTest(unittest.TestCase):
    def test_traffic_increase(self):
        lines = mod._executive_summary(
            {"impressions": 114, "position": 17},
            {"impressions": 100, "position": 21},
            [{"query": "ai blog"}],
            [{"page": "/post", "clicks": 5}],
        )
        self.assertTrue(any("increased" in l.lower() for l in lines))
        self.assertTrue(any("position improved" in l.lower() for l in lines))

    def test_fallback_when_empty(self):
        lines = mod._executive_summary(
            {"impressions": 0, "position": 0},
            {"impressions": 0, "position": 0},
            [],
            [],
        )
        self.assertEqual(len(lines), 1)
        self.assertIn("Connected", lines[0])


class PropertyUrlTest(unittest.TestCase):
    def test_default_property(self):
        # Post-Cloudflare migration: must be sc-domain: (domain property), not URL-prefix.
        self.assertEqual(mod.DEFAULT_GSC_PROPERTY_URL, "sc-domain:seomoney.org")

    def test_normalize_trailing_slash(self):
        # URL-prefix properties still normalized (backwards compat for env var override).
        self.assertEqual(
            mod.normalize_gsc_property_url("https://seomoney.org"),
            "https://seomoney.org/",
        )

    def test_normalize_sc_domain_passthrough(self):
        # sc-domain: entries are passed through unchanged (no trailing slash added).
        self.assertEqual(
            mod.normalize_gsc_property_url("sc-domain:seomoney.org"),
            "sc-domain:seomoney.org",
        )

    def test_pick_preferred_sc_domain(self):
        # pick_preferred_property must select the sc-domain: entry.
        props = [
            "https://example.com/",
            "sc-domain:seomoney.org",
        ]
        self.assertEqual(mod.pick_preferred_property(props), "sc-domain:seomoney.org")

    def test_pick_preferred_only_blog_property(self):
        # Still rejects unrelated domains.
        props = [
            "https://example.com/",
            "sc-domain:other.com",
        ]
        self.assertIsNone(mod.pick_preferred_property(props))

    def test_pick_preferred_rejects_other_domains(self):
        self.assertIsNone(mod.pick_preferred_property(["https://example.com/"]))


class DisconnectedPayloadTest(unittest.TestCase):
    def test_not_connected(self):
        payload = mod.disconnected_payload()
        self.assertFalse(payload["connected"])
        self.assertIsNone(payload["clicks"])
        self.assertEqual(payload["top_pages"], [])


class RowsConversionTest(unittest.TestCase):
    def test_pages(self):
        rows = mod._rows_to_pages(
            [{"keys": ["https://example.com/a"], "clicks": 3, "impressions": 30, "ctr": 0.1, "position": 5}]
        )
        self.assertEqual(rows[0]["page"], "https://example.com/a")
        self.assertEqual(rows[0]["clicks"], 3)

    def test_queries(self):
        rows = mod._rows_to_queries(
            [{"keys": ["hello world"], "clicks": 1, "impressions": 10, "ctr": 0.1, "position": 8}]
        )
        self.assertEqual(rows[0]["query"], "hello world")


if __name__ == "__main__":
    unittest.main()