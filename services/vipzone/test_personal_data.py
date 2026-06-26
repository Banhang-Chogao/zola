"""Tests for the private Calendar + 3M Whiteboard API (personal_data router).

Covers the task's security/QA contract:
  - unauthenticated callers cannot read or write any private data
  - a non-admin (logged-in but not on the allowlist) is rejected
  - an authenticated admin can fully CRUD events and notes
  - data is owner-scoped (one user never sees another's rows)
  - "cookie deletion" (new session) still returns the same stored records
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("VIPZONE_DB_PATH", "")
os.environ.setdefault("GSC_CLIENT_ID", "test-id.apps.googleusercontent.com")
os.environ.setdefault("GSC_CLIENT_SECRET", "test-secret")

from main import app, get_db  # noqa: E402


class PersonalDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "vipzone-test.db"
        os.environ["VIPZONE_DB_PATH"] = str(self.db_path)
        import main as main_mod

        # main.DB_PATH is captured at import time; patch it so each test gets an
        # isolated SQLite file (mirrors how get_db resolves the path).
        main_mod.DB_PATH = str(self.db_path)
        main_mod._db = None
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _admin_sid(self, email: str = "admin@example.com") -> str:
        return get_db().create_cms_session(
            {"email": email, "username": "banhang-chogao", "name": "Admin", "is_super": True},
            3600,
        )

    def _user_sid(self, email: str = "stranger@example.com") -> str:
        # A logged-in but NON-allowlisted GitHub user.
        return get_db().create_cms_session(
            {"email": email, "username": "stranger", "name": "Stranger", "is_super": False},
            3600,
        )

    def _auth(self, sid: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {sid}"}

    # ---------- unauthenticated ----------
    def test_endpoints_require_auth(self) -> None:
        for method, path in (
            ("get", "/calendar/events"),
            ("post", "/calendar/events"),
            ("patch", "/calendar/events/x"),
            ("delete", "/calendar/events/x"),
            ("get", "/whiteboard/notes"),
            ("post", "/whiteboard/notes"),
            ("patch", "/whiteboard/notes/x"),
            ("delete", "/whiteboard/notes/x"),
        ):
            with self.subTest(path=path, method=method):
                fn = getattr(self.client, method)
                res = fn(path) if method in ("get", "delete") else fn(path, json={})
                self.assertEqual(res.status_code, 401, f"{method} {path}")

    def test_non_admin_forbidden(self) -> None:
        headers = self._auth(self._user_sid())
        res = self.client.get("/calendar/events", headers=headers)
        self.assertEqual(res.status_code, 403)
        res = self.client.get("/whiteboard/notes", headers=headers)
        self.assertEqual(res.status_code, 403)

    # ---------- calendar CRUD ----------
    def test_calendar_crud(self) -> None:
        headers = self._auth(self._admin_sid())

        # empty to start
        res = self.client.get("/calendar/events", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["events"], [])

        # create
        res = self.client.post(
            "/calendar/events",
            headers=headers,
            json={
                "title": "Họp kế hoạch",
                "start": "2026-06-22 09:00",
                "end": "2026-06-22 10:00",
                "color": "teal",
                "location": "Phòng A",
                "notes": "mang laptop",
            },
        )
        self.assertEqual(res.status_code, 201)
        ev = res.json()["event"]
        eid = ev["id"]
        self.assertEqual(ev["title"], "Họp kế hoạch")
        self.assertFalse(ev["allDay"])

        # update (PATCH)
        res = self.client.patch(
            f"/calendar/events/{eid}", headers=headers, json={"title": "Họp đã đổi", "color": "red"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["event"]["title"], "Họp đã đổi")
        self.assertEqual(res.json()["event"]["color"], "red")
        # untouched field preserved
        self.assertEqual(res.json()["event"]["location"], "Phòng A")

        # list shows it
        res = self.client.get("/calendar/events", headers=headers)
        self.assertEqual(len(res.json()["events"]), 1)

        # delete
        res = self.client.delete(f"/calendar/events/{eid}", headers=headers)
        self.assertEqual(res.status_code, 200)
        res = self.client.get("/calendar/events", headers=headers)
        self.assertEqual(res.json()["events"], [])

        # deleting again → 404
        res = self.client.delete(f"/calendar/events/{eid}", headers=headers)
        self.assertEqual(res.status_code, 404)

    def test_calendar_rejects_bad_color_and_sanitizes(self) -> None:
        headers = self._auth(self._admin_sid())
        res = self.client.post(
            "/calendar/events",
            headers=headers,
            json={"title": "x\x00y", "start": "2026-06-22", "color": "rainbow"},
        )
        self.assertEqual(res.status_code, 201)
        ev = res.json()["event"]
        self.assertEqual(ev["color"], "teal")  # invalid color falls back
        self.assertNotIn("\x00", ev["title"])  # control char stripped

    def test_calendar_create_requires_start(self) -> None:
        headers = self._auth(self._admin_sid())
        res = self.client.post("/calendar/events", headers=headers, json={"title": "no date"})
        self.assertEqual(res.status_code, 400)

    # ---------- whiteboard CRUD ----------
    def test_whiteboard_crud(self) -> None:
        headers = self._auth(self._admin_sid())

        res = self.client.post(
            "/whiteboard/notes", headers=headers, json={"text": "1042 5.2", "color": "yellow"}
        )
        self.assertEqual(res.status_code, 201)
        note = res.json()["note"]
        nid = note["id"]
        self.assertEqual(note["color"], "yellow")
        self.assertEqual(note["order"], 0)

        # second note gets next order
        res2 = self.client.post("/whiteboard/notes", headers=headers, json={"text": "1050 5.4"})
        self.assertEqual(res2.json()["note"]["order"], 1)

        # update text + color
        res = self.client.patch(
            f"/whiteboard/notes/{nid}", headers=headers, json={"text": "updated", "color": "pink"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["note"]["text"], "updated")
        self.assertEqual(res.json()["note"]["color"], "pink")

        res = self.client.get("/whiteboard/notes", headers=headers)
        self.assertEqual(len(res.json()["notes"]), 2)

        res = self.client.delete(f"/whiteboard/notes/{nid}", headers=headers)
        self.assertEqual(res.status_code, 200)
        res = self.client.get("/whiteboard/notes", headers=headers)
        self.assertEqual(len(res.json()["notes"]), 1)

    # ---------- owner scoping + cookie-deletion durability ----------
    def test_owner_scoping(self) -> None:
        a = self._auth(self._admin_sid("a@example.com"))
        # b is admin by username allowlist but a different email owner
        b_sid = get_db().create_cms_session(
            {"email": "b@example.com", "username": "banhang-chogao", "is_super": True}, 3600
        )
        b = self._auth(b_sid)

        self.client.post("/calendar/events", headers=a, json={"title": "A event", "start": "2026-06-22"})
        self.client.post("/whiteboard/notes", headers=b, json={"text": "B note"})

        # a sees only its own event, none of b's notes
        self.assertEqual(len(self.client.get("/calendar/events", headers=a).json()["events"]), 1)
        self.assertEqual(len(self.client.get("/whiteboard/notes", headers=a).json()["notes"]), 0)
        # b sees only its own note
        self.assertEqual(len(self.client.get("/whiteboard/notes", headers=b).json()["notes"]), 1)
        self.assertEqual(len(self.client.get("/calendar/events", headers=b).json()["events"]), 0)

    def test_data_survives_session_change(self) -> None:
        """Clearing cookies = new session; same owner email gets the same rows back."""
        sid1 = self._admin_sid("owner@example.com")
        self.client.post(
            "/calendar/events",
            headers=self._auth(sid1),
            json={"title": "durable", "start": "2026-06-22"},
        )
        # simulate logout / cookie wipe
        get_db().delete_cms_session(sid1)
        self.assertIsNone(get_db().get_cms_session(sid1))
        res = self.client.get("/calendar/events", headers=self._auth(sid1))
        self.assertEqual(res.status_code, 401)  # old session truly gone

        # re-login → brand new session for the SAME email
        sid2 = self._admin_sid("owner@example.com")
        res = self.client.get("/calendar/events", headers=self._auth(sid2))
        self.assertEqual(res.status_code, 200)
        events = res.json()["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "durable")


if __name__ == "__main__":
    unittest.main()
