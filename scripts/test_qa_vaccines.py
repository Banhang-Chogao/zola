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
            '<a href="/tools/deploy-monitor/">x</a></details>')

    def _wire(self, **over):
        self.repo.write("data/deploy-monitor.json", over.get("json", self.SEED))
        self.repo.write("templates/base.html", over.get("base", self.BASE))
        self.repo.write("content/tools/deploy-monitor.md", over.get("md", '+++\ntitle="x"\n+++'))
        self.repo.write("templates/deploy-monitor.html", over.get("tmpl", "detail"))
        self.repo.write("content/tools/_index.md", over.get("idx", 'url = "$BASE_URL/tools/deploy-monitor"'))
        self.repo.write("scripts/fetch_deploy_monitor.py", over.get("script", "# env token only"))
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
