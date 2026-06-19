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


if __name__ == "__main__":
    unittest.main()