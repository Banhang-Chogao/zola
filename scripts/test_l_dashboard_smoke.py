#!/usr/bin/env python3
"""Smoke tests — L-Dashboard frontend (auth gate, template, built HTML)."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUTH_GATE = ROOT / "static/js/l-dashboard/auth-gate.js"
TEMPLATE = ROOT / "templates/l-dashboard.html"
PUBLIC_PAGE = ROOT / "public/tools/l-dashboard/index.html"


class LDashboardSmokeTest(unittest.TestCase):
    def test_auth_gate_uses_ld_view_dataset(self):
        """showView must read data-ld-view, not copy-paste data-fd-view."""
        src = AUTH_GATE.read_text(encoding="utf-8")
        self.assertIn("[data-ld-view]", src)
        self.assertIn("el.dataset.ldView", src)
        self.assertNotIn("el.dataset.fdView", src)
        self.assertNotIn("[data-fd-view]", src)

    def test_template_has_login_and_dashboard_views(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('id="ld-app"', html)
        self.assertIn('data-ld-view="login"', html)
        self.assertIn('data-ld-view="dashboard"', html)
        self.assertIn('data-ld-action="github-login"', html)
        self.assertIn('id="ld-upload-zone"', html)
        self.assertIn('id="ld-table-body"', html)
        self.assertIn("get_url(path='js/l-dashboard/auth-gate.js')", html)

    def test_built_page_renders_sections(self):
        if not PUBLIC_PAGE.exists():
            self.skipTest("Run `zola build` first to generate public/tools/l-dashboard/")
        html = PUBLIC_PAGE.read_text(encoding="utf-8")
        self.assertIn('data-ld-view="login"', html)
        self.assertIn('data-ld-view="dashboard"', html)
        self.assertIn("L-Dashboard — Xác thực", html)
        self.assertIn("Upload sao kê PDF", html)
        self.assertIn("Bảng thống kê", html)
        self.assertRegex(
            html,
            r'/zola/js/l-dashboard/auth-gate\.js',
            msg="auth-gate.js must use GitHub Pages base path",
        )

    def test_show_view_logic_matches_f_dashboard_pattern(self):
        """Static parity check: F-Dashboard uses fdView; L-Dashboard uses ldView."""
        fd_src = (ROOT / "static/js/f-dashboard/auth-gate.js").read_text(encoding="utf-8")
        ld_src = AUTH_GATE.read_text(encoding="utf-8")
        fd_match = re.search(
            r'document\.querySelectorAll\("\[data-fd-view\]"\)\.forEach\(\(el\) => \{\s*'
            r"el\.hidden = el\.dataset\.fdView !== name;",
            fd_src,
        )
        ld_match = re.search(
            r'document\.querySelectorAll\("\[data-ld-view\]"\)\.forEach\(\(el\) => \{\s*'
            r"el\.hidden = el\.dataset\.ldView !== name;",
            ld_src,
        )
        self.assertIsNotNone(fd_match, "F-Dashboard showView pattern changed — update smoke test")
        self.assertIsNotNone(ld_match, "L-Dashboard showView must mirror F-Dashboard with ld* attrs")


def _ensure_built() -> None:
    if PUBLIC_PAGE.exists():
        return
    subprocess.run(["zola", "build"], cwd=ROOT, check=True, capture_output=True)


if __name__ == "__main__":
    if "--build" in sys.argv:
        _ensure_built()
        sys.argv.remove("--build")
    unittest.main()