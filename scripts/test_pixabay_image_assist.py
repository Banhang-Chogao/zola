#!/usr/bin/env python3
"""Unit tests for scripts/pixabay_image_assist.py (no-API Pixabay image-assist).

Hợp đồng được kiểm:
  - crawl bị chặn (robots disallow / fetch lỗi) → fallback "blocked", không raise
  - không có ứng viên → fallback "no_candidates", không raise
  - metadata bắt buộc PHẢI đủ + verify trước khi dùng ảnh (confirm refuse nếu thiếu)
  - ảnh đã xác nhận → file tồn tại sau khi confirm (path under third-party + sidecar)
  - ảnh Pixabay (third-party) KHÔNG bị watermark (watermark policy bỏ qua)
  - legal/AdSense guard: query/ứng viên unsafe bị loại; brand được đánh dấu review
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixabay_image_assist as pia  # noqa: E402
import watermark_blog_images as wm  # noqa: E402


def _search_html(*photos):
    """Dựng HTML giả của 1 trang search Pixabay với các (id, slug, alt, src, user)."""
    blocks = []
    for pid, slug, alt, src, user in photos:
        blocks.append(
            f'<div class="cell">'
            f'<a href="/photos/{slug}-{pid}/">'
            f'<img alt="{alt}" src="{src}" />'
            f'</a>'
            f'<a href="/users/{user}-99{pid}/">{user}</a>'
            f'</div>'
        )
    return "<html><body>" + "".join(blocks) + "</body></html>"


GOOD_HTML = _search_html(
    (101, "mountain-lake", "Mountain lake at sunrise", "https://cdn.pixabay.com/photo/a_640.jpg", "alice"),
    (102, "forest-path", "Green forest path", "https://cdn.pixabay.com/photo/b_640.jpg", "bob"),
    (103, "city-skyline", "City skyline panorama", "https://cdn.pixabay.com/photo/c_640.jpg", "carol"),
)


class QueryTests(unittest.TestCase):
    def test_build_queries_dedupe_and_priority(self):
        q = pia.build_search_queries(
            title="SEO Onpage là gì", keyword="seo onpage",
            category="Công nghệ", tags=["seo", "onpage"])
        self.assertTrue(q)
        self.assertEqual(q[0], "seo onpage")  # keyword ưu tiên
        # "Tất cả" bị bỏ
        q2 = pia.build_search_queries(title="x y", category="Tất cả")
        self.assertNotIn("Tất cả", q2)

    def test_unsafe_query_dropped(self):
        ok, _ = pia.is_query_safe("nude model")
        self.assertFalse(ok)
        q = pia.build_search_queries(keyword="nude photo", title="casino jackpot win")
        self.assertEqual(q, [])  # mọi query unsafe → rỗng


class DiscoveryTests(unittest.TestCase):
    def test_ok_returns_3_to_5_landscape_candidates(self):
        res = pia.discover_candidates(
            title="Phong cảnh thiên nhiên", keyword="nature landscape",
            html_by_query={"nature landscape": GOOD_HTML,
                           "Phong cảnh thiên nhiên": GOOD_HTML},
        )
        self.assertEqual(res["status"], "ok")
        self.assertGreaterEqual(len(res["candidates"]), 3)
        self.assertLessEqual(len(res["candidates"]), 5)
        c0 = res["candidates"][0]
        for key in ("title", "alt", "author", "source_url", "preview_url",
                    "license_note", "orientation", "crawled_at"):
            self.assertIn(key, c0)
        self.assertEqual(c0["orientation"], "landscape")
        self.assertTrue(c0["source_url"].startswith("https://pixabay.com/photos/"))

    def test_crawl_blocked_fallback(self):
        # robots disallow → status blocked, không raise, không ứng viên
        res = pia.discover_candidates(
            keyword="nature", robots_check=lambda u: False)
        self.assertEqual(res["status"], "blocked")
        self.assertEqual(res["candidates"], [])

    def test_fetch_error_is_blocked_not_crash(self):
        def boom(url):
            raise RuntimeError("network down")
        res = pia.discover_candidates(
            keyword="nature", robots_check=lambda u: True, fetcher=boom)
        self.assertEqual(res["status"], "blocked")
        self.assertEqual(res["candidates"], [])

    def test_no_candidate_fallback(self):
        res = pia.discover_candidates(
            keyword="nature", html_by_query={"nature": "<html></html>"})
        self.assertEqual(res["status"], "no_candidates")
        self.assertEqual(res["candidates"], [])

    def test_unsafe_candidate_excluded(self):
        html = _search_html(
            (201, "weapon-gun", "gun and weapon closeup", "https://cdn.pixabay.com/photo/x_640.jpg", "dan"),
            (202, "calm-beach", "calm beach landscape", "https://cdn.pixabay.com/photo/y_640.jpg", "eve"),
        )
        res = pia.discover_candidates(keyword="beach", html_by_query={"beach": html})
        ids = [c["id"] for c in res["candidates"]]
        self.assertIn("202", ids)
        self.assertNotIn("201", ids)  # ảnh unsafe bị loại khỏi gợi ý

    def test_brand_candidate_flagged(self):
        html = _search_html(
            (301, "apple-logo", "Apple logo on wall", "https://cdn.pixabay.com/photo/z_640.jpg", "frank"),
        )
        res = pia.discover_candidates(keyword="tech", html_by_query={"tech": html})
        self.assertEqual(len(res["candidates"]), 1)
        self.assertTrue(res["candidates"][0]["needs_brand_review"])


class MetadataTests(unittest.TestCase):
    def _cand(self):
        return {
            "id": "101", "title": "Mountain lake", "alt": "Mountain lake",
            "author": "alice", "source_url": "https://pixabay.com/photos/mountain-lake-101/",
            "preview_url": "https://cdn.pixabay.com/photo/a_640.jpg",
            "license_note": pia.LICENSE_NOTE, "crawled_at": "2026-06-22T00:00:00Z",
        }

    def test_metadata_required_fields_present(self):
        meta = pia.build_metadata(self._cand(), verified_manually=True,
                                  commercial_use_checked=True)
        ok, missing = pia.validate_metadata(meta)
        self.assertTrue(ok, missing)
        for f in pia.MANDATORY_META_FIELDS:
            self.assertIn(f, meta)

    def test_metadata_required_before_use(self):
        # chưa verify → invalid
        meta = pia.build_metadata(self._cand(), verified_manually=False,
                                  commercial_use_checked=True)
        ok, missing = pia.validate_metadata(meta)
        self.assertFalse(ok)
        self.assertTrue(any("verified_manually" in m for m in missing))

    def test_frontmatter_injection(self):
        meta = pia.build_metadata(self._cand(), verified_manually=True,
                                  commercial_use_checked=True)
        text = '+++\ntitle = "x"\n\n[extra]\nseo_keyword = "k"\n+++\nbody\n'
        out = pia.inject_extra_fields(
            text, pia.frontmatter_lines(meta, thumbnail_rel="/img/third-party/pixabay/x/cover.webp"))
        self.assertIn('image_source = "Pixabay"', out)
        self.assertIn('image_verified_manually = true', out)
        self.assertIn('thumbnail = "/img/third-party/pixabay/x/cover.webp"', out)
        self.assertIn("body", out)


class ConfirmDownloadTests(unittest.TestCase):
    def _cand(self):
        return {
            "id": "101", "title": "Mountain lake", "alt": "Mountain lake",
            "author": "alice", "source_url": "https://pixabay.com/photos/mountain-lake-101/",
            "preview_url": "https://cdn.pixabay.com/photo/a_640.jpg",
            "license_note": pia.LICENSE_NOTE, "crawled_at": "2026-06-22T00:00:00Z",
            "adsense_unsafe": False,
        }

    def test_refused_without_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            res = pia.confirm_download(
                candidate=self._cand(), slug="post",
                verified_manually=False, commercial_use_checked=True,
                dest_root=Path(d) / "static/img/third-party/pixabay",
                fetcher=lambda u: b"IMGDATA", to_webp=False)
        self.assertEqual(res["status"], "refused")
        self.assertIsNone(res["image_path"])

    def test_confirmed_image_path_exists_after_build(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "static/img/third-party/pixabay"
            res = pia.confirm_download(
                candidate=self._cand(), slug="post",
                verified_manually=True, commercial_use_checked=True,
                dest_root=dest, fetcher=lambda u: b"\xff\xd8FAKEJPEG", to_webp=False)
            self.assertEqual(res["status"], "downloaded", res.get("errors"))
            img = Path(res["image_path"])
            sidecar = Path(res["sidecar_path"])
            self.assertTrue(img.exists())
            self.assertTrue(sidecar.exists())
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            ok, missing = pia.validate_metadata(meta)
            self.assertTrue(ok, missing)
            self.assertEqual(meta["image_source"], "Pixabay")
            self.assertTrue(meta["image_verified_manually"])

    def test_refuse_save_into_owned_folder(self):
        # ép dest vào owned root → assert_third_party raise → confirm trả lỗi, không ghi
        with self.assertRaises(ValueError):
            pia.assert_third_party(pia.REPO / "static/img/posting/x/cover.webp")
        with self.assertRaises(ValueError):
            pia.assert_third_party(pia.REPO / "static/img/owned/x/cover.webp")
        # third-party path hợp lệ → không raise
        pia.assert_third_party(pia.REPO / "static/img/third-party/pixabay/x/cover.webp")


class WatermarkExclusionTests(unittest.TestCase):
    def test_third_party_pixabay_not_watermarked(self):
        # Ảnh trong third-party/pixabay KHÔNG eligible để watermark (đúng chính sách).
        p = pia.REPO / "static/img/third-party/pixabay/post/cover.webp"
        self.assertFalse(wm.is_eligible(p))
        # Đối chứng: ảnh owned thì eligible.
        owned = pia.REPO / "static/img/posting/post/cover.webp"
        self.assertTrue(wm.is_eligible(owned))


class SuggestionsIOTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        slug = "__pia_test_tmp__"
        res = {"status": "ok", "candidates": [], "queries": ["x"], "note": "n"}
        path = pia.save_suggestions(slug, res)
        try:
            loaded = pia.load_suggestions(slug)
            self.assertEqual(loaded["status"], "ok")
            self.assertEqual(loaded["slug"], slug)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
