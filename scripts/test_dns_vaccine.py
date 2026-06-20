#!/usr/bin/env python3
"""Offline-safe tests for the DNS Vaccine (no network required)."""

from __future__ import annotations

import unittest

import dns_vaccine as dv


class ClassifyTest(unittest.TestCase):
    def test_github_pages_ipv4_set(self):
        # The 4 apex anycast IPs — third octet 108..111, all host .153.
        self.assertEqual(
            dv.GITHUB_PAGES_IPV4,
            {"185.199.108.153", "185.199.109.153",
             "185.199.110.153", "185.199.111.153"},
        )

    def test_1016_signature_detection(self):
        for body in ("Error 1016", "ORIGIN DNS ERROR", "1016: origin dns"):
            self.assertTrue(any(s in body.lower() for s in dv.CF_1016_SIGNS), body)
        self.assertFalse(any(s in "all good 200 ok" for s in dv.CF_1016_SIGNS))


class RepoCheckTest(unittest.TestCase):
    def test_drift_detected(self):
        # base_url host != CNAME → must yield an R2 fail.
        orig_base = dv.read_base_url_host
        orig_cname = dv.read_cname
        dv.read_base_url_host = lambda: ("https://banhang-chogao.github.io/zola",
                                         "banhang-chogao.github.io")
        dv.read_cname = lambda: "seomoney.org"
        try:
            checks: list[dict] = []
            apex = dv.repo_checks(checks)
            self.assertEqual(apex, "seomoney.org")
            r2 = [c for c in checks if c["check"] == "R2-host-match"][0]
            self.assertEqual(r2["status"], "fail")
        finally:
            dv.read_base_url_host = orig_base
            dv.read_cname = orig_cname

    def test_aligned_passes(self):
        orig_base = dv.read_base_url_host
        orig_cname = dv.read_cname
        dv.read_base_url_host = lambda: ("https://seomoney.org", "seomoney.org")
        dv.read_cname = lambda: "seomoney.org"
        try:
            checks: list[dict] = []
            dv.repo_checks(checks)
            r2 = [c for c in checks if c["check"] == "R2-host-match"][0]
            self.assertEqual(r2["status"], "pass")
            r3path = [c for c in checks if c["check"] == "R3-base-path"]
            self.assertFalse(r3path, "no /zola path warning when base_url is apex")
        finally:
            dv.read_base_url_host = orig_base
            dv.read_cname = orig_cname


class SummaryTest(unittest.TestCase):
    def test_status_precedence(self):
        self.assertEqual(dv.summarize([{"check": "x", "status": "fail"}])["status"], "fail")
        self.assertEqual(dv.summarize([{"check": "x", "status": "warn"}])["status"], "warn")
        self.assertEqual(dv.summarize([{"check": "x", "status": "pass"}])["status"], "ok")


class OfflineRunTest(unittest.TestCase):
    def test_offline_never_raises_and_skips_live(self):
        # Simulate argv for offline; main() must not raise and must return int.
        import sys
        argv = sys.argv
        sys.argv = ["dns_vaccine.py", "--offline", "--domain", "seomoney.org"]
        try:
            rc = dv.main()
            self.assertIn(rc, (0, 1, 2))
        finally:
            sys.argv = argv


if __name__ == "__main__":
    unittest.main(verbosity=2)
