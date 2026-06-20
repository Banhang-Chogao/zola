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


# --- Sticky single-active helpers (mirror services/visitor-counter/main.py) ---
_EXTRA_BLOCK_RE = re.compile(r"(?ms)^(\[extra\]\s*\n)(.*?)(?=^\[|\Z)")
_STICKY_TRUE_RE = re.compile(r"(?m)^sticky\s*=\s*true\s*$")
_STICKY_LINE_RE = re.compile(r"(?m)^sticky\s*=\s*true\s*\n?")


def frontmatter_forces_sticky(content: str) -> bool:
    extra = _EXTRA_BLOCK_RE.search(content or "")
    return bool(extra and _STICKY_TRUE_RE.search(extra.group(2)))


def demote_sticky_frontmatter(content: str) -> str:
    def replace_extra(match: "re.Match") -> str:
        body = _STICKY_LINE_RE.sub("", match.group(2))
        return match.group(1) + body
    return _EXTRA_BLOCK_RE.sub(replace_extra, content or "", count=1)


SAMPLE_STICKY = '+++\ntitle = "Old"\n\n[extra]\nfeatured = true\nsticky = true\n+++\n\nBody.\n'
SAMPLE_PLAIN = '+++\ntitle = "New"\n\n[extra]\nsticky = true\n+++\n\nBody.\n'


class StickySingleActiveTests(unittest.TestCase):
    def test_detects_sticky(self):
        self.assertTrue(frontmatter_forces_sticky(SAMPLE_STICKY))
        self.assertFalse(frontmatter_forces_sticky('+++\ntitle="x"\n[extra]\n+++\n'))

    def test_demote_removes_only_sticky(self):
        out = demote_sticky_frontmatter(SAMPLE_STICKY)
        self.assertFalse(frontmatter_forces_sticky(out))
        # featured must survive — only sticky is removed
        self.assertIn("featured = true", out)

    def test_demote_idempotent_when_absent(self):
        plain = '+++\ntitle = "x"\n\n[extra]\nfeatured = true\n+++\n'
        self.assertEqual(demote_sticky_frontmatter(plain), plain)

    def test_single_active_after_save(self):
        # Simulate saving SAMPLE_PLAIN as the new sticky; the old one is demoted.
        posts = {"old": SAMPLE_STICKY, "new": SAMPLE_PLAIN}
        for slug, content in posts.items():
            if slug != "new" and frontmatter_forces_sticky(content):
                posts[slug] = demote_sticky_frontmatter(content)
        sticky_count = sum(1 for c in posts.values() if frontmatter_forces_sticky(c))
        self.assertEqual(sticky_count, 1)


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