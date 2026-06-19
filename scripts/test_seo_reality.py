#!/usr/bin/env python3
"""Tests for build_seo_reality.py — honest SEO reality data."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_seo_reality.py"

_spec = importlib.util.spec_from_file_location("build_seo_reality", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["build_seo_reality"] = mod
_spec.loader.exec_module(mod)


class GrowthStageTest(unittest.TestCase):
    def test_new_site_is_indexing(self):
        self.assertEqual(mod._growth_stage(4)["stage"], "Indexing Phase")
        self.assertEqual(mod._growth_stage(0)["slug"], "indexing")

    def test_discovery_phase(self):
        self.assertEqual(mod._growth_stage(60)["stage"], "Discovery Phase")

    def test_growth_phase(self):
        self.assertEqual(mod._growth_stage(120)["stage"], "Growth Phase")

    def test_authority_phase(self):
        self.assertEqual(mod._growth_stage(400)["stage"], "Authority Phase")


class AuthorityLevelTest(unittest.TestCase):
    def test_new_site(self):
        self.assertEqual(mod._authority_level(10)["level"], "New Site")

    def test_growing(self):
        self.assertEqual(mod._authority_level(120)["level"], "Growing")

    def test_established(self):
        self.assertEqual(mod._authority_level(200)["level"], "Established")

    def test_strong_authority(self):
        self.assertEqual(mod._authority_level(500)["level"], "Strong Authority")


class GscSectionTest(unittest.TestCase):
    def test_not_connected_when_missing(self):
        sec = mod._gsc_section(None)
        self.assertFalse(sec["connected"])
        self.assertIsNone(sec["impressions"])
        self.assertIsNone(sec["clicks"])

    def test_not_connected_when_empty(self):
        self.assertFalse(mod._gsc_section({})["connected"])

    def test_connected_passes_real_values(self):
        sec = mod._gsc_section({"connected": True, "impressions": 1234, "clicks": 56})
        self.assertTrue(sec["connected"])
        self.assertEqual(sec["impressions"], 1234)
        self.assertEqual(sec["clicks"], 56)


class IndexingSectionTest(unittest.TestCase):
    def test_disconnected_unknown(self):
        sec = mod._indexing_section(None, 42)
        self.assertFalse(sec["connected"])
        self.assertIsNone(sec["pages_indexed"])
        self.assertEqual(sec["sitemap_pages"], 42)

    def test_connected_with_health(self):
        gsc = {
            "connected": True,
            "indexed_pages": 80,
            "submitted_pages": 100,
            "non_indexed_pages": 20,
            "index_health": "Good",
            "sitemap_status": "ok",
        }
        sec = mod._indexing_section(gsc, 100)
        self.assertTrue(sec["connected"])
        self.assertEqual(sec["pages_indexed"], 80)
        self.assertEqual(sec["index_health"], "Good")


class GscExtrasTest(unittest.TestCase):
    def test_empty_when_disconnected(self):
        extras = mod._gsc_extras(None)
        self.assertEqual(extras["top_pages"], [])
        self.assertEqual(extras["executive_summary"], [])

    def test_passes_through_when_connected(self):
        gsc = {
            "connected": True,
            "top_pages": [{"page": "/a", "clicks": 1}],
            "top_queries": [{"query": "test", "clicks": 2}],
            "executive_summary": ["Traffic up."],
        }
        extras = mod._gsc_extras(gsc)
        self.assertEqual(len(extras["top_pages"]), 1)
        self.assertEqual(extras["executive_summary"][0], "Traffic up.")


class ComputeRealityTest(unittest.TestCase):
    def test_required_fields(self):
        payload = mod.compute_reality()
        for key in (
            "technical_seo",
            "gsc",
            "indexing",
            "authority",
            "growth",
            "tooltip",
            "top_pages",
            "top_queries",
            "trend",
            "executive_summary",
        ):
            self.assertIn(key, payload)

    def test_technical_seo_is_internal(self):
        payload = mod.compute_reality()
        self.assertEqual(payload["technical_seo"]["source"], "internal")
        self.assertIn("score", payload["technical_seo"])

    def test_authority_never_faked(self):
        payload = mod.compute_reality()
        auth = payload["authority"]
        # Without an external backlink API these MUST stay null + labelled.
        self.assertIsNone(auth["backlinks"])
        self.assertIsNone(auth["referring_domains"])
        self.assertEqual(auth["backlinks_source"], "not_measured")
        self.assertEqual(auth["authority_source"], "estimated")

    def test_growth_is_estimated(self):
        payload = mod.compute_reality()
        self.assertEqual(payload["growth"]["source"], "estimated")
        self.assertIn(payload["growth"]["confidence"], ("low", "medium", "high"))

    def test_write_outputs_creates_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            orig_data, orig_static = mod.DATA, mod.STATIC_DATA
            try:
                mod.DATA = tpath / "data"
                mod.STATIC_DATA = tpath / "static" / "data"
                payload = mod.compute_reality()
                mod.write_outputs(payload)
                self.assertTrue((mod.DATA / "seo-reality.json").is_file())
                self.assertTrue((mod.STATIC_DATA / "seo-reality.json").is_file())
                loaded = json.loads((mod.DATA / "seo-reality.json").read_text())
                self.assertEqual(
                    loaded["technical_seo"]["score"],
                    payload["technical_seo"]["score"],
                )
            finally:
                mod.DATA, mod.STATIC_DATA = orig_data, orig_static


if __name__ == "__main__":
    unittest.main()
