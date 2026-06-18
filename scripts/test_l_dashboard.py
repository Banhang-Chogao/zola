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
L_DASHBOARD_HTML = ROOT / "templates" / "l-dashboard.html"

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


if __name__ == "__main__":
    unittest.main()