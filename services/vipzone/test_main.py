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

    def test_auth_me_superadmin_role(self) -> None:
        db = get_db()
        sid = db.create_cms_session(
            {
                "email": "admin@example.com",
                "username": "banhang-chogao",
                "name": "Admin",
                "avatar": "",
                "is_super": True,
                "is_superadmin": True,
            },
            3600,
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {sid}"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["role"], "superadmin")
        self.assertTrue(body["is_super"])
        self.assertEqual(body["username"], "banhang-chogao")

    def test_auth_me_email_alone_not_superadmin_cookie(self) -> None:
        import cms_auth as auth_mod

        db = get_db()
        sid = db.create_cms_session(
            {
                "email": "tamsudev.com@gmail.com",
                "username": "other-user",
                "name": "Owner",
                "avatar": "",
                "is_super": False,
            },
            3600,
        )
        res = self.client.get(
            "/auth/me",
            cookies={auth_mod.SESSION_COOKIE_NAME: sid},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["role"], "user")
        self.assertFalse(body["is_super"])

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
            {
                "email": "admin@example.com",
                "username": "banhang-chogao",
                "name": "Admin",
                "is_super": True,
            },
            3600,
        )
        res = self.client.post("/auth/logout", headers={"Authorization": f"Bearer {sid}"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])
        self.assertIsNone(db.get_cms_session(sid))

    def test_public_picker_endpoint(self) -> None:
        db = get_db()
        db.set_picker(["/tools/f-dashboard/"])
        res = self.client.get("/api/vipzone/picker")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("items", body)
        self.assertIn("access", body)
        if body["items"]:
            self.assertIn("access", body["items"][0])

    def test_admin_picker_items_put(self) -> None:
        db = get_db()
        sid = db.create_cms_session(
            {
                "email": "admin@example.com",
                "username": "banhang-chogao",
                "name": "Admin",
                "is_super": True,
            },
            3600,
        )
        headers = {"Authorization": f"Bearer {sid}"}
        put = self.client.put(
            "/api/vipzone/admin/picker",
            headers=headers,
            json={
                "items": [
                    {"url": "/tools/f-dashboard/", "access": "premium"},
                    {"url": "/tools/l-dashboard/", "access": "admin_only"},
                ]
            },
        )
        self.assertEqual(put.status_code, 200)
        self.assertTrue(put.json()["ok"])
        get = self.client.get("/api/vipzone/admin/picker", headers=headers)
        self.assertEqual(get.status_code, 200)
        by_url = {i["url"]: i["access"] for i in get.json()["items"]}
        self.assertEqual(by_url.get("/tools/f-dashboard/"), "premium")
        self.assertEqual(by_url.get("/tools/l-dashboard/"), "admin_only")

    def test_vipzone_me_email_alone_not_superadmin_cookie(self) -> None:
        import cms_auth as auth_mod

        db = get_db()
        sid = db.create_cms_session(
            {
                "email": "tamsudev.com@gmail.com",
                "username": "other-user",
                "name": "Owner",
                "avatar": "",
                "is_super": False,
            },
            3600,
        )
        res = self.client.get(
            "/api/vipzone/me",
            cookies={auth_mod.SESSION_COOKIE_NAME: sid},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["role"], "user")
        self.assertFalse(body["is_super"])
        self.assertFalse(body["is_admin"])

    def test_vipzone_me_shares_auth_session(self) -> None:
        db = get_db()
        sid = db.create_cms_session(
            {
                "email": "admin@example.com",
                "username": "banhang-chogao",
                "name": "Admin",
                "is_super": True,
            },
            3600,
        )
        headers = {"Authorization": f"Bearer {sid}"}
        auth_res = self.client.get("/auth/me", headers=headers)
        me_res = self.client.get("/api/vipzone/me", headers=headers)
        self.assertEqual(auth_res.status_code, 200)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(auth_res.json()["role"], me_res.json()["role"])
        self.assertEqual(me_res.json()["role"], "superadmin")


class VipzoneDbTests(unittest.TestCase):
    def test_picker_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = VipzoneDB(Path(tmp) / "picker.db")
            items = [
                {"url": "/tools/f-dashboard/", "access": "premium"},
                {"url": "/tools/l-dashboard/", "access": "admin_only"},
            ]
            db.set_picker(items)
            self.assertEqual(db.get_picker(), items)

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
                {"email": "admin@example.com", "username": "banhang-chogao", "name": "Admin"},
                3600,
            )
            got = db.get_cms_session(sid)
            self.assertEqual(got["email"], "admin@example.com")
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


class GscOAuthRouteTests(unittest.TestCase):
    """GSC OAuth bootstrap routes are mounted on the DEPLOYED vipzone app.

    Regression: the routes used to live only in services/visitor-counter (not the
    Render service), so /gsc/oauth/start 404'd on blog-vipzone-api.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "gsc-test.db"
        os.environ["VIPZONE_DB_PATH"] = str(self.db_path)
        import main as main_mod

        main_mod._db = None
        self.client = TestClient(app)

        import gsc_oauth

        self.gsc = gsc_oauth
        self._saved = (gsc_oauth.GSC_CLIENT_ID, gsc_oauth.GSC_CLIENT_SECRET)
        gsc_oauth.GSC_CLIENT_ID = "client-id.apps.googleusercontent.com"
        gsc_oauth.GSC_CLIENT_SECRET = "client-secret"

    def tearDown(self) -> None:
        self.gsc.GSC_CLIENT_ID, self.gsc.GSC_CLIENT_SECRET = self._saved
        self._tmp.cleanup()

    def _superadmin_sid(self) -> str:
        return get_db().create_cms_session(
            {
                "email": "tamsudev.com@gmail.com",
                "username": "banhang-chogao",
                "name": "Admin",
                "is_super": True,
                "is_superadmin": True,
            },
            3600,
        )

    def test_status_no_secrets(self) -> None:
        res = self.client.get("/gsc/status")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["configured"])
        self.assertEqual(body["property"], "sc-domain:seomoney.org")
        self.assertEqual(
            body["redirect_uri"], "https://blog-vipzone-api.onrender.com/gsc/oauth/callback"
        )
        self.assertEqual(body["oauth_scope"], "https://www.googleapis.com/auth/webmasters.readonly")
        # Secrets must never appear in status.
        self.assertNotIn("client-secret", res.text)

    def test_oauth_start_requires_superadmin(self) -> None:
        # No session → 401.
        res = self.client.get("/gsc/oauth/start", follow_redirects=False)
        self.assertEqual(res.status_code, 401)

    def test_oauth_start_redirects_to_google(self) -> None:
        sid = self._superadmin_sid()
        res = self.client.get(f"/gsc/oauth/start?sid={sid}", follow_redirects=False)
        self.assertEqual(res.status_code, 307)
        loc = res.headers["location"]
        self.assertTrue(loc.startswith("https://accounts.google.com/o/oauth2/v2/auth"))
        self.assertIn("access_type=offline", loc)
        self.assertIn("prompt=consent", loc)
        self.assertIn("webmasters.readonly", loc)
        self.assertIn(
            "redirect_uri=https%3A%2F%2Fblog-vipzone-api.onrender.com%2Fgsc%2Foauth%2Fcallback", loc
        )

    def test_oauth_start_not_configured(self) -> None:
        self.gsc.GSC_CLIENT_ID = ""
        sid = self._superadmin_sid()
        res = self.client.get(f"/gsc/oauth/start?sid={sid}", follow_redirects=False)
        self.assertEqual(res.status_code, 503)

    def test_callback_invalid_state(self) -> None:
        res = self.client.get(
            "/gsc/oauth/callback?code=abc&state=bogus", follow_redirects=False
        )
        self.assertEqual(res.status_code, 307)
        self.assertIn("gsc_error=invalid_state", res.headers["location"])

    def test_callback_missing_params(self) -> None:
        res = self.client.get("/gsc/oauth/callback", follow_redirects=False)
        self.assertEqual(res.status_code, 307)
        self.assertIn("gsc_error=missing_params", res.headers["location"])

    def test_token_endpoint_requires_superadmin_and_returns_stored(self) -> None:
        res = self.client.get("/gsc/oauth/token")
        self.assertEqual(res.status_code, 401)
        get_db().set_setting("gsc:refresh_token", "1//stored-refresh-token")
        sid = self._superadmin_sid()
        ok = self.client.get(f"/gsc/oauth/token?sid={sid}")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["refresh_token"], "1//stored-refresh-token")


if __name__ == "__main__":
    unittest.main()