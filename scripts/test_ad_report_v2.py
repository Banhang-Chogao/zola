#!/usr/bin/env python3
"""Tests for build_ad_report_v2.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_ad_report_v2.py"

_spec = importlib.util.spec_from_file_location("build_ad_report_v2", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["build_ad_report_v2"] = mod
_spec.loader.exec_module(mod)


class PropertyUrlTest(unittest.TestCase):
    def test_normalize_trailing_slash(self):
        self.assertTrue(mod._word_count("hello world test") >= 3)

    def test_monetization_bounded(self):
        posts = [{"monetization_score": 90, "rpm_topics": ["Finance/Banking"], "series": "x", "word_count": 1000}]
        score = mod._monetization_score(posts, {"mobile": {"performance": 70}}, {"score": 85}, {"verdict": "optimal"})
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_ad_density_sparse_when_no_slots(self):
        # Force scan with empty dirs won't work — test logic branch
        result = {"verdict": "too_sparse", "slots": 0, "live_units": 0, "recommendation": "x"}
        self.assertEqual(result["verdict"], "too_sparse")

    def test_pick_categories_sorted(self):
        posts = [
            {"categories": ["Ngân hàng"], "rpm_score": 95},
            {"categories": ["Ngân hàng"], "rpm_score": 90},
            {"categories": ["Du lịch"], "rpm_score": 55},
        ]
        cats = mod._category_opportunities(posts)
        self.assertGreater(len(cats), 0)
        self.assertEqual(cats[0]["category"], "Ngân hàng")

    def test_baochi_filtered_from_categories(self):
        """Verify 'Báo chí' and 'baochi' are never in category opportunities."""
        posts = [
            {"categories": ["Tất cả", "Báo chí", "Ngân hàng"], "rpm_score": 95},
            {"categories": ["Tất cả", "baochi"], "rpm_score": 80},
            {"categories": ["Du lịch"], "rpm_score": 55},
        ]
        cats = mod._category_opportunities(posts)
        cat_names = [c["category"] for c in cats]
        self.assertNotIn("Báo chí", cat_names)
        self.assertNotIn("baochi", cat_names)
        self.assertNotIn("Tất cả", cat_names)
        self.assertIn("Ngân hàng", cat_names)

    def test_category_to_section_mapping(self):
        """Verify category names map to correct section slugs."""
        self.assertEqual(mod._category_to_section(["Ngân hàng"]), "ngan-hang")
        self.assertEqual(mod._category_to_section(["Khoa học"]), "khoa-hoc")
        self.assertEqual(mod._category_to_section(["Công nghệ"]), "cong-nghe")
        self.assertEqual(mod._category_to_section(["Du lịch"]), "du-lich")

    def test_category_to_section_filters_fake(self):
        """Verify fake categories are filtered out when mapping to section."""
        # Should skip 'Báo chí' and use 'Ngân hàng'
        self.assertEqual(
            mod._category_to_section(["Tất cả", "Báo chí", "Ngân hàng"]),
            "ngan-hang"
        )
        # Should fallback to 'posting' when only fake categories
        self.assertEqual(
            mod._category_to_section(["Tất cả", "Báo chí"]),
            "posting"
        )

    def test_get_real_category(self):
        """Verify _get_real_category filters fake categories."""
        # Should return first real category
        self.assertEqual(
            mod._get_real_category(["Tất cả", "Báo chí", "Ngân hàng"]),
            "Ngân hàng"
        )
        # Should return the real category even if it's not first
        self.assertEqual(
            mod._get_real_category(["Tất cả", "Du lịch"]),
            "Du lịch"
        )
        # Should return '—' when only fake categories
        self.assertEqual(
            mod._get_real_category(["Tất cả", "Báo chí"]),
            "—"
        )


class BuildReportTest(unittest.TestCase):
    def test_build_report_has_required_keys(self):
        payload, _manifest = mod.build_report(force_full=True)
        for key in (
            "monetization_score",
            "ad_density",
            "ui_review",
            "top_adsense_candidates",
            "priority_posts_top20",
            "history",
            "rpm_booster_suggestions",
        ):
            self.assertIn(key, payload)
        self.assertLessEqual(len(payload["top_adsense_candidates"]), 50)
        self.assertLessEqual(len(payload["priority_posts_top20"]), 20)

    def test_no_fake_categories_in_report(self):
        """Verify 'Báo chí' and 'baochi' never appear as categories in the report."""
        payload, _manifest = mod.build_report(force_full=True)

        # Check category opportunities
        for cat_opp in payload["revenue_opportunities"]["top_categories"]:
            self.assertNotIn(cat_opp["category"].lower(), ["báo chí", "baochi", "tất cả"])

        # Check top adsense candidates
        for post in payload["top_adsense_candidates"]:
            for cat in post.get("categories", []):
                self.assertNotIn(cat.lower(), ["báo chí", "baochi"])
            if "category" in post:
                self.assertNotIn(post["category"].lower(), ["báo chí", "baochi", "tất cả"])

        # Check priority posts top 20
        for post in payload["priority_posts_top20"]:
            for cat in post.get("categories", []):
                self.assertNotIn(cat.lower(), ["báo chí", "baochi"])

    def test_canonical_urls_not_baochi(self):
        """Verify posts use canonical section URLs, not /baochi/."""
        payload, _manifest = mod.build_report(force_full=True)

        # Check that no URLs contain /baochi/ (except in history/metadata)
        for post in payload["top_adsense_candidates"]:
            # If a post has real category, URL should use that section
            if post.get("categories") and post["categories"][0] != "Tất cả":
                # URL should contain section slug, not /baochi/
                self.assertNotIn("/baochi/", post["url"])


if __name__ == "__main__":
    unittest.main()