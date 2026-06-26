"""Tests for the native SEOMONEY comment system + comment-auth role boundaries."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("VIPZONE_DB_PATH", "")
os.environ.setdefault("GSC_CLIENT_ID", "test-id.apps.googleusercontent.com")
os.environ.setdefault("GSC_CLIENT_SECRET", "test-secret")
# Admin allowlist used by is_admin / Google admin gate.
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("GOOGLE_ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("AUTH_PROVIDER", "dual")
os.environ.setdefault("COMMENTS_ENABLED", "true")
os.environ.setdefault("COMMENTS_DEFAULT_STATUS", "pending")
os.environ.setdefault("COMMENTS_MAX_LENGTH", "1500")
os.environ.setdefault("COMMENTS_RATE_MAX", "3")
os.environ.setdefault("COMMENTS_RATE_WINDOW", "60")

from fastapi.testclient import TestClient  # noqa: E402

import main as main_mod  # noqa: E402
from db import VipzoneDB  # noqa: E402
from main import app, get_db  # noqa: E402

PAGE = "/posting/test-bai-viet/"


def _auth(sid: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + sid}


class CommentSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "vipzone-test.db"
        # main.DB_PATH is captured at import → inject a fresh per-test DB directly
        # so each test is fully isolated (don't rely on the env var being re-read).
        main_mod._db = VipzoneDB(self.db_path)
        self.client = TestClient(app)
        db = get_db()
        # A public commenter session (any Google account, NOT an admin).
        self.commenter_sid = db.create_cms_session(
            {
                "provider": "google",
                "email": "visitor@gmail.com",
                "sub": "google-sub-123",
                "username": "",  # commenters carry no username
                "name": "Khách Ghé Thăm",
                "avatar": "https://example.com/a.png",
                "is_super": False,
                "is_superadmin": False,
                "account_type": "commenter",
            },
            3600,
        )
        # An admin Google session.
        self.admin_sid = db.create_cms_session(
            {
                "provider": "google",
                "email": "admin@example.com",
                "sub": "google-admin-1",
                "username": "admin",
                "name": "Quản Trị",
                "avatar": "",
                "is_super": True,
                "is_superadmin": True,
                "account_type": "admin",
            },
            3600,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ---- 1. anonymous can read ----
    def test_anonymous_can_read(self) -> None:
        res = self.client.get("/comments", params={"path": PAGE})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["enabled"])
        self.assertEqual(body["comments"], [])

    # ---- 2. anonymous submit -> 401 ----
    def test_anonymous_submit_401(self) -> None:
        res = self.client.post("/comments", json={"path": PAGE, "body": "Xin chào"})
        self.assertEqual(res.status_code, 401)

    # ---- 3. commenter can submit (pending) ----
    def test_commenter_submit_pending(self) -> None:
        res = self.client.post(
            "/comments",
            json={"path": PAGE, "body": "Bài viết rất hay!"},
            headers=_auth(self.commenter_sid),
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertTrue(body["pending"])
        self.assertEqual(body["status"], "pending")
        self.assertIn("chờ duyệt", body["message"])
        # Not visible publicly until approved.
        pub = self.client.get("/comments", params={"path": PAGE}).json()
        self.assertEqual(pub["count"], 0)

    # ---- 4. commenter blocked from admin + CMS ----
    def test_commenter_cannot_moderate(self) -> None:
        res = self.client.get("/admin/comments", headers=_auth(self.commenter_sid))
        self.assertEqual(res.status_code, 403)

    def test_commenter_cannot_save_post(self) -> None:
        # No GitHub access_token in a Google session → CMS save is rejected.
        res = self.client.post(
            "/cms/save-post",
            json={"slug": "hack", "content": "x"},
            headers=_auth(self.commenter_sid),
        )
        self.assertEqual(res.status_code, 401)

    def test_commenter_cannot_reach_personal_admin(self) -> None:
        res = self.client.get("/calendar/events", headers=_auth(self.commenter_sid))
        self.assertEqual(res.status_code, 403)

    # ---- 5. admin can moderate + approve becomes public ----
    def test_admin_moderation_flow(self) -> None:
        self.client.post(
            "/comments",
            json={"path": PAGE, "body": "Chờ duyệt nhé"},
            headers=_auth(self.commenter_sid),
        )
        listing = self.client.get("/admin/comments", headers=_auth(self.admin_sid))
        self.assertEqual(listing.status_code, 200)
        rows = listing.json()["comments"]
        self.assertEqual(len(rows), 1)
        cid = rows[0]["id"]
        # approve
        ap = self.client.post(
            f"/admin/comments/{cid}/approve", headers=_auth(self.admin_sid)
        )
        self.assertEqual(ap.status_code, 200)
        pub = self.client.get("/comments", params={"path": PAGE}).json()
        self.assertEqual(pub["count"], 1)
        self.assertEqual(pub["comments"][0]["body"], "Chờ duyệt nhé")
        # hide
        self.client.post(f"/admin/comments/{cid}/hide", headers=_auth(self.admin_sid))
        self.assertEqual(self.client.get("/comments", params={"path": PAGE}).json()["count"], 0)
        # delete
        dele = self.client.delete(f"/admin/comments/{cid}", headers=_auth(self.admin_sid))
        self.assertEqual(dele.status_code, 200)

    def test_admin_comment_auto_approved(self) -> None:
        res = self.client.post(
            "/comments",
            json={"path": PAGE, "body": "Bình luận của admin"},
            headers=_auth(self.admin_sid),
        )
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.json()["pending"])
        pub = self.client.get("/comments", params={"path": PAGE}).json()
        self.assertEqual(pub["count"], 1)

    # ---- 7. sanitisation ----
    def test_sanitisation_strips_html(self) -> None:
        payload = 'Hello <script>alert(1)</script> <b>x</b> world'
        self.client.post(
            "/comments",
            json={"path": PAGE, "body": payload},
            headers=_auth(self.admin_sid),  # auto-approve so we can read it back
        )
        pub = self.client.get("/comments", params={"path": PAGE}).json()
        body = pub["comments"][0]["body"]
        self.assertNotIn("<", body)
        self.assertNotIn(">", body)
        self.assertIn("Hello", body)

    def test_empty_body_rejected(self) -> None:
        res = self.client.post(
            "/comments",
            json={"path": PAGE, "body": "   "},
            headers=_auth(self.commenter_sid),
        )
        self.assertEqual(res.status_code, 400)

    def test_too_long_rejected(self) -> None:
        res = self.client.post(
            "/comments",
            json={"path": PAGE, "body": "a" * 5000},
            headers=_auth(self.commenter_sid),
        )
        self.assertEqual(res.status_code, 400)

    # ---- 8. no raw email exposed ----
    def test_no_raw_email_exposed(self) -> None:
        self.client.post(
            "/comments",
            json={"path": PAGE, "body": "kiểm tra email"},
            headers=_auth(self.admin_sid),
        )
        pub_raw = self.client.get("/comments", params={"path": PAGE}).text
        self.assertNotIn("admin@example.com", pub_raw)
        adm_raw = self.client.get("/admin/comments", headers=_auth(self.admin_sid)).text
        self.assertNotIn("admin@example.com", adm_raw)
        # admin projection carries only a hash
        adm = self.client.get("/admin/comments", headers=_auth(self.admin_sid)).json()
        self.assertIn("author_email_hash", adm["comments"][0])
        self.assertNotIn("email", adm["comments"][0])

    # ---- 9. /auth/me normalized roles ----
    def test_auth_me_roles(self) -> None:
        commenter = self.client.get("/auth/me", headers=_auth(self.commenter_sid)).json()
        self.assertEqual(commenter["comment_role"], "commenter")
        self.assertEqual(commenter["account_type"], "commenter")
        self.assertFalse(commenter["is_admin"])
        self.assertEqual(commenter["provider"], "google")

        admin = self.client.get("/auth/me", headers=_auth(self.admin_sid)).json()
        self.assertEqual(admin["comment_role"], "admin")
        self.assertTrue(admin["is_admin"])

    def test_auth_me_anonymous_401(self) -> None:
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    # ---- 10. rate limit ----
    def test_rate_limit(self) -> None:
        codes = []
        for i in range(5):
            r = self.client.post(
                "/comments",
                json={"path": PAGE, "body": f"spam {i}"},
                headers=_auth(self.commenter_sid),
            )
            codes.append(r.status_code)
        self.assertIn(429, codes)

    # ---- path normalisation: GET and POST agree ----
    def test_path_normalisation(self) -> None:
        self.client.post(
            "/comments",
            json={"path": "/zola" + PAGE, "body": "normalize test"},
            headers=_auth(self.admin_sid),
        )
        pub = self.client.get("/comments", params={"path": PAGE}).json()
        self.assertEqual(pub["count"], 1)

    # ---- comment-auth start route exists ----
    def test_comment_start_route(self) -> None:
        res = self.client.get(
            "/auth/comment/start", params={"return_to": PAGE}, follow_redirects=False
        )
        # 307 redirect (to Google, or to an error page if Google unconfigured).
        self.assertIn(res.status_code, (302, 307))

    # ---- 9 (dual). GitHub admin fallback still works ----
    def test_github_admin_session_still_admin(self) -> None:
        gh_sid = get_db().create_cms_session(
            {
                "provider": "github",
                "email": "admin@example.com",
                "username": "banhang-chogao",
                "name": "GH Admin",
                "is_super": True,
                "is_superadmin": True,
            },
            3600,
        )
        res = self.client.get("/admin/comments", headers=_auth(gh_sid))
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
