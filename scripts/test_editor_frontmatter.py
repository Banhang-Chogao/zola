#!/usr/bin/env python3
"""Unit tests for CMS editor premium/MoMo frontmatter rules."""

import re
import unittest


def is_premium_category(cat: str) -> bool:
    return (cat or "").strip().lower() == "premium"


def build_extra_lines(category: str, momo_link: str = "") -> list[str]:
    lines: list[str] = []
    if is_premium_category(category):
        lines.append("premium = true")
        if momo_link:
            lines.append(f'momo_payment_link = "{momo_link}"')
    return lines


def parse_momo_from_extra(fm_text: str) -> tuple[bool, str]:
    premium = False
    momo = ""
    section = "root"
    for line in fm_text.splitlines():
        t = line.strip()
        if t == "[extra]":
            section = "extra"
            continue
        if section != "extra":
            continue
        m = re.match(r'^(\w+)\s*=\s*(.+)$', t)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip('"')
        if key == "premium" and val == "true":
            premium = True
        if key in ("momo_payment_link", "momo_link"):
            momo = val
    return premium, momo


class EditorFrontmatterTests(unittest.TestCase):
    def test_premium_adds_flags(self):
        lines = build_extra_lines("premium", "https://me.momo.vn/test")
        self.assertIn("premium = true", lines)
        self.assertIn('momo_payment_link = "https://me.momo.vn/test"', lines)

    def test_non_premium_omits_momo(self):
        lines = build_extra_lines("Posting", "https://me.momo.vn/test")
        self.assertEqual(lines, [])

    def test_premium_without_link(self):
        lines = build_extra_lines("premium", "")
        self.assertEqual(lines, ["premium = true"])

    def test_category_case_insensitive(self):
        self.assertTrue(is_premium_category("Premium"))
        self.assertTrue(is_premium_category("PREMIUM"))
        self.assertFalse(is_premium_category("Posting"))

    def test_parse_existing_extra(self):
        fm = """
[extra]
featured = true
premium = true
momo_payment_link = "https://me.momo.vn/abc"
"""
        premium, momo = parse_momo_from_extra(fm)
        self.assertTrue(premium)
        self.assertEqual(momo, "https://me.momo.vn/abc")


if __name__ == "__main__":
    unittest.main()