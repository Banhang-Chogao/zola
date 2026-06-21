"""Tests for deploysafe29 — production backend smoke check (V29). Stdlib, no network.

Proves the core contract: a backend route 404 on production means the deployed
backend lags `main` (GitHub Pages deploy != Render deploy → Render Manual Sync),
while any non-404 proves the route is present. Also proves a sandbox egress block
(`host_not_allowed`) is reported as "external verification blocked" — never retried
forever or mistaken for a real failure.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prod_smoke_check import (  # noqa: E402
    CRITICAL_ROUTES,
    _is_egress_blocked,
    classify_route,
    classify_smoke,
    curl_commands,
)


class RouteClassifyTests(unittest.TestCase):
    def test_non_404_is_present(self):
        for code in (200, 301, 401, 403, 422, 500, 503):
            r = classify_route("GET", "/gsc/status", code, "", "")
            self.assertTrue(r["present"], f"{code} should be present")
            self.assertEqual(r["state"], "present")

    def test_404_is_missing(self):
        # The whole point: a 404 means the route is absent → backend not redeployed.
        r = classify_route("POST", "/cms/save-post", 404, '{"detail":"Not Found"}', "")
        self.assertFalse(r["present"])
        self.assertEqual(r["state"], "missing")
        self.assertIn("Render Manual Sync", r["note"])

    def test_egress_block_is_blocked_not_missing(self):
        r = classify_route("GET", "/health", 403, '{"error":"host_not_allowed"}', "")
        self.assertIsNone(r["present"])
        self.assertEqual(r["state"], "blocked")

    def test_connection_error_is_unreachable(self):
        r = classify_route("GET", "/health", None, "", "URLError: timed out")
        self.assertIsNone(r["present"])
        self.assertEqual(r["state"], "unreachable")

    def test_genuine_403_not_treated_as_egress(self):
        # An app 403 (superadmin_required) is a real answer → present, NOT blocked.
        r = classify_route("GET", "/gsc/oauth/start", 403, '{"detail":"superadmin_required"}', "")
        self.assertEqual(r["state"], "present")


class EgressDetectTests(unittest.TestCase):
    def test_token_in_body(self):
        self.assertTrue(_is_egress_blocked(403, "host_not_allowed", ""))

    def test_token_in_error(self):
        self.assertTrue(_is_egress_blocked(None, "", "URLError: host not allowed"))

    def test_clean_response_not_blocked(self):
        self.assertFalse(_is_egress_blocked(200, '{"status":"ok"}', ""))
        self.assertFalse(_is_egress_blocked(401, '{"detail":"missing_token"}', ""))

    def test_real_sandbox_signature(self):
        # Exact sandbox proxy block: 403 + x-deny-reason header + allowlist body.
        headers = {"x-deny-reason": "host_not_allowed", "content-type": "text/plain"}
        body = ("Host not in allowlist: blog-vipzone-api.onrender.com. Add this host "
                "to your network egress settings to allow access.")
        self.assertTrue(_is_egress_blocked(403, body, "", headers))
        # Body alone (no header) still trips via the "not in allowlist" fallback token.
        self.assertTrue(_is_egress_blocked(403, body, "", None))
        # And the route classifier reports it as blocked, not present, despite the 403.
        r = classify_route("GET", "/health", 403, body, "", headers)
        self.assertEqual(r["state"], "blocked")

    def test_app_403_with_deny_header_absent_is_present(self):
        # A real app 403 carries no x-deny-reason and no allowlist body → present.
        r = classify_route("GET", "/gsc/oauth/start", 403, '{"detail":"superadmin_required"}',
                           "", {"content-type": "application/json"})
        self.assertEqual(r["state"], "present")


class SmokeVerdictTests(unittest.TestCase):
    def _routes(self, *states):
        return [{"route": f"GET /r{i}", "state": s} for i, s in enumerate(states)]

    def test_all_present_ok(self):
        v = classify_smoke(self._routes("present", "present", "present", "present"))
        self.assertEqual(v["overall"], "all_present")
        self.assertTrue(v["ok"])

    def test_any_404_is_routes_missing(self):
        v = classify_smoke(self._routes("present", "missing", "present", "present"))
        self.assertEqual(v["overall"], "routes_missing")
        self.assertFalse(v["ok"])
        self.assertEqual(v["action"], "render-deploy")
        self.assertIn("Manual Sync", v["message"])

    def test_blocked_takes_precedence_over_missing(self):
        # If the host is blocked we cannot trust 404s → report verification blocked.
        v = classify_smoke(self._routes("blocked", "missing", "blocked", "blocked"))
        self.assertEqual(v["overall"], "verification_blocked")
        self.assertEqual(v["action"], "human-curl")
        self.assertIn("host_not_allowed", v["message"])

    def test_unreachable_is_not_missing(self):
        v = classify_smoke(self._routes("unreachable", "unreachable", "unreachable", "unreachable"))
        self.assertEqual(v["overall"], "unreachable")
        self.assertEqual(v["action"], "retry")

    def test_empty_is_unknown(self):
        self.assertEqual(classify_smoke([])["overall"], "unknown")


class CurlCommandTests(unittest.TestCase):
    def test_one_curl_per_route(self):
        cmds = curl_commands("https://blog-vipzone-api.onrender.com")
        self.assertEqual(len(cmds), len(CRITICAL_ROUTES))
        for r in CRITICAL_ROUTES:
            self.assertTrue(any(r["path"] in c for c in cmds), f"missing curl for {r['path']}")

    def test_post_uses_post_method(self):
        cmds = curl_commands("https://x")
        save = [c for c in cmds if "/cms/save-post" in c][0]
        self.assertIn("-X POST", save)


class CriticalRouteContractTests(unittest.TestCase):
    """The four routes the task pins must always be probed."""

    def test_required_routes_present(self):
        paths = {r["path"] for r in CRITICAL_ROUTES}
        for p in ("/health", "/gsc/status", "/gsc/oauth/start", "/cms/save-post"):
            self.assertIn(p, paths)


if __name__ == "__main__":
    unittest.main()
