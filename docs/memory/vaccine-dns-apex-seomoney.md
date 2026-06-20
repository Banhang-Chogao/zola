# DNS Vaccine — seomoney.org apex (Cloudflare ↔ GitHub Pages)

**Date:** 2026-06-20
**Scope:** `scripts/dns_vaccine.py`, `scripts/test_dns_vaccine.py`,
`.github/CLOUDFLARE-DDOS-SETUP.md`, `static/CNAME`, `config.toml`
**PR:** #540 (`claude/dns-apex-vaccine`)

## Symptom

- `www.seomoney.org` resolved correctly (CNAME → `banhang-chogao.github.io` +
  GitHub Pages IPs) but apex `seomoney.org` `A` returned **empty** → apex
  unreachable while www worked.
- Earlier in the migration the apex returned **Cloudflare Error 1016 (Origin DNS
  error)** / NXDOMAIN.

## Root cause

Cloudflare DNS was missing the four apex `@` `A` records (it was **not** an
NS / R2 / email-routing problem). Repo side was already correct
(`static/CNAME = seomoney.org`, `config.toml base_url = https://seomoney.org`),
so the gap was DNS configuration + lack of early detection for the apex.

## Vaccine Summary

### Existing vaccines used
- **DNS Vaccine** (`scripts/dns_vaccine.py`) — pre-existing repo checks R1/R2/R3
  (CNAME present, `base_url` host == CNAME, https + no `/zola`) and live checks
  L1 (apex A ⊆ GitHub Pages IPs, no apex CNAME), L2 (www resolves), L3 (HTTP
  probe + 1016 detection), L4 (origin reachable). Reused as the base.
- **QA Vaccine Gate** (`qa_check.py` / `scripts/qa_vaccines.py`) — used to gate
  the change (100/100 PRODUCTION-SAFE).

### New vaccines created
- **L0-ns** — apex NS must be delegated to Cloudflare (`*.ns.cloudflare.com`).
- **L5-www-redirect** — `https://www/` must HTTP-redirect (301/308) to the apex
  (or serve 200) and must NOT NXDOMAIN; warns on a non-apex redirect target.
  Backed by `http_redirect()` (HEAD without following redirects).

### Existing vaccines upgraded
- **L1** — empty apex A now **fails with explicit Cloudflare-dashboard fix steps**
  (`CF_APEX_FIX_STEPS`: add 4× `A @` → `185.199.108–111.153`, DNS-only; keep `www`
  CNAME; no apex CNAME).
- **L3** — asserts apex returns **HTTP 200** explicitly (still tolerant of
  redirect/404-as-reachable; hard-fail on 1016).
- **Scope exclusion documented** — `EXCLUDED_RECORD_TYPES` (MX/TXT/SRV/CAA) +
  `CLOUDFLARE_NS_SUFFIX`: R2 custom-domain CNAMEs and email-routing MX/TXT are
  structurally out of scope and never flagged.

### Root cause prevented
A silent apex outage where **www works but the apex is broken** (empty A /
NXDOMAIN / 1016 / apex-CNAME), or NS de-delegation, or www not redirecting to the
apex — each now surfaces as a clear gated failure with fix steps before users hit
a dead apex.

### Files changed (vs `main`)
- `scripts/dns_vaccine.py` (+L0-ns, +L5-www-redirect, +http_redirect, L1/L3 upgrade, scope docs)
- `scripts/test_dns_vaccine.py` (regression for 1016 · NXDOMAIN · missing apex A · www-ok-apex-broken · healthy 200+redirect · wrong-redirect warn · NS pass/fail)
- `.github/CLOUDFLARE-DDOS-SETUP.md` (accurate apex A-records runbook)
- `CLAUDE.md` (F-Dashboard flow + watermark refs github.io/zola → seomoney.org; this rule)

### Validation passed
- `python3 scripts/dns_vaccine.py --gate --offline` → exit 0 (R1/R2/R3 PASS)
- `python3 -m unittest scripts.test_dns_vaccine` → 16/16
- `python3 qa_check.py` → 100/100 PRODUCTION-SAFE
- `python3 scripts/check_internal_links.py` → OK
- `python3 qa-404-checker.py` → exit 0
- grep `github.io/zola | seomomey.org | conflict markers` on site-output → none

### Where saved
- Vaccine code/tests: `scripts/dns_vaccine.py`, `scripts/test_dns_vaccine.py`
- Runbook: `.github/CLOUDFLARE-DDOS-SETUP.md`
- This memory: `docs/memory/vaccine-dns-apex-seomoney.md`
- Live diagnostics: `data/dns-vaccine-report.json` (workflow `dns-vaccine.yml`, cron 30')

## Manual residual (outside repo)
Add the 4 apex `A @` records in Cloudflare (DNS-only) per the runbook; the live
checks go green once apex A resolves.
