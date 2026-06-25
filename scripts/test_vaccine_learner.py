#!/usr/bin/env python3
"""Tests for scripts/vaccine_learner.py — ML-assisted vaccine learning."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaccine_learner as vl  # noqa: E402


HF_LOG = """
2026-06-20T10:00:01Z snapshot_download failed
huggingface_hub.utils._errors.RepositoryNotFoundError: 401 Client Error.
Repository Not Found for url: https://huggingface.co/api/models/paraphrase-MiniLM
Invalid username or password.
scripts/build_related.py line 42
"""

HF_LOG_VARIANT = """
[run 9931] 2026-06-21T11:22:33Z snapshot_download error
401 Client Error. Repository Not Found for url: https://huggingface.co/api/models/foo
Invalid username or password. in scripts/build_related.py
"""

LINK_LOG = """
qa-404-checker.py: 3 broken internal links found
content/posting/foo.md -> /zola/pages/privacy/ (404)
exit code 2
"""


class TestNormalization(unittest.TestCase):
    def test_digits_and_hashes_stripped(self):
        toks = vl.normalize_tokens("error 12345 0xABCDEF abcdef1234567 build_related")
        self.assertNotIn("12345", toks)
        self.assertIn("build_related", toks)
        # 'build' is a stopword; identifier with underscore survives
        self.assertTrue(any("related" in t for t in toks))

    def test_same_failure_different_runids_same_signature(self):
        a = set(vl.normalize_tokens(HF_LOG))
        b = set(vl.normalize_tokens(HF_LOG_VARIANT))
        overlap = len(a & b) / max(1, len(a | b))
        self.assertGreater(overlap, 0.5)


class TestCosine(unittest.TestCase):
    def test_identical_is_one(self):
        v = {"a": 1.0, "b": 2.0}
        self.assertAlmostEqual(vl.cosine(v, v), 1.0, places=6)

    def test_disjoint_is_zero(self):
        self.assertEqual(vl.cosine({"a": 1.0}, {"b": 1.0}), 0.0)


class TestLearnAndMatch(unittest.TestCase):
    def _store(self, tmp):
        return Path(tmp) / "learned.jsonl"

    def test_learn_then_match_variant(self):
        cases = []
        case, merged = vl.learn(
            logs=HF_LOG, root_cause="HF model id missing org prefix",
            fix_summary="org-qualify MODEL_NAME", files_changed=["scripts/build_related.py"],
            fix_tool="manual", proof_command="python3 scripts/qa_vaccines.py",
            risk="medium", confidence=90, cases=cases, persist=False,
        )
        self.assertFalse(merged)
        self.assertEqual(case.vaccine_code, "VL1")
        # A different run of the SAME failure should match the learned case.
        res = vl.match(HF_LOG_VARIANT, cases=cases)
        self.assertTrue(res.matched)
        self.assertEqual(res.case.vaccine_code, "VL1")
        self.assertGreater(res.confidence, 40)

    def test_unrelated_log_does_not_match(self):
        cases = []
        vl.learn(logs=HF_LOG, root_cause="hf", fix_summary="fix",
                 fix_tool="manual", risk="medium", cases=cases, persist=False)
        res = vl.match("totally unrelated cabbage recipe text here", cases=cases)
        self.assertFalse(res.matched)

    def test_dedup_on_learn(self):
        cases = []
        vl.learn(logs=HF_LOG, root_cause="hf", fix_summary="a",
                 fix_tool="manual", risk="medium", cases=cases, persist=False)
        _, merged = vl.learn(logs=HF_LOG_VARIANT, root_cause="hf", fix_summary="b",
                             fix_tool="manual", risk="medium", cases=cases, persist=False)
        self.assertTrue(merged)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].occurrences, 2)


class TestAutoApplyGating(unittest.TestCase):
    def test_low_risk_safe_tool_is_auto_applicable(self):
        cases = []
        vl.learn(logs=LINK_LOG, root_cause="broken internal link",
                 fix_summary="run --fix", fix_tool="internal-link-fix",
                 risk="low", confidence=95, cases=cases, persist=False)
        res = vl.match(LINK_LOG, cases=cases)
        self.assertTrue(res.matched)
        self.assertTrue(res.auto_applicable)

    def test_manual_tool_never_auto_applicable(self):
        cases = []
        vl.learn(logs=HF_LOG, root_cause="hf", fix_summary="fix",
                 fix_tool="manual", risk="low", confidence=99, cases=cases, persist=False)
        res = vl.match(HF_LOG, cases=cases)
        self.assertFalse(res.auto_applicable)

    def test_high_risk_never_auto_applicable(self):
        cases = []
        vl.learn(logs=LINK_LOG, root_cause="x", fix_summary="y",
                 fix_tool="internal-link-fix", risk="high", confidence=99,
                 cases=cases, persist=False)
        res = vl.match(LINK_LOG, cases=cases)
        self.assertFalse(res.auto_applicable)

    def test_apply_refuses_non_auto(self):
        case = vl.LearnedCase(
            id="x", vaccine_code="VL9", title="t", pattern_id="P",
            root_cause="r", fix_summary="f", fix_tool="manual",
            proof_command="", risk="high", confidence=99,
        )
        res = vl.MatchResult(True, 99, 0.9, case, False, "suggest only")
        out = vl.apply_fix(res)
        self.assertFalse(out["applied"])


class TestRiskInference(unittest.TestCase):
    def test_content_change_is_high(self):
        self.assertEqual(vl._infer_risk("manual", ["content/posting/x.md"]), "high")

    def test_safe_tool_is_low(self):
        self.assertEqual(vl._infer_risk("internal-link-fix", []), "low")


class TestPersistence(unittest.TestCase):
    def test_round_trip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learned.jsonl"
            cases = []
            vl.learn(logs=HF_LOG, root_cause="hf", fix_summary="fix",
                     fix_tool="manual", risk="medium", cases=cases, persist=False)
            vl.save_store(cases, path)
            reloaded = vl.load_store(path)
            self.assertEqual(len(reloaded), 1)
            self.assertEqual(reloaded[0].vaccine_code, "VL1")

    def test_corrupt_line_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learned.jsonl"
            path.write_text('{"bad json\nnot json at all\n', encoding="utf-8")
            self.assertEqual(vl.load_store(path), [])


if __name__ == "__main__":
    unittest.main()
