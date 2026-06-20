# uptime_me_vaccine — UPTIME_ME dashboard safety

**Date:** 2026-06-20
**Scope:** `scripts/fetch_uptime_me.py`, `data/uptime-me.json`,
`.github/workflows/uptime-me.yml`, `templates/uptime-me.html`,
`content/tools/uptime-me.md`, `sass/_uptime-me.scss`, `static/js/uptime-me.js`,
`templates/tools.html`, `content/tools/_index.md`, `scripts/qa_vaccines.py`.
**Route:** `/tools/uptime-me/`

## Feature
UPTIME_ME — a playful-but-calm uptime dashboard fed by 3 free UptimeRobot
accounts. Because the site is static, the browser never calls UptimeRobot: a CI
cron (`uptime-me.yml`, every 30 min) runs `fetch_uptime_me.py`, which reads the 3
keys from secrets, normalizes the read-only `getMonitors` data, and publishes a
sanitized `data/uptime-me.json`. The page renders it via Zola `load_data` +
KPI cards, 3 account cards, response-time sparklines (vanilla JS), an incident
timeline, a "Website đang thở ổn không?" verdict, last-updated + stale flag, and
a clean empty/error state.

## Risk
A secrets-bearing feature on a public static repo: the main failure mode is an
**API key leaking** into a committed file, plus the usual static-feature breakage
(invalid public JSON, missing route, dead Tools card, stale cron).

## Vaccine Summary

### Existing vaccines used
- **QA Vaccine Gate** (`qa_check.py` / `scripts/qa_vaccines.py`) — host for the
  new detector; gated the change (100/100).
- Reused conventions (no new framework): `load_data` server-render (like
  `ad-report-v2.html`), `fetch_*` env-secrets pattern (like `fetch_pagespeed.py`),
  `push_to_main.sh` publish (like `dns-vaccine.yml`), `.content-block` card system
  (existing `__lock` / `--locked` styles), `docs/memory/` writeup.

### New vaccines created
- **`uptime_me_vaccine`** → `check_uptime_me` (code `UI-UPTIME`) in
  `scripts/qa_vaccines.py`, registered in `DETECTORS`:
  1. **No key leak** — scans the feature's tracked files for an UptimeRobot key
     shape (`(ur|u|m)NNNNN-<alnum≥20>`) → FAIL.
  2. **Public JSON schema** — `data/uptime-me.json` must parse and contain
     `checked_at, ok, summary{total,up,down,paused,breathing}, accounts[],
     monitors[], incidents[]` → FAIL on malformed/missing.
  3. **Route exists** — `content/tools/uptime-me.md` + `templates/uptime-me.html`
     (loads `data/uptime-me.json`) → FAIL/WARN.
  4. **Card links** — `content/tools/_index.md` must link `/tools/uptime-me` → FAIL.
  5. **Stale warning** — real `checked_at` older than 6h → WARN (empty = awaiting
     first run, OK).
- Defense-in-depth in `fetch_uptime_me.py`: aborts the write (exit 2) if any key
  string appears in the serialized report.

### Existing vaccines upgraded
- None (additive detector + additive `subtitle`/`locked` support in `tools.html`).

### Root cause prevented
An UptimeRobot API key committed to the public repo, or the dashboard shipping
with broken/missing data, a dead route, an unlinked Tools card, or a silently
dead cron serving stale uptime — all caught by the QA gate before deploy.

### Files changed
- New: `scripts/fetch_uptime_me.py`, `data/uptime-me.json` (seed),
  `.github/workflows/uptime-me.yml`, `content/tools/uptime-me.md`,
  `templates/uptime-me.html`, `sass/_uptime-me.scss`, `static/js/uptime-me.js`,
  `docs/memory/vaccine-uptime-me.md`
- Edited: `content/tools/_index.md` (card), `templates/tools.html` (subtitle/lock),
  `sass/_content-blocks.scss` (`__subtitle`), `sass/site.scss` (import),
  `scripts/qa_vaccines.py` (+`check_uptime_me`), `scripts/test_qa_vaccines.py` (tests)

### Validation result
- `python3 scripts/qa_vaccines.py` → UI-UPTIME **PASS**, 19/19, 100/100
- `python3 -m unittest scripts.test_qa_vaccines` → 34/34 (incl. 6 uptime)
- `python3 scripts/fetch_uptime_me.py` (no keys) → graceful fallback, valid JSON,
  0 key-like strings
- `python3 qa_check.py` → 100/100 PRODUCTION-SAFE
- `python3 scripts/check_internal_links.py` → OK · `qa-404-checker.py` → exit 0
- secret scan (feature files) → no hardcoded keys; only `secrets.*` refs
- 0 conflict markers · `zola build` runs in CI

### Where saved
- Vaccine code/test: `scripts/qa_vaccines.py`, `scripts/test_qa_vaccines.py`
- This memory: `docs/memory/vaccine-uptime-me.md`

## How to set the 3 secrets
GitHub → repo **Settings → Secrets and variables → Actions → New repository
secret**, add (read-only UptimeRobot API keys, one per free account):
`UPTIMEROBOT_API_KEY_1`, `UPTIMEROBOT_API_KEY_2`, `UPTIMEROBOT_API_KEY_3`.
Then run the **UPTIME_ME** workflow (Actions → Run workflow) for the first report.
R2/email-routing are unrelated and untouched. Never paste a key into code/config.
