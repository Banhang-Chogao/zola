"""Tests for VIPZone picker catalog builder."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from vipzone_picker_catalog import (
    build_catalog,
    is_excluded,
    migrate_picks,
    normalize_pick_url,
)


class TestVipzonePickerCatalog(unittest.TestCase):
    def test_excludes_internal_paths(self) -> None:
        self.assertTrue(is_excluded("/insights/", "insights"))
        self.assertTrue(is_excluded("/tools/vipzone-admin/", "vipzone-admin"))
        self.assertTrue(is_excluded("/tools/h-dashboard/", "h-dashboard"))
        self.assertFalse(is_excluded("/tools/f-dashboard/", "f-dashboard"))

    def test_build_catalog_has_tools_and_premium(self) -> None:
        cat = build_catalog()
        self.assertIn("tools", cat)
        self.assertIn("premium", cat)
        self.assertGreater(len(cat["tools"]), 5)
        urls = {t["url"] for t in cat["tools"]}
        self.assertIn("/tools/f-dashboard/", urls)
        self.assertNotIn("/insights/", urls)
        self.assertNotIn("/tools/h-dashboard/", urls)
        if cat["premium"]:
            self.assertTrue(all("premium" in t["url"] or "/posting/" in t["url"] for t in cat["premium"]))

    def test_migrate_picks_drops_legacy_and_maps_slug(self) -> None:
        cat = build_catalog()
        raw = ["/categories/premium/", "/insights/", "/tools/f-dashboard"]
        out = migrate_picks(raw, cat)
        self.assertNotIn("/categories/premium/", out)
        self.assertNotIn("/insights/", out)
        self.assertIn(normalize_pick_url("/tools/f-dashboard/"), out)


if __name__ == "__main__":
    unittest.main()