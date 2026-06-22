#!/usr/bin/env python3
"""
Lightweight mobile-readability regression guard.

Static (no browser, no build) checks that the mobile-hardening layer keeps
its core guarantees so a future edit cannot silently reintroduce the worst
small-screen problems: media wider than the viewport, article tables that
break the layout, long URLs that do not wrap, and ad slots without a width
cap. Pairs with sass/_mobile-hardening.scss.

Run: python3 -m unittest scripts.test_mobile_readability -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARDENING = ROOT / "sass" / "_mobile-hardening.scss"
SITE_SCSS = ROOT / "sass" / "site.scss"


def _norm(text: str) -> str:
    """Collapse whitespace so we can match declarations regardless of formatting."""
    return re.sub(r"\s+", " ", text)


class MobileHardeningPresent(unittest.TestCase):
    def setUp(self):
        self.assertTrue(HARDENING.exists(), "sass/_mobile-hardening.scss is missing")
        self.raw = HARDENING.read_text(encoding="utf-8")
        self.css = _norm(self.raw)

    def test_imported_last(self):
        """The partial must be imported AFTER every component so its guards win."""
        order = SITE_SCSS.read_text(encoding="utf-8")
        imports = re.findall(r'@import\s+"([^"]+)"', order)
        self.assertIn("mobile-hardening", imports, "partial not imported in site.scss")
        self.assertEqual(
            imports[-1], "mobile-hardening",
            f"mobile-hardening must be the LAST @import; current last = {imports[-1]}",
        )

    def test_media_capped(self):
        """Embeds cannot exceed their container (no horizontal scroll from media)."""
        for tag in ("iframe", "video", "embed", "object"):
            self.assertRegex(self.css, rf"\b{tag}\b", f"{tag} not constrained")
        self.assertIn("max-width: 100%", self.css)

    def test_long_words_wrap(self):
        """Prose + card titles wrap long URLs/tokens instead of overflowing."""
        self.assertIn("overflow-wrap: anywhere", self.css)
        self.assertIn(".post-single__content", self.css)

    def test_article_tables_scroll(self):
        """In-article tables become their own horizontal scroll box on mobile."""
        self.assertRegexpMatches(
            self.css,
            r"\.post-single__content table\s*\{[^}]*overflow-x: auto",
        )

    def test_adsense_slots_capped(self):
        """Ad slots stay inside the column and keep policy-safe spacing."""
        self.assertIn("adsbygoogle", self.css)
        self.assertIn(".ad-slot", self.css)
        # width cap so a creative cannot widen the page
        self.assertRegexpMatches(self.css, r"adsbygoogle[^{]*\{[^}]*max-width: 100%")

    def test_no_quote_chars(self):
        """Comments must avoid ' or \" so the SCSS QA brace-counter stays accurate."""
        self.assertNotIn("'", self.raw)
        self.assertNotIn('"', self.raw)


if __name__ == "__main__":
    unittest.main()
