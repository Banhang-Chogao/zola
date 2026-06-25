"""Tests for ai_diagnose.py — free Tier-1 heuristics."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent / "ai_diagnose.py"
_spec = importlib.util.spec_from_file_location("ai_diagnose", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["ai_diagnose"] = mod
_spec.loader.exec_module(mod)


LOG_HF_401 = """
build-related  Error downloading model
401 Client Error: Unauthorized for url: https://huggingface.co/paraphrase-multilingual-MiniLM-L12-v2
"""

LOG_PYTHON_DEP = """
qa-gate  Traceback (most recent call last):
ModuleNotFoundError: No module named 'sentence_transformers'
"""

LOG_TERA = """
zola build  Error: Failed to build the site
Variable `section.extra.foo` not found in templates/partials/head.html
"""

LOG_SCSS = """
sass/custom.scss:42:5 invalid syntax: expected selector
Error: Undefined variable: $brand-primary
"""

_LOG_MERGE_MARKERS = "\n".join(
    ("<" * 7 + " HEAD", "=" * 7, ">" * 7 + " origin/main")
)
LOG_MERGE = f"""
git merge  CONFLICT (content): Merge conflict in content/blog/post.md
{_LOG_MERGE_MARKERS}
"""

LOG_ZOLA_ANCHOR = """
Failed to build the site
Error parsing heading anchor in content/seo/bai-2.md
"""

LOG_UNKNOWN = """
Something weird happened
Process exited with code 1
"""


class AiDiagnoseTest(unittest.TestCase):
    def test_hf_401_high_confidence(self):
        d = mod.diagnose_tier1(LOG_HF_401)
        self.assertEqual(d.pattern_id, "HF_401")
        self.assertGreaterEqual(d.confidence, 85)
        self.assertIn("HuggingFace", d.root_cause)

    def test_python_dep(self):
        d = mod.diagnose_tier1(LOG_PYTHON_DEP)
        self.assertEqual(d.pattern_id, "PYTHON_DEP")
        self.assertIn("sentence_transformers", d.affected_files)

    def test_tera_template(self):
        d = mod.diagnose_tier1(LOG_TERA)
        self.assertEqual(d.pattern_id, "TERA_TEMPLATE")
        self.assertGreaterEqual(d.confidence, 80)

    def test_scss_error(self):
        d = mod.diagnose_tier1(LOG_SCSS)
        self.assertEqual(d.pattern_id, "SCSS_ERROR")

    def test_merge_conflict(self):
        d = mod.diagnose_tier1(LOG_MERGE)
        self.assertEqual(d.pattern_id, "MERGE_CONFLICT")
        self.assertGreaterEqual(d.confidence, 90)

    def test_zola_anchor(self):
        d = mod.diagnose_tier1(LOG_ZOLA_ANCHOR)
        self.assertIn(d.pattern_id, ("ZOLA_ANCHOR", "ZOLA_BUILD", "FRONTMATTER"))

    def test_unknown_low_confidence(self):
        d = mod.diagnose_tier1(LOG_UNKNOWN)
        self.assertEqual(d.pattern_id, "UNKNOWN")
        self.assertLess(d.confidence, mod.LOW_CONFIDENCE_THRESHOLD)

    def test_empty_log(self):
        d = mod.diagnose_tier1("")
        self.assertEqual(d.pattern_id, "EMPTY_LOG")

    def test_format_text_fields(self):
        d = mod.diagnose_tier1(LOG_HF_401)
        text = mod.format_text(d)
        self.assertIn("Likely root cause", text)
        self.assertIn("Confidence score", text)
        self.assertIn("Suggested fix", text)
        self.assertIn("Affected files", text)

    def test_format_markdown(self):
        d = mod.diagnose_tier1(LOG_PYTHON_DEP)
        md = mod.format_markdown(d, run_url="https://example.com/run/1")
        self.assertIn("AI Diagnose (free-first)", md)
        self.assertIn("example.com/run/1", md)

    def test_tier1_only_skips_claude_env(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"AI_DIAGNOSE_USE_CLAUDE": "1", "ANTHROPIC_API_KEY": "sk-test"}):
            d = mod.diagnose_tier1(LOG_UNKNOWN)
            self.assertEqual(d.tier, "heuristic")

    def test_diagnosis_to_dict(self):
        d = mod.diagnose_tier1(LOG_HF_401)
        payload = d.to_dict()
        self.assertIn("root_cause", payload)
        self.assertIn("confidence", payload)


if __name__ == "__main__":
    unittest.main()