#!/usr/bin/env python3
"""Unit tests for fetch_uptime_me monitor filtering (network-free).

Covers the "show seomoney.org only" invariant for /tools/uptime-me/:
  * unrelated infra (e.g. blog-visitor-api.onrender.com) is dropped;
  * the seomoney.org monitor is deduped to a single card even when all 3
    accounts report it;
  * host matching is normalized (scheme / www. / trailing slash / case);
  * summary + incidents are derived only from the kept monitors;
  * an empty (no-key) build still produces a valid, seomoney-only report;
  * the committed data/uptime-me.json never exposes blog-visitor-api.

Run: python3 -m unittest scripts.test_fetch_uptime_me -v
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_uptime_me as f  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "uptime-me.json")


def _mon(host, name=None, status="up", uptime_30d=100.0, avg=194, incidents=None):
    return {
        "name": name or (host + "/"),
        "host": host,
        "status": status,
        "uptime_24h": uptime_30d,
        "uptime_7d": uptime_30d,
        "uptime_30d": uptime_30d,
        "avg_response_ms": avg,
        "response_times": [{"t": "2026-06-20T11:00:00+00:00", "ms": 12}],
        "last_down": None,
        "incidents": incidents or [],
    }


class SelectMonitorsTest(unittest.TestCase):
    def test_drops_unrelated_hosts(self):
        mons = [_mon("blog-visitor-api.onrender.com", status="down"),
                _mon("seomoney.org")]
        kept = f.select_monitors(mons)
        self.assertEqual([m["host"] for m in kept], ["seomoney.org"])

    def test_dedupes_same_host(self):
        # All 3 accounts report seomoney.org → exactly one card.
        kept = f.select_monitors([_mon("seomoney.org")] * 3)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["host"], "seomoney.org")

    def test_host_normalization(self):
        for host in ("seomoney.org", "seomoney.org/", "www.seomoney.org",
                     "https://seomoney.org/", "SEOMONEY.ORG"):
            kept = f.select_monitors([_mon(host)])
            self.assertEqual(len(kept), 1, f"expected {host!r} to match allow-list")

    def test_empty_when_no_seomoney(self):
        kept = f.select_monitors([_mon("blog-visitor-api.onrender.com")])
        self.assertEqual(kept, [])

    def test_handles_empty_input(self):
        self.assertEqual(f.select_monitors([]), [])
        self.assertEqual(f.select_monitors(None), [])


class SummarizeTest(unittest.TestCase):
    def test_summary_only_counts_kept_monitors(self):
        kept = f.select_monitors([
            _mon("blog-visitor-api.onrender.com", status="down", uptime_30d=0.0,
                 incidents=[{"start": "2026-06-15T06:46:15+00:00",
                             "reason": "Method Not Allowed", "duration_s": 0}]),
            _mon("seomoney.org"),
        ])
        summary, incidents = f.summarize(kept)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["up"], 1)
        self.assertEqual(summary["down"], 0)
        self.assertEqual(summary["overall_uptime_30d"], 100.0)
        # The blog-visitor-api incident must not leak into the timeline.
        self.assertEqual(incidents, [])

    def test_empty_summary_is_safe(self):
        summary, incidents = f.summarize([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["breathing"], "chưa rõ")
        self.assertEqual(incidents, [])


class BuildReportTest(unittest.TestCase):
    def test_no_keys_produces_clean_empty_report(self):
        env = {k: "" for k in f.ENV_KEYS}
        old = {k: os.environ.get(k) for k in f.ENV_KEYS}
        os.environ.update(env)
        try:
            rep = f.build_report()
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.assertEqual(rep["monitors"], [])
        self.assertEqual(rep["summary"]["total"], 0)
        for key in ("checked_at", "ok", "summary", "accounts", "monitors", "incidents"):
            self.assertIn(key, rep)


class CommittedDataTest(unittest.TestCase):
    """The shipped report must already be seomoney-only (no infra leakage)."""
    def setUp(self):
        with open(DATA, encoding="utf-8") as fh:
            self.rep = json.load(fh)

    def test_only_seomoney_hosts(self):
        hosts = [m["host"] for m in self.rep["monitors"]]
        self.assertTrue(hosts, "expected at least one monitor or an empty-state report")
        for h in hosts:
            self.assertEqual(f._norm_host(h), "seomoney.org")

    def test_no_duplicate_seomoney_cards(self):
        hosts = [f._norm_host(m["host"]) for m in self.rep["monitors"]]
        self.assertEqual(len(hosts), len(set(hosts)))

    def test_blog_visitor_api_absent_everywhere(self):
        blob = json.dumps(self.rep, ensure_ascii=False).lower()
        self.assertNotIn("blog-visitor-api", blob)
        self.assertNotIn("onrender.com", blob)


if __name__ == "__main__":
    unittest.main()
