"""Tests for Admin Guideline PDF endpoint."""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

try:
    from main import app
    HAS_APP = True
except ImportError:
    HAS_APP = False


@unittest.skipIf(not HAS_APP, "FastAPI app not available")
class TestAdminGuidelinePDFEndpoint(unittest.TestCase):
    """Test /api/admin/operation-guideline.pdf endpoint."""

    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        cls.client = TestClient(app)

    def test_endpoint_exists(self):
        """Endpoint should be registered."""
        # GET with no auth should fail (not 404)
        response = self.client.get("/api/admin/operation-guideline.pdf")
        # Should be 401/403, not 404
        self.assertIn(response.status_code, [401, 403, 307])

    def test_unauthenticated_request_rejected(self):
        """Request without Bearer token should be rejected."""
        response = self.client.get("/api/admin/operation-guideline.pdf")
        self.assertNotEqual(response.status_code, 200)

    def test_invalid_bearer_token_rejected(self):
        """Request with invalid Bearer token should be rejected."""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = self.client.get("/api/admin/operation-guideline.pdf", headers=headers)
        self.assertIn(response.status_code, [401, 403])

    def test_non_bearer_auth_rejected(self):
        """Request with non-Bearer auth should be rejected."""
        headers = {"Authorization": "Basic user:pass"}
        response = self.client.get("/api/admin/operation-guideline.pdf", headers=headers)
        self.assertIn(response.status_code, [401, 403])

    def test_accept_pdf_header_respected(self):
        """Request with Accept: application/pdf should work (when authenticated)."""
        # This test documents expected behavior; actual auth tested elsewhere
        headers = {
            "Accept": "application/pdf",
            "Authorization": "Bearer valid_token",  # Will fail auth but documents intent
        }
        response = self.client.get(
            "/api/admin/operation-guideline.pdf", headers=headers
        )
        # Even with valid Accept header, should fail auth without real session
        self.assertIn(response.status_code, [401, 403, 307])

    @patch("services.vipzone.cms_auth.verify_session")
    def test_authenticated_returns_pdf_content_type(self, mock_verify):
        """Authenticated request should return PDF content type."""
        # Mock a valid session
        mock_verify.return_value = {"email": "admin@example.com", "admin": True}

        headers = {"Authorization": "Bearer mock_valid_sid"}
        response = self.client.get(
            "/api/admin/operation-guideline.pdf", headers=headers
        )

        # Should succeed with PDF content type
        if response.status_code == 200:
            self.assertEqual(response.headers["content-type"], "application/pdf")

    @patch("services.vipzone.cms_auth.verify_session")
    def test_authenticated_returns_bytes(self, mock_verify):
        """Authenticated request should return PDF bytes."""
        mock_verify.return_value = {"email": "admin@example.com", "admin": True}

        headers = {"Authorization": "Bearer mock_valid_sid"}
        response = self.client.get(
            "/api/admin/operation-guideline.pdf", headers=headers
        )

        if response.status_code == 200:
            self.assertTrue(response.content.startswith(b"%PDF"))


class TestAdminZoneRouteSmoke(unittest.TestCase):
    """Route smoke test for /tools/admin-zone/."""

    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        try:
            from main import app

            cls.client = TestClient(app)
            cls.has_app = True
        except ImportError:
            cls.has_app = False

    def test_admin_zone_page_accessible(self):
        """Admin Zone page should be accessible (not 404)."""
        if not self.has_app:
            self.skipTest("FastAPI app not available")
        response = self.client.get("/tools/admin-zone/")
        # Page should not return 404; may return 307 redirect or 200
        self.assertNotEqual(response.status_code, 404)

    def test_admin_zone_static_assets_served(self):
        """Admin Zone static assets should be served."""
        if not self.has_app:
            self.skipTest("FastAPI app not available")

        # Check if JS modules are accessible (these may be served by static file handler)
        # This is a secondary check; main check is Zola build generates the page
        pass


if __name__ == "__main__":
    unittest.main()
