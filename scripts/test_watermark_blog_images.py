#!/usr/bin/env python3
"""Unit tests for scripts/watermark_blog_images.py (owned-folder watermark policy).

Covers the contract:
  - deterministic 16-digit watermark generation
  - OWNED article images (posting/, owned/) are eligible
  - third-party brand/app/bank/card/logo images are excluded
  - unknown-source images (outside owned roots) are excluded BY DEFAULT
  - explicit include (watermark:true) / exclude (watermark:false) overrides
  - idempotent second run (no stacking); changed image reprocessed
  - .webp output stays watermarked; the --check gate fails before / passes after
"""

import json
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
        a = w.watermark_hash("static/img/posting/a/cover.webp", b"same")
        b = w.watermark_hash("static/img/posting/a/cover.webp", b"same")
        self.assertEqual(a, b)

    def test_hash_changes_with_bytes(self):
        self.assertNotEqual(
            w.watermark_hash("static/img/posting/a/cover.webp", b"one"),
            w.watermark_hash("static/img/posting/a/cover.webp", b"two"))

    def test_hash_changes_with_path(self):
        self.assertNotEqual(
            w.watermark_hash("static/img/posting/a/cover.webp", b"x"),
            w.watermark_hash("static/img/posting/b/cover.webp", b"x"))

    def test_text_format(self):
        t = w.watermark_text("static/img/posting/a/cover.webp", b"x")
        self.assertTrue(t.endswith("_seomoney.org"))
        self.assertEqual(len(t.split("_seomoney.org")[0]), 16)


class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name).resolve()
        self._orig = (w.REPO, w.DATA)
        w.REPO = self.repo
        w.DATA = self.repo / "data"  # no policy file present -> conservative defaults

    def tearDown(self):
        w.REPO, w.DATA = self._orig
        self._tmp.cleanup()

    def p(self, rel):
        return self.repo / rel

    def test_owned_article_images_eligible(self):
        self.assertTrue(w.is_eligible(self.p("static/img/posting/a/cover.webp")))
        self.assertTrue(w.is_eligible(self.p("static/img/posting/a/photo.jpg")))
        self.assertTrue(w.is_eligible(self.p("static/img/owned/original.webp")))
        self.assertTrue(w.is_eligible(self.p("static/img/owned/sub/pic.png")))

    def test_third_party_brand_app_card_excluded(self):
        self.assertFalse(w.is_eligible(self.p("static/img/covers/liobank-app-quan-ly-chi-tieu.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/covers/mo-the-techcombank-eco-digital-mien-phi.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/covers/post.og.webp")))

    def test_logos_icons_excluded_even_inside_owned(self):
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/techcombank-logo.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/app-icon.png")))
        self.assertFalse(w.is_eligible(self.p("static/img/owned/brand-mark.webp")))

    def test_unknown_source_excluded_by_default(self):
        self.assertFalse(w.is_eligible(self.p("static/img/random.webp")))
        self.assertFalse(w.is_eligible(self.p("static/img/screenshots/shot.png")))
        self.assertFalse(w.is_eligible(self.p("static/img/brand/seomoney-mark.webp")))

    def test_svg_gif_ico_never_eligible(self):
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/cover.svg")))
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/anim.gif")))
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/fav.ico")))

    def test_explicit_include_and_exclude_override(self):
        (self.repo / "data").mkdir(parents=True, exist_ok=True)
        (self.repo / "data/watermark-policy.json").write_text(json.dumps({
            "include": ["static/img/extra/owned-shot.webp"],
            "exclude": ["static/img/posting/a/third-party.webp"],
        }), encoding="utf-8")
        # opt-in an owned image that lives outside the owned roots
        self.assertTrue(w.is_eligible(self.p("static/img/extra/owned-shot.webp")))
        # opt-out a third-party image that happens to sit inside an owned root
        self.assertFalse(w.is_eligible(self.p("static/img/posting/a/third-party.webp")))


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

    def test_apply_watermarks_owned_and_marks(self):
        res = w.process(["static/img"], apply=True, dry_run=False)
        self.assertEqual(len(res["watermarked"]), 1)
        with Image.open(self.img) as im:
            self.assertEqual(im.size, (240, 160))  # dimensions preserved
        marker = w.read_marker(self.img)
        self.assertIsNotNone(marker)
        rel = w._rel(self.img)
        self.assertEqual(w.load_manifest()["images"][rel]["hash16"], marker)

    def test_second_run_idempotent(self):
        w.process(["static/img"], apply=True, dry_run=False)
        after_first = self.img.read_bytes()
        res2 = w.process(["static/img"], apply=True, dry_run=False)
        self.assertEqual(len(res2["watermarked"]), 0)
        self.assertEqual(self.img.read_bytes(), after_first)  # no stacking / rewrite

    def test_changed_image_reprocessed(self):
        w.process(["static/img"], apply=True, dry_run=False)
        rel = w._rel(self.img)
        first = w.load_manifest()["images"][rel]["hash16"]
        _make_webp(self.img, color=(10, 200, 60))  # genuinely new, un-watermarked image
        res = w.process(["static/img"], apply=True, dry_run=False)
        self.assertEqual(len(res["watermarked"]), 1)
        self.assertNotEqual(first, w.load_manifest()["images"][rel]["hash16"])

    def test_webp_output_remains_watermarked(self):
        w.process(["static/img"], apply=True, dry_run=False)
        self.assertIsNotNone(w.read_marker(self.img))
        ok, missing, stale = w.check_watermarks(["static/img"])
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_check_gate_fails_before_passes_after(self):
        ok, missing, _ = w.check_watermarks(["static/img"])
        self.assertFalse(ok)
        self.assertIn(w._rel(self.img), missing)
        w.process(["static/img"], apply=True, dry_run=False)
        ok2, missing2, _ = w.check_watermarks(["static/img"])
        self.assertTrue(ok2)
        self.assertEqual(missing2, [])

    def test_third_party_image_not_watermarked_and_pruned(self):
        # A bank cover outside owned roots must never be watermarked, and a stale
        # manifest entry for it must be pruned on the next apply.
        cover = self.repo / "static/img/covers/techcombank-card.webp"
        _make_webp(cover, color=(200, 30, 30))
        before = cover.read_bytes()
        # seed a stale manifest entry as if it had been watermarked before
        man = w.load_manifest()
        man["images"][w._rel(cover)] = {"hash16": "0", "watermark_text": "0_seomoney.org",
                                        "source_sha256": "x", "watermarked_sha256": "y",
                                        "processed_at": "t"}
        w.save_manifest(man)
        w.process(["static/img"], apply=True, dry_run=False)
        self.assertEqual(cover.read_bytes(), before)              # untouched
        self.assertIsNone(w.read_marker(cover))                   # no watermark
        self.assertNotIn(w._rel(cover), w.load_manifest()["images"])  # pruned

    def test_dry_run_changes_nothing(self):
        before = self.img.read_bytes()
        res = w.process(["static/img"], apply=False, dry_run=True)
        self.assertEqual(len(res["would"]), 1)
        self.assertEqual(self.img.read_bytes(), before)
        self.assertFalse(w.MANIFEST_PATH.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
