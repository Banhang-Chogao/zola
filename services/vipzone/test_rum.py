"""Tests for the Web Vitals RUM pipeline (POST ingest + GET summary)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("VIPZONE_DB_PATH", "")
os.environ.setdefault("GSC_CLIENT_ID", "test-id.apps.googleusercontent.com")
os.environ.setdefault("GSC_CLIENT_SECRET", "test-secret")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("RUM_ENABLED", "true")
# Big enough that the batch tests don't trip the per-IP flood guard.
os.environ.setdefault("RUM_RATE_MAX", "100000")

from fastapi.testclient import TestClient  # noqa: E402

import main as main_mod  # noqa: E402
import rum as rum_mod  # noqa: E402
from db import VipzoneDB  # noqa: E402
from main import app  # noqa: E402


class WebVitalsRumTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "vipzone-test.db"
        main_mod._db = VipzoneDB(self.db_path)
        # rum_mod resolves the db through main.get_db at call time, so the fresh
        # per-test db is picked up automatically.
        rum_mod._rate_buckets.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _post(self, payload):
        return self.client.post("/rum/web-vitals", json=payload)

    # ---- ingest ----
    def test_single_event_accepted(self) -> None:
        r = self._post(
            {
                "metric_name": "LCP",
                "metric_value": 2100,
                "page_path": "/posting/abc/",
                "device_type": "mobile",
                "navigation_type": "navigate",
            }
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["accepted"], 1)

    def test_batch_events_accepted(self) -> None:
        r = self._post(
            {
                "events": [
                    {"metric_name": "LCP", "metric_value": 2000, "page_path": "/"},
                    {"metric_name": "INP", "metric_value": 150, "page_path": "/"},
                    {"metric_name": "CLS", "metric_value": 0.05, "page_path": "/"},
                    {"metric_name": "FCP", "metric_value": 1200, "page_path": "/"},
                    {"metric_name": "TTFB", "metric_value": 400, "page_path": "/"},
                ]
            }
        )
        self.assertEqual(r.json()["accepted"], 5)

    def test_invalid_metric_rejected_but_200(self) -> None:
        r = self._post({"metric_name": "BOGUS", "metric_value": 1})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["accepted"], 0)

    def test_negative_and_nan_rejected(self) -> None:
        self.assertEqual(self._post({"metric_name": "LCP", "metric_value": -5}).json()["accepted"], 0)
        self.assertEqual(self._post({"metric_name": "LCP", "metric_value": "x"}).json()["accepted"], 0)

    def test_malformed_body_never_errors(self) -> None:
        r = self.client.post("/rum/web-vitals", data="not json",
                             headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["accepted"], 0)

    def test_path_is_canonicalised(self) -> None:
        self._post({"metric_name": "LCP", "metric_value": 1000,
                    "page_path": "https://seomoney.org/zola/posting/x/?utm=1#frag"})
        data = self.client.get("/rum/web-vitals/summary?window=30d").json()
        self.assertGreaterEqual(data["metrics"]["LCP"]["count"], 1)

    # ---- summary ----
    def test_summary_empty_has_no_fake_scores(self) -> None:
        data = self.client.get("/rum/web-vitals/summary").json()
        self.assertEqual(data["total_samples"], 0)
        cls = data["metrics"]["CLS"]
        self.assertEqual(cls["count"], 0)
        self.assertIsNone(cls["p75"])
        self.assertEqual(cls["rating"], "none")  # NOT "good"

    def test_summary_aggregates_p75(self) -> None:
        for v in [1000, 2000, 3000, 4000]:
            self._post({"metric_name": "LCP", "metric_value": v, "page_path": "/"})
        m = self.client.get("/rum/web-vitals/summary?window=30d").json()["metrics"]["LCP"]
        self.assertEqual(m["count"], 4)
        self.assertIsNotNone(m["p75"])
        self.assertEqual(m["average"], 2500)
        self.assertTrue(m["core"])

    def test_core_vs_diagnostic_classification(self) -> None:
        data = self.client.get("/rum/web-vitals/summary").json()
        self.assertTrue(data["metrics"]["LCP"]["core"])
        self.assertTrue(data["metrics"]["INP"]["core"])
        self.assertTrue(data["metrics"]["CLS"]["core"])
        self.assertFalse(data["metrics"]["FCP"]["core"])
        self.assertFalse(data["metrics"]["TTFB"]["core"])
        self.assertEqual(data["core_metrics"], ["LCP", "INP", "CLS"])

    def test_slow_pages_ranked_by_lcp(self) -> None:
        for v in [5000, 5200]:
            self._post({"metric_name": "LCP", "metric_value": v, "page_path": "/slow/"})
        for v in [800, 900]:
            self._post({"metric_name": "LCP", "metric_value": v, "page_path": "/fast/"})
        data = self.client.get("/rum/web-vitals/summary").json()
        self.assertTrue(data["slow_pages"])
        self.assertEqual(data["slow_pages"][0]["path"], "/slow/")

    def test_rating_thresholds(self) -> None:
        # 2.5s LCP is exactly "good"; 4.5s is "poor".
        self._post({"metric_name": "LCP", "metric_value": 2500, "page_path": "/g/"})
        good = self.client.get("/rum/web-vitals/summary").json()["metrics"]["LCP"]
        self.assertEqual(good["rating"], "good")


if __name__ == "__main__":
    unittest.main()
