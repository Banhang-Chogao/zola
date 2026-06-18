"""Regression tests for H-Dashboard OCR loader paths and vendored assets."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OCR_JS = ROOT / "static/js/h-dashboard/ocr-loader.js"
VENDOR_TESS = ROOT / "static/vendor/tesseract/tesseract.min.js"
VENDOR_WORKER = ROOT / "static/vendor/tesseract/worker.min.js"
BASE_HTML = ROOT / "templates/base.html"
HD_HTML = ROOT / "templates/h-dashboard.html"


class OcrLoaderRegressionTest(unittest.TestCase):
    def test_vendored_tesseract_assets_exist(self):
        self.assertTrue(VENDOR_TESS.exists(), "vendor tesseract.min.js missing")
        self.assertTrue(VENDOR_WORKER.exists(), "vendor worker.min.js missing")
        self.assertGreater(VENDOR_TESS.stat().st_size, 10_000)
        self.assertGreater(VENDOR_WORKER.stat().st_size, 10_000)

    def test_ocr_loader_core_path_and_timeout(self):
        js = OCR_JS.read_text(encoding="utf-8")
        self.assertIn('TESS_VERSION = "5.1.1"', js)
        self.assertIn("tesseract.js-core@", js)
        self.assertIn("WORKER_TIMEOUT_MS", js)
        self.assertIn("workerBlobURL: false", js)
        self.assertIn("OCR_LANGS_FALLBACK", js)
        self.assertIn("wasm", js.lower())  # progress message for core load

    def test_h_dashboard_meta_local_tesseract(self):
        html = HD_HTML.read_text(encoding="utf-8")
        self.assertIn('name="hd-tesseract-src"', html)
        self.assertIn("vendor/tesseract/tesseract.min.js", html)
        self.assertIn('name="hd-tesseract-core"', html)

    def test_csp_allows_wasm(self):
        csp = BASE_HTML.read_text(encoding="utf-8")
        self.assertIn("wasm-unsafe-eval", csp)
        self.assertIn("https://cdn.jsdelivr.net", csp)
        self.assertIn("https://tessdata.projectnaptha.com", csp)


if __name__ == "__main__":
    unittest.main()