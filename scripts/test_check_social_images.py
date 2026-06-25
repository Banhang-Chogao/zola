#!/usr/bin/env python3
"""Tests for check_social_images.py."""

import unittest
from pathlib import Path
from scripts.check_social_images import extract_og_meta, validate_og_image


class TestOGMetaExtractor(unittest.TestCase):
    """Test HTML parsing for OG meta tags."""

    def test_extract_og_image_absolute(self):
        """Extract og:image when it's an absolute URL."""
        html = '''
        <html>
        <head>
            <meta property="og:image" content="https://seomoney.org/img/og/test-post.og.webp">
            <meta property="og:image:width" content="1200">
            <meta property="og:image:height" content="630">
        </head>
        </html>
        '''
        meta = extract_og_meta(html)
        self.assertEqual(meta["og_image"], "https://seomoney.org/img/og/test-post.og.webp")
        self.assertEqual(meta["og_width"], "1200")
        self.assertEqual(meta["og_height"], "630")

    def test_extract_missing_og_image(self):
        """Detect missing og:image."""
        html = '<html><head><meta name="description" content="test"></head></html>'
        meta = extract_og_meta(html)
        self.assertIsNone(meta["og_image"])

    def test_extract_twitter_image(self):
        """Extract twitter:image."""
        html = '''
        <html>
        <head>
            <meta name="twitter:image" content="https://example.com/img.webp">
        </head>
        </html>
        '''
        meta = extract_og_meta(html)
        self.assertEqual(meta["twitter_image"], "https://example.com/img.webp")

    def test_extract_blog_posting_schema(self):
        """Detect BlogPosting JSON-LD schema."""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "BlogPosting", "headline": "Test"}
            </script>
        </head>
        </html>
        '''
        meta = extract_og_meta(html)
        self.assertTrue(meta["has_schema"])


class TestValidateOGImage(unittest.TestCase):
    """Test OG image validation."""

    def test_valid_og_image(self):
        """Valid OG image: absolute URL, .webp, correct dimensions."""
        meta = {
            "og_image": "https://seomoney.org/img/og/test.og.webp",
            "og_width": "1200",
            "og_height": "630",
        }
        is_valid, errors = validate_og_image("https://seomoney.org/posting/test/", meta, check_files=False)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_missing_og_image(self):
        """Invalid: missing og:image."""
        meta = {"og_image": "", "og_width": "", "og_height": ""}
        is_valid, errors = validate_og_image("https://seomoney.org/posting/test/", meta)
        self.assertFalse(is_valid)
        self.assertIn("missing og:image", errors[0])

    def test_relative_og_image(self):
        """Invalid: og:image is relative URL."""
        meta = {
            "og_image": "/img/og/test.webp",
            "og_width": "1200",
            "og_height": "630",
        }
        is_valid, errors = validate_og_image("https://seomoney.org/posting/test/", meta)
        self.assertFalse(is_valid)
        self.assertTrue(any("relative URL" in e for e in errors))

    def test_svg_og_image(self):
        """Invalid: og:image cannot be SVG."""
        meta = {
            "og_image": "https://seomoney.org/img/cover/test.svg",
            "og_width": "1200",
            "og_height": "630",
        }
        is_valid, errors = validate_og_image("https://seomoney.org/posting/test/", meta)
        self.assertFalse(is_valid)
        self.assertTrue(any("SVG" in e for e in errors))

    def test_wrong_og_dimensions(self):
        """Invalid: og:image has wrong dimensions."""
        meta = {
            "og_image": "https://seomoney.org/img/og/test.webp",
            "og_width": "800",
            "og_height": "600",
        }
        is_valid, errors = validate_og_image("https://seomoney.org/posting/test/", meta)
        self.assertFalse(is_valid)
        self.assertTrue(any("dimensions" in e for e in errors))

    def test_og_image_jpg(self):
        """Valid: og:image can be JPG."""
        meta = {
            "og_image": "https://seomoney.org/img/og/test.jpg",
            "og_width": "1200",
            "og_height": "630",
        }
        is_valid, errors = validate_og_image("https://seomoney.org/posting/test/", meta)
        # Should be valid even though JPG (not WebP)
        # No error about file format
        jpeg_format_error = any(".jpg" in e and "social" in e for e in errors)
        self.assertFalse(jpeg_format_error)


if __name__ == "__main__":
    unittest.main()
