"""VIPZone API unit tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("VIPZONE_DB_PATH", "")

from db import VipzoneDB  # noqa: E402
from main import app, get_db  # noqa: E402


class VipzoneApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "vipzone-test.db"
        os.environ["VIPZONE_DB_PATH"] = str(self.db_path)
        import main as main_mod

        main_mod._db = None
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_health(self) -> None:
        for path in ("/", "/health"):
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200)
                body = res.json()
                self.assertEqual(body["service"], "vipzone")
                self.assertEqual(body["status"], "ok")
                self.assertEqual(body["cms_auth"], "https://blog-vipzone-api.onrender.com")
                self.assertIn("deployed_sha", body)  # V16 split-brain marker
                self.assertIn("premium_content", body)

    def test_payment_request_and_redeem(self) -> None:
        pay = self.client.post(
            "/api/vipzone/payment-request",
            json={"email": "vip@example.com", "plan": "monthly", "payment_note": "test"},
        )
        self.assertEqual(pay.status_code, 200)
        self.assertEqual(pay.json()["status"], "pending")

        db = get_db()
        code = db.gen_code16()
        db.insert_code({"code_hash": db.hash_code(code), "plan": "monthly", "email": "vip@example.com"})

        redeem = self.client.post(
            "/api/vipzone/redeem",
            json={"code": code, "email": "vip@example.com"},
        )
        self.assertEqual(redeem.status_code, 200)
        self.assertEqual(redeem.json()["email"], "vip@example.com")

    def test_vipzone_me_requires_auth(self) -> None:
        res = self.client.get("/api/vipzone/me")
        self.assertEqual(res.status_code, 401)

    def test_vipzone_content_requires_auth(self) -> None:
        # V16 — premium content endpoint must reject unauthenticated callers.
        res = self.client.get("/api/vipzone/content/premium-han30-01")
        self.assertEqual(res.status_code, 401)

    def test_admin_endpoints_require_auth(self) -> None:
        for path, method in (
            ("/api/vipzone/admin/stats", "get"),
            ("/api/vipzone/admin/picker", "get"),
            ("/api/vipzone/admin/picker", "put"),
            ("/api/vipzone/admin/users/vip@example.com/activate", "post"),
        ):
            if method == "get":
                res = self.client.get(path)
            elif method == "put":
                res = self.client.put(path, json={"picks": []})
            else:
                res = self.client.post(path, json={"plan": "monthly"})
            self.assertEqual(res.status_code, 401, path)


    def test_auth_login_without_oauth_config(self) -> None:
        res = self.client.get("/auth/login")
        self.assertEqual(res.status_code, 503)

    def test_auth_login_redirects_when_configured(self) -> None:
        import cms_auth as auth_mod

        old_id, old_secret = auth_mod.GH_CLIENT_ID, auth_mod.GH_CLIENT_SECRET
        auth_mod.GH_CLIENT_ID = "test-client-id"
        auth_mod.GH_CLIENT_SECRET = "test-client-secret"
        try:
            res = self.client.get(
                "/auth/login",
                params={"return_to": "/tools/vipzone-admin/"},
                follow_redirects=False,
            )
            self.assertEqual(res.status_code, 307)
            loc = res.headers.get("location", "")
            self.assertIn("github.com/login/oauth/authorize", loc)
            self.assertIn("client_id=test-client-id", loc)
            self.assertIn("redirect_uri=", loc)
        finally:
            auth_mod.GH_CLIENT_ID, auth_mod.GH_CLIENT_SECRET = old_id, old_secret

    def test_auth_me_requires_token(self) -> None:
        res = self.client.get("/auth/me")
        self.assertEqual(res.status_code, 401)

    def test_auth_me_supervip_role(self) -> None:
        db = get_db()
        sid = db.create_cms_session(
            {
                "email": "tamsudev.com@gmail.com",
                "username": "banhang-chogao",
                "name": "Admin",
                "avatar": "",
            },
            3600,
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {sid}"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["role"], "supervip")
        self.assertTrue(body["is_super"])
        self.assertEqual(body["username"], "banhang-chogao")

    def test_auth_me_vip_role(self) -> None:
        db = get_db()
        db.upsert_vip("vip@example.com", "monthly", "2099-01-01T00:00:00Z")
        sid = db.create_cms_session(
            {"email": "vip@example.com", "username": "vipuser", "name": "VIP", "avatar": ""},
            3600,
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {sid}"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["role"], "vip")
        self.assertFalse(body["is_super"])
        self.assertEqual(body["vip_plan"], "monthly")

    def test_auth_logout_clears_session(self) -> None:
        db = get_db()
        sid = db.create_cms_session(
            {"email": "tamsudev.com@gmail.com", "username": "banhang-chogao", "name": "Admin"},
            3600,
        )
        res = self.client.post("/auth/logout", headers={"Authorization": f"Bearer {sid}"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])
        self.assertIsNone(db.get_cms_session(sid))

    def test_vipzone_me_shares_auth_session(self) -> None:
        db = get_db()
        sid = db.create_cms_session(
            {"email": "tamsudev.com@gmail.com", "username": "banhang-chogao", "name": "Admin"},
            3600,
        )
        headers = {"Authorization": f"Bearer {sid}"}
        auth_res = self.client.get("/auth/me", headers=headers)
        me_res = self.client.get("/api/vipzone/me", headers=headers)
        self.assertEqual(auth_res.status_code, 200)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(auth_res.json()["role"], me_res.json()["role"])
        self.assertEqual(me_res.json()["role"], "supervip")


class VipzoneDbTests(unittest.TestCase):
    def test_picker_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = VipzoneDB(Path(tmp) / "picker.db")
            picks = ["/tools/f-dashboard/", "/tools/l-dashboard/"]
            db.set_picker(picks)
            self.assertEqual(db.get_picker(), picks)

    def test_stats_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = VipzoneDB(Path(tmp) / "stats.db")
            stats = db.get_stats()
            self.assertEqual(stats["pending"], 0)
            self.assertEqual(stats["active_vips"], 0)

    def test_cms_session_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = VipzoneDB(Path(tmp) / "sess.db")
            sid = db.create_cms_session(
                {"email": "tamsudev.com@gmail.com", "username": "banhang-chogao", "name": "Admin"},
                3600,
            )
            got = db.get_cms_session(sid)
            self.assertEqual(got["email"], "tamsudev.com@gmail.com")
            db.delete_cms_session(sid)
            self.assertIsNone(db.get_cms_session(sid))

    def test_get_active_vip(self) -> None:
        # V16 — require_vip relies on this: active+unexpired → row; expired/missing → None.
        from datetime import datetime, timedelta, timezone

        with tempfile.TemporaryDirectory() as tmp:
            db = VipzoneDB(Path(tmp) / "vip.db")
            self.assertIsNone(db.get_active_vip("none@example.com"))
            future = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
            db.upsert_vip("vip@example.com", "monthly", future)
            self.assertIsNotNone(db.get_active_vip("vip@example.com"))
            past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            db.upsert_vip("old@example.com", "monthly", past)
            self.assertIsNone(db.get_active_vip("old@example.com"))


if __name__ == "__main__":
    unittest.main()