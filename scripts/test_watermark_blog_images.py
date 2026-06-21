#!/usr/bin/env python3
"""Unit tests for scripts/watermark_blog_images.py.

Covers the contract from the watermark rule:
  - deterministic 16-digit watermark generation
  - skip SVG / logo / icon / brand / .og.webp assets
  - idempotent second run (no stacking)
  - a changed image gets reprocessed with a new hash
  - .webp output stays watermarked (embedded marker + manifest + valid image)
  - the --check gate fails before apply and passes after
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watermark_blog_images as w  # noqa: E402

try:
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


def _make_webp(path: Path, color=(120, 130, 140), size=(240, 160)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, "WEBP", quality=90)


class WatermarkHashTests(unittest.TestCase):
    def test_hash_is_16_numeric_digits(self):
        h = w.watermark_hash("static/img/posting/a/cover.webp", b"abc")
        self.assertEqual(len(h), 16)
        self.assertTrue(h.isdigit())

    def test_hash_deterministic(self):
        a = w.watermark_hash("static/img/posting/a/cover.webp", b"same-bytes")
        b = w.watermark_hash("static/img/posting/a/cover.webp", b"same-bytes")
        self.assertEqual(a, b)

    def test_hash_changes_with_bytes(self):
        a = w.watermark_hash("static/img/posting/a/cover.webp", b"one")
        b = w.watermark_hash("static/img/posting/a/cover.webp", b"two")
        self.assertNotEqual(a, b)

    def test_hash_changes_with_path(self):
        a = w.watermark_hash("static/img/posting/a/cover.webp", b"x")
        b = w.watermark_hash("static/img/posting/b/cover.webp", b"x")
        self.assertNotEqual(a, b)

    def test_text_format(self):
        t = w.watermark_text("static/img/posting/a/cover.webp", b"x")
        self.assertTrue(t.endswith("_seomoney.org"))
        self.assertEqual(len(t.split("_seomoney.org")[0]), 16)


class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name).resolve()
        self._orig_repo = w.REPO
        w.REPO = self.repo

    def tearDown(self):
        w.REPO = self._orig_repo
        self._tmp.cleanup()

    def p(self, rel):
        return self.repo / rel

    def test_content_image_eligible(self):
        self.assertTrue(w.is_eligible(self.p("static/img/posting/a/cover.webp")))
        self.assertTrue(w.is_eligible(self.p("static/img/covers/some-post.webp")))
        self.assertTrue(w.is_eligible(self.p("static/img/posting/a/photo.jpg")))
        self.assertTrue(w.is_eligible(self.p("static/img/posting/a/photo.png")))

    def test_skip_svg_gif_ico(self):
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/cover.svg")))
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/anim.gif")))
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/fav.ico")))

    def test_skip_og_twins(self):
        self.assertFalse(w.is_eligible(self.p("static/img/covers/post.og.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/og/seomoney-og.og.webp")))

    def test_skip_brand_ui_dirs(self):
        self.assertFalse(w.is_eligible(self.p("static/img/brand/seomoney-mark.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/placeholder/placeholder.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/icons/menu.png")))

    def test_skip_brand_ui_names(self):
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/logo.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/site-favicon.png")))
        self.assertFalse(w.is_eligible(self.p("static/img/author-avatar.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/og-default.webp")))


@unittest.skipUnless(HAVE_PIL, "Pillow required for apply/round-trip tests")
class ApplyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name).resolve()
        self._orig = (w.REPO, w.DATA, w.MANIFEST_PATH)
        w.REPO = self.repo
        w.DATA = self.repo / "data"
        w.MANIFEST_PATH = w.DATA / "image-watermark-manifest.json"
        self.img = self.repo / "static/img/posting/sample/cover.webp"
        _make_webp(self.img)

    def tearDown(self):
        w.REPO, w.DATA, w.MANIFEST_PATH = self._orig
        self._tmp.cleanup()

    def test_apply_watermarks_and_marks(self):
        res = w.process(["static/img"], apply=True, dry_run=False)
        self.assertEqual(len(res["watermarked"]), 1)
        # image still opens and keeps its dimensions (not corrupted)
        with Image.open(self.img) as im:
            self.assertEqual(im.size, (240, 160))
        # embedded marker present and matches the manifest hash
        marker = w.read_marker(self.img)
        self.assertIsNotNone(marker)
        rel = w._rel(self.img)
        self.assertEqual(w.load_manifest()["images"][rel]["hash16"], marker)
        # watermark text shape
        self.assertTrue(
            w.load_manifest()["images"][rel]["watermark_text"].endswith("_seomoney.org"))

    def test_second_run_is_idempotent(self):
        w.process(["static/img"], apply=True, dry_run=False)
        bytes_after_first = self.img.read_bytes()
        res2 = w.process(["static/img"], apply=True, dry_run=False)
        self.assertEqual(len(res2["watermarked"]), 0)
        self.assertEqual(len(res2["skipped"]), 1)
        # file unchanged on the second run (no stacking / no rewrite)
        self.assertEqual(self.img.read_bytes(), bytes_after_first)

    def test_changed_image_is_reprocessed(self):
        w.process(["static/img"], apply=True, dry_run=False)
        rel = w._rel(self.img)
        first_hash = w.load_manifest()["images"][rel]["hash16"]
        # Replace with a genuinely different, un-watermarked image at the same path.
        _make_webp(self.img, color=(10, 200, 60), size=(240, 160))
        res = w.process(["static/img"], apply=True, dry_run=False)
        self.assertEqual(len(res["watermarked"]), 1)
        new_hash = w.load_manifest()["images"][rel]["hash16"]
        self.assertNotEqual(first_hash, new_hash)

    def test_webp_output_remains_watermarked(self):
        w.process(["static/img"], apply=True, dry_run=False)
        # marker survives in the saved .webp
        self.assertIsNotNone(w.read_marker(self.img))
        ok, missing, stale = w.check_watermarks(["static/img"])
        self.assertTrue(ok)
        self.assertEqual(missing, [])
        self.assertEqual(stale, [])

    def test_check_gate_fails_before_apply_passes_after(self):
        ok, missing, stale = w.check_watermarks(["static/img"])
        self.assertFalse(ok)
        self.assertIn(w._rel(self.img), missing)
        w.process(["static/img"], apply=True, dry_run=False)
        ok2, missing2, _ = w.check_watermarks(["static/img"])
        self.assertTrue(ok2)
        self.assertEqual(missing2, [])

    def test_dry_run_changes_nothing(self):
        before = self.img.read_bytes()
        res = w.process(["static/img"], apply=False, dry_run=True)
        self.assertEqual(len(res["would"]), 1)
        self.assertEqual(self.img.read_bytes(), before)
        self.assertFalse(w.MANIFEST_PATH.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
