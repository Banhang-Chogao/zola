#!/usr/bin/env python3
"""Tests for stale /zola/ link auto-heal (V19)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fix_stale_zola_links import _fix_html, _fix_markdown, fix_file
from site_link_prefix import strip_stale_zola_path


class TestStripStaleZolaPath(unittest.TestCase):
    def test_home(self) -> None:
        self.assertEqual(strip_stale_zola_path("/zola/"), "/")
        self.assertEqual(strip_stale_zola_path("/zola"), "/")

    def test_posting(self) -> None:
        self.assertEqual(
            strip_stale_zola_path("/zola/posting/foo/"),
            "/posting/foo/",
        )

    def test_passthrough(self) -> None:
        self.assertEqual(strip_stale_zola_path("/posting/foo/"), "/posting/foo/")


class TestFixMarkdown(unittest.TestCase):
    def test_markdown_link(self) -> None:
        raw = "Xem [bài](/zola/posting/slug/) nhé."
        new, n = _fix_markdown(raw)
        self.assertEqual(n, 1)
        self.assertIn("](/posting/slug/)", new)
        self.assertNotIn("/zola/", new)


class TestFixHtml(unittest.TestCase):
    def test_href(self) -> None:
        raw = '<a href="/zola/">Home</a>'
        new, n = _fix_html(raw)
        self.assertEqual(n, 1)
        self.assertIn('href="/"', new)


class TestFixFile(unittest.TestCase):
    def test_apply_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text("[home](/zola/)\n", encoding="utf-8")
            n = fix_file(path, apply=True)
            self.assertEqual(n, 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "[home](/)\n")


if __name__ == "__main__":
    unittest.main()