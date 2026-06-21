#!/usr/bin/env python3
"""Tests for the GA Vacxin health bot (scripts/ga_vacxin.py).

Focus: offline-safety (no crash, neutral pending), property/measurement stamps,
status rollup logic, and the public-JSON secret-safety invariant.
"""
import importlib.util
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("ga_vacxin", ROOT / "scripts" / "ga_vacxin.py")
ga = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ga)


def _chk(cid, status):
    return {"id": cid, "label": cid, "status": status, "detail": ""}


class MeasurementIdTests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(ga._measurement_id_valid("G-SMTFZVC0XN"))

    def test_invalid_forms(self):
        for bad in ("", "SMTFZVC0XN", "G-", "UA-12345-1", "G-短", "G-AB"):
            self.assertFalse(ga._measurement_id_valid(bad), bad)


class IdentityTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(ga.PROPERTY_ID, "542421812")
        self.assertEqual(ga.MEASUREMENT_ID, "G-SMTFZVC0XN")
        self.assertEqual(ga.SITE_DOMAIN, "seomoney.org")

    def test_dashboard_url_has_property_no_old_account(self):
        url = ga._dashboard_url()
        self.assertIn("542421812", url)
        self.assertNotIn("541698865", url)
        self.assertNotIn("a250151829", url)

    def test_fix_url_points_at_property_admin(self):
        self.assertIn("542421812", ga._fix_url())
        self.assertIn("admin", ga._fix_url())


class OverallRollupTests(unittest.TestCase):
    def test_auth_fail_is_error(self):
        checks = [_chk("auth", "fail"), _chk("property_access", "skip"),
                  _chk("recent_data", "skip"), _chk("measurement", "ok")]
        status, ok, _ = ga._overall(checks)
        self.assertEqual(status, ga.ERROR)
        self.assertFalse(ok)

    def test_property_denied_is_error(self):
        checks = [_chk("auth", "ok"), _chk("property_access", "fail"),
                  _chk("recent_data", "skip"), _chk("measurement", "ok")]
        status, ok, _ = ga._overall(checks)
        self.assertEqual(status, ga.ERROR)

    def test_all_ok_is_healthy(self):
        checks = [_chk("auth", "ok"), _chk("property_access", "ok"),
                  _chk("recent_data", "ok"), _chk("measurement", "ok")]
        status, ok, _ = ga._overall(checks)
        self.assertEqual(status, ga.HEALTHY)
        self.assertTrue(ok)

    def test_offline_skips_are_pending_not_error(self):
        checks = [_chk("auth", "skip"), _chk("property_access", "skip"),
                  _chk("recent_data", "skip"), _chk("measurement", "ok")]
        status, ok, _ = ga._overall(checks)
        self.assertEqual(status, ga.PENDING)
        self.assertTrue(ok)

    def test_reached_ga_but_no_data_is_degraded(self):
        checks = [_chk("auth", "ok"), _chk("property_access", "ok"),
                  _chk("recent_data", "skip"), _chk("measurement", "ok")]
        status, ok, _ = ga._overall(checks)
        self.assertEqual(status, ga.DEGRADED)
        self.assertTrue(ok)


class BuildReportOfflineTests(unittest.TestCase):
    def setUp(self):
        self._saved = dict(os.environ)
        os.environ["GA_VACXIN_NO_NETWORK"] = "1"
        os.environ.pop("GA_SERVICE_ACCOUNT_KEY", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def test_offline_report_is_neutral_pending(self):
        report = ga.build_report()
        # Offline (no SDK/secret) must never read as a hard error.
        self.assertIn(report["status"], (ga.PENDING, ga.DEGRADED))
        self.assertTrue(report["ok"])

    def test_report_carries_property_stamps(self):
        report = ga.build_report()
        self.assertEqual(report["property_id"], "542421812")
        self.assertEqual(report["measurement_id"], "G-SMTFZVC0XN")
        self.assertEqual(report["site_domain"], "seomoney.org")
        self.assertEqual(len(report["checks"]), 4)
        self.assertIn("dashboard_url", report)
        self.assertEqual(report["bot"], "GA Vacxin")
        self.assertEqual(report["interval"], "hourly")

    def test_no_secret_fields_in_public_report(self):
        report = ga.build_report()
        for bad in ("private_key", "client_secret", "refresh_token",
                    "access_token", "GA_SERVICE_ACCOUNT_KEY"):
            self.assertNotIn(bad, report)

    def test_main_writes_both_files_and_exits_zero(self):
        import tempfile
        saved = (ga.DATA_OUT, ga.STATIC_OUT)
        with tempfile.TemporaryDirectory() as tmp:
            ga.DATA_OUT = Path(tmp) / "ga-vacxin-report.json"
            ga.STATIC_OUT = Path(tmp) / "static-ga-vacxin-report.json"
            try:
                rc = ga.main([])
                self.assertEqual(rc, 0)
                self.assertTrue(ga.DATA_OUT.is_file())
                self.assertTrue(ga.STATIC_OUT.is_file())
            finally:
                ga.DATA_OUT, ga.STATIC_OUT = saved


if __name__ == "__main__":
    unittest.main()
