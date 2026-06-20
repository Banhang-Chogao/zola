#!/usr/bin/env python3
"""Tests for scripts/qa_vaccines.py — the QA Vaccine Gate.

Two kinds of assertions:
  1. NEGATIVE — each FAIL detector must actually catch a synthetic broken repo
     (so the gate genuinely blocks known recurring bugs, not just passes).
  2. CALIBRATION — run_all() on the REAL repo must return failed == 0, so the
     reinforced gate stays green on current `main` and future false positives
     are caught by CI.

Run:
    python3 -m unittest scripts.test_qa_vaccines -v
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import qa_vaccines as qv  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


class TmpRepo:
    """Minimal on-disk repo for pointing a Ctx at synthetic files."""
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="qavax-"))

    def write(self, rel: str, content: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def ctx(self) -> qv.Ctx:
        return qv.Ctx(self.root)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class VaccineLoaderTest(unittest.TestCase):
    def test_loads_real_library(self):
        vaccines = qv.load_vaccines()
        self.assertGreaterEqual(len(vaccines), 12,
                                "expected the full V1..V12 library (plus compliance set)")
        codes = {v["code"] for v in vaccines}
        for needed in ("V1", "V5", "V8", "V12"):
            self.assertIn(needed, codes)

    def test_parses_synthetic_blocks(self):
        text = "#### V1 — first thing\nbody\n#### V99 — another\nbody"
        out = qv.load_vaccines(text)
        self.assertEqual([v["code"] for v in out], ["V1", "V99"])


class FailDetectorTest(unittest.TestCase):
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def test_v8a_tera_python_kwargs_fail(self):
        self.repo.write("templates/x.html",
                        '<p>{{ name | replace(old="-", new=" ") }}</p>')
        r = qv.check_v8a_tera_filter_kwargs(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertIn("V8", r.vaccine)

    def test_v8a_correct_from_to_pass(self):
        self.repo.write("templates/x.html",
                        '<p>{{ name | replace(from="-", to=" ") }}</p>')
        r = qv.check_v8a_tera_filter_kwargs(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_v8a_ignores_kwargs_in_comment(self):
        # A replace(old=…) written inside a Tera comment must NOT trip the gate.
        self.repo.write("templates/x.html",
                        '{# ví dụ sai: replace(old="-", new=" ") #}\n<p>ok</p>')
        r = qv.check_v8a_tera_filter_kwargs(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_v8b_unbalanced_block_fail(self):
        self.repo.write("templates/y.html", "{% if x %}\n<p>no endif</p>")
        r = qv.check_v8b_template_block_balance(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_v8b_balanced_block_pass(self):
        self.repo.write("templates/y.html",
                        "{% if x %}<p>a</p>{% else %}<p>b</p>{% endif %}\n"
                        "{% for i in xs %}{{ i }}{% endfor %}")
        r = qv.check_v8b_template_block_balance(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_dashboard_invalid_json_fail(self):
        self.repo.write("data/broken.json", "{ not: valid json, }")
        r = qv.check_dashboard_json(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_dashboard_valid_json_pass(self):
        self.repo.write("data/ok.json", '{"a": 1}')
        r = qv.check_dashboard_json(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_config_invalid_toml_fail(self):
        self.repo.write("config.toml", 'base_url = "x\nbroken = ')
        r = qv.check_config_toml(self.repo.ctx())
        # tomllib present on 3.11+ → FAIL; otherwise SKIP/WARN (still not PASS)
        self.assertIn(r.status, (qv.FAIL, qv.WARN, qv.SKIP))
        if r.status != qv.SKIP:
            self.assertNotEqual(r.status, qv.PASS)

    def test_paywall_missing_private_file_fail(self):
        self.repo.write("content/posting/p.md",
                        '+++\ntitle = "x"\n[extra]\npremium = true\n'
                        'premium_post_id = "premium-xyz-001"\n+++\nteaser')
        r = qv.check_paywall_integrity(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_paywall_with_private_file_pass(self):
        self.repo.write("content/posting/p.md",
                        '+++\ntitle = "x"\n[extra]\npremium = true\n'
                        'premium_post_id = "premium-xyz-001"\n+++\nteaser')
        self.repo.write("private_content/premium-xyz-001.md", "full body")
        r = qv.check_paywall_integrity(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_v1_bare_model_id_fail(self):
        self.repo.write("scripts/related_engine.py",
                        'MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"')
        r = qv.check_v1_hf_model_id(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_v1_org_qualified_pass(self):
        self.repo.write("scripts/related_engine.py",
                        'MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"')
        r = qv.check_v1_hf_model_id(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_v2_v1_syntax_fail(self):
        self.repo.write(".github/workflows/slack-notify.yml",
                        "env:\n  SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK\n")
        r = qv.check_v2_slack_v3(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_category_first_violation_warns(self):
        self.repo.write("content/posting/p.md",
                        '+++\ntitle = "x"\n[taxonomies]\ncategories = ["Banking"]\n+++\nbody')
        r = qv.check_category_first(self.repo.ctx())
        self.assertEqual(r.status, qv.WARN)

    def test_category_first_ok_pass(self):
        self.repo.write("content/posting/p.md",
                        '+++\ntitle = "x"\n[taxonomies]\ncategories = ["Tất cả", "Banking"]\n+++\nbody')
        r = qv.check_category_first(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)


class LinkUtilsLayerTest(unittest.TestCase):
    """V10-LINKS — the shared link-utils safety layer detector."""
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def test_missing_layer_fail(self):
        r = qv.check_v10_link_utils_layer(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_host_guard_drops_zola_fail(self):
        # The classic regression: a HOST guard makes /zola/* non-internal.
        self.repo.write("scripts/link_utils.py",
                        "def classify(u):\n"
                        "    return 'internal' if 'banhang-chogao.github.io' in u else 'skip'\n"
                        "def extract_urls(t):\n    return []\n")
        r = qv.check_v10_link_utils_layer(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("/zola/ invariant" in d for d in r.details))

    def test_code_span_leak_fail(self):
        # classify is fine, but extraction leaks links from code spans.
        self.repo.write("scripts/link_utils.py",
                        "def classify(u):\n"
                        "    if not u or u[0] == '#':\n        return 'skip'\n"
                        "    if u.startswith(('/', '@/', './', '../')):\n        return 'internal'\n"
                        "    if u.startswith(('http://', 'https://')):\n        return 'external'\n"
                        "    return 'skip'\n"
                        "import re\n"
                        "def extract_urls(t):\n"
                        "    return re.findall(r'\\]\\(([^)\\s]+)', t)\n")
        r = qv.check_v10_link_utils_layer(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_real_layer_pass(self):
        # Copy the real, correct link_utils + its sibling wiring → clean PASS.
        src = (REPO_ROOT / "scripts" / "link_utils.py").read_text(encoding="utf-8")
        self.repo.write("scripts/link_utils.py", src)
        self.repo.write("scripts/test_link_utils.py", "# tests present")
        self.repo.write("scripts/fix_site_prefix_links.py",
                        "from link_utils import code_span_ranges  # code-span aware")
        r = qv.check_v10_link_utils_layer(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_real_layer_missing_test_warns(self):
        # Invariant holds but the test/wiring layer is absent → WARN (not FAIL).
        src = (REPO_ROOT / "scripts" / "link_utils.py").read_text(encoding="utf-8")
        self.repo.write("scripts/link_utils.py", src)
        r = qv.check_v10_link_utils_layer(self.repo.ctx())
        self.assertEqual(r.status, qv.WARN)


class JsSyntaxTest(unittest.TestCase):
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_js_syntax_error_fail(self):
        self.repo.write("static/js/broken.js", "function ( { syntax error +=")
        r = qv.check_js_syntax(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_js_valid_pass(self):
        self.repo.write("static/js/ok.js", "const x = 1;\nfunction f(a){ return a+1; }")
        r = qv.check_js_syntax(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)


class SummaryTest(unittest.TestCase):
    def test_score_and_production_safe(self):
        ctx = qv.Ctx(REPO_ROOT)
        results = [
            qv.CheckResult("V1", "a", qv.PASS),
            qv.CheckResult("V2", "b", qv.PASS),
            qv.CheckResult("V8", "c", qv.WARN),
        ]
        s = qv.summarize(results, ctx)
        self.assertEqual(s["failed"], 0)
        self.assertEqual(s["warnings"], 1)
        self.assertTrue(s["production_safe"])
        self.assertEqual(s["score"], 96)  # 100 - 1*4

    def test_fail_caps_score_and_blocks(self):
        ctx = qv.Ctx(REPO_ROOT)
        results = [qv.CheckResult("V8", "c", qv.FAIL)]
        s = qv.summarize(results, ctx)
        self.assertFalse(s["production_safe"])
        self.assertLessEqual(s["score"], 60)
        self.assertTrue(qv.gate_failed(s))

    def test_strict_warn_blocks(self):
        ctx = qv.Ctx(REPO_ROOT)
        results = [qv.CheckResult("V8", "c", qv.WARN)]
        s = qv.summarize(results, ctx)
        self.assertFalse(qv.gate_failed(s, strict_warn=False))
        self.assertTrue(qv.gate_failed(s, strict_warn=True))


class UptimeMeTest(unittest.TestCase):
    """uptime_me_vaccine — no key leak · schema · route · card · freshness."""
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    SEED = ('{"checked_at":"","ok":false,'
            '"summary":{"total":0,"up":0,"down":0,"paused":0,"breathing":"chưa rõ"},'
            '"accounts":[],"monitors":[],"incidents":[],"stale":true}')

    def _wire(self, **over):
        self.repo.write("data/uptime-me.json", over.get("json", self.SEED))
        self.repo.write("content/tools/uptime-me.md", over.get("md", '+++\ntitle="x"\n+++'))
        self.repo.write("templates/uptime-me.html",
                        over.get("tmpl", '{% set u = load_data(path="data/uptime-me.json", required=false) %}'))
        self.repo.write("content/tools/_index.md",
                        over.get("idx", 'url = "$BASE_URL/tools/uptime-me"'))
        self.repo.write("scripts/fetch_uptime_me.py", over.get("script", "# env only"))
        self.repo.write(".github/workflows/uptime-me.yml", over.get("wf", "secrets only"))
        self.repo.write("static/js/uptime-me.js", over.get("js", "// no keys"))
        return self.repo.ctx()

    def test_real_repo_passes(self):
        r = qv.check_uptime_me(qv.Ctx(REPO_ROOT))
        self.assertIn(r.status, (qv.PASS, qv.WARN))  # never FAIL on committed repo
        self.assertNotEqual(r.status, qv.FAIL)

    def test_seed_baseline_passes(self):
        r = qv.check_uptime_me(self._wire())
        self.assertEqual(r.status, qv.PASS)

    def test_api_key_leak_fails(self):
        leaked = self.SEED.replace('"stale":true',
                                   '"stale":true,"oops":"u1234567-abcdef0123456789abcdef99"')
        r = qv.check_uptime_me(self._wire(json=leaked))
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("API key" in d for d in r.details))

    def test_broken_schema_fails(self):
        r = qv.check_uptime_me(self._wire(json='{"checked_at":""}'))
        self.assertEqual(r.status, qv.FAIL)

    def test_missing_card_link_fails(self):
        r = qv.check_uptime_me(self._wire(idx='url = "$BASE_URL/tools/other"'))
        self.assertEqual(r.status, qv.FAIL)

    def test_stale_report_warns(self):
        old = ('{"checked_at":"2000-01-01T00:00:00+00:00","ok":true,'
               '"summary":{"total":1,"up":1,"down":0,"paused":0,"breathing":"ok"},'
               '"accounts":[],"monitors":[],"incidents":[]}')
        r = qv.check_uptime_me(self._wire(json=old))
        self.assertEqual(r.status, qv.WARN)


class RealRepoCalibrationTest(unittest.TestCase):
    """The reinforced gate must be GREEN on current main (0 FAIL), or it would
    block every merge. Warnings are allowed (they surface latent issues)."""
    def test_real_repo_has_no_failures(self):
        results, summary = qv.run_all(REPO_ROOT)
        failed = [r for r in results if r.status == qv.FAIL]
        msg = "\n".join(f"{r.vaccine} {r.title}: {r.diagnosis}" for r in failed)
        self.assertEqual(summary["failed"], 0, f"unexpected FAIL on main:\n{msg}")
        self.assertTrue(summary["production_safe"])
        self.assertGreaterEqual(summary["vaccines_loaded"], 12)


if __name__ == "__main__":
    unittest.main()
