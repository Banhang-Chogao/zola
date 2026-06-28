#!/usr/bin/env python3
"""
Tests for baochi migration script.

Test cases cover:
- Category mapping (Khoa học → khoa-hoc, etc.)
- Primary category detection (skip Tất cả/Premium/Báo chí)
- Alias generation
- Fallback to Đời sống when confidence low
- Preservation of source metadata
"""

import os
import unittest
from pathlib import Path
from migrate_baochi_routes import (
    determine_target_section,
    get_categories_from_frontmatter,
    add_alias_to_frontmatter,
)


class TestCategoryMapping(unittest.TestCase):
    """Test category → section mapping."""

    def test_khoa_hoc_mapping(self):
        """Khoa học → khoa-hoc"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Khoa học"]
        )
        self.assertEqual(section, "khoa-hoc")
        self.assertEqual(category, "Khoa học")
        self.assertGreater(confidence, 0.9)

    def test_ngan_hang_mapping(self):
        """Ngân hàng → ngan-hang"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Ngân hàng"]
        )
        self.assertEqual(section, "ngan-hang")
        self.assertEqual(category, "Ngân hàng")
        self.assertGreater(confidence, 0.9)

    def test_du_lich_mapping(self):
        """Du lịch → du-lich"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Du lịch"]
        )
        self.assertEqual(section, "du-lich")
        self.assertEqual(category, "Du lịch")
        self.assertGreater(confidence, 0.9)

    def test_tai_chinh_mapping(self):
        """Tài chính → tai-chinh"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Tài chính"]
        )
        self.assertEqual(section, "tai-chinh")
        self.assertEqual(category, "Tài chính")
        self.assertGreater(confidence, 0.9)

    def test_cong_nghe_mapping(self):
        """Công nghệ → cong-nghe"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Công nghệ"]
        )
        self.assertEqual(section, "cong-nghe")
        self.assertEqual(category, "Công nghệ")
        self.assertGreater(confidence, 0.9)

    def test_bao_hiem_mapping(self):
        """Bảo hiểm → bao-hiem"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Bảo hiểm"]
        )
        self.assertEqual(section, "bao-hiem")
        self.assertEqual(category, "Bảo hiểm")
        self.assertGreater(confidence, 0.9)

    def test_khoa_hoc_with_kien_thuc(self):
        """Khoa học + Kiến thức → khoa-hoc (Kiến thức is skipped)"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Khoa học", "Kiến thức"]
        )
        self.assertEqual(section, "khoa-hoc")
        self.assertEqual(category, "Khoa học")


class TestPrimaryCategoryDetection(unittest.TestCase):
    """Test primary category detection and skipping."""

    def test_skip_tat_ca(self):
        """Skip 'Tất cả' — it's not a real category"""
        section, category, confidence = determine_target_section(["Tất cả"])
        self.assertEqual(section, "doi-song")  # Fallback
        self.assertEqual(category, "Đời sống")
        self.assertLess(confidence, 0.65)

    def test_skip_premium(self):
        """Skip 'Premium' — it's not a real category"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Premium"]
        )
        self.assertEqual(section, "doi-song")  # Fallback
        self.assertEqual(category, "Đời sống")
        self.assertLess(confidence, 0.65)

    def test_skip_bao_chi(self):
        """Skip 'Báo chí' — it's source metadata, not content category"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Báo chí"]
        )
        self.assertEqual(section, "doi-song")  # Fallback
        self.assertEqual(category, "Đời sống")
        self.assertLess(confidence, 0.65)

    def test_fallback_when_only_meta(self):
        """Fallback when only meta categories present"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Báo chí", "Premium"]
        )
        self.assertEqual(section, "doi-song")
        self.assertEqual(category, "Đời sống")
        self.assertLess(confidence, 0.65)

    def test_first_real_category_wins(self):
        """First real category (after skipping meta) is used"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Ngân hàng", "Du lịch"]
        )
        self.assertEqual(section, "ngan-hang")
        self.assertEqual(category, "Ngân hàng")

    def test_two_real_categories_first_wins(self):
        """When multiple real categories, first (after meta) wins"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Khoa học", "Thế giới"]
        )
        self.assertEqual(section, "khoa-hoc")
        self.assertEqual(category, "Khoa học")


class TestAliasGeneration(unittest.TestCase):
    """Test /baochi/<slug>/ alias generation."""

    def test_add_alias_basic(self):
        """Add alias to frontmatter without existing aliases"""
        frontmatter = """title = "Test"
date = 2026-06-28"""
        result = add_alias_to_frontmatter(frontmatter, "bang-ma-codon")
        self.assertIn('aliases = ["/baochi/bang-ma-codon/"]', result)

    def test_add_alias_preserves_other_fields(self):
        """Alias addition doesn't corrupt other fields"""
        frontmatter = """title = "Test"
date = 2026-06-28
[extra]
foo = "bar" """
        result = add_alias_to_frontmatter(frontmatter, "test-slug")
        self.assertIn("title", result)
        self.assertIn("date", result)
        self.assertIn("foo", result)
        self.assertIn('aliases = ["/baochi/test-slug/"]', result)

    def test_add_alias_with_existing_aliases(self):
        """Don't duplicate alias if already present"""
        frontmatter = 'aliases = ["/old-path/"]'
        result = add_alias_to_frontmatter(frontmatter, "test-slug")
        # Should append, not duplicate
        self.assertIn('"/old-path/"', result)
        self.assertIn('"/baochi/test-slug/"', result)


class TestCategoryParsing(unittest.TestCase):
    """Test parsing categories from frontmatter dict."""

    def test_parse_single_category(self):
        """Parse single category"""
        frontmatter = {
            "taxonomies": {
                'categories': '["Tất cả", "Ngân hàng"]'
            }
        }
        categories = get_categories_from_frontmatter(frontmatter)
        self.assertEqual(categories, ["Tất cả", "Ngân hàng"])

    def test_parse_multiple_categories(self):
        """Parse multiple categories"""
        frontmatter = {
            "taxonomies": {
                'categories': '["Tất cả", "Khoa học", "Kiến thức"]'
            }
        }
        categories = get_categories_from_frontmatter(frontmatter)
        self.assertEqual(categories, ["Tất cả", "Khoa học", "Kiến thức"])

    def test_parse_empty_categories(self):
        """Handle empty categories gracefully"""
        frontmatter = {"taxonomies": {"categories": "[]"}}
        categories = get_categories_from_frontmatter(frontmatter)
        self.assertEqual(categories, [])

    def test_parse_missing_taxonomies(self):
        """Handle missing taxonomies gracefully"""
        frontmatter = {"title": "Test"}
        categories = get_categories_from_frontmatter(frontmatter)
        self.assertEqual(categories, [])


class TestBBShortcutIntegration(unittest.TestCase):
    """Test that bb shortcut rules are followed."""

    def test_bb_no_bao_chi_as_category(self):
        """bb shortcut must not put 'Báo chí' in categories"""
        # Simulating a bb-generated post
        categories = ["Tất cả", "Ngân hàng"]
        section, category, confidence = determine_target_section(categories)

        # Báo chí should NOT be in the primary category
        self.assertNotEqual(category, "Báo chí")

    def test_bb_uses_real_content_category(self):
        """bb shortcut must use real content category"""
        # Simulating a banking news post
        categories = ["Tất cả", "Ngân hàng"]
        section, category, confidence = determine_target_section(categories)

        # Should map to real section
        self.assertIn(section, ["ngan-hang", "tai-chinh", "doi-song"])

    def test_bb_fallback_is_doi_song(self):
        """bb shortcut fallback is Đời sống, NOT Báo chí"""
        # Edge case: no clear content category
        categories = ["Tất cả", "Báo chí"]
        section, category, confidence = determine_target_section(categories)

        # Should fallback to Đời sống, not leave as Báo chí
        self.assertEqual(section, "doi-song")
        self.assertEqual(category, "Đời sống")


class TestMigrationSafety(unittest.TestCase):
    """Test migration safety constraints."""

    def test_khoa_hoc_and_kien_thuc_prefers_khoa_hoc(self):
        """When both Khoa học and Kiến thức, prefer Khoa học (more specific)"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Khoa học", "Kiến thức"]
        )
        self.assertEqual(section, "khoa-hoc")
        self.assertEqual(category, "Khoa học")

    def test_confidence_score_high_for_clear_category(self):
        """High confidence when category is clear"""
        section, category, confidence = determine_target_section(
            ["Tất cả", "Ngân hàng"]
        )
        self.assertGreater(confidence, 0.9)

    def test_confidence_score_low_for_fallback(self):
        """Low confidence for fallback"""
        section, category, confidence = determine_target_section(
            ["Tất cả"]  # Only meta categories
        )
        self.assertLess(confidence, 0.65)

    def test_never_create_empty_category_list(self):
        """Never have a post with only ['Tất cả']"""
        # After migration, posts should have real categories
        section, category, confidence = determine_target_section(
            ["Tất cả"]
        )
        # Should fallback to Đời sống, not stay as just Tất cả
        self.assertNotEqual(category, "Tất cả")


if __name__ == "__main__":
    # Run from scripts/ directory
    os.chdir(Path(__file__).parent)
    unittest.main(verbosity=2)
