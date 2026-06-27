"""Tests for the content placement admin endpoints.

Mirrors test_main.py (temp DB + TestClient + Bearer session). DATA_PATH is
redirected to a temp file so the real data/content-placements.json is never
touched, and no GitHub token is configured so writes stay local (committed=false).
"""

import json
import os
import tempfile
import unittest
from pathlib import Path


class ContentPlacementTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "vipzone-test.db"
        os.environ["VIPZONE_DB_PATH"] = str(self.db_path)
        # Ensure no service token → writes stay local, deterministic.
        for var in (
            "CONTENT_PLACEMENTS_GH_TOKEN",
            "ZOLA_GH_TOKEN",
            "WORKFLOW_BOT_PAT",
            "GH_PAT",
        ):
            os.environ.pop(var, None)

        import main as main_mod
        import content_placements as cp_mod
        from fastapi.testclient import TestClient

        main_mod._db = None  # force DB reinit against the temp path

        # Seed a registry + redirect the data file to the temp dir.
        self.data_file = Path(self._tmp.name) / "content-placements.json"
        self.data_file.write_text(
            json.dumps(
                {
                    "version": 1,
                    "placements": [
                        {"id": "global_header_below", "label": "Dưới header", "scope": "global"},
                        {"id": "post_after_intro", "label": "Sau intro", "scope": "post"},
                    ],
                    "blocks": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        cp_mod.DATA_PATH = self.data_file
        self.cp_mod = cp_mod
        self.main_mod = main_mod
        self.client = TestClient(main_mod.app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _admin_sid(self) -> str:
        db = self.main_mod.get_db()
        return db.create_cms_session(
            {
                "provider": "google",
                "email": "tamsudev.com@gmail.com",
                "username": "banhang-chogao",
                "name": "Admin",
                "is_super": True,
                "is_superadmin": True,
                "account_type": "admin",
            },
            3600,
        )

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._admin_sid()}"}

    def test_requires_auth(self) -> None:
        res = self.client.get("/admin/content-placements")
        self.assertEqual(res.status_code, 401)

    def test_get_registry(self) -> None:
        res = self.client.get("/admin/content-placements", headers=self._auth())
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(len(body["placements"]), 2)
        self.assertEqual(body["placements"][0]["block_count"], 0)

    def test_create_and_get_block(self) -> None:
        payload = {
            "id": "test_header_cta",
            "placement_id": "global_header_below",
            "type": "momo_cta",
            "enabled": True,
            "title": "Ủng hộ",
            "body": "Mời cà phê.",
            "button_text": "Ủng hộ qua MoMo",
            "url": "https://me.momo.vn/abc/def",
            "style": "compact",
            "priority": 10,
        }
        res = self.client.post("/admin/content-blocks", json=payload, headers=self._auth())
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["committed"])  # no token configured
        # Roundtrip
        res2 = self.client.get("/admin/content-blocks", headers=self._auth())
        ids = [b["id"] for b in res2.json()["blocks"]]
        self.assertIn("test_header_cta", ids)

    def test_reject_unknown_placement(self) -> None:
        payload = {
            "id": "bad_block",
            "placement_id": "does_not_exist",
            "type": "notice",
            "title": "x",
            "body": "y",
        }
        res = self.client.post("/admin/content-blocks", json=payload, headers=self._auth())
        self.assertEqual(res.status_code, 400)

    def test_reject_non_https_url(self) -> None:
        payload = {
            "id": "bad_url",
            "placement_id": "global_header_below",
            "type": "link_card",
            "title": "x",
            "button_text": "go",
            "url": "javascript:alert(1)",
        }
        res = self.client.post("/admin/content-blocks", json=payload, headers=self._auth())
        self.assertEqual(res.status_code, 400)

    def test_reject_momo_url_for_momo_type(self) -> None:
        payload = {
            "id": "wrong_momo",
            "placement_id": "global_header_below",
            "type": "momo_cta",
            "title": "x",
            "button_text": "go",
            "url": "https://example.com/not-momo",
        }
        res = self.client.post("/admin/content-blocks", json=payload, headers=self._auth())
        self.assertEqual(res.status_code, 400)

    def test_reject_duplicate_id(self) -> None:
        payload = {
            "id": "dup",
            "placement_id": "post_after_intro",
            "type": "notice",
            "title": "x",
            "body": "y",
        }
        self.assertEqual(
            self.client.post("/admin/content-blocks", json=payload, headers=self._auth()).status_code,
            200,
        )
        self.assertEqual(
            self.client.post("/admin/content-blocks", json=payload, headers=self._auth()).status_code,
            409,
        )

    def test_reject_html_safe_script(self) -> None:
        payload = {
            "id": "xss_try",
            "placement_id": "post_after_intro",
            "type": "html_safe",
            "title": "x",
            "body": "<script>alert(1)</script>",
        }
        res = self.client.post("/admin/content-blocks", json=payload, headers=self._auth())
        self.assertEqual(res.status_code, 400)

    def test_patch_and_delete(self) -> None:
        create = {
            "id": "editme",
            "placement_id": "post_after_intro",
            "type": "notice",
            "title": "old",
            "body": "body",
        }
        self.client.post("/admin/content-blocks", json=create, headers=self._auth())
        patch = self.client.patch(
            "/admin/content-blocks/editme", json={"title": "new"}, headers=self._auth()
        )
        self.assertEqual(patch.status_code, 200, patch.text)
        self.assertEqual(patch.json()["block"]["title"], "new")
        delete = self.client.delete("/admin/content-blocks/editme", headers=self._auth())
        self.assertEqual(delete.status_code, 200)
        self.assertEqual(
            self.client.delete("/admin/content-blocks/editme", headers=self._auth()).status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
