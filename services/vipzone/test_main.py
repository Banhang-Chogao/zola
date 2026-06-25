"""VIPZone API unit tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("VIPZONE_DB_PATH", "")
# GSC client id/secret are read by gsc_routes at import time; set dummies BEFORE
# importing main so the /gsc/* router mounts configured (production sets the real
# values in the Render service env). Harmless to the non-GSC tests.
os.environ.setdefault("GSC_CLIENT_ID", "test-id.apps.googleusercontent.com")
os.environ.setdefault("GSC_CLIENT_SECRET", "test-secret")

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


class GscRoutesTests(unittest.TestCase):
    """Regression: /gsc/* must be served BY THIS service (blog-vipzone-api).

    config.toml points the SEO Reality Check widget's API base (vipzone_api_url) at
    this service, so the GSC OAuth + status routes have to live here. They used to
    404 because the router was only mounted on services/visitor-counter (not deployed).
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["VIPZONE_DB_PATH"] = str(Path(self._tmp.name) / "gsc.db")
        import main as main_mod

        main_mod._db = None
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_router_mounted(self) -> None:
        import main as main_mod

        self.assertTrue(main_mod.GSC_MOUNTED, "GSC router failed to mount on vipzone")
        # This FastAPI version wraps included routers lazily (not flat in app.routes),
        # so assert via the OpenAPI schema, which lists every served path.
        schema_paths = set(self.client.get("/openapi.json").json()["paths"])
        for p in ("/gsc/status", "/gsc/oauth/start", "/gsc/oauth/callback", "/gsc/metrics"):
            self.assertIn(p, schema_paths, f"{p} not mounted")

    def test_status_uses_vipzone_redirect_uri(self) -> None:
        body = self.client.get("/gsc/status").json()
        self.assertEqual(
            body["redirect_uri"], "https://blog-vipzone-api.onrender.com/gsc/oauth/callback"
        )
        self.assertEqual(body["oauth_scope"], "https://www.googleapis.com/auth/webmasters.readonly")
        self.assertEqual(body["property"], "sc-domain:seomoney.org")

    def test_oauth_start_requires_auth_not_404(self) -> None:
        res = self.client.get("/gsc/oauth/start", follow_redirects=False)
        self.assertEqual(res.status_code, 401)  # missing_token, NOT 404

    def test_oauth_start_supervip_redirects_to_google(self) -> None:
        from urllib.parse import parse_qs, urlparse

        sid = get_db().create_cms_session(
            {"email": "admin@example.com", "username": "banhang-chogao", "is_super": True}, 3600
        )
        res = self.client.get(f"/gsc/oauth/start?sid={sid}", follow_redirects=False)
        self.assertEqual(res.status_code, 307)
        q = parse_qs(urlparse(res.headers["location"]).query)
        self.assertEqual(
            q["redirect_uri"][0], "https://blog-vipzone-api.onrender.com/gsc/oauth/callback"
        )
        self.assertEqual(q["scope"][0], "https://www.googleapis.com/auth/webmasters.readonly")
        self.assertEqual(q["access_type"][0], "offline")
        # Force Google to return a refresh token on every connect.
        self.assertEqual(q["prompt"][0], "consent")
        self.assertEqual(q["include_granted_scopes"][0], "true")

    def test_oauth_start_non_super_forbidden_not_404(self) -> None:
        sid = get_db().create_cms_session(
            {"email": "x@y.com", "username": "rando", "is_super": False}, 3600
        )
        res = self.client.get(f"/gsc/oauth/start?sid={sid}", follow_redirects=False)
        self.assertEqual(res.status_code, 403)

    def test_callback_bad_state_redirects_not_404(self) -> None:
        res = self.client.get("/gsc/oauth/callback?code=x&state=bad", follow_redirects=False)
        self.assertEqual(res.status_code, 307)
        self.assertIn("gsc_error=invalid_state", res.headers["location"])


class GscRefreshTokenExportTests(unittest.TestCase):
    """Operator path: export the OAuth-acquired refresh token to set Render env.

    /gsc/status stays public-safe (never leaks the token, only has_refresh_token +
    token_source); /gsc/refresh-token is supervip-only, masked by default, full only
    with ?reveal=1; env token takes priority over the volatile KV copy.
    """

    KV_KEY = "gsc:refresh_token"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["VIPZONE_DB_PATH"] = str(Path(self._tmp.name) / "gsc.db")
        os.environ.pop("GSC_REFRESH_TOKEN", None)
        import main as main_mod

        main_mod._db = None
        self._main = main_mod
        self.client = TestClient(app)
        self._kv_set(None)  # start clean

    def tearDown(self) -> None:
        self._kv_set(None)
        os.environ.pop("GSC_REFRESH_TOKEN", None)
        self._tmp.cleanup()

    def _kv_set(self, value) -> None:
        import asyncio

        async def run():
            if value is None:
                await self._main._gsc_kv.delete(self.KV_KEY)
            else:
                await self._main._gsc_kv.set(self.KV_KEY, value)

        asyncio.run(run())

    def _super_sid(self) -> str:
        return get_db().create_cms_session(
            {"email": "admin@example.com", "username": "banhang-chogao", "is_super": True}, 3600
        )

    def _rando_sid(self) -> str:
        return get_db().create_cms_session(
            {"email": "x@y.com", "username": "rando", "is_super": False}, 3600
        )

    # ---- status: no token leak ----
    def test_status_never_leaks_token_and_reports_source(self) -> None:
        self._kv_set("kv-secret-refresh-token-1234567890")
        body = self.client.get("/gsc/status").json()
        self.assertTrue(body["has_refresh_token"])
        self.assertEqual(body["token_source"], "kv")
        self.assertNotIn("refresh_token", body)
        # Nothing in the response should contain the actual secret.
        self.assertNotIn("kv-secret-refresh-token-1234567890", repr(body))

    def test_status_none_when_no_token(self) -> None:
        body = self.client.get("/gsc/status").json()
        self.assertFalse(body["has_refresh_token"])
        self.assertEqual(body["token_source"], "none")

    # ---- supervip-only export ----
    def test_export_denied_without_sid(self) -> None:
        self._kv_set("tok")
        res = self.client.get("/gsc/refresh-token")
        self.assertEqual(res.status_code, 401)  # missing_token

    def test_export_denied_for_non_super(self) -> None:
        self._kv_set("tok")
        res = self.client.get(f"/gsc/refresh-token?sid={self._rando_sid()}")
        self.assertEqual(res.status_code, 403)

    def test_export_invalid_sid_denied(self) -> None:
        self._kv_set("tok")
        res = self.client.get("/gsc/refresh-token?sid=not-a-real-session")
        self.assertEqual(res.status_code, 401)

    def test_export_masked_by_default(self) -> None:
        self._kv_set("1//abcdefghijklmnopqrstuvwxyz0123456789")
        body = self.client.get(f"/gsc/refresh-token?sid={self._super_sid()}").json()
        self.assertTrue(body["masked"])
        self.assertNotEqual(body["refresh_token"], "1//abcdefghijklmnopqrstuvwxyz0123456789")
        self.assertNotIn("abcdefghijklmnop", body["refresh_token"])
        self.assertEqual(body["env_var"], "GSC_REFRESH_TOKEN")
        self.assertIn("instructions", body)

    def test_export_reveal_returns_full_for_super(self) -> None:
        self._kv_set("1//full-secret-token-value-987654321")
        body = self.client.get(
            f"/gsc/refresh-token?reveal=1&sid={self._super_sid()}"
        ).json()
        self.assertFalse(body["masked"])
        self.assertEqual(body["refresh_token"], "1//full-secret-token-value-987654321")

    def test_export_missing_token_handled_clearly(self) -> None:
        res = self.client.get(f"/gsc/refresh-token?sid={self._super_sid()}")
        self.assertEqual(res.status_code, 404)
        self.assertIn("no_refresh_token", res.json()["detail"])

    # ---- env preferred over KV ----
    def test_env_token_preferred_over_kv(self) -> None:
        self._kv_set("kv-token-value")
        os.environ["GSC_REFRESH_TOKEN"] = "env-token-value"
        try:
            status = self.client.get("/gsc/status").json()
            self.assertEqual(status["token_source"], "env")
            body = self.client.get(
                f"/gsc/refresh-token?reveal=1&sid={self._super_sid()}"
            ).json()
            self.assertEqual(body["token_source"], "env")
            self.assertEqual(body["refresh_token"], "env-token-value")
            self.assertTrue(body["already_persisted"])
        finally:
            os.environ.pop("GSC_REFRESH_TOKEN", None)


class GscKvTests(unittest.TestCase):
    """SQLite KV shim used in place of Redis for the GSC router on this service."""

    def test_set_get_delete(self) -> None:
        import asyncio

        from gsc_kv import SqliteKV

        with tempfile.TemporaryDirectory() as tmp:
            kv = SqliteKV(Path(tmp) / "kv.db")

            async def run():
                await kv.set("k", "v")
                self.assertEqual(await kv.get("k"), "v")
                await kv.delete("k")
                self.assertIsNone(await kv.get("k"))
                # setex + getdel single-use semantics (OAuth state)
                await kv.setex("s", 60, "/return")
                self.assertEqual(await kv.getdel("s"), "/return")
                self.assertIsNone(await kv.get("s"))
                # expired entries read as None (advance the clock past the TTL)
                await kv.setex("e", 1, "stale")
                import gsc_kv

                real_time = gsc_kv.time.time
                gsc_kv.time.time = lambda: real_time() + 5
                try:
                    self.assertIsNone(await kv.get("e"))
                finally:
                    gsc_kv.time.time = real_time

            asyncio.run(run())


class CmsRepoRoutesTests(unittest.TestCase):
    """CMS repo-write routes must be SERVED by this deployed app (not 404).

    Regression for the production smoke failure after #588: editor.js POSTs to
    {AUTH_API}/cms/save-post, AUTH_API points at this vipzone service, but the
    route only existed on the undeployed visitor-counter app → 404 Not Found.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "vipzone-cms-test.db"
        os.environ["VIPZONE_DB_PATH"] = str(self.db_path)
        import main as main_mod

        main_mod._db = None
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_cms_routes_exist_not_404(self) -> None:
        # Unauthenticated → 401 (missing_token), NEVER 404. A 404 would mean the
        # route is absent (the original production bug).
        cases = [
            ("post", "/cms/save-post", {"slug": "x", "content": "y"}),
            ("post", "/cms/posts/bulk-delete", {"slugs": ["x"]}),
            ("get", "/api/categories/list", None),
            ("post", "/api/categories/add", {"name": "X"}),
        ]
        for method, path, body in cases:
            with self.subTest(path=path):
                res = getattr(self.client, method)(path, json=body) if body is not None \
                    else getattr(self.client, method)(path)
                self.assertNotEqual(res.status_code, 404, f"{path} must be served, got 404")
                self.assertEqual(res.status_code, 401, path)

    def test_unknown_cms_route_still_404(self) -> None:
        # Control: a route we did NOT add must still 404 (proves the 401 above is
        # real auth-gating, not a catch-all).
        res = self.client.post("/cms/does-not-exist", json={})
        self.assertEqual(res.status_code, 404)

    def test_github_token_from_session(self) -> None:
        import asyncio

        from cms_auth import github_token_from_session

        db = get_db()
        sid = db.create_cms_session(
            {"email": "a@b.c", "username": "u", "name": "U", "avatar": "",
             "access_token": "ghs_secret_token"},
            3600,
        )
        token = asyncio.run(github_token_from_session(db, f"Bearer {sid}"))
        self.assertEqual(token, "ghs_secret_token")

    def test_github_token_missing_raises_401(self) -> None:
        import asyncio

        from fastapi import HTTPException

        from cms_auth import github_token_from_session

        db = get_db()
        # Legacy session without access_token (pre-token-persistence).
        sid = db.create_cms_session(
            {"email": "a@b.c", "username": "u", "name": "U", "avatar": ""}, 3600,
        )
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(github_token_from_session(db, f"Bearer {sid}"))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_access_token_not_leaked_via_auth_me(self) -> None:
        # The persisted GitHub token must never surface in profile responses.
        db = get_db()
        sid = db.create_cms_session(
            {"email": "a@b.c", "username": "u", "name": "U", "avatar": "",
             "is_super": False, "access_token": "ghs_secret_token"},
            3600,
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {sid}"})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("access_token", res.json())
        self.assertNotIn("ghs_secret_token", res.text)


class V25HealthAndCriticalRoutesTests(unittest.TestCase):
    """V25 — /health exposes split-backend diagnostics and the critical routes the
    production frontend calls are actually mounted on THIS deployed app.

    TestClient-free (inspects app.routes + _health_payload directly) so it runs even
    when the local FastAPI/httpx TestClient signature drifts from production pins.
    """

    def test_health_payload_has_split_backend_fields(self) -> None:
        import main as main_mod

        body = main_mod._health_payload()
        for field in ("backend_sha", "deployed_sha", "cms_mounted",
                      "gsc_mounted", "critical_routes"):
            self.assertIn(field, body, f"/health missing {field}")
        # backend_sha is an alias of deployed_sha.
        self.assertEqual(body["backend_sha"], body["deployed_sha"])
        self.assertIsInstance(body["critical_routes"], dict)

    def test_critical_routes_mounted(self) -> None:
        import main as main_mod

        mounted = main_mod._registered_paths()
        # These never require Google libs → always mounted on the deployed app.
        for route in ("/health", "/cms/save-post"):
            self.assertIn(route, mounted, f"{route} not mounted → production 404")

    def test_critical_routes_status_reflects_mounts(self) -> None:
        import main as main_mod

        status = main_mod._critical_routes_status()
        self.assertTrue(status["/health"])
        self.assertTrue(status["/cms/save-post"])  # cms_repo router mounted here
        # /gsc/status mounts only when google libs are present (GSC_MOUNTED).
        self.assertEqual(status["/gsc/status"], main_mod.GSC_MOUNTED)

    def test_critical_routes_constant_matches_checker(self) -> None:
        # The backend's critical set must match the post-deploy checker's smoke set.
        import main as main_mod

        self.assertEqual(
            set(main_mod.CRITICAL_ROUTES),
            {"/health", "/gsc/status", "/cms/save-post"},
        )


class ProdSmokeContractTests(unittest.TestCase):
    """V29 prod smoke check contract — CRITICAL_ROUTES parity between backend and checker.

    deploysafe29 (scripts/prod_smoke_check.py) probes specific routes on production.
    The backend MUST expose exactly the same routes; if /gsc/status or /cms/save-post
    exist only on undeployed services/visitor-counter, they return 404 → split-brain.
    """

    def test_critical_routes_exist_in_backend(self) -> None:
        """Backend CRITICAL_ROUTES must include /health, /gsc/status, /cms/save-post."""
        import main as main_mod

        # These are the exact routes prod_smoke_check.py probes.
        expected = {"/health", "/gsc/status", "/gsc/oauth/start", "/cms/save-post"}
        actual = set(main_mod.CRITICAL_ROUTES)
        self.assertEqual(
            actual,
            expected,
            f"Backend CRITICAL_ROUTES {actual} does not match checker expectations {expected}",
        )

    def test_health_and_cms_always_present(self) -> None:
        """These two routes must exist regardless of optional deps (Google libs)."""
        import main as main_mod

        mounted = main_mod._registered_paths()
        # No Google libs required for these.
        self.assertIn("/health", mounted, "/health must be mounted")
        self.assertIn("/cms/save-post", mounted, "/cms/save-post must be mounted")

    def test_gsc_status_present_when_google_libs_available(self) -> None:
        """GSC status mounts only when Google libs are available."""
        import main as main_mod

        mounted = main_mod._registered_paths()
        status_mounted = "/gsc/status" in mounted
        self.assertEqual(status_mounted, main_mod.GSC_MOUNTED,
                        "gsc/status mount status must match GSC_MOUNTED flag")

    def test_health_payload_includes_critical_routes_status(self) -> None:
        """The health endpoint reports whether each critical route is mounted."""
        import main as main_mod

        payload = main_mod._health_payload()
        self.assertIn("critical_routes", payload)
        cr = payload["critical_routes"]
        self.assertIsInstance(cr, dict)
        # All CRITICAL_ROUTES should have an entry in the status dict.
        for route in main_mod.CRITICAL_ROUTES:
            self.assertIn(route, cr, f"{route} missing from health.critical_routes")


class CmsStickyFeaturedHelpersTests(unittest.TestCase):
    """Single-active sticky/featured frontmatter demote logic (offline, pure)."""

    def test_detect_sticky_and_featured(self) -> None:
        import cms_repo

        md = '+++\ntitle = "T"\n\n[extra]\nsticky = true\nfeatured = true\n+++\n\nbody'
        self.assertTrue(cms_repo._frontmatter_forces_sticky(md))
        self.assertTrue(cms_repo._frontmatter_forces_featured(md))

    def test_demote_sticky_removes_only_sticky(self) -> None:
        import cms_repo

        md = '+++\ntitle = "T"\n\n[extra]\nthumbnail = "/x.webp"\nsticky = true\n+++\n\nbody'
        out = cms_repo._demote_sticky_frontmatter(md)
        self.assertNotIn("sticky = true", out)
        self.assertIn('thumbnail = "/x.webp"', out)  # other fields preserved

    def test_demote_featured_removes_featured_and_featured_at(self) -> None:
        import cms_repo

        md = ('+++\ntitle = "T"\n\n[extra]\nfeatured = true\n'
              'featured_at = "2026-06-20T00:00:00Z"\n+++\n\nbody')
        out = cms_repo._demote_featured_frontmatter(md)
        self.assertNotIn("featured = true", out)
        self.assertNotIn("featured_at", out)

    def test_non_sticky_post_not_detected(self) -> None:
        import cms_repo

        md = '+++\ntitle = "T"\n\n[extra]\nthumbnail = "/x.webp"\n+++\n\nbody'
        self.assertFalse(cms_repo._frontmatter_forces_sticky(md))
        self.assertFalse(cms_repo._frontmatter_forces_featured(md))


if __name__ == "__main__":
    unittest.main()