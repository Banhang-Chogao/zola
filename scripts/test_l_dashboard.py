#!/usr/bin/env python3
"""Unit tests — LPBank L-Dashboard parser + auth-gate regression."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

AUTH_GATE_JS = ROOT / "static" / "js" / "l-dashboard" / "auth-gate.js"
PDF_LOADER_JS = ROOT / "static" / "js" / "l-dashboard" / "pdf-loader.js"
L_DASHBOARD_HTML = ROOT / "templates" / "l-dashboard.html"
PDF_MIN_JS = ROOT / "static" / "vendor" / "pdfjs" / "pdf.min.js"
PDF_WORKER_JS = ROOT / "static" / "vendor" / "pdfjs" / "pdf.worker.min.js"

from lpbank_parser import (  # noqa: E402
    FIXTURE_PDF,
    parse_lpbank_pdf,
    reconcile,
)


class LPBankParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not FIXTURE_PDF.exists():
            raise unittest.SkipTest(f"Missing fixture: {FIXTURE_PDF}")

    def test_fixture_totals(self):
        stmt = parse_lpbank_pdf(FIXTURE_PDF)
        rec = reconcile(stmt)

        self.assertEqual(stmt.total_debit, 12_881_300)
        self.assertEqual(stmt.total_credit, 12_881_300)
        self.assertEqual(stmt.ending_balance, 0)
        self.assertEqual(stmt.opening_balance, 0)
        self.assertTrue(rec["ok"], rec)
        self.assertEqual(rec["sum_debit"], 12_881_300)
        self.assertEqual(rec["sum_credit"], 12_881_300)
        self.assertGreaterEqual(len(stmt.transactions), 18)

    def test_transaction_fields(self):
        stmt = parse_lpbank_pdf(FIXTURE_PDF)
        first = stmt.transactions[0]
        self.assertTrue(first.txn_no.startswith("FT"))
        self.assertRegex(first.txn_date, r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue(first.description)
        self.assertTrue(first.debit or first.credit)


class LDashboardAuthGateTest(unittest.TestCase):
    """Regression: showView must read dataset.ldView for data-ld-view sections."""

    def test_auth_gate_show_view_uses_ld_dataset(self):
        src = AUTH_GATE_JS.read_text(encoding="utf-8")
        self.assertIn("[data-ld-view]", src)
        self.assertIn("dataset.ldView", src)
        self.assertNotIn("dataset.fdView", src)

    def test_template_uses_ld_view_attrs(self):
        html = L_DASHBOARD_HTML.read_text(encoding="utf-8")
        self.assertIn('data-ld-view="login"', html)
        self.assertIn('data-ld-view="dashboard"', html)
        self.assertNotRegex(html, re.compile(r"data-fd-view"))

    def test_return_path_uses_location_pathname(self):
        src = AUTH_GATE_JS.read_text(encoding="utf-8")
        self.assertIn("location.pathname", src)
        self.assertNotIn('"/tools/l-dashboard/"', src)


class LDashboardPdfJsTest(unittest.TestCase):
    """HOTFIX: pdf.js must load via CSP-safe local/get_url paths, not cdnjs."""

    def test_vendor_pdf_assets_exist(self):
        self.assertTrue(PDF_MIN_JS.is_file(), "static/vendor/pdfjs/pdf.min.js")
        self.assertTrue(PDF_WORKER_JS.is_file(), "static/vendor/pdfjs/pdf.worker.min.js")
        self.assertGreater(PDF_MIN_JS.stat().st_size, 10_000)
        self.assertGreater(PDF_WORKER_JS.stat().st_size, 10_000)

    def test_template_no_cdnjs_pdfjs(self):
        html = L_DASHBOARD_HTML.read_text(encoding="utf-8")
        self.assertNotIn("cdnjs.cloudflare.com", html)
        self.assertIn("ld-pdfjs-src", html)
        self.assertIn("ld-pdfjs-worker", html)
        self.assertIn("get_url(path='vendor/pdfjs/pdf.min.js')", html)
        self.assertIn("get_url(path='js/l-dashboard/pdf-loader.js')", html)

    def test_pdf_loader_sets_worker_and_fallback(self):
        src = PDF_LOADER_JS.read_text(encoding="utf-8")
        self.assertIn("GlobalWorkerOptions.workerSrc", src)
        self.assertIn("cdn.jsdelivr.net/npm/pdfjs-dist@", src)
        self.assertIn("ld-pdfjs-src", src)
        self.assertIn("retryWithCdnWorker", src)

    def test_parser_uses_pdf_loader(self):
        parser = (ROOT / "static" / "js" / "l-dashboard" / "lpbank-parser.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("LDashboardPdf.ensureReady", parser)


if __name__ == "__main__":
    unittest.main()