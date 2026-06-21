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


class SidebarLayoutTest(unittest.TestCase):
    """sidebar_layout_vaccine — menu/sidebar must be in-grid, not a fixed/absolute
    overlay covering content (regression: PR #526 right-column nav)."""

    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def _baseline(self, **over):
        sidenav = over.get("sidenav",
            ".side-nav { position: sticky; top: 1rem; z-index: 5; }\n"
            ".side-nav__link { color: red; }\n"
            "@media (max-width: 960px) { .side-nav { display: none; } }\n")
        sidebar = over.get("sidebar", ".sidebar { display: flex; flex-direction: column; }\n")
        layout = over.get("layout",
            ".layout-grid { display: grid; grid-template-columns: minmax(0, 1fr) 400px; }\n"
            ".main-column { min-width: 0; }\n"
            "@media (max-width: 960px) { .layout-grid { grid-template-columns: 1fr; } }\n")
        base = over.get("base",
            '<div class="nav-drawer" id="nav-drawer" hidden></div>\n')
        self.repo.write("sass/_side-nav.scss", sidenav)
        self.repo.write("sass/_sidebar.scss", sidebar)
        self.repo.write("sass/_layout.scss", layout)
        self.repo.write("templates/base.html", base)
        return self.repo.ctx()

    def test_real_repo_passes(self):
        # Calibration: the committed layout is in-grid sticky → PASS (no overlay).
        r = qv.check_sidebar_layout(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS)

    def test_baseline_passes(self):
        r = qv.check_sidebar_layout(self._baseline())
        self.assertEqual(r.status, qv.PASS)

    def test_side_nav_fixed_overlay_fails(self):
        ctx = self._baseline(
            sidenav=".side-nav { position: fixed; top: 0; z-index: 999; }\n")
        r = qv.check_sidebar_layout(ctx)
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("side-nav" in d for d in r.details))

    def test_sidebar_absolute_fails(self):
        ctx = self._baseline(sidebar=".sidebar { position: absolute; right: 0; }\n")
        r = qv.check_sidebar_layout(ctx)
        self.assertEqual(r.status, qv.FAIL)

    def test_single_track_grid_fails(self):
        # Only a 1-column grid anywhere → sidebar column not reserved → overlap risk.
        ctx = self._baseline(
            layout=".layout-grid { display: grid; grid-template-columns: 1fr; }\n"
                   ".main-column { min-width: 0; }\n")
        r = qv.check_sidebar_layout(ctx)
        self.assertEqual(r.status, qv.FAIL)

    def test_missing_min_width_warns(self):
        ctx = self._baseline(
            layout=".layout-grid { grid-template-columns: minmax(0, 1fr) 400px; }\n"
                   ".main-column { padding: 0; }\n"
                   "@media (max-width: 960px) { .layout-grid { grid-template-columns: 1fr; } }\n")
        r = qv.check_sidebar_layout(ctx)
        self.assertEqual(r.status, qv.WARN)


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


class DeployMonitorTest(unittest.TestCase):
    """deploy_monitor_vaccine — no token leak · schema · footer · route · pending."""
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    SEED = ('{"checked_at":"","ok":false,"stale":true,'
            '"summary":{"prod_status":"unknown","pending_count":0,"avg_deploy_s":null},'
            '"pending":[],"recent":[]}')
    BASE = ('{% set dm = load_data(path="data/deploy-monitor.json", required=false) %}'
            '<details class="deploy-watch"><span>{{ d.pending_count }}</span>'
            '{% if dm.stale %}<span class="deploy-watch__stale">⚠</span>{% endif %}'
            '<a href="/tools/deploy-monitor/">x</a></details>')
    # Fetcher stub carrying every invariant the vaccine now enforces: deploy.yml
    # only, telemetry guard list, TTL/expiry, already-deployed guard.
    SCRIPT = ('WORKFLOW_FILE = "deploy.yml"\n'
              'TELEMETRY_WORKFLOWS = ("merge-report.yml",)\n'
              '_PENDING_TTL_S = 2700\n'
              'success_shas = set()  # already-deployed guard\n'
              '# expired in_progress runs are dropped from pending\nexpired = []\n')
    JS = 'const STALE_NONTERMINAL_MS = 1800000; // stale deploy guard\n'

    def _wire(self, **over):
        self.repo.write("data/deploy-monitor.json", over.get("json", self.SEED))
        self.repo.write("templates/base.html", over.get("base", self.BASE))
        self.repo.write("content/tools/deploy-monitor.md", over.get("md", '+++\ntitle="x"\n+++'))
        self.repo.write("templates/deploy-monitor.html", over.get("tmpl", "detail"))
        self.repo.write("content/tools/_index.md", over.get("idx", 'url = "$BASE_URL/tools/deploy-monitor"'))
        self.repo.write("scripts/fetch_deploy_monitor.py", over.get("script", self.SCRIPT))
        self.repo.write("static/js/deploy-status.js", over.get("js", self.JS))
        self.repo.write(".github/workflows/deploy-monitor.yml", over.get("wf", "secrets.GITHUB_TOKEN"))
        return self.repo.ctx()

    def test_real_repo_passes(self):
        r = qv.check_deploy_monitor(qv.Ctx(REPO_ROOT))
        self.assertNotEqual(r.status, qv.FAIL)

    def test_seed_baseline_passes(self):
        self.assertEqual(qv.check_deploy_monitor(self._wire()).status, qv.PASS)

    def test_token_leak_fails(self):
        leak = self.SEED.replace('"stale":true',
                                 '"stale":true,"oops":"ghp_' + "a" * 36 + '"')
        r = qv.check_deploy_monitor(self._wire(json=leak))
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("token" in d for d in r.details))

    def test_broken_schema_fails(self):
        self.assertEqual(qv.check_deploy_monitor(self._wire(json='{"checked_at":""}')).status, qv.FAIL)

    def test_footer_not_wired_fails(self):
        r = qv.check_deploy_monitor(self._wire(base='<footer>no widget</footer>'))
        self.assertEqual(r.status, qv.FAIL)

    def test_pending_count_not_shown_fails(self):
        base = ('{% set dm = load_data(path="data/deploy-monitor.json", required=false) %}'
                '<details class="deploy-watch"><a href="/tools/deploy-monitor/">x</a></details>')
        r = qv.check_deploy_monitor(self._wire(base=base))
        self.assertEqual(r.status, qv.FAIL)

    def test_missing_card_link_fails(self):
        r = qv.check_deploy_monitor(self._wire(idx='url = "$BASE_URL/tools/other"'))
        self.assertEqual(r.status, qv.FAIL)

    def test_stale_report_warns(self):
        old = ('{"checked_at":"2000-01-01T00:00:00+00:00","ok":true,"stale":false,'
               '"summary":{"prod_status":"green","pending_count":0,"avg_deploy_s":42},'
               '"pending":[],"recent":[]}')
        self.assertEqual(qv.check_deploy_monitor(self._wire(json=old)).status, qv.WARN)

    def test_telemetry_workflow_source_fails(self):
        # A report workflow used as a deploy-state source (no TELEMETRY guard) FAILs.
        bad = ('WORKFLOW_FILE = "deploy.yml"\n_PENDING_TTL_S = 1\nexpired = []\n'
               'success_shas = set()\nruns = query("merge-report.yml")\n')
        r = qv.check_deploy_monitor(self._wire(script=bad))
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("merge-report" in d for d in r.details))

    def test_missing_ttl_detection_fails(self):
        # No TTL/expiry → a stuck deploy would show "deploying" forever.
        bad = 'WORKFLOW_FILE = "deploy.yml"\nsuccess_shas = set()\n'
        r = qv.check_deploy_monitor(self._wire(script=bad))
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("TTL" in d or "expiry" in d for d in r.details))

    def test_js_missing_stale_guard_fails(self):
        r = qv.check_deploy_monitor(self._wire(js='function render(s){ /* no guard */ }'))
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("stale guard" in d for d in r.details))


class SeomoneyBrandTest(unittest.TestCase):
    """seomoney_brand_vaccine — site brand SEOMONEY, author Duy Nguyen, OG + placeholders."""
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def _wire(self, title="SEOMONEY", **over):
        self.repo.write("config.toml",
                        over.get("cfg", f'base_url = "https://seomoney.org"\ntitle = "{title}"\n'
                                        '[extra]\nauthor = "duynguyenlog"\n'))
        self.repo.write("author.json", over.get("aj", '{"name": "Duy Nguyen"}'))
        self.repo.write("static/img/og/seomoney-og.svg", "<svg/>")
        self.repo.write("static/img/og/seomoney-og.og.webp", "RIFFwebp")
        self.repo.write("static/img/placeholder/placeholder.svg", "<svg/>")
        self.repo.write("static/img/placeholder/placeholder-2.svg", "<svg/>")
        self.repo.write("static/img/placeholder/placeholder-3.svg", "<svg/>")
        self.repo.write("templates/base.html", over.get("base",
                        'og:image "/img/og/seomoney-og.og.webp" placeholder-2.svg placeholder-3.svg'))
        return self.repo.ctx()

    def test_real_repo_passes(self):
        self.assertNotEqual(qv.check_seomoney_brand(qv.Ctx(REPO_ROOT)).status, qv.FAIL)

    def test_seomoney_baseline_passes(self):
        self.assertEqual(qv.check_seomoney_brand(self._wire()).status, qv.PASS)

    def test_brand_regression_fails(self):
        self.assertEqual(qv.check_seomoney_brand(self._wire(title="Duy Nguyen")).status, qv.FAIL)

    def test_author_identity_lost_fails(self):
        r = qv.check_seomoney_brand(self._wire(aj='{"name": "SEOMONEY"}'))
        self.assertEqual(r.status, qv.FAIL)

    def test_missing_og_default_fails(self):
        ctx = self._wire(base='no og here, placeholder-2.svg placeholder-3.svg')
        self.assertEqual(qv.check_seomoney_brand(ctx).status, qv.FAIL)


class RuntimeArtifactV18Test(unittest.TestCase):
    """V18 — Runtime artifact conflict regression: exact #551 conflict file set.

    Covers the self-conflict pattern where the V18 fix PR itself was blocked by
    the same volatile runtime artifacts it was trying to gitignore.
    Conflict file set: data/qa-rule-checker-state.json,
                       data/vaccine-hotfix-state.json,
                       data/vaccine-hotfix.log  (PR #551, 2026-06-20).
    """

    # The 3 exact files that conflicted in PR #551
    PR551_FILES = [
        "data/qa-rule-checker-state.json",
        "data/vaccine-hotfix-state.json",
        "data/vaccine-hotfix.log",
    ]
    # Full set of 6 volatile files that V18 gitignores
    ALL_VOLATILE = [
        "data/vaccine-hotfix-state.json",
        "data/vaccine-hotfix.log",
        "data/vaccine-autofixer-state.json",
        "data/vaccine-autofixer.log",
        "data/qa-rule-checker-state.json",
        "data/autofix-conflicts-state.json",
        "reports/rule-conflict-report.json",
        "reports/rule-conflict-report.md",
    ]

    def _make_git_repo(self) -> Path:
        """Create a minimal git repo in a temp dir for git ls-files tests."""
        import subprocess
        root = Path(tempfile.mkdtemp(prefix="qavax-v18-"))
        subprocess.run(["git", "init"], cwd=root, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=root, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, capture_output=True)
        return root

    def _cleanup(self, root: Path) -> None:
        shutil.rmtree(root, ignore_errors=True)

    def test_pr551_files_tracked_causes_fail(self):
        """FAIL when the 3 exact #551 conflict files are tracked by git."""
        root = self._make_git_repo()
        try:
            for rel in self.PR551_FILES:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('{"ts":"2026-06-20"}', encoding="utf-8")
            import subprocess
            subprocess.run(["git", "add"] + [str(root / f) for f in self.PR551_FILES],
                           cwd=root, capture_output=True, check=True)
            r = qv.check_v18_runtime_artifact_conflict(qv.Ctx(root))
            self.assertEqual(r.status, qv.FAIL,
                             f"Expected FAIL when #551 conflict files are tracked; got {r.status}: {r.details}")
            detail_text = " ".join(r.details)
            # At least one of the #551 files must be named in the failure
            self.assertTrue(
                any(f.split("/")[-1] in detail_text for f in self.PR551_FILES),
                f"Expected a #551 file name in details; got: {r.details}",
            )
        finally:
            self._cleanup(root)

    def test_pr551_files_untracked_passes(self):
        """PASS when #551 conflict files exist on disk but are NOT tracked by git."""
        root = self._make_git_repo()
        try:
            # Write gitignore + workflow + idempotent marker so WARN checks pass too
            (root / ".gitignore").write_text(
                "\n".join(self.ALL_VOLATILE), encoding="utf-8"
            )
            (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            wf_content = (
                "git add -A\n"
                "git restore --staged \\\n"
                "  data/vaccine-hotfix-state.json \\\n"
                "  data/vaccine-autofixer-state.json \\\n"
                "  data/qa-rule-checker-state.json \\\n"
                "  reports/rule-conflict-report.json \\\n"
                "  reports/rule-conflict-report.md \\\n"
                "  2>/dev/null || true\n"
            )
            (root / ".github" / "workflows" / "vaccine-hotfix.yml").write_text(wf_content, encoding="utf-8")
            (root / ".github" / "workflows" / "vaccine-autofixer.yml").write_text(wf_content, encoding="utf-8")
            (root / "scripts").mkdir(exist_ok=True)
            (root / "scripts" / "qa-auto-rule-checker.py").write_text(
                "total_conflicts = 0  # idempotent: skip write when count unchanged", encoding="utf-8"
            )
            # Write the files but DO NOT git add them
            for rel in self.PR551_FILES:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('{"ts":"2026-06-20"}', encoding="utf-8")
            r = qv.check_v18_runtime_artifact_conflict(qv.Ctx(root))
            self.assertEqual(r.status, qv.PASS,
                             f"Expected PASS when #551 files untracked; got {r.status}: {r.details}")
        finally:
            self._cleanup(root)

    def test_missing_restore_staged_warns(self):
        """WARN when vaccine-hotfix.yml lacks the git restore --staged filter."""
        root = self._make_git_repo()
        try:
            (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (root / ".github" / "workflows" / "vaccine-hotfix.yml").write_text(
                "git add -A\ngit commit -m fix", encoding="utf-8"
            )
            (root / "scripts").mkdir(exist_ok=True)
            (root / "scripts" / "qa-auto-rule-checker.py").write_text(
                "# no meaningful change — skip", encoding="utf-8"
            )
            r = qv.check_v18_runtime_artifact_conflict(qv.Ctx(root))
            self.assertIn(r.status, (qv.WARN, qv.FAIL),
                          f"Expected WARN/FAIL for missing restore filter; got {r.status}")
        finally:
            self._cleanup(root)

    def test_real_repo_v18_passes(self):
        """V18 detector must PASS on the current repo (0 volatile files tracked)."""
        r = qv.check_v18_runtime_artifact_conflict(qv.Ctx(REPO_ROOT))
        self.assertNotEqual(r.status, qv.FAIL,
                            f"V18 FAIL on real repo — volatile files still tracked: {r.details}")

    def test_all_volatile_files_gitignored(self):
        """All 6 V18 volatile files must be in .gitignore of the real repo."""
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for rel in self.ALL_VOLATILE:
            fname = rel.split("/")[-1]
            self.assertIn(fname, gitignore,
                          f"V18: {fname} not found in .gitignore — will cause merge conflicts")

    def test_v18_self_conflict_resolve_by_rm_cached(self):
        """Regression: V18 self-conflict (PR #551) must be resolvable by git rm --cached.

        This test verifies the exact resolution procedure: when the 3 conflict
        files are tracked and then git rm --cached'd, the detector returns PASS.
        """
        root = self._make_git_repo()
        try:
            import subprocess
            # Step 1: track the PR #551 files BEFORE writing .gitignore
            # (simulates the pre-fix state where volatile files were tracked)
            for rel in self.PR551_FILES:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("{}", encoding="utf-8")
                subprocess.run(["git", "add", str(p)], cwd=root, capture_output=True)

            # Confirm it's FAIL before fix: no .gitignore yet → missing patterns → FAIL
            r_before = qv.check_v18_runtime_artifact_conflict(qv.Ctx(root))
            self.assertEqual(r_before.status, qv.FAIL,
                             f"Expected FAIL (missing gitignore patterns); got {r_before.status}: {r_before.details}")

            # Step 2: add workflows + gitignore + idempotent marker (the V18 fix)
            (root / ".gitignore").write_text("\n".join(self.ALL_VOLATILE), encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            wf = (
                "git add -A\n"
                "git restore --staged \\\n"
                "  data/vaccine-hotfix-state.json \\\n"
                "  data/qa-rule-checker-state.json \\\n"
                "  reports/rule-conflict-report.json \\\n"
                "  reports/rule-conflict-report.md \\\n"
                "  2>/dev/null || true\n"
            )
            (root / ".github" / "workflows" / "vaccine-hotfix.yml").write_text(wf, encoding="utf-8")
            (root / ".github" / "workflows" / "vaccine-autofixer.yml").write_text(wf, encoding="utf-8")
            (root / "scripts").mkdir(exist_ok=True)
            (root / "scripts" / "qa-auto-rule-checker.py").write_text(
                "total_conflicts = 0  # idempotent: skip write when count unchanged", encoding="utf-8"
            )

            # Apply the FIXER: git rm --cached
            subprocess.run(
                ["git", "rm", "--cached"] + [str(root / f) for f in self.PR551_FILES],
                cwd=root, capture_output=True,
            )

            r_after = qv.check_v18_runtime_artifact_conflict(qv.Ctx(root))
            self.assertNotEqual(r_after.status, qv.FAIL,
                                f"After git rm --cached, expected PASS; got {r_after.status}")
        finally:
            self._cleanup(root)


class RuntimeArtifactVaccineTest(unittest.TestCase):
    """V18 regression: exact PR #555 conflict file set must be gitignored and
    the vaccine-autofixer workflow must filter them before commit.

    PR #555 conflict files:
      data/qa-rule-checker-state.json
      reports/rule-conflict-report.json
      reports/rule-conflict-report.md
    Related volatile siblings:
      data/vaccine-autofixer-state.json
      data/vaccine-autofixer.log
      data/autofix-conflicts-state.json
    """

    # Minimal gitignore containing all required patterns.
    GITIGNORE_GOOD = (
        "data/vaccine-autofixer-state.json\n"
        "data/vaccine-autofixer.log\n"
        "data/qa-rule-checker-state.json\n"
        "data/autofix-conflicts-state.json\n"
        "reports/rule-conflict-report.json\n"
        "reports/rule-conflict-report.md\n"
    )

    # Minimal vaccine-autofixer.yml with the V18 git restore guard.
    WORKFLOW_GOOD = (
        "git add -A\n"
        "git restore --staged \\\n"
        "  data/vaccine-autofixer-state.json \\\n"
        "  data/qa-rule-checker-state.json \\\n"
        "  reports/rule-conflict-report.json \\\n"
        "  reports/rule-conflict-report.md \\\n"
        "  2>/dev/null || true\n"
    )

    def _ctx(self, gitignore: str = GITIGNORE_GOOD, workflow: str = WORKFLOW_GOOD) -> "qv.Ctx":
        r = TmpRepo()
        r.write(".gitignore", gitignore)
        r.write(".github/workflows/vaccine-autofixer.yml", workflow)
        r.write("scripts/qa-auto-rule-checker.py",
                "def write_reports(p, m):\n    # idempotent: total_conflicts check\n    pass\n")
        return r.ctx()

    def test_pass_when_all_patterns_present(self):
        """All 6 PR-#555 volatile files gitignored + workflow filter → PASS."""
        self.assertEqual(qv.check_v18_runtime_artifact_conflict(self._ctx()).status, qv.PASS)

    def test_real_repo_passes(self):
        """Real repo on current main must pass V18 (calibration)."""
        r = qv.check_v18_runtime_artifact_conflict(qv.Ctx(REPO_ROOT))
        self.assertNotEqual(r.status, qv.FAIL,
                            f"V18 FAIL on main — {r.diagnosis}")

    def test_missing_gitignore_patterns_fails(self):
        """Missing gitignore entries for the exact #555 files → FAIL."""
        ctx = self._ctx(gitignore="# nothing\n")
        r = qv.check_v18_runtime_artifact_conflict(ctx)
        self.assertEqual(r.status, qv.FAIL)
        self.assertIn("gitignore", r.diagnosis.lower())

    def test_missing_workflow_filter_fails(self):
        """vaccine-autofixer.yml without git restore --staged filter → FAIL."""
        ctx = self._ctx(workflow="git add -A\ngit commit -m 'x'\n")
        r = qv.check_v18_runtime_artifact_conflict(ctx)
        self.assertEqual(r.status, qv.FAIL)
        self.assertIn("git restore", r.diagnosis)

    def test_pr555_exact_conflict_set_covered(self):
        """Every file in the exact PR #555 conflict set must appear in .gitignore."""
        pr555_files = [
            "data/qa-rule-checker-state.json",
            "reports/rule-conflict-report.json",
            "reports/rule-conflict-report.md",
        ]
        ctx = self._ctx()
        # Good baseline passes
        self.assertEqual(qv.check_v18_runtime_artifact_conflict(ctx).status, qv.PASS)

        # Removing any one PR #555 file from gitignore → FAIL
        for f in pr555_files:
            bad_gi = self.GITIGNORE_GOOD.replace(f + "\n", "")
            ctx2 = self._ctx(gitignore=bad_gi)
            r = qv.check_v18_runtime_artifact_conflict(ctx2)
            self.assertEqual(r.status, qv.FAIL,
                             f"Expected FAIL when {f!r} missing from .gitignore")


class DomainMigrationDriftTest(unittest.TestCase):
    """V19 — Domain Migration Drift detector tests."""

    def _ctx(self, base_url="https://seomoney.org", cname="seomoney.org",
             snap_url=None, extra_files=None):
        """Build a minimal Ctx with the given config values."""
        import tempfile, os
        td = Path(tempfile.mkdtemp())
        # config.toml
        (td / "config.toml").write_text(f'base_url = "{base_url}"\n', encoding="utf-8")
        # CNAME
        (td / "static").mkdir(parents=True, exist_ok=True)
        (td / "static" / "CNAME").write_text(cname + "\n", encoding="utf-8")
        # snapshot
        if snap_url is not None:
            (td / "data").mkdir(parents=True, exist_ok=True)
            import json
            (td / "data" / "performance-audit-snapshot.json").write_text(
                json.dumps({"url": snap_url}), encoding="utf-8")
        # extra files with stale refs
        if extra_files:
            for rel, content in extra_files.items():
                p = td / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
        return qv.Ctx(td)

    def test_clean_state_passes(self):
        """No stale refs, correct config → PASS."""
        ctx = self._ctx(snap_url="https://seomoney.org/")
        r = qv.check_v19_domain_migration_drift(ctx)
        self.assertEqual(r.status, qv.PASS)

    def test_old_base_url_fails(self):
        """base_url holding github.io → FAIL."""
        ctx = self._ctx(base_url="https://banhang-chogao.github.io/zola",
                        cname="seomoney.org")
        r = qv.check_v19_domain_migration_drift(ctx)
        self.assertEqual(r.status, qv.FAIL)
        self.assertIn("github.io", r.diagnosis)

    def test_old_cname_fails(self):
        """CNAME holding github.io → FAIL."""
        ctx = self._ctx(cname="banhang-chogao.github.io")
        r = qv.check_v19_domain_migration_drift(ctx)
        self.assertEqual(r.status, qv.FAIL)

    def test_stale_snapshot_url_warns(self):
        """performance-audit-snapshot.json with old url → WARN."""
        ctx = self._ctx(snap_url="https://banhang-chogao.github.io/zola/")
        r = qv.check_v19_domain_migration_drift(ctx)
        self.assertEqual(r.status, qv.WARN)
        self.assertTrue(any("performance-audit-snapshot" in d for d in r.details))

    def test_stale_comment_in_script_warns(self):
        """Script file with github.io/zola comment → WARN."""
        ctx = self._ctx(extra_files={
            "scripts/some_tool.py": "# links to banhang-chogao.github.io/zola/posting/x/\n"
        })
        r = qv.check_v19_domain_migration_drift(ctx)
        self.assertEqual(r.status, qv.WARN)

    def test_real_repo_passes_or_warns_not_fails(self):
        """Real repo must not FAIL V19 after migration fixes applied."""
        r = qv.check_v19_domain_migration_drift(qv.Ctx(REPO_ROOT))
        self.assertNotEqual(r.status, qv.FAIL,
                            f"V19 FAIL on main — {r.diagnosis}")


class SearchUiVaccineTest(unittest.TestCase):
    """search_ui_vaccine — the search dialog must render a styled, native,
    responsive surface with its markup + engine intact (no raw/default UI)."""

    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    # A minimal, well-formed search component the detector should PASS on.
    _GOOD_SCSS = (
        ".site-search { position: fixed; inset: 0; z-index: 10050; display: flex; }\n"
        ".site-search[hidden] { display: none; }\n"
        ".site-search__panel { max-width: 640px; border-radius: 16px; }\n"
        ".site-search__field { display: flex; border: 1px solid; }\n"
        ".site-search__submit { background: var(--c-accent); padding: 0 1.4rem; }\n"
        ".site-search__result { border: 1px solid; padding: 0.9rem; }\n"
        "@media (max-width: 720px) { .site-search__panel { max-width: 100%; } }\n"
    )
    _GOOD_BASE = (
        '<div class="site-search" data-site-search hidden>'
        '<button data-search-close></button>'
        '<input data-search-input>'
        '<button class="site-search__submit">Tìm</button></div>'
        '<script id="site-search-data">[]</script>'
    )
    _GOOD_JS = "function renderResults(q){ return q; }\n"

    def _wire_good(self):
        self.repo.write("sass/_site-search.scss", self._GOOD_SCSS)
        self.repo.write("sass/site.scss", '@import "site-search";\n')
        self.repo.write("templates/base.html", self._GOOD_BASE)
        self.repo.write("static/js/site-search.js", self._GOOD_JS)

    def test_missing_partial_fails(self):
        # Markup + engine present, but no structural SCSS → raw render → FAIL.
        self.repo.write("sass/site.scss", "@import \"post\";\n")
        self.repo.write("templates/base.html", self._GOOD_BASE)
        self.repo.write("static/js/site-search.js", self._GOOD_JS)
        r = qv.check_search_ui_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("_site-search.scss" in d for d in r.details))

    def test_not_imported_fails(self):
        self._wire_good()
        self.repo.write("sass/site.scss", '@import "post";\n')  # partial not imported
        r = qv.check_search_ui_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("@import" in d or "site.scss" in d for d in r.details))

    def test_raw_layout_fails(self):
        # Partial exists & imported but has no positioning / panel / submit → raw.
        self.repo.write("sass/_site-search.scss", ".site-search__title { color: blue; }\n")
        self.repo.write("sass/site.scss", '@import "site-search";\n')
        self.repo.write("templates/base.html", self._GOOD_BASE)
        self.repo.write("static/js/site-search.js", self._GOOD_JS)
        r = qv.check_search_ui_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_missing_input_markup_fails(self):
        self._wire_good()
        # Strip the input hook the engine needs → search logic broken.
        self.repo.write("templates/base.html",
                        self._GOOD_BASE.replace("data-search-input", "data-x-input"))
        r = qv.check_search_ui_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_missing_engine_fails(self):
        self.repo.write("sass/_site-search.scss", self._GOOD_SCSS)
        self.repo.write("sass/site.scss", '@import "site-search";\n')
        self.repo.write("templates/base.html", self._GOOD_BASE)
        # No static/js/site-search.js at all.
        r = qv.check_search_ui_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_no_mobile_query_warns(self):
        good = dict(scss=self._GOOD_SCSS.replace(
            "@media (max-width: 720px) { .site-search__panel { max-width: 100%; } }\n", ""))
        self.repo.write("sass/_site-search.scss", good["scss"])
        self.repo.write("sass/site.scss", '@import "site-search";\n')
        self.repo.write("templates/base.html", self._GOOD_BASE)
        self.repo.write("static/js/site-search.js", self._GOOD_JS)
        r = qv.check_search_ui_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.WARN)
        self.assertTrue(any("mobile" in d.lower() or "720px" in d for d in r.details))

    def test_good_component_passes(self):
        self._wire_good()
        r = qv.check_search_ui_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_real_repo_passes(self):
        """The shipped search UI must PASS on the real repo (calibration)."""
        r = qv.check_search_ui_vaccine(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS, f"search_ui_vaccine not PASS: {r.diagnosis} {r.details}")


class EditorPublishVaccineTest(unittest.TestCase):
    """EDITOR-PUBLISH — saving in /editor/ must commit to GitHub (not download),
    edits must send SHA, the SEO rail must hydrate old posts, and sticky must be
    single-active (backend auto-unstick)."""

    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    _GOOD_JS = (
        "async function commitPostToGithub(payload){\n"
        "  const res = await fetch(AUTH_API + '/cms/save-post', {\n"
        "    method:'POST',\n"
        "    body: JSON.stringify({ slug: payload.slug, content: payload.content,\n"
        "      message: payload.message, sha: payload.sha || '' }) });\n"
        "  return res.json();\n"
        "}\n"
        "function saveAndCommit(){ const sha = state.editing ? state.editing.sha : null;\n"
        "  commitPostToGithub({ slug, content, message, sha }); }\n"
        "function dispatchHydrated(){ document.dispatchEvent(new CustomEvent('cms:hydrated')); }\n"
    )
    _GOOD_RAIL = "document.addEventListener('cms:hydrated', function(){ analyze(); });\n"
    _GOOD_BACKEND = (
        '@app.post("/cms/save-post")\n'
        "async def cms_save_post(): pass\n"
        "async def _demote_other_sticky_posts(): pass\n"
        "force_sticky and await _demote_other_sticky_posts(client, path, slug, token)\n"
    )

    def _wire_good(self):
        self.repo.write("static/js/editor.js", self._GOOD_JS)
        self.repo.write("static/js/cms/editor-seo-rail.js", self._GOOD_RAIL)
        self.repo.write("services/visitor-counter/main.py", self._GOOD_BACKEND)

    def test_good_passes(self):
        self._wire_good()
        r = qv.check_editor_publish_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS, f"{r.diagnosis} {r.details}")

    def test_missing_save_endpoint_fails(self):
        self._wire_good()
        self.repo.write("static/js/editor.js",
                        self._GOOD_JS.replace("/cms/save-post", "/cms/nope"))
        r = qv.check_editor_publish_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("save-post" in d for d in r.details))

    def test_draft_only_download_fails(self):
        self._wire_good()
        bad = self._GOOD_JS + (
            "function putPost(path, content){ const a=document.createElement('a');"
            " a.download = filename; a.click(); }\n")
        self.repo.write("static/js/editor.js", bad)
        r = qv.check_editor_publish_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("putPost" in d or "tải file" in d for d in r.details))

    def test_edit_without_sha_fails(self):
        self._wire_good()
        # Strip every SHA signal from the commit path.
        bad = (self._GOOD_JS
               .replace("sha: payload.sha || ''", "")
               .replace("const sha = state.editing ? state.editing.sha : null;", "")
               .replace("commitPostToGithub({ slug, content, message, sha });",
                        "commitPostToGithub({ slug, content, message });"))
        self.repo.write("static/js/editor.js", bad)
        r = qv.check_editor_publish_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("SHA" in d or "sha" in d for d in r.details))

    def test_seo_rail_no_hydrate_fails(self):
        self._wire_good()
        self.repo.write("static/js/cms/editor-seo-rail.js",
                        "function analyze(){}\n")  # no cms:hydrated listener
        r = qv.check_editor_publish_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("hydrate" in d.lower() or "cms:hydrated" in d for d in r.details))

    def test_backend_no_sticky_demote_fails(self):
        self._wire_good()
        self.repo.write("services/visitor-counter/main.py",
                        '@app.post("/cms/save-post")\nasync def cms_save_post(): pass\n')
        r = qv.check_editor_publish_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("sticky" in d.lower() for d in r.details))

    def test_sticky_hard_block_warns(self):
        self._wire_good()
        self.repo.write("static/js/editor.js",
                        self._GOOD_JS + "function ensureStickyAllowed(){ return false; }\n")
        r = qv.check_editor_publish_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.WARN)

    def test_real_repo_passes(self):
        """The shipped editor must PASS on the real repo (calibration)."""
        r = qv.check_editor_publish_vaccine(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS, f"editor_publish not PASS: {r.diagnosis} {r.details}")


class NoFloatingNavVaccineTest(unittest.TestCase):
    """V21 — No Floating Bar / Stable Nav. Desktop nav must stay in normal flow;
    floating/sticky/scroll-linked desktop nav → FAIL. Overlays/modals/search and
    the mobile drawer (or anything under a mobile @media) are exempt."""

    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    # ---- PASS cases -------------------------------------------------------
    def test_static_side_nav_passes(self):
        self.repo.write("sass/_side-nav.scss",
                        ".side-nav { position: static; background: #fff; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_normal_flow_no_position_passes(self):
        self.repo.write("sass/_side-nav.scss",
                        ".side-nav { background: #fff; padding: 1rem; }\n"
                        ".side-nav__actions { display: flex; margin-top: 0.5rem; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_mobile_drawer_fixed_is_exempt(self):
        # The hamburger drawer + toggle are overlays — fixed is allowed (not protected).
        self.repo.write("sass/_side-nav.scss",
                        ".side-nav { position: static; }\n"
                        ".nav-toggle { position: fixed; top: 14px; right: 14px; }\n"
                        ".nav-drawer { position: fixed; inset: 0; }\n"
                        ".nav-drawer__panel { position: absolute; transform: translateX(100%); }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_search_modal_fixed_is_exempt(self):
        self.repo.write("sass/_site-search.scss",
                        ".site-search { position: fixed; inset: 0; z-index: 10050; }\n"
                        ".site-search__panel { max-width: 640px; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_sticky_under_mobile_media_is_exempt(self):
        # A protected selector going sticky ONLY inside a mobile breakpoint is not
        # flagged — mobile is handled separately, do not break it here.
        self.repo.write("sass/_side-nav.scss",
                        ".side-nav { position: static; }\n"
                        "@media (max-width: 720px) {\n"
                        "  .side-nav { position: sticky; top: 0; }\n"
                        "}\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_commented_sticky_does_not_trip(self):
        self.repo.write("sass/_side-nav.scss",
                        "/* trước đây position: sticky; top: 1rem; */\n"
                        ".side-nav { position: static; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    # ---- FAIL cases -------------------------------------------------------
    def test_sticky_side_nav_fails(self):
        self.repo.write("sass/_side-nav.scss",
                        ".side-nav { position: sticky; top: 1rem; z-index: 5; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertEqual(r.vaccine, "V21")
        self.assertTrue(any("side-nav" in d for d in r.details))

    def test_fixed_side_nav_fails(self):
        self.repo.write("sass/_side-nav.scss",
                        ".side-nav { position: fixed; top: 0; left: 0; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_floating_bottom_action_bar_fails(self):
        self.repo.write("sass/_side-nav.scss",
                        ".side-nav { position: static; }\n"
                        ".side-nav__actions { position: fixed; bottom: 0; left: 0; right: 0; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("side-nav__actions" in d for d in r.details))

    def test_scroll_driven_animation_fails(self):
        self.repo.write("sass/_side-nav.scss",
                        ".primary-nav { animation-timeline: scroll(root block); "
                        "animation-name: drift; }\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_js_translate_on_scroll_fails(self):
        self.repo.write("sass/_side-nav.scss", ".side-nav { position: static; }\n")
        self.repo.write("static/js/side-nav.js",
                        "var el = document.querySelector('.side-nav');\n"
                        "window.addEventListener('scroll', function () {\n"
                        "  el.style.transform = 'translateY(' + window.scrollY + 'px)';\n"
                        "});\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any(".js" in d for d in r.details))

    def test_js_scroll_without_nav_token_passes(self):
        # A scroll handler that mutates style but never touches a nav element is fine.
        self.repo.write("sass/_x.scss", ".hero { color: red; }\n")
        self.repo.write("static/js/reveal.js",
                        "window.addEventListener('scroll', function () {\n"
                        "  document.querySelector('.hero').style.top = '0';\n"
                        "});\n")
        r = qv.check_no_floating_nav_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    # ---- calibration ------------------------------------------------------
    def test_real_repo_passes(self):
        """Current main keeps desktop nav static → V21 PASS (calibration)."""
        r = qv.check_no_floating_nav_vaccine(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS, f"V21 not PASS: {r.diagnosis} {r.details}")


class DomainRootUrlVaccineTest(unittest.TestCase):
    """DOMAIN-ROOT — scanner base-path /zola assumption detector tests."""

    def _ctx_with_config(self, base_url: str,
                         scanner_files: dict | None = None) -> "qv.Ctx":
        """Build a minimal Ctx with a config.toml and optional scanner files."""
        import tempfile
        td = Path(tempfile.mkdtemp(prefix="qavax-domroot-"))
        (td / "config.toml").write_text(f'base_url = "{base_url}"\n', encoding="utf-8")
        if scanner_files:
            for rel, content in scanner_files.items():
                p = td / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
        return qv.Ctx(td)

    def test_pass_when_root_domain(self):
        """config.toml base_url = seomoney.org (no /zola), clean scanner → PASS."""
        ctx = self._ctx_with_config(
            base_url="https://seomoney.org",
            scanner_files={
                "qa-404-checker.py": (
                    'BASE_URL = "https://seomoney.org"\n'
                    'SITE_PREFIX = ""\n'
                    'SITE_BASE_PATH = urlparse(BASE_URL).path.rstrip("/")\n'
                ),
            },
        )
        r = qv.check_domain_root_url_vaccine(ctx)
        self.assertEqual(r.status, qv.PASS, f"expected PASS, got {r.status}: {r.diagnosis}")

    def test_fail_when_zola_prefix_in_base_url(self):
        """config.toml base_url contains /zola subpath → FAIL."""
        ctx = self._ctx_with_config(base_url="https://seomoney.org/zola")
        r = qv.check_domain_root_url_vaccine(ctx)
        self.assertEqual(r.status, qv.FAIL,
                         f"expected FAIL for base_url with /zola, got {r.status}")
        self.assertIn("/zola", r.diagnosis)

    def test_fail_when_scanner_hardcodes_site_prefix_zola(self):
        """Scanner script hardcodes SITE_PREFIX = '/zola' → FAIL."""
        ctx = self._ctx_with_config(
            base_url="https://seomoney.org",
            scanner_files={
                "qa-404-checker.py": (
                    'BASE_URL = "https://seomoney.org"\n'
                    'SITE_PREFIX = "/zola"  # old GitHub Pages subpath\n'
                ),
            },
        )
        r = qv.check_domain_root_url_vaccine(ctx)
        self.assertEqual(r.status, qv.FAIL,
                         f"expected FAIL for hardcoded SITE_PREFIX='/zola', got {r.status}")
        self.assertIn("qa-404-checker.py", r.diagnosis)

    def test_fail_when_scanner_hardcodes_site_base_path_zola(self):
        """Scanner script hardcodes SITE_BASE_PATH = '/zola' → FAIL."""
        ctx = self._ctx_with_config(
            base_url="https://seomoney.org",
            scanner_files={
                "scripts/check_internal_links.py": (
                    'BASE_URL = "https://seomoney.org"\n'
                    'SITE_BASE_PATH = "/zola"\n'
                ),
            },
        )
        r = qv.check_domain_root_url_vaccine(ctx)
        self.assertEqual(r.status, qv.FAIL,
                         f"expected FAIL for hardcoded SITE_BASE_PATH='/zola', got {r.status}")

    def test_comment_with_zola_does_not_fail(self):
        """Comment lines mentioning /zola in scanner scripts must NOT cause FAIL."""
        ctx = self._ctx_with_config(
            base_url="https://seomoney.org",
            scanner_files={
                "qa-404-checker.py": (
                    '# Old value was SITE_PREFIX = "/zola" — now derived from BASE_URL\n'
                    'BASE_URL = "https://seomoney.org"\n'
                    'SITE_PREFIX = ""\n'
                ),
            },
        )
        r = qv.check_domain_root_url_vaccine(ctx)
        # Comment lines must not trigger FAIL (PASS or at most WARN for other reasons)
        self.assertNotEqual(r.status, qv.FAIL,
                            f"comment-only /zola mention should not FAIL: {r.diagnosis}")

    def test_real_repo_passes(self):
        """Real repo must not FAIL DOMAIN-ROOT after migration fixes applied."""
        r = qv.check_domain_root_url_vaccine(qv.Ctx(REPO_ROOT))
        self.assertNotEqual(r.status, qv.FAIL,
                            f"DOMAIN-ROOT FAIL on real repo — {r.diagnosis}")


def _make_webp(w: int, h: int) -> bytes:
    """Build a minimal valid RIFF/WEBP (VP8X) byte string of the given size."""
    payload = bytes(4) + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")
    body = b"VP8X" + len(payload).to_bytes(4, "little") + payload
    riff = b"WEBP" + body
    return b"RIFF" + len(riff).to_bytes(4, "little") + riff


class OgImageVaccineTest(unittest.TestCase):
    """OG-IMAGE — social cover SVG + .og.webp twin must stay 1200×630, valid XML,
    fresh, and free of old-domain branding."""

    _GOOD_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" '
        'viewBox="0 0 1200 630"><rect width="1200" height="630" fill="#0b1220"/>'
        '<text x="72" y="72" fill="#fff">SEOMONEY · seomoney.org</text></svg>'
    )

    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def _write_bytes(self, rel: str, data: bytes) -> Path:
        p = self.repo.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def _wire_good(self, svg: str | None = None):
        import hashlib
        import json as _json
        svg = svg if svg is not None else self._GOOD_SVG
        self.repo.write("static/img/og/seomoney-og.svg", svg)
        self._write_bytes("static/img/og/seomoney-og.og.webp", _make_webp(1200, 630))
        # fresh manifest: records the CURRENT svg sha → twin not stale.
        sha = hashlib.sha256(svg.encode("utf-8")).hexdigest()
        self.repo.write("static/img/og-manifest.json",
                        _json.dumps({"static/img/og/seomoney-og.svg": sha}))

    def test_webp_dimensions_parser(self):
        self.assertEqual(qv._webp_dimensions(_make_webp(1200, 630)), (1200, 630))
        self.assertIsNone(qv._webp_dimensions(b"not a webp"))

    def test_good_og_passes(self):
        self._wire_good()
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS, f"{r.diagnosis} {r.details}")

    def test_missing_default_svg_fails(self):
        # an OG svg exists but the named default seomoney-og.svg does not.
        self.repo.write("static/img/og/other.svg", self._GOOD_SVG)
        self._write_bytes("static/img/og/other.og.webp", _make_webp(1200, 630))
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("seomoney-og.svg" in d for d in r.details))

    def test_broken_xml_fails(self):
        self.repo.write("static/img/og/seomoney-og.svg",
                        '<svg width="1200" height="630"><rect></svg>')  # unclosed/mismatched
        self._write_bytes("static/img/og/seomoney-og.og.webp", _make_webp(1200, 630))
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("XML" in d for d in r.details))

    def test_wrong_canvas_size_fails(self):
        self.repo.write("static/img/og/seomoney-og.svg",
                        self._GOOD_SVG.replace('width="1200" height="630"',
                                               'width="800" height="418"'))
        self._write_bytes("static/img/og/seomoney-og.og.webp", _make_webp(1200, 630))
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("1200×630" in d for d in r.details))

    def test_missing_twin_fails(self):
        self.repo.write("static/img/og/seomoney-og.svg", self._GOOD_SVG)
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any(".og.webp" in d for d in r.details))

    def test_wrong_twin_dimensions_fails(self):
        self.repo.write("static/img/og/seomoney-og.svg", self._GOOD_SVG)
        self._write_bytes("static/img/og/seomoney-og.og.webp", _make_webp(600, 315))
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("600×315" in d for d in r.details))

    def test_old_domain_warns(self):
        self.repo.write("static/img/og/seomoney-og.svg",
                        self._GOOD_SVG.replace("seomoney.org",
                                               "banhang-chogao.github.io/zola"))
        self._write_bytes("static/img/og/seomoney-og.og.webp", _make_webp(1200, 630))
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.WARN)
        self.assertTrue(any("old-domain" in d for d in r.details))

    def test_stale_twin_fails_via_manifest(self):
        # manifest records a DIFFERENT sha than the current svg → twin is stale
        # → deterministic FAIL (no mtime dependency).
        import json as _json
        self.repo.write("static/img/og/seomoney-og.svg", self._GOOD_SVG)
        self._write_bytes("static/img/og/seomoney-og.og.webp", _make_webp(1200, 630))
        self.repo.write("static/img/og-manifest.json",
                        _json.dumps({"static/img/og/seomoney-og.svg": "deadbeef" * 8}))
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("STALE" in d for d in r.details))

    def test_stale_bootstrap_mtime_warns_only(self):
        # No manifest entry → fall back to mtime heuristic as a soft WARN, never
        # a FAIL (a fresh CI checkout must never falsely block the merge).
        svg = self.repo.root / "static/img/og/seomoney-og.svg"
        svg.parent.mkdir(parents=True, exist_ok=True)
        twin = self._write_bytes("static/img/og/seomoney-og.og.webp", _make_webp(1200, 630))
        svg.write_text(self._GOOD_SVG, encoding="utf-8")
        os.utime(twin, (1000, 1000))
        os.utime(svg, (2000, 2000))
        r = qv.check_og_image_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.WARN)
        self.assertTrue(any("stale" in d.lower() for d in r.details))

    def test_real_repo_passes(self):
        r = qv.check_og_image_vaccine(qv.Ctx(REPO_ROOT))
        self.assertIn(r.status, (qv.PASS, qv.WARN),
                      f"OG vaccine unexpectedly FAILed: {r.diagnosis} {r.details}")


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


class EditorSdnaVaccineTest(unittest.TestCase):
    """EDITOR-SDNA — the /editor/ S-DNA visual layer + emoji-free + logic guard."""

    GOOD_SCSS = (
        '.editor-app { .ed-ico { color: red; } .esr-kpi { padding: 1rem; } }\n'
        '@media (max-width: 720px) { .editor-app { } }\n'
    )
    GOOD_EDITOR = (
        '{# comment 🚀 in a comment must be ignored #}\n'
        '<form data-form="post"><button data-action="publish">Đăng</button></form>\n'
        '{% include "partials/editor-seo-rail.html" %}\n'
        '<script src="js/editor.js"></script>\n'
    )
    GOOD_RAIL = '<aside data-seo-rail><div class="esr-kpi"></div></aside>\n'

    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def _write_good(self):
        self.repo.write("sass/_editor-sdna.scss", self.GOOD_SCSS)
        self.repo.write("sass/site.scss", '@import "editor";\n@import "editor-sdna";\n')
        self.repo.write("templates/editor.html", self.GOOD_EDITOR)
        self.repo.write("templates/partials/editor-seo-rail.html", self.GOOD_RAIL)

    def test_missing_stylesheet_fail(self):
        r = qv.check_editor_sdna_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_emoji_in_visible_ui_fail(self):
        self._write_good()
        # an emoji OUTSIDE a comment (visible UI) must FAIL
        self.repo.write("templates/editor.html",
                        self.GOOD_EDITOR + '<button data-action="x">🚀 Đăng</button>\n')
        r = qv.check_editor_sdna_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertTrue(any("emoji" in d for d in r.details))

    def test_emoji_only_in_comment_passes(self):
        self._write_good()  # GOOD_EDITOR has 🚀 inside a {# … #} comment
        r = qv.check_editor_sdna_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_publish_handler_removed_fail(self):
        self._write_good()
        self.repo.write("templates/editor.html",
                        self.GOOD_EDITOR.replace('data-action="publish"', 'data-action="noop"'))
        r = qv.check_editor_sdna_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_seo_rail_removed_fail(self):
        self._write_good()
        self.repo.write("templates/partials/editor-seo-rail.html",
                        '<aside>no hook</aside>\n')
        r = qv.check_editor_sdna_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_not_imported_fail(self):
        self._write_good()
        self.repo.write("sass/site.scss", '@import "editor";\n')  # no editor-sdna import
        r = qv.check_editor_sdna_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_good_repo_pass(self):
        self._write_good()
        r = qv.check_editor_sdna_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.PASS)

    def test_real_repo_pass(self):
        r = qv.check_editor_sdna_vaccine(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS,
                         f"editor S-DNA detector not green on repo: {r.details}")


class SeoIdentityV20Test(unittest.TestCase):
    """V20 — canonical apex root + SEOMONEY homepage brand + BlogPosting schema."""
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def _wire(self, base_url='https://seomoney.org',
              title='SEOMONEY – SEO, AI WebOps & Tài chính cá nhân',
              h1='SEOMONEY – SEO, AI WebOps &amp; Tài chính cá nhân',
              schema='"@type": "BlogPosting"'):
        self.repo.write("config.toml", f'base_url = "{base_url}"\n')
        self.repo.write("templates/index.html",
                        f"{{% block title %}}{title}{{% endblock %}}\n<h1 class=\"x\">{h1}</h1>")
        self.repo.write("templates/base.html", f'<script>{{ {schema} }}</script>')

    def test_real_repo_passes(self):
        r = qv.check_v20_seo_identity_homepage(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS, r.diagnosis)

    def test_canonical_identity_passes(self):
        self._wire()
        self.assertEqual(qv.check_v20_seo_identity_homepage(self.repo.ctx()).status, qv.PASS)

    def test_github_io_base_url_fails(self):
        self._wire(base_url='https://banhang-chogao.github.io/zola')
        self.assertEqual(qv.check_v20_seo_identity_homepage(self.repo.ctx()).status, qv.FAIL)

    def test_http_scheme_fails(self):
        self._wire(base_url='http://seomoney.org')
        self.assertEqual(qv.check_v20_seo_identity_homepage(self.repo.ctx()).status, qv.FAIL)

    def test_lost_brand_in_homepage_fails(self):
        self._wire(title='Blog công nghệ, du lịch & ẩm thực',
                   h1='Blog công nghệ, du lịch &amp; ẩm thực')
        self.assertEqual(qv.check_v20_seo_identity_homepage(self.repo.ctx()).status, qv.FAIL)

    def test_non_blogposting_schema_warns(self):
        self._wire(schema='"@type": "Article"')
        self.assertEqual(qv.check_v20_seo_identity_homepage(self.repo.ctx()).status, qv.WARN)


class VaccineRegistryGuardTest(unittest.TestCase):
    """VACCINE-REGISTRY — duplicate V-number or detector registration must FAIL."""
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def test_next_free_number(self):
        text = "#### V1 — a\n#### V19 — b\n#### V10 — dupe legacy\n"
        self.repo.write("CLAUDE.md", text)
        self.assertEqual(qv.next_free_vaccine_number(self.repo.ctx()), 20)

    def test_real_repo_registry_passes(self):
        r = qv.check_vaccine_registry_integrity(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS, r.diagnosis)

    def test_legacy_duplicates_allowed(self):
        self.repo.write("CLAUDE.md",
                        "#### V10 — main\n#### V10 — compliance\n#### V20 — new\n")
        self.assertEqual(qv.check_vaccine_registry_integrity(self.repo.ctx()).status, qv.PASS)

    def test_unexpected_duplicate_number_fails(self):
        self.repo.write("CLAUDE.md", "#### V20 — first\n#### V20 — second copy\n")
        r = qv.check_vaccine_registry_integrity(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)
        self.assertIn("V20", r.diagnosis)

    def test_no_duplicate_detector_registration(self):
        names = [getattr(d, "__name__", repr(d)) for d in qv.DETECTORS]
        self.assertEqual(len(names), len(set(names)),
                         "a detector is registered more than once in DETECTORS")

    def test_import_time_guard_raises_on_dupe(self):
        original = list(qv.DETECTORS)
        qv.DETECTORS.append(original[0])  # register the same callable twice
        try:
            with self.assertRaises(RuntimeError):
                qv._assert_no_duplicate_registration()
        finally:
            qv.DETECTORS[:] = original


class GaStatsVaccineTest(unittest.TestCase):
    """V25 — GA stats module identity, cache isolation, hourly GA Vacxin, banner."""
    def setUp(self):
        self.repo = TmpRepo()
        self.addCleanup(self.repo.cleanup)

    def _wire(self, *, config=None, fetch=None, base_html=None,
              ga_stats=None, ga_health=None, vacxin_yml=None, health_js=None):
        self.repo.write("config.toml", config if config is not None else (
            'base_url = "https://seomoney.org"\n'
            '[extra]\n'
            'ga_measurement_id = "G-SMTFZVC0XN"\n'
            'ga_property_id = "542421812"\n'
            'ga_dashboard_url = "https://analytics.google.com/analytics/web/#/p542421812/reports/intelligenthome"\n'
            'ga_fix_url = "https://analytics.google.com/analytics/web/#/p542421812/admin/streams/table"\n'
        ))
        self.repo.write("scripts/fetch_ga_stats.py", fetch if fetch is not None else (
            'import os\nPROPERTY_ID = os.environ.get("GA_PROPERTY_ID", "542421812")\n'
        ))
        self.repo.write("templates/base.html", base_html if base_html is not None else (
            '<script async src="https://www.googletagmanager.com/gtag/js?id={{ config.extra.ga_measurement_id }}"></script>\n'
            '<div class="ga-stats" data-ga-health><div data-ga-banner></div></div>\n'
        ))
        self.repo.write("data/ga-stats.json", ga_stats if ga_stats is not None else (
            '{"property_id":"542421812","measurement_id":"G-SMTFZVC0XN","site":"seomoney.org","updated_at":null}'
        ))
        self.repo.write("data/ga-health.json", ga_health if ga_health is not None else (
            '{"status":"pending","last_checked":"2026-06-21T01:00:00+00:00","property_id":"542421812"}'
        ))
        self.repo.write(".github/workflows/ga-vacxin.yml",
                        vacxin_yml if vacxin_yml is not None else "on:\n  schedule:\n    - cron: '30 * * * *'\n")
        self.repo.write("static/js/ga-health.js",
                        health_js if health_js is not None else "(function(){try{}catch(e){}})();\n")

    def test_real_repo_passes(self):
        r = qv.check_ga_stats_vaccine(qv.Ctx(REPO_ROOT))
        self.assertEqual(r.status, qv.PASS, r.diagnosis + " :: " + "; ".join(r.details))

    def test_synthetic_canonical_passes(self):
        self._wire()
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.PASS)

    def test_old_property_in_fetch_fails(self):
        self._wire(fetch='PROPERTY_ID = "541698865"\n')
        r = qv.check_ga_stats_vaccine(self.repo.ctx())
        self.assertEqual(r.status, qv.FAIL)

    def test_wrong_config_property_fails(self):
        self._wire(config=(
            '[extra]\nga_measurement_id = "G-SMTFZVC0XN"\nga_property_id = "999999999"\n'
            'ga_dashboard_url = "x"\nga_fix_url = "y"\n'
        ))
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.FAIL)

    def test_old_measurement_in_config_fails(self):
        self._wire(config=(
            '[extra]\nga_measurement_id = "G-REFBXH86Z5"\nga_property_id = "542421812"\n'
            'ga_dashboard_url = "x"\nga_fix_url = "y"\n'
        ))
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.FAIL)

    def test_foreign_property_in_stats_fails(self):
        self._wire(ga_stats='{"property_id":"541698865","updated_at":"2026-06-20T00:00:00Z"}')
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.FAIL)

    def test_credential_leak_in_health_fails(self):
        self._wire(ga_health=(
            '{"status":"ok","last_checked":"2026-06-21T01:00:00Z","property_id":"542421812",'
            '"private_key":"-----BEGIN PRIVATE KEY-----"}'
        ))
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.FAIL)

    def test_hardcoded_gtag_id_fails(self):
        self._wire(base_html=(
            '<script src="https://www.googletagmanager.com/gtag/js?id=G-ABCDEF12"></script>\n'
            '<div data-ga-health><div data-ga-banner></div></div>'
        ))
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.FAIL)

    def test_missing_vacxin_workflow_warns(self):
        self._wire()
        # remove the hourly workflow → WARN (not FAIL)
        (self.repo.root / ".github/workflows/ga-vacxin.yml").unlink()
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.WARN)

    def test_missing_banner_warns(self):
        self._wire(base_html=(
            '<script src="https://www.googletagmanager.com/gtag/js?id={{ config.extra.ga_measurement_id }}"></script>\n'
            '<div data-ga-health></div>'  # no data-ga-banner
        ))
        self.assertEqual(qv.check_ga_stats_vaccine(self.repo.ctx()).status, qv.WARN)


if __name__ == "__main__":
    unittest.main()
