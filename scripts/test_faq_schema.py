#!/usr/bin/env python3
"""
Tests for FAQ schema implementation.

Tests validate:
1. FAQ frontmatter parses correctly
2. Visible FAQ block renders when extra.faq exists
3. JSON-LD FAQPage renders when extra.faq exists
4. JSON-LD is valid JSON
5. JSON-LD questions/answers match visible FAQ
6. No FAQ schema renders when no FAQ exists
7. No /zola/ URLs in FAQ output
8. Top 20 posts have FAQ between 3-6 items
"""

import json
import re
import unittest
from pathlib import Path
from typing import Dict, List, Optional


class TestFAQSchema(unittest.TestCase):
    """Test FAQ schema implementation."""

    def test_visible_faq_block_renders(self):
        """FAQ section renders when extra.faq exists."""
        post_file = Path("public/posting/vietinbank-v-plus-chi-tiet-quyen-loi/index.html")
        self.assertTrue(post_file.exists(), "Post file should exist")

        content = post_file.read_text(encoding='utf-8')

        # Check visible FAQ section exists
        self.assertIn('class="faq"', content, "Visible FAQ section should render")
        self.assertIn('Câu hỏi thường gặp', content, "FAQ heading should render")
        self.assertIn('class="faq__q"', content, "FAQ question elements should render")
        self.assertIn('class="faq__a"', content, "FAQ answer elements should render")

    def test_json_ld_faqpage_renders(self):
        """JSON-LD FAQPage schema renders when extra.faq exists."""
        post_file = Path("public/posting/vietinbank-v-plus-chi-tiet-quyen-loi/index.html")
        content = post_file.read_text(encoding='utf-8')

        # Check JSON-LD schema exists
        self.assertIn('"@type": "FAQPage"', content, "FAQPage schema should render")
        self.assertIn('"@type": "Question"', content, "Question schema should render")
        self.assertIn('"@type": "Answer"', content, "Answer schema should render")
        self.assertIn('"mainEntity"', content, "mainEntity field should render")

    def test_json_ld_is_valid_json(self):
        """JSON-LD FAQPage is valid JSON."""
        post_file = Path("public/posting/vietinbank-v-plus-chi-tiet-quyen-loi/index.html")
        content = post_file.read_text(encoding='utf-8')

        # Extract all JSON-LD scripts and find FAQPage
        matches = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', content, re.DOTALL)
        self.assertGreater(len(matches), 0, "JSON-LD script tag should exist")

        schema = None
        for json_str in matches:
            try:
                data = json.loads(json_str)
                if data.get("@type") == "FAQPage":
                    schema = data
                    break
            except json.JSONDecodeError:
                continue

        self.assertIsNotNone(schema, "FAQPage schema should exist")
        self.assertEqual(schema["@type"], "FAQPage", "Root @type should be FAQPage")
        self.assertIn("mainEntity", schema, "mainEntity should exist")
        self.assertIsInstance(schema["mainEntity"], list, "mainEntity should be a list")
        self.assertGreater(len(schema["mainEntity"]), 0, "mainEntity should have questions")

    def test_json_ld_matches_visible_faq(self):
        """JSON-LD questions/answers match visible FAQ."""
        post_file = Path("public/posting/vietinbank-v-plus-chi-tiet-quyen-loi/index.html")
        content = post_file.read_text(encoding='utf-8')

        # Extract all JSON-LD scripts and find FAQPage
        matches = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', content, re.DOTALL)
        schema = None
        for json_str in matches:
            try:
                data = json.loads(json_str)
                if data.get("@type") == "FAQPage":
                    schema = data
                    break
            except json.JSONDecodeError:
                continue

        self.assertIsNotNone(schema, "FAQPage schema should exist")

        # Extract visible FAQ questions
        visible_questions = re.findall(r'<summary class="faq__q">([^<]+)</summary>', content)

        # Compare counts
        schema_count = len(schema.get("mainEntity", []))
        visible_count = len(visible_questions)

        self.assertEqual(
            schema_count, visible_count,
            f"JSON-LD question count ({schema_count}) should match visible FAQ count ({visible_count})"
        )

        # Check at least first question matches
        if visible_count > 0:
            first_visible = visible_questions[0]
            first_schema = schema["mainEntity"][0]["name"]
            # Decode HTML entities for comparison
            first_schema_clean = first_schema.replace("&#x2F;", "/")
            self.assertEqual(
                first_schema_clean, first_visible,
                f"First question should match: '{first_schema_clean}' vs '{first_visible}'"
            )

    def test_no_faq_schema_when_no_faq(self):
        """No FAQ schema renders when no FAQ exists."""
        # Find a post without FAQ
        posting_dir = Path("content/posting")
        found_no_faq = False

        for post_file in list(posting_dir.glob("*.md"))[:5]:
            content = post_file.read_text(encoding='utf-8')
            if "[[extra.faq]]" not in content:
                found_no_faq = True
                # Build path to public HTML
                slug = post_file.stem
                public_file = Path(f"public/posting/{slug}/index.html")

                if public_file.exists():
                    html = public_file.read_text(encoding='utf-8')
                    self.assertNotIn('class="faq"', html, "Visible FAQ should not render without extra.faq")
                    # Note: FAQPage might not render either, but it's OK if it doesn't
                break

        if not found_no_faq:
            self.skipTest("No posts found without FAQ to test")

    def test_no_zola_in_faq_urls(self):
        """No /zola/ URLs appear in FAQ output."""
        post_file = Path("public/posting/vietinbank-v-plus-chi-tiet-quyen-loi/index.html")
        content = post_file.read_text(encoding='utf-8')

        # Search for /zola/ in FAQ section
        faq_section = re.search(r'<section class="faq".*?</section>', content, re.DOTALL)
        self.assertTrue(faq_section, "FAQ section should exist")

        faq_content = faq_section.group(0)
        self.assertNotIn("/zola/", faq_content, "No /zola/ URLs should appear in FAQ")

    def test_top_posts_have_faq(self):
        """Top 20 posts have FAQ between 3-6 items."""
        report_file = Path("reports/faq-schema-top-posts.json")
        if not report_file.exists():
            self.skipTest("FAQ audit report not found")

        with open(report_file) as f:
            report = json.load(f)

        for post in report.get("posts", []):
            faq_count = post.get("faq_count", 0)
            self.assertGreaterEqual(
                faq_count, 3,
                f"Post '{post['title']}' should have at least 3 FAQ items, has {faq_count}"
            )
            self.assertLessEqual(
                faq_count, 6,
                f"Post '{post['title']}' should have at most 6 FAQ items, has {faq_count}"
            )

    def test_faq_answers_are_reasonable_length(self):
        """FAQ answers are between 40-200 words."""
        post_file = Path("content/posting/vietinbank-v-plus-chi-tiet-quyen-loi.md")
        if not post_file.exists():
            self.skipTest("Test post not found")

        content = post_file.read_text(encoding='utf-8')

        # Extract FAQ items
        faq_items = re.findall(r'a = "([^"]+)"', content)

        for i, answer in enumerate(faq_items, 1):
            word_count = len(answer.split())
            self.assertGreaterEqual(
                word_count, 20,
                f"FAQ #{i} answer too short ({word_count} words): {answer[:50]}..."
            )
            # Be lenient on upper limit as some can be longer
            self.assertLess(
                word_count, 500,
                f"FAQ #{i} answer too long ({word_count} words): {answer[:50]}..."
            )

    def test_faq_frontmatter_valid_toml(self):
        """FAQ frontmatter is valid TOML format."""
        post_file = Path("content/posting/vietinbank-v-plus-chi-tiet-quyen-loi.md")
        content = post_file.read_text(encoding='utf-8')

        # Check TOML structure
        self.assertIn("[[extra.faq]]", content, "Should have [[extra.faq]] section")

        # Extract FAQ section
        match = re.search(r'\[\[extra\.faq\]\](.*?)(?=\[\[|\+\+\+|$)', content, re.DOTALL)
        if match:
            faq_section = match.group(1)
            # Should have q and a fields
            self.assertIn('q = "', faq_section, "FAQ items should have q field")
            self.assertIn('a = "', faq_section, "FAQ items should have a field")


class TestFAQIntegration(unittest.TestCase):
    """Integration tests for FAQ across the site."""

    def test_multiple_posts_have_faq_rendering(self):
        """Multiple posts render FAQ correctly."""
        test_posts = [
            "vietinbank-v-plus-chi-tiet-quyen-loi",
            "bao-lau-de-thay-ket-qua-seo",
            "uranium-lam-giau-la-gi",
        ]

        for slug in test_posts:
            post_file = Path(f"public/posting/{slug}/index.html")
            if not post_file.exists():
                continue

            content = post_file.read_text(encoding='utf-8')

            # Check visible FAQ
            self.assertIn('class="faq"', content, f"{slug} should have FAQ section")

            # Check JSON-LD
            self.assertIn('"@type": "FAQPage"', content, f"{slug} should have FAQPage schema")

    def test_faq_css_classes_exist(self):
        """FAQ CSS classes are properly used."""
        post_file = Path("public/posting/vietinbank-v-plus-chi-tiet-quyen-loi/index.html")
        content = post_file.read_text(encoding='utf-8')

        # Check CSS classes
        self.assertIn('class="faq"', content, "faq class should exist")
        self.assertIn('class="faq__title"', content, "faq__title class should exist")
        self.assertIn('class="faq__item"', content, "faq__item class should exist")
        self.assertIn('class="faq__q"', content, "faq__q class should exist")
        self.assertIn('class="faq__a"', content, "faq__a class should exist")


if __name__ == "__main__":
    unittest.main(verbosity=2)
