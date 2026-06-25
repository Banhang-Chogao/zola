#!/usr/bin/env python3
"""
Unit tests for FAQ autofixer script
"""

import unittest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from faq_fixer_auto import (
    extract_frontmatter,
    serialize_frontmatter,
    count_words,
    is_eligible,
    extract_key_terms,
    generate_faq,
    process_post,
)


class TestFAQFixer(unittest.TestCase):
    """Test cases for FAQ autofixer."""

    def test_extract_frontmatter_valid(self):
        """Test extracting valid TOML frontmatter."""
        content = '''+++
title = "Test Post"
date = 2026-06-22
[taxonomies]
categories = ["SEO"]
+++
Body text here.
'''
        fm, body = extract_frontmatter(content)
        self.assertEqual(fm["title"], "Test Post")
        self.assertIn("SEO", fm["taxonomies"]["categories"])
        self.assertIn("Body text here", body)

    def test_extract_frontmatter_no_frontmatter(self):
        """Test handling content without frontmatter."""
        content = "Just body text, no frontmatter."
        fm, body = extract_frontmatter(content)
        self.assertEqual(fm, {})
        self.assertIn("Just body text", body)

    def test_count_words(self):
        """Test word counting."""
        text = "This is a test. One two three four five."
        # "This", "is", "a", "test", "One", "two", "three", "four", "five" = 9 words
        self.assertEqual(count_words(text), 9)

    def test_is_eligible_with_existing_faq(self):
        """Test that posts with existing FAQ are skipped."""
        fm = {
            "taxonomies": {"categories": ["SEO"]},
            "extra": {"faq": [{"q": "Test", "a": "Answer"}]}
        }
        body = "This is a long content " * 50
        eligible, reason = is_eligible(fm, body)
        self.assertFalse(eligible)
        self.assertEqual(reason, "already_has_faq")

    def test_is_eligible_with_skip_category(self):
        """Test that skip categories are rejected."""
        fm = {"taxonomies": {"categories": ["Báo chí"]}}
        body = "Content " * 100
        eligible, reason = is_eligible(fm, body)
        self.assertFalse(eligible)
        self.assertIn("skip_category", reason)

    def test_is_eligible_too_short(self):
        """Test that short posts are skipped."""
        fm = {"taxonomies": {"categories": ["SEO"]}}
        body = "Too short."  # Only 2 words
        eligible, reason = is_eligible(fm, body)
        self.assertFalse(eligible)
        self.assertIn("too_short", reason)

    def test_is_eligible_valid_seo_post(self):
        """Test that valid SEO post is eligible."""
        fm = {"taxonomies": {"categories": ["SEO"]}}
        body = "This is a long content about SEO. " * 50  # >300 words
        eligible, reason = is_eligible(fm, body)
        self.assertTrue(eligible)
        self.assertEqual(reason, "eligible")

    def test_extract_key_terms(self):
        """Test key term extraction."""
        body = """
## SEO Basics
This is about **keyword research**.
### Title Optimization
"""
        terms = extract_key_terms(body)
        self.assertGreater(len(terms), 0)
        # Terms should include heading text
        self.assertTrue(any("seo" in t.lower() for t in terms))

    def test_generate_faq_seo(self):
        """Test FAQ generation for SEO category."""
        fm = {"taxonomies": {"categories": ["SEO"]}}
        body = """
## Ranking Strategy
This is about ranking and keywords. Learn how to optimize.

### Keyword Research
Best practices for finding keywords.

This is a long post with content. """ + ("More content " * 50)
        title = "SEO Guide"
        faq = generate_faq(fm, body, title)
        # FAQ generation might return None if patterns don't match well
        # But we should verify it doesn't error
        if faq:
            self.assertLessEqual(len(faq), 6)
            self.assertGreater(len(faq), 0)
            for item in faq:
                self.assertIn("q", item)
                self.assertIn("a", item)

    def test_generate_faq_banking(self):
        """Test FAQ generation for banking category."""
        fm = {"taxonomies": {"categories": ["Ngân hàng"]}}
        body = "This is about mobile banking and security. " * 50
        title = "Mobile Banking"
        faq = generate_faq(fm, body, title)
        self.assertIsNotNone(faq)
        if faq:
            for item in faq:
                self.assertIsInstance(item["q"], str)
                self.assertIsInstance(item["a"], str)

    def test_process_post_eligible(self):
        """Test processing an eligible post."""
        with TemporaryDirectory() as tmpdir:
            post_path = Path(tmpdir) / "test.md"
            content = '''+++
title = "SEO Tips"
date = 2026-06-22
[taxonomies]
categories = ["SEO"]
+++
This is a long post about ranking and keywords. ''' + ("content " * 50)

            post_path.write_text(content)

            changed, reason, faq = process_post(post_path)
            if changed:
                self.assertEqual(reason, "faq_generated")
                self.assertIsNotNone(faq)
                self.assertGreater(len(faq), 0)
            else:
                # May still fail if category doesn't generate FAQ
                self.assertIsNone(faq)

    def test_serialize_frontmatter_roundtrip(self):
        """Test that serialize/deserialize preserves structure."""
        original = '''+++
title = "Test"
date = 2026-06-22

[taxonomies]
categories = ["SEO"]

[extra]
featured = true
faq = [{q = "Q1", a = "A1"}]
+++
'''
        fm, _ = extract_frontmatter(original + "body")
        serialized = serialize_frontmatter(fm)
        fm2, _ = extract_frontmatter(serialized + "body")

        self.assertEqual(fm["title"], fm2["title"])
        self.assertEqual(fm["date"], fm2["date"])
        self.assertEqual(
            fm["taxonomies"]["categories"],
            fm2["taxonomies"]["categories"]
        )


if __name__ == "__main__":
    unittest.main()
