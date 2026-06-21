#!/usr/bin/env python3
"""Tests for scripts/ga_vacxin.py — the hourly GA4 health monitor.

Focus:
  * config parsing + the canonical identity (542421812 / G-SMTFZVC0XN)
  * cache isolation (foreign / old property, credential leak)
  * auth degradation (offline / missing key / bad JSON) — never raises
  * status roll-up + secret scrubbing
  * end-to-end offline run writes a public-safe report and exits 0

Run:
    python3 -m unittest scripts.test_ga_vacxin -v
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ga_vacxin as ga  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

GOOD_CONFIG = (
    'base_url = "https://seomoney.org"\n'
    '[extra]\n'
    'ga_measurement_id = "G-SMTFZVC0XN"\n'
    'ga_property_id = "542421812"\n'
    'ga_dashboard_url = "https://analytics.google.com/analytics/web/#/p542421812/reports/intelligenthome"\n'
    'ga_fix_url = "https://analytics.google.com/analytics/web/#/p542421812/admin/streams/table"\n'
)


class _Sandbox:
    """Point ga_vacxin's module paths at a throwaway dir."""
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="gavax-"))
        self._saved = {
            "CONFIG": ga.CONFIG, "GA_STATS": ga.GA_STATS,
            "DATA_OUT": ga.DATA_OUT, "STATIC_OUT": ga.STATIC_OUT,
        }
        ga.CONFIG = self.root / "config.toml"
        ga.GA_STATS = self.root / "data" / "ga-stats.json"
        ga.DATA_OUT = self.root / "data" / "ga-health.json"
        ga.STATIC_OUT = self.root / "static" / "data" / "ga-health.json"

    def write(self, rel: str, content: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def restore(self) -> None:
        for k, v in self._saved.items():
            setattr(ga, k, v)
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.sb = _Sandbox()
        self.addCleanup(self.sb.restore)

    def test_parses_canonical_identity(self):
        self.sb.write("config.toml", GOOD_CONFIG)
        cfg = ga.load_config()
        self.assertEqual(cfg["property_id"], "542421812")
        self.assertEqual(cfg["measurement_id"], "G-SMTFZVC0XN")
        self.assertEqual(cfg["site"], "seomoney.org")
        self.assertIn("p542421812", cfg["dashboard_url"])

    def test_missing_config_falls_back_to_canon(self):
        cfg = ga.load_config()  # no file written
        self.assertEqual(cfg["property_id"], ga.EXPECTED_PROPERTY_ID)
        self.assertEqual(cfg["measurement_id"], ga.EXPECTED_MEASUREMENT_ID)

    def test_check_config_ok(self):
        self.sb.write("config.toml", GOOD_CONFIG)
        self.assertEqual(ga.check_config(ga.load_config())["status"], ga.OK)

    def test_check_config_wrong_property_fails(self):
        bad = ga.load_config()
        bad["property_id"] = "541698865"
        self.assertEqual(ga.check_config(bad)["status"], ga.FAIL)


class CacheIsolationTest(unittest.TestCase):
    def setUp(self):
        self.sb = _Sandbox()
        self.addCleanup(self.sb.restore)
        self.cfg = {"property_id": "542421812"}

    def test_ok_when_stamped_current_property(self):
        self.sb.write("data/ga-stats.json",
                      '{"property_id":"542421812","updated_at":null}')
        self.assertEqual(ga.check_cache_isolation(self.cfg)["status"], ga.OK)

    def test_foreign_property_fails(self):
        self.sb.write("data/ga-stats.json", '{"property_id":"123","updated_at":null}')
        self.assertEqual(ga.check_cache_isolation(self.cfg)["status"], ga.FAIL)

    def test_old_property_string_fails(self):
        self.sb.write("data/ga-stats.json",
                      '{"property_id":"542421812","note":"old 541698865 cache"}')
        self.assertEqual(ga.check_cache_isolation(self.cfg)["status"], ga.FAIL)

    def test_credential_leak_fails(self):
        self.sb.write("data/ga-stats.json",
                      '{"property_id":"542421812","private_key":"x"}')
        self.assertEqual(ga.check_cache_isolation(self.cfg)["status"], ga.FAIL)

    def test_missing_file_skips(self):
        self.assertEqual(ga.check_cache_isolation(self.cfg)["status"], ga.SKIP)


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.sb = _Sandbox()
        self.addCleanup(self.sb.restore)
        self._saved_cred = os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    def tearDown(self):
        if self._saved_cred is not None:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._saved_cred

    def test_offline_skips(self):
        info, chk = ga.load_service_account(offline=True)
        self.assertIsNone(info)
        self.assertEqual(chk["status"], ga.SKIP)

    def test_missing_credentials_fails(self):
        info, chk = ga.load_service_account(offline=False)
        self.assertIsNone(info)
        self.assertEqual(chk["status"], ga.FAIL)

    def test_missing_file_fails(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/nonexistent/path.json"
        try:
            info, chk = ga.load_service_account(offline=False)
            self.assertIsNone(info)
            self.assertEqual(chk["status"], ga.FAIL)
        finally:
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    def test_bad_json_file_fails(self):
        self.sb.write("bad.json", "{not json")
        bad_path = str(self.sb.root / "bad.json")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = bad_path
        try:
            info, chk = ga.load_service_account(offline=False)
            self.assertIsNone(info)
            self.assertEqual(chk["status"], ga.FAIL)
        finally:
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    def test_good_credentials_file(self):
        cred_data = {
            "type": "service_account",
            "client_email": "test@example.iam.gserviceaccount.com",
            "client_id": "123",
            "private_key_id": "key123",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n",
        }
        self.sb.write("cred.json", json.dumps(cred_data))
        cred_path = str(self.sb.root / "cred.json")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
        try:
            info, chk = ga.load_service_account(offline=False)
            self.assertIsNotNone(info)
            self.assertEqual(chk["status"], ga.OK)
            self.assertEqual(info["client_email"], "test@example.iam.gserviceaccount.com")
        finally:
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


class StatusAndScrubTest(unittest.TestCase):
    def test_scrub_strips_secrets(self):
        report = {"status": "ok", "private_key": "x", "client_email": "y@z", "property_id": "542421812"}
        scrubbed = ga._scrub(report)
        self.assertNotIn("private_key", scrubbed)
        self.assertNotIn("client_email", scrubbed)
        self.assertIn("status", scrubbed)

    def test_derive_status_config_fail_is_error(self):
        checks = [ga._check("config", "c", ga.FAIL, "bad")]
        status, _ = ga.derive_status(checks, offline=False, had_key=True)
        self.assertEqual(status, "error")

    def test_derive_status_offline_is_pending(self):
        checks = [ga._check("config", "c", ga.OK, "ok")]
        status, _ = ga.derive_status(checks, offline=True, had_key=False)
        self.assertEqual(status, "pending")

    def test_derive_status_auth_fail_is_disconnected(self):
        checks = [
            ga._check("config", "c", ga.OK, "ok"),
            ga._check("cache_isolation", "ci", ga.OK, "ok"),
            ga._check("auth", "a", ga.FAIL, "no key"),
        ]
        status, _ = ga.derive_status(checks, offline=False, had_key=True)
        self.assertEqual(status, "disconnected")

    def test_derive_status_all_ok(self):
        checks = [
            ga._check("config", "c", ga.OK, "ok"),
            ga._check("cache_isolation", "ci", ga.OK, "ok"),
            ga._check("auth", "a", ga.OK, "ok"),
            ga._check("property_access", "p", ga.OK, "ok"),
            ga._check("site_tag", "s", ga.OK, "ok"),
            ga._check("recent_data", "d", ga.OK, "ok"),
        ]
        status, _ = ga.derive_status(checks, offline=False, had_key=True)
        self.assertEqual(status, "ok")


class OfflineRunTest(unittest.TestCase):
    def setUp(self):
        self.sb = _Sandbox()
        self.addCleanup(self.sb.restore)
        self.sb.write("config.toml", GOOD_CONFIG)
        self.sb.write("data/ga-stats.json", '{"property_id":"542421812","updated_at":null}')
        self._saved_cred = os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    def tearDown(self):
        if self._saved_cred is not None:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._saved_cred

    def test_build_report_offline_pending(self):
        rep = ga.build_report(offline=True)
        self.assertEqual(rep["status"], "pending")
        self.assertEqual(rep["property_id"], "542421812")
        # cache + config checks both green even offline
        by_id = {c["id"]: c for c in rep["checks"]}
        self.assertEqual(by_id["config"]["status"], ga.OK)
        self.assertEqual(by_id["cache_isolation"]["status"], ga.OK)

    def test_main_offline_writes_clean_report_exit0(self):
        rc = ga.main(["--offline"])
        self.assertEqual(rc, 0)
        for out in (ga.DATA_OUT, ga.STATIC_OUT):
            self.assertTrue(out.is_file(), out)
            data = json.loads(out.read_text(encoding="utf-8"))
            # public-safe: no credential field ever persisted
            for field in ga.SECRET_FIELDS:
                self.assertNotIn(field, data)
            self.assertIn("status", data)
            self.assertEqual(data["property_id"], "542421812")

    def test_strict_offline_exits_2(self):
        rc = ga.main(["--offline", "--strict"])
        self.assertEqual(rc, 2)  # pending != ok


if __name__ == "__main__":
    unittest.main()
