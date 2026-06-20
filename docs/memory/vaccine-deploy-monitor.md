# deploy_monitor_vaccine — Deploy Watch footer + /tools/deploy-monitor/

**Date:** 2026-06-20
**Scope:** `scripts/fetch_deploy_monitor.py`, `data/deploy-monitor.json`,
`.github/workflows/deploy-monitor.yml`, `templates/base.html` (footer widget),
`sass/_deploy-watch.scss`, `templates/deploy-monitor.html`,
`content/tools/deploy-monitor.md`, `content/tools/_index.md`, `scripts/qa_vaccines.py`.
**Route / data:** `/tools/deploy-monitor/` · `data/deploy-monitor.json`

## Feature
A compact **Deploy Watch** footer widget + a full **Deploy Monitor** detail page
that track GitHub Pages deploy speed. Static-safe: the browser never calls GitHub
— a CI cron (`deploy-monitor.yml`, every 20 min) reads the Actions `GITHUB_TOKEN`
from secrets, queries the `deploy.yml` runs, and publishes a sanitized
`data/deploy-monitor.json`. Metrics: current prod commit, latest deployed commit,
pending/queued/in_progress commits (+waiting time + title), per-run duration,
average + longest deploy, failed/cancelled counts, and a **V5 rate-limit /
concurrency storm signal**. The footer widget is a collapsed `<details>` (no
layout shift, mobile-tight, no overflow); the detail page reuses the `.uptime-card`
KPI components (no new framework).

## Risk
A secrets-bearing CI feature on a public repo: the main failure mode is a
**GitHub token leaking** into a committed file, plus broken public JSON, an
unwired footer widget, a missing/404 detail route, or stale data from a dead cron.

## Vaccine Summary

### Existing vaccines used
- **QA Vaccine Gate** (`qa_check.py` / `scripts/qa_vaccines.py`) — host + gate (100/100).
- Reused conventions (no new framework): `load_data` server render; `fetch_*`
  env-token pattern (`fetch_build_dashboard.py`); `push_to_main.sh` publish
  (`uptime-me.yml`); footer structure + `.uptime-card` components; `docs/memory/`.
- **V5** awareness — the fetcher emits a storm signal (≥3 cancelled deploys within
  20 min) matching the documented configure-pages rate-limit pattern.

### New vaccines created
- **`deploy_monitor_vaccine`** → `check_deploy_monitor` (code `DEPLOY-MON`) in
  `scripts/qa_vaccines.py`, registered in `DETECTORS`:
  1. **No token leak** — scans feature files for `ghp_/gho_/ghs_/…/github_pat_`
     token shapes → FAIL.
  2. **Public JSON schema** — `checked_at, ok, stale, summary{prod_status,
     pending_count, avg_deploy_s}, pending[], recent[]` → FAIL on malformed.
  3. **Footer renders if data exists** — `base.html` must `load_data` the JSON +
     contain the `.deploy-watch` widget → FAIL.
  4. **Pending count shown** — `base.html` must reference `pending_count` → FAIL.
  5. **Route not 404** — `content/tools/deploy-monitor.md` + template exist; footer
     link + Tools card point to `/tools/deploy-monitor` → FAIL/WARN.
  6. **Stale warning** — `checked_at` older than 3h → WARN (empty = awaiting).
- Defense-in-depth in `fetch_deploy_monitor.py`: aborts the write (exit 2) if the
  token appears in the serialized report; meaningful-change-only write (no churn).

### Existing vaccines upgraded
- None (additive detector + additive footer widget; `_index.md` card; `tools.html`
  already supported `subtitle`).

### Root cause prevented
A GitHub token committed to the public repo, or the deploy widget/page shipping
with broken JSON, an unwired footer, a 404 detail route, a missing pending count,
or silently stale deploy data — all caught by the QA gate before deploy.

### Files changed
- New: `scripts/fetch_deploy_monitor.py`, `data/deploy-monitor.json` (seed),
  `.github/workflows/deploy-monitor.yml`, `content/tools/deploy-monitor.md`,
  `templates/deploy-monitor.html`, `sass/_deploy-watch.scss`,
  `docs/memory/vaccine-deploy-monitor.md`
- Edited: `templates/base.html` (footer Deploy Watch widget), `sass/site.scss`
  (import), `content/tools/_index.md` (card), `scripts/qa_vaccines.py`
  (+`check_deploy_monitor`), `scripts/test_qa_vaccines.py` (+8 tests)

### Validation result
- `python3 scripts/qa_vaccines.py` → DEPLOY-MON **PASS**, 22/22, 100/100
- `python3 -m unittest scripts.test_qa_vaccines` → 48/48 (incl. 8 deploy-monitor)
- `python3 scripts/fetch_deploy_monitor.py` (no token) → graceful fallback (keeps
  prior report, marks stale), valid JSON, 0 token-like strings
- `python3 qa_check.py` → 100/100 PRODUCTION-SAFE (incl. V8 template balance)
- `python3 scripts/check_internal_links.py` → OK · `qa-404-checker.py` → exit 0
- secret scan → no hardcoded tokens; only `secrets.GITHUB_TOKEN` refs
- 0 conflict markers · `zola build` runs in CI

### Where saved
- Vaccine code/test: `scripts/qa_vaccines.py`, `scripts/test_qa_vaccines.py`
- This memory: `docs/memory/vaccine-deploy-monitor.md`

## How to set the required secret
None to add manually for read access — the workflow uses the built-in
`secrets.GITHUB_TOKEN` (Actions auto-provides it) with `permissions: actions: read`.
If publishing the report needs to bypass branch protection, set the existing
`WORKFLOW_BOT_PAT` secret (already used by `push_to_main.sh`). Never paste a token
into code/config; the vaccine + the script's abort-on-leak guard enforce this.
