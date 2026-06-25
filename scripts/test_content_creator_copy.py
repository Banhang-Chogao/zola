"""Regression tests for Content Creator copy prompt wiring."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ContentCreatorCopyTest(unittest.TestCase):
    def test_template_has_copy_feedback_near_button(self):
        html = (ROOT / "templates" / "content-creator.html").read_text(encoding="utf-8")
        self.assertIn('id="cc-copy"', html)
        self.assertIn('id="cc-copy-feedback"', html)
        self.assertIn("aria-live", html)

    def test_js_has_clipboard_fallback_and_feedback(self):
        js = (ROOT / "static/js/content-creator/app.js").read_text(encoding="utf-8")
        self.assertIn("copyToClipboard", js)
        self.assertIn("fallbackCopy", js)
        self.assertIn("execCommand", js)
        self.assertIn("setCopyFeedback", js)
        self.assertIn("Copied!", js)
        self.assertIn(".catch", js)

    def test_js_binds_copy_click_handler(self):
        js = (ROOT / "static/js/content-creator/app.js").read_text(encoding="utf-8")
        self.assertIn('getElementById("cc-copy")', js)
        self.assertIn("addEventListener(\"click\"", js)

    def test_scss_has_copy_feedback_styles(self):
        scss = (ROOT / "sass/_content-creator.scss").read_text(encoding="utf-8")
        self.assertIn(".cc-copy-feedback", scss)
        self.assertIn("&--success", scss)
        self.assertIn("&--error", scss)

    def test_prompt_source_is_textarea_value(self):
        js = (ROOT / "static/js/content-creator/app.js").read_text(encoding="utf-8")
        self.assertIn("promptEl.value", js)
        self.assertIn("buildPrompt", js)
        block = re.search(r"copyBtn\.addEventListener\([^{]+\{([\s\S]*?)\n    \}\);", js)
        self.assertIsNotNone(block)
        self.assertIn("promptEl.value", block.group(1))


if __name__ == "__main__":
    unittest.main()