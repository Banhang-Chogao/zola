"""CMS-V5 API integration tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

os.environ.setdefault("VIPZONE_DB_PATH", "")
os.environ.setdefault("GSC_CLIENT_ID", "test-id.apps.googleusercontent.com")
os.environ.setdefault("GSC_CLIENT_SECRET", "test-secret")

import cms_v5  # noqa: E402
import main as main_mod  # noqa: E402
from db import VipzoneDB  # noqa: E402
from main import app, get_db  # noqa: E402


def auth(sid: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + sid}


class CmsV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        main_mod._db = VipzoneDB(base / "vipzone.db")
        cms_v5.MEDIA_ROOT = base / "media"
        self.client = TestClient(app)
        self.sid = get_db().create_cms_session(
            {
                "provider": "github",
                "email": "admin@example.com",
                "username": "banhang-chogao",
                "name": "Duy Nguyen",
                "is_super": True,
                "access_token": "github-test-token",
            },
            3600,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def payload(self, **overrides):
        value = {
            "title": "Bài viết thử CMS-V5",
            "slug": "bai-viet-thu-cms-v5",
            "excerpt": "Mô tả thật",
            "blocks": [
                {"type": "text", "text": "Nội dung do người viết nhập."},
                {"type": "heading", "text": "Tiêu đề phụ"},
            ],
            "category": "Công nghệ",
            "tags": ["CMS", "Blog"],
            "status": "draft",
            "visibility": "public",
        }
        value.update(overrides)
        return value

    def test_routes_require_github_admin(self) -> None:
        self.assertEqual(self.client.get("/api/cms-v5/dashboard").status_code, 401)
        google_sid = get_db().create_cms_session(
            {
                "provider": "google",
                "email": "admin@example.com",
                "username": "banhang-chogao",
                "is_super": True,
            },
            3600,
        )
        response = self.client.get("/api/cms-v5/dashboard", headers=auth(google_sid))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "github_oauth_required")

    def test_save_queue_dashboard_and_taxonomy(self) -> None:
        saved = self.client.post(
            "/api/cms-v5/posts", json=self.payload(), headers=auth(self.sid)
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        post = saved.json()["post"]
        self.assertEqual(post["status"], "draft")
        self.assertEqual(post["blocks"][0]["text"], "Nội dung do người viết nhập.")

        dashboard = self.client.get(
            "/api/cms-v5/dashboard", headers=auth(self.sid)
        ).json()
        self.assertEqual(dashboard["queue"][0]["id"], post["id"])
        self.assertGreaterEqual(dashboard["stats"]["posts_total"], 1)

        taxonomy = self.client.get(
            "/api/cms-v5/taxonomy", headers=auth(self.sid)
        ).json()
        names = {item["name"] for item in taxonomy["categories"]}
        tags = {item["name"] for item in taxonomy["tags"]}
        self.assertIn("Công nghệ", names)
        self.assertTrue({"CMS", "Blog"}.issubset(tags))

    def test_upload_serve_and_protect_used_media(self) -> None:
        upload = self.client.post(
            "/api/cms-v5/media",
            files=[("files", ("photo.png", b"\x89PNG\r\n\x1a\nfake", "image/png"))],
            headers=auth(self.sid),
        )
        self.assertEqual(upload.status_code, 200, upload.text)
        media = upload.json()["media"][0]
        served = self.client.get(f"/api/cms-v5/media/{media['id']}/file")
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.content, b"\x89PNG\r\n\x1a\nfake")

        body = self.payload(
            blocks=[{"type": "image", "media_id": media["id"], "alt": "Ảnh thử"}],
            featured_media_id=media["id"],
        )
        self.assertEqual(
            self.client.post("/api/cms-v5/posts", json=body, headers=auth(self.sid)).status_code,
            200,
        )
        blocked = self.client.delete(
            f"/api/cms-v5/media/{media['id']}", headers=auth(self.sid)
        )
        self.assertEqual(blocked.status_code, 409)

    def test_public_analytics_updates_real_dashboard_counts(self) -> None:
        for metric in ("view", "view", "interaction"):
            response = self.client.post(
                "/api/cms-v5/analytics",
                json={"path": "/cong-nghe/bai-thu/", "metric": metric},
            )
            self.assertEqual(response.status_code, 200)
        stats = self.client.get(
            "/api/cms-v5/dashboard", headers=auth(self.sid)
        ).json()["stats"]
        self.assertEqual(stats["views_today"], 2)
        self.assertGreaterEqual(stats["interactions_today"], 1)

    def test_schedule_validation_and_publish_endpoint(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        scheduled = self.client.post(
            "/api/cms-v5/posts",
            json=self.payload(status="scheduled", scheduled_at=future),
            headers=auth(self.sid),
        )
        self.assertEqual(scheduled.status_code, 200, scheduled.text)
        self.assertEqual(scheduled.json()["post"]["status"], "scheduled")

        post_id = scheduled.json()["post"]["id"]
        with patch.object(
            cms_v5,
            "_publish",
            AsyncMock(return_value={"ok": True, "url": "https://seomoney.org/cong-nghe/bai-viet-thu-cms-v5/"}),
        ) as publish:
            response = self.client.post(
                f"/api/cms-v5/posts/{post_id}/publish", headers=auth(self.sid)
            )
        self.assertEqual(response.status_code, 200)
        publish.assert_awaited_once_with(post_id, "github-test-token")

    def test_github_oauth_canonicalizes_cms_v5_return_to_cms_v6(self) -> None:
        from cms_auth import github_success_return_to, normalize_github_return_to

        self.assertEqual(
            normalize_github_return_to("https://seomoney.org/cms-v5/"),
            "https://seomoney.org/cms-v6/",
        )
        self.assertEqual(
            github_success_return_to("https://seomoney.org/cms-v5/?draft=1"),
            "https://seomoney.org/cms-v6/?success=1",
        )


if __name__ == "__main__":
    unittest.main()
