#!/usr/bin/env python3
"""Tests cho scripts/build_owned_covers.py — owned-image fallback SEOMONEY."""
import unittest

import build_owned_covers as boc


class TestOwnedCovers(unittest.TestCase):
    def test_explicit_image_priority(self):
        # extra.image thắng cover/thumbnail
        self.assertEqual(boc.explicit_image({"image": "/uploads/a.webp"}), "/uploads/a.webp")
        self.assertEqual(boc.explicit_image({"cover": "/uploads/b.webp"}), "/uploads/b.webp")
        # thumbnail thật được nhận
        self.assertEqual(
            boc.explicit_image({"thumbnail": "/img/covers/x.svg"}), "/img/covers/x.svg"
        )
        # placeholder chung KHÔNG tính là ảnh thật
        self.assertIsNone(
            boc.explicit_image({"thumbnail": "https://seomoney.org/img/placeholder/placeholder.svg"})
        )
        self.assertIsNone(boc.explicit_image({}))

    def test_first_local_upload_only_owned_path(self):
        body = "text ![alt](/uploads/pic.webp) more"
        self.assertEqual(boc.first_local_upload(body), "/uploads/pic.webp")
        # ảnh ngoài KHÔNG được chọn
        self.assertIsNone(boc.first_local_upload("![x](https://picsum.photos/1/1)"))
        # ảnh local KHÔNG nằm dưới uploads → bỏ qua
        self.assertIsNone(boc.first_local_upload("![x](/img/random.webp)"))
        # html img
        self.assertEqual(
            boc.first_local_upload('<img src="/img/uploads/h.webp">'), "/img/uploads/h.webp"
        )

    def test_cover_svg_deterministic_and_branded(self):
        a = boc.build_cover_svg("my-slug", "Tiêu đề bài viết SEOMONEY", "Công nghệ")
        b = boc.build_cover_svg("my-slug", "Tiêu đề bài viết SEOMONEY", "Công nghệ")
        self.assertEqual(a, b)  # deterministic
        self.assertIn("SEOMONEY", a)  # wordmark
        self.assertIn("&#9672;", a)  # S-DNA mark ◈
        self.assertIn("<svg", a)
        # khác slug → khác output
        self.assertNotEqual(a, boc.build_cover_svg("other", "Tiêu đề", "Công nghệ"))

    def test_no_external_image_hosts_in_output(self):
        svg = boc.build_cover_svg("s", "T", "Ngân hàng")
        # KHÔNG hotlink host ảnh ngoài (xmlns w3.org namespace KHÔNG tính là ảnh).
        for bad in ("pixabay", "unsplash", "pexels", "picsum.photos"):
            self.assertNotIn(bad, svg)

    def test_xml_escaping_in_title(self):
        svg = boc.build_cover_svg("s", 'A & B <script> "q"', None)
        self.assertNotIn("<script>", svg)
        self.assertIn("&amp;", svg)

    def test_category_topic_mapping(self):
        self.assertEqual(boc._topic_for("Công nghệ"), "tech")
        self.assertEqual(boc._topic_for("Ngân hàng"), "finance")
        self.assertEqual(boc._topic_for("Khoa học"), "ai")
        self.assertEqual(boc._topic_for("không-có"), "default")
        self.assertEqual(boc._topic_for(None), "default")

    def test_alt_text_descriptive(self):
        alt = boc.alt_for("Cách mở tài khoản", "Ngân hàng")
        self.assertIn("Cách mở tài khoản", alt)
        self.assertIn("Ngân hàng", alt)
        self.assertIn("SEOMONEY", alt)


if __name__ == "__main__":
    unittest.main()
