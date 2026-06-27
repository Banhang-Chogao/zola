#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests cho scripts/audit_category_mapping.py.

Chạy: python3 -m unittest scripts.test_audit_category_mapping -v
"""

import os
import tempfile
import unittest

from scripts import audit_category_mapping as acm


class TestStripAccents(unittest.TestCase):
    def test_vietnamese(self):
        self.assertEqual(acm.strip_accents("Ngân hàng"), "ngan hang")
        self.assertEqual(acm.strip_accents("Đời sống"), "doi song")
        self.assertEqual(acm.strip_accents("Báo chí"), "bao chi")


class TestClassify(unittest.TestCase):
    def test_banking(self):
        r = acm.classify(
            "Mở thẻ tín dụng Liobank online nhanh",
            "Liobank là ngân hàng số, mở thẻ bằng eKYC, hoàn tiền khi chi tiêu qua app banking.")
        self.assertEqual(r.category, "Ngân hàng")
        self.assertGreaterEqual(r.confidence, 0.65)

    def test_travel(self):
        r = acm.classify(
            "Bí kíp xin visa Hàn Quốc 5 năm",
            "Kinh nghiệm xin visa du lịch, chuẩn bị hồ sơ, sân bay Incheon và khách sạn.")
        self.assertEqual(r.category, "Du lịch")
        self.assertGreaterEqual(r.confidence, 0.65)

    def test_sport(self):
        r = acm.classify(
            "Lịch thi đấu World Cup 2026: Messi hat-trick",
            "Argentina thắng mở màn, Messi lập hat-trick, bóng đá thế giới sôi động.")
        self.assertEqual(r.category, "Thể thao")
        self.assertGreaterEqual(r.confidence, 0.8)

    def test_never_returns_source_type(self):
        # Dù nội dung nói về 'báo chí' chung chung vẫn không trả 'Báo chí'.
        r = acm.classify("Tin tức ngân hàng", "ngân hàng lãi suất tài khoản")
        self.assertNotEqual(r.category, "Báo chí")
        self.assertNotIn("Báo chí", acm.CATEGORY_KEYWORDS)

    def test_fallback_on_empty(self):
        r = acm.classify("abcxyz", "qwerty lorem ipsum")
        self.assertEqual(r.category, acm.FALLBACK_CATEGORY)
        self.assertLess(r.confidence, acm.CONFIDENCE_THRESHOLD)

    def test_never_auto_premium(self):
        r = acm.classify("Bài premium đặc biệt", "nội dung premium trả phí")
        self.assertNotEqual(acm.strip_accents(r.category), "premium")


class TestArrayParsing(unittest.TestCase):
    def test_roundtrip(self):
        cats = ["Tất cả", "Ngân hàng"]
        raw = acm.build_category_array(cats)
        self.assertEqual(acm.parse_category_array(raw), cats)


def _write_tmp(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class TestProcessFile(unittest.TestCase):
    def _baochi_path(self, content: str) -> str:
        # Đặt trong thư mục con 'baochi' để kích hoạt source-meta.
        d = tempfile.mkdtemp()
        sub = os.path.join(d, "baochi")
        os.makedirs(sub)
        path = os.path.join(sub, "sample.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_drop_baochi_keep_real(self):
        content = (
            '+++\n'
            'title = "Mở thẻ Liobank"\n'
            '[taxonomies]\n'
            'categories = ["Tất cả", "Báo chí", "Ngân hàng"]\n'
            'tags = ["liobank"]\n'
            '[extra]\n'
            'seo_keyword = "liobank"\n'
            '+++\n'
            'Nội dung ngân hàng số liobank.\n'
        )
        path = self._baochi_path(content)
        rec = acm.process_file(path, apply=True)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.new_cats, ["Tất cả", "Ngân hàng"])
        with open(path, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn('categories = ["Tất cả", "Ngân hàng"]', txt)
        self.assertNotIn("Báo chí", txt)
        self.assertIn('source = "bb"', txt)
        self.assertIn('content_origin = "baochi"', txt)

    def test_infer_when_no_real_cat(self):
        content = (
            '+++\n'
            'title = "Lịch thi đấu World Cup 2026 Messi hat-trick"\n'
            '[taxonomies]\n'
            'categories = ["Tất cả", "Báo chí"]\n'
            'tags = ["world cup"]\n'
            '[extra]\n'
            '+++\n'
            'Argentina thắng, Messi lập hat-trick, bóng đá thế giới.\n'
        )
        path = self._baochi_path(content)
        rec = acm.process_file(path, apply=True)
        self.assertEqual(rec.new_cats, ["Tất cả", "Thể thao"])

    def test_preserve_premium(self):
        content = (
            '+++\n'
            'title = "Bài ngân hàng premium"\n'
            '[taxonomies]\n'
            'categories = ["Tất cả", "Báo chí", "Ngân hàng", "premium"]\n'
            '[extra]\n'
            '+++\n'
            'Nội dung ngân hàng.\n'
        )
        path = self._baochi_path(content)
        rec = acm.process_file(path, apply=True)
        self.assertEqual(rec.new_cats, ["Tất cả", "Ngân hàng", "premium"])
        self.assertIn("premium", rec.new_cats)

    def test_skip_file_without_baochi(self):
        content = (
            '+++\n'
            'title = "Bài thường"\n'
            '[taxonomies]\n'
            'categories = ["Tất cả", "Ngân hàng"]\n'
            '+++\n'
            'Nội dung.\n'
        )
        path = _write_tmp(content)
        rec = acm.process_file(path, apply=True)
        self.assertIsNone(rec)  # không có 'Báo chí' → bỏ qua

    def test_posting_no_source_meta(self):
        # File KHÔNG thuộc section baochi → không thêm source/content_origin.
        d = tempfile.mkdtemp()
        sub = os.path.join(d, "posting")
        os.makedirs(sub)
        path = os.path.join(sub, "wc.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(
                '+++\n'
                'title = "World Cup 2026 Messi"\n'
                '[taxonomies]\n'
                'categories = ["Tất cả", "Báo chí"]\n'
                '[extra]\n'
                '+++\n'
                'bóng đá world cup messi hat-trick.\n'
            )
        rec = acm.process_file(path, apply=True)
        self.assertEqual(rec.new_cats, ["Tất cả", "Thể thao"])
        with open(path, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertNotIn('content_origin', txt)


if __name__ == "__main__":
    unittest.main()
