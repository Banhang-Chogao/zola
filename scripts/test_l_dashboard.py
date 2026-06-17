#!/usr/bin/env python3
"""Unit tests — LPBank L-Dashboard parser."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

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


if __name__ == "__main__":
    unittest.main()