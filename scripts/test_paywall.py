"""Tests for Paywall backend, auth, and build strip script."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.paywall_auth import (  # noqa: E402
    generate_approve_code,
    hash_code,
    hash_email,
    is_expired,
    session_expires,
    token_hash,
    verify_admin_token,
)
from backend.paywall_db import PaywallDB  # noqa: E402


class PaywallAuthTest(unittest.TestCase):
    def test_hash_code_deterministic(self) -> None:
        h1 = hash_code("ABCD1234")
        h2 = hash_code("abcd1234")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_hash_email_truncated(self) -> None:
        h = hash_email("Reader@Example.com")
        self.assertEqual(len(h), 16)

    def test_generate_approve_code(self) -> None:
        code = generate_approve_code(12)
        self.assertEqual(len(code), 12)
        self.assertTrue(code.isalnum())

    def test_admin_token_verify(self) -> None:
        os.environ["PAYWALL_ADMIN_TOKEN"] = "secret-token"
        self.assertTrue(verify_admin_token("Bearer secret-token"))
        self.assertFalse(verify_admin_token("Bearer wrong"))
        self.assertFalse(verify_admin_token(None))

    def test_is_expired(self) -> None:
        self.assertTrue(is_expired("2000-01-01T00:00:00Z"))
        self.assertFalse(is_expired(session_expires(hours=24)))


class PaywallDBTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.db = PaywallDB(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_request_and_list(self) -> None:
        rid = self.db.insert_request(
            {
                "post_id": "premium-fintech-001",
                "post_title": "Demo",
                "post_url": "/posting/demo/",
                "email": "reader@example.com",
                "payment_link": "https://me.momo.vn/test",
                "payment_note": "CK 2030",
            }
        )
        rows = self.db.list_requests(status="pending")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["request_id"], rid)
        self.assertEqual(rows[0]["email"], "reader@example.com")

    def test_code_unlock_flow(self) -> None:
        plain = "TESTCODE1234"
        cid = self.db.insert_code(
            {
                "approve_code_hash": hash_code(plain),
                "email": "reader@example.com",
                "post_id": "premium-fintech-001",
                "post_url": "/posting/demo/",
                "expires_at": session_expires(hours=48),
                "max_usage": 3,
            }
        )
        rows = self.db.get_code_for_unlock("reader@example.com", "premium-fintech-001")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code_id"], cid)

        self.db.increment_code_usage(cid)
        updated = self.db.get_code_by_id(cid)
        assert updated
        self.assertEqual(updated["usage_count"], 1)

    def test_session_insert(self) -> None:
        tok = "session-token-xyz"
        self.db.insert_session(
            {
                "token_hash": token_hash(tok),
                "email": "reader@example.com",
                "post_id": "premium-fintech-001",
                "trace_code": "AABBCCDD",
                "reader_email_hash": hash_email("reader@example.com"),
                "expires_at": session_expires(hours=4),
            }
        )
        sess = self.db.get_session(token_hash(tok))
        self.assertIsNotNone(sess)
        assert sess
        self.assertEqual(sess["post_id"], "premium-fintech-001")


class PaywallStripTest(unittest.TestCase):
    def test_teaser_truncation_logic(self) -> None:
        body = " ".join(["word"] * 250)
        teaser_words = 50
        tokens = body.split()
        teaser = " ".join(tokens[:teaser_words]) + "\n\n…"
        self.assertLess(len(teaser), len(body))
        self.assertIn("…", teaser)

    def test_is_premium_by_category(self) -> None:
        from scripts.paywall_prepare_build import (  # noqa: PLC0415
            DEFAULT_PREMIUM_PRICE,
            PREMIUM_CATEGORY,
            _inject_premium_flags,
            _is_premium,
        )

        self.assertEqual(PREMIUM_CATEGORY, "premium")
        self.assertEqual(DEFAULT_PREMIUM_PRICE, 100_000)
        self.assertTrue(
            _is_premium({"taxonomies": {"categories": ["Tất cả", "premium"]}})
        )
        self.assertFalse(_is_premium({"taxonomies": {"categories": ["Công nghệ"]}}))
        self.assertTrue(_is_premium({"extra": {"premium": True}}))

    def test_inject_premium_flags(self) -> None:
        from scripts.paywall_prepare_build import _inject_premium_flags  # noqa: PLC0415

        fm = '+++\n[taxonomies]\ncategories = ["premium"]\n\n[extra]\npremium_post_id = "x"\n+++'
        meta = {"taxonomies": {"categories": ["premium"]}, "extra": {}}
        out = _inject_premium_flags(fm, meta)
        self.assertIn("premium = true", out)
        self.assertIn("price = 100000", out)

    def test_strip_preserves_existing_full_private(self) -> None:
        """Regression: strip must NOT clobber an existing full private_content
        body with the teaser when content/ has no <!-- more --> marker."""
        import scripts.paywall_prepare_build as pb  # noqa: PLC0415

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        content = root / "content"
        private = root / "private_content"
        (content / "posting").mkdir(parents=True)
        private.mkdir(parents=True)

        # content/ holds ONLY a teaser (no <!-- more --> marker).
        teaser = "Teaser mở đầu cho bài premium, chỉ là phần xem trước ngắn."
        post = content / "posting" / "lesson.md"
        post.write_text(
            '+++\ntitle = "L"\n[taxonomies]\ncategories = ["premium"]\n'
            '[extra]\npremium = true\npremium_post_id = "premium-x"\n+++\n\n'
            + teaser,
            encoding="utf-8",
        )
        # private_content/ already holds the FULL body (source of truth).
        full = "# Bài đầy đủ\n\n" + " ".join(["nội"] * 500)
        priv = private / "premium-x.md"
        priv.write_text(full, encoding="utf-8")

        saved = (pb.ROOT, pb.CONTENT, pb.PRIVATE, pb.BACKUP)
        pb.ROOT, pb.CONTENT, pb.PRIVATE, pb.BACKUP = (
            root, content, private, root / "backup.json")
        try:
            pb.strip_premium()
        finally:
            pb.ROOT, pb.CONTENT, pb.PRIVATE, pb.BACKUP = saved

        # Full private body must be untouched; teaser must NOT have overwritten it.
        self.assertEqual(priv.read_text(encoding="utf-8"), full)
        self.assertNotIn("xem trước", priv.read_text(encoding="utf-8"))
        # content/ now serves only the teaser (no leaked full body).
        self.assertNotIn("Bài đầy đủ", post.read_text(encoding="utf-8"))

    def test_strip_splits_on_more_marker(self) -> None:
        """When content/ has a <!-- more --> marker, the part after it becomes
        the private full body."""
        import scripts.paywall_prepare_build as pb  # noqa: PLC0415

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        content = root / "content"
        private = root / "private_content"
        (content / "posting").mkdir(parents=True)
        private.mkdir(parents=True)

        post = content / "posting" / "lesson.md"
        post.write_text(
            '+++\ntitle = "L"\n[taxonomies]\ncategories = ["premium"]\n'
            '[extra]\npremium = true\npremium_post_id = "premium-y"\n+++\n\n'
            "Teaser công khai.\n\n<!-- more -->\n\nPHẦN TRẢ PHÍ bí mật.",
            encoding="utf-8",
        )

        saved = (pb.ROOT, pb.CONTENT, pb.PRIVATE, pb.BACKUP)
        pb.ROOT, pb.CONTENT, pb.PRIVATE, pb.BACKUP = (
            root, content, private, root / "backup.json")
        try:
            pb.strip_premium()
        finally:
            pb.ROOT, pb.CONTENT, pb.PRIVATE, pb.BACKUP = saved

        priv = (private / "premium-y.md").read_text(encoding="utf-8")
        self.assertIn("PHẦN TRẢ PHÍ", priv)
        self.assertNotIn("PHẦN TRẢ PHÍ", post.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()