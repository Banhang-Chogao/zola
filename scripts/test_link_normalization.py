#!/usr/bin/env python3
"""Tests for link parsing / regex / normalization that keep /zola canonical and
prevent false skips (a real on-site link slipping past validation) and false 404s
(a valid link wrongly flagged).

Covers:
  * qa-404-checker.py `_classify` — boundary- and host-aware normalization.
  * scripts/check_internal_links.py — attribute-level parsing (no raw-text regex
    false positives) for the missing-/zola-prefix gate.

Both tools must treat /zola as the canonical GitHub Pages runtime subpath and
must NOT assume a root-domain deployment.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


qa404 = _load(ROOT / "qa-404-checker.py", "qa404")
cil = _load(ROOT / "scripts" / "check_internal_links.py", "check_internal_links")


class ClassifyTest(unittest.TestCase):
    """qa-404-checker `_classify` — /zola stays canonical, no mis-normalization."""

    def test_scheme_less_internal_strips_zola(self):
        self.assertEqual(qa404._classify("/zola/posting/foo/"),
                         ("internal", "/posting/foo/"))

    def test_bare_prefix_is_home(self):
        self.assertEqual(qa404._classify("/zola"), ("internal", "/"))
        self.assertEqual(qa404._classify("/zola/"), ("internal", "/"))

    def test_absolute_self_url_internal(self):
        self.assertEqual(
            qa404._classify("https://banhang-chogao.github.io/zola/posting/foo/"),
            ("internal", "/posting/foo/"),
        )

    def test_http_self_url_is_internal_not_skipped(self):
        # Anti-false-skip: the http:// spelling must still be validated on-site.
        self.assertEqual(
            qa404._classify("http://banhang-chogao.github.io/zola/x/"),
            ("internal", "/x/"),
        )

    def test_protocol_relative_self_url_is_internal(self):
        # Anti-false-skip: //host/zola/… is our own site, not external.
        self.assertEqual(
            qa404._classify("//banhang-chogao.github.io/zola/x/"),
            ("internal", "/x/"),
        )

    def test_sibling_path_not_mangled_into_internal(self):
        # B1: NOT boundary-aware before — '/zola-blog/' became internal '/-blog/'.
        kind, _ = qa404._classify("https://banhang-chogao.github.io/zola-blog/")
        self.assertEqual(kind, "external")

    def test_top_level_zola_prefixed_slug_not_stripped(self):
        # B2: '/zola-tutorial/' must stay intact (was mangled to '-tutorial/').
        self.assertEqual(qa404._classify("/zola-tutorial/"),
                         ("internal", "/zola-tutorial/"))
        self.assertEqual(qa404._classify("/zolab/"), ("internal", "/zolab/"))

    def test_external_other_host(self):
        self.assertEqual(qa404._classify("https://example.com/x"),
                         ("external", "https://example.com/x"))

    def test_skip_schemes(self):
        for h in ("mailto:a@b.com", "tel:+84", "#frag", "javascript:void(0)",
                  "data:image/png;base64,xx", ""):
            self.assertEqual(qa404._classify(h), ("skip", None), h)

    def test_other_scheme_skipped(self):
        self.assertEqual(qa404._classify("ftp://host/file"), ("skip", None))

    def test_dotted_slug_resolution_form_preserved(self):
        # Unchanged vs. legacy behaviour (no trailing slash on a dotted leaf;
        # _internal_ok() handles the slash variants on disk).
        self.assertEqual(qa404._classify("/zola/posting/web-3.0-guide"),
                         ("internal", "/posting/web-3.0-guide"))

    def test_query_and_fragment_dropped(self):
        self.assertEqual(qa404._classify("/zola/x/?a=1#top"),
                         ("internal", "/x/"))


class MissingPrefixGateTest(unittest.TestCase):
    """check_internal_links — attribute parsing, no raw-text false positives."""

    def _bad_in(self, html: str) -> list[str]:
        p = cil.LinkParser()
        p.feed(html)
        return [h for h in p.links if cil._is_bad_href(h)]

    def test_real_missing_prefix_anchor_flagged(self):
        self.assertEqual(self._bad_in('<a href="/posting/foo/">x</a>'),
                         ["/posting/foo/"])

    def test_correct_prefixed_anchor_not_flagged(self):
        self.assertEqual(self._bad_in('<a href="/zola/posting/foo/">x</a>'), [])

    def test_data_href_attribute_not_flagged(self):
        # B3: raw-text regex flagged data-href="/x"; attribute parsing must not.
        self.assertEqual(self._bad_in('<div data-href="/spa/route">x</div>'), [])

    def test_xlink_href_not_flagged(self):
        self.assertEqual(
            self._bad_in('<svg><use xlink:href="/img/s.svg#i"/></svg>'), [])

    def test_absolute_self_url_not_flagged(self):
        self.assertEqual(
            self._bad_in('<a href="https://banhang-chogao.github.io/zola/x/">x</a>'),
            [],
        )

    def test_external_link_not_flagged(self):
        self.assertEqual(self._bad_in('<a href="https://example.com/x">x</a>'), [])

    def test_missing_prefix_asset_src_flagged(self):
        # Anti-false-skip: a root-absolute asset missing /zola 404s in the browser.
        self.assertEqual(self._bad_in('<img src="/img/x.webp">'), ["/img/x.webp"])

    def test_prefixed_asset_src_not_flagged(self):
        self.assertEqual(self._bad_in('<img src="/zola/img/x.webp">'), [])

    def test_bare_root_and_relative_not_flagged(self):
        self.assertEqual(self._bad_in('<a href="/">home</a>'), [])
        self.assertEqual(self._bad_in('<a href="relative/page/">x</a>'), [])

    def test_protocol_relative_not_flagged(self):
        self.assertEqual(self._bad_in('<img src="//cdn.example.com/a.js">'), [])

    def test_skip_schemes_not_flagged(self):
        self.assertEqual(
            self._bad_in('<a href="mailto:a@b.com">m</a><a href="#x">f</a>'), [])


if __name__ == "__main__":
    unittest.main()
