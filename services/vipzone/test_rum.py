"""Tests for the RUM (Core Web Vitals) ingest + summary endpoints."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("VIPZONE_DB_PATH", "")
os.environ.setdefault("GSC_CLIENT_ID", "test-id.apps.googleusercontent.com")
os.environ.setdefault("GSC_CLIENT_SECRET", "test-secret")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("GOOGLE_ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("AUTH_PROVIDER", "dual")
os.environ.setdefault("RUM_ENABLED", "true")

from fastapi.testclient import TestClient  # noqa: E402

import main as main_mod  # noqa: E402
import rum as rum_mod  # noqa: E402
from db import VipzoneDB  # noqa: E402
from main import app, get_db  # noqa: E402


def _auth(sid: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + sid}


def _payload(**over) -> dict:
    base = {
        "v": 1,
        "page_path": "/posting/bai-viet-demo/",
        "page_type": "article",
        "metric": "LCP",
        "value": 1234.5,
        "rating": "good",
        "delta": 1234.5,
        "id": "v4-abc",
        "nav_type": "navigate",
        "viewport_w": 1280,
        "viewport_h": 720,
        "connection": "4g",
        "save_data": False,
        "ua": "Mozilla/5.0 (X11; Linux x86_64) RUMTest/1.0",
    }
    base.update(over)
    return base


class RumIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "vipzone-test.db"
        main_mod._db = VipzoneDB(self.db_path)
        # Restore a sane default rate limit for each test (the rate-limit test
        # mutates the module constant).
        rum_mod.RUM_RATE_MAX = 120
        self.client = TestClient(app)
        self.db = get_db()
        self.admin_sid = self.db.create_cms_session(
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
        self.commenter_sid = self.db.create_cms_session(
            {
                "provider": "google",
                "email": "visitor@gmail.com",
                "sub": "google-sub-123",
                "username": "",
                "name": "Khách",
                "avatar": "",
                "is_super": False,
                "is_superadmin": False,
                "account_type": "commenter",
            },
            3600,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ---- ingest --------------------------------------------------------------
    def test_ingest_valid_returns_204_and_stores(self) -> None:
        r = self.client.post("/rum/web-vitals", json=_payload())
        self.assertEqual(r.status_code, 204)
        summary = self.db.web_vitals_summary("1970-01-01T00:00:00Z")
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["metrics"]["LCP"]["count"], 1)
        self.assertEqual(summary["metrics"]["LCP"]["good"], 1)

    def test_ingest_stores_no_raw_ip_only_hash(self) -> None:
        self.client.post(
            "/rum/web-vitals",
            json=_payload(),
            headers={"x-forwarded-for": "203.0.113.7"},
        )
        with self.db._conn() as conn:
            row = conn.execute(
                "SELECT ip_hash, ua, page_path FROM web_vitals LIMIT 1"
            ).fetchone()
        self.assertNotIn("203.0.113.7", row["ip_hash"])
        self.assertEqual(len(row["ip_hash"]), 64)  # sha256 hex
        self.assertEqual(row["page_path"], "/posting/bai-viet-demo/")
        self.assertTrue(row["ua"].startswith("Mozilla/5.0"))

    def test_ingest_strips_query_string_from_path(self) -> None:
        self.client.post(
            "/rum/web-vitals",
            json=_payload(page_path="/posting/x/?utm_source=secret&token=abc#frag"),
        )
        with self.db._conn() as conn:
            row = conn.execute("SELECT page_path FROM web_vitals LIMIT 1").fetchone()
        self.assertEqual(row["page_path"], "/posting/x/")

    def test_all_five_metrics_accepted(self) -> None:
        for m, val in [("LCP", 1200.0), ("INP", 180.0), ("CLS", 0.05),
                       ("FCP", 900.0), ("TTFB", 300.0)]:
            r = self.client.post("/rum/web-vitals", json=_payload(metric=m, value=val))
            self.assertEqual(r.status_code, 204, m)
        summary = self.db.web_vitals_summary("1970-01-01T00:00:00Z")
        self.assertEqual(set(summary["metrics"].keys()), {"LCP", "INP", "CLS", "FCP", "TTFB"})

    def test_unknown_metric_rejected(self) -> None:
        r = self.client.post("/rum/web-vitals", json=_payload(metric="BOGUS"))
        self.assertEqual(r.status_code, 422)

    def test_negative_value_rejected(self) -> None:
        r = self.client.post("/rum/web-vitals", json=_payload(value=-5))
        self.assertEqual(r.status_code, 422)

    def test_out_of_range_value_rejected(self) -> None:
        r = self.client.post("/rum/web-vitals", json=_payload(value=9_999_999))
        self.assertEqual(r.status_code, 422)

    def test_bad_path_rejected(self) -> None:
        r = self.client.post("/rum/web-vitals", json=_payload(page_path="not-a-path"))
        self.assertEqual(r.status_code, 204)  # normalized to /not-a-path, still valid
        r2 = self.client.post("/rum/web-vitals", json=_payload(page_path="/has space"))
        self.assertEqual(r2.status_code, 422)

    def test_unknown_page_type_coerced_to_other(self) -> None:
        self.client.post("/rum/web-vitals", json=_payload(page_type="hacker<script>"))
        with self.db._conn() as conn:
            row = conn.execute("SELECT page_type FROM web_vitals LIMIT 1").fetchone()
        self.assertEqual(row["page_type"], "other")

    def test_invalid_json_rejected(self) -> None:
        r = self.client.post(
            "/rum/web-vitals",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(r.status_code, 400)

    def test_oversized_body_rejected(self) -> None:
        big = _payload(ua="x" * 100, attribution={"element": "a" * 20000})
        r = self.client.post("/rum/web-vitals", json=big)
        self.assertEqual(r.status_code, 413)

    def test_rate_limit_drops_silently(self) -> None:
        rum_mod.RUM_RATE_MAX = 2
        codes = [
            self.client.post("/rum/web-vitals", json=_payload()).status_code
            for _ in range(5)
        ]
        self.assertTrue(all(c == 204 for c in codes))  # never errors the beacon
        summary = self.db.web_vitals_summary("1970-01-01T00:00:00Z")
        self.assertLessEqual(summary["total"], 2)  # only up to the limit stored

    def test_attribution_summary_stored_when_present(self) -> None:
        self.client.post(
            "/rum/web-vitals",
            json=_payload(attribution={"element": "main>h1", "ignored": 123}),
        )
        with self.db._conn() as conn:
            row = conn.execute("SELECT attribution FROM web_vitals LIMIT 1").fetchone()
        self.assertIn("main>h1", row["attribution"])

    # ---- summary (admin-gated) ----------------------------------------------
    def test_summary_requires_auth(self) -> None:
        r = self.client.get("/rum/web-vitals/summary")
        self.assertIn(r.status_code, (401, 403))

    def test_summary_forbidden_for_commenter(self) -> None:
        r = self.client.get("/rum/web-vitals/summary", headers=_auth(self.commenter_sid))
        self.assertEqual(r.status_code, 403)

    def test_summary_p75_for_admin(self) -> None:
        for v in [100.0, 200.0, 300.0, 400.0]:
            self.client.post("/rum/web-vitals", json=_payload(metric="TTFB", value=v))
        r = self.client.get(
            "/rum/web-vitals/summary?days=7", headers=_auth(self.admin_sid)
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["metrics"]["TTFB"]["count"], 4)
        # nearest-rank p75 of [100,200,300,400] → ceil(0.75*4)=3 → 3rd = 300
        self.assertEqual(data["metrics"]["TTFB"]["p75"], 300.0)
        self.assertIn("article", data["by_page_type"])

    def test_summary_days_bounds(self) -> None:
        r = self.client.get(
            "/rum/web-vitals/summary?days=0", headers=_auth(self.admin_sid)
        )
        self.assertEqual(r.status_code, 422)  # ge=1


if __name__ == "__main__":
    unittest.main()
