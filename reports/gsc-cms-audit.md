# GSC / CMS Integration Audit — 2026-06-23

## TL;DR

GSC backend routes exist and are mounted on `blog-vipzone-api`. OAuth flow works. **Root cause** why CMS stats show "Chưa kết nối": the GitHub Actions workflow `gsc-stats.yml` runs every 20 minutes but only 1 out of 4 required secrets is configured (`GSC_PROPERTY_URL`). The other three (`GSC_REFRESH_TOKEN`, `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET`) are absent → workflow always writes `connected: false` to `data/gsc-metrics.json` → static file deployed to site has no live data.

Secondary bug found: **CTR double-multiplication** in `static/js/cms/app.js:193` (dormant until GSC is actually connected).

---

## CMS Card / Section Audit

| CMS Card | Current Data Source | Expected GSC Source | Status | Root Cause | Suggested Fix | Risk |
|----------|--------------------|--------------------|--------|------------|---------------|------|
| **CTR (KPI card)** | `BASE/data/gsc-metrics.json` (static file) | `gsc-metrics.json` `ctr` field (populated when secrets set) | **mock** — always shows "Chưa kết nối GSC" | `GSC_REFRESH_TOKEN`, `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET` secrets missing → workflow writes `connected: false` placeholder | Add the 3 missing secrets to repo, run OAuth flow via `/gsc/oauth/start` on Render backend | Low (just secret config) |
| **Impressions (KPI card)** | Same static file → `g.impressions` | Same | **mock** | Same | Same | Low |
| **Vị trí trung bình (KPI card)** | Same static file → `g.avg_position` | Same | **mock** | Same | Same | Low |
| **CMS GSC panel** (`data-cms-gsc`) | Same static file | `indexed_pages`, `clicks`, `sitemap_status` | **mock** | Same | Same | Low |
| **Alerts (non-indexed pages)** | Same static file → `g.non_indexed_pages` | Real coverage data | **mock** | Same | Same | Low |
| **SEO Reality Check widget** (sidebar, blog posts) | Priority: 1) localStorage cache, 2) live `authApi()+/gsc/metrics`, 3) static `BASE/data/gsc-metrics.json` | Live API `/gsc/metrics` on `blog-vipzone-api` | **partial** — calls live API correctly, but backend returns `connected: false` because token not in env | `GSC_REFRESH_TOKEN` not set as Render env var (V24/V29 pattern) | Set `GSC_REFRESH_TOKEN` on Render via operator export flow | Low |
| **Technical SEO Score** (seo-reality) | `data/seo-reality.json` → `technical_seo` section (build-time, internal) | N/A (internal metric) | **OK** | — | — | — |

---

## Backend GSC Endpoints

All routes are on `blog-vipzone-api` via `services/visitor-counter/gsc_routes.py` (mounted in `services/vipzone/main.py`):

| Endpoint | Auth | Returns |
|----------|------|---------|
| `GET /gsc/status` | Public | `connected`, `token_source`, `property`, `cache_updated_at`, `missing_credentials` |
| `GET /gsc/metrics` | Public (no-auth, 20m cache) | Full bundle: `clicks`, `impressions`, `ctr`, `avg_position`, `indexed_pages`, `top_pages`, `top_queries`, `trend`, `executive_summary` |
| `GET /gsc/oauth/start` | SuperVIP session | Redirects to Google OAuth |
| `GET /gsc/oauth/callback` | OAuth callback | Saves refresh token to KV, redirects with `#gsc_connected=1` |
| `GET /gsc/refresh-token` | SuperVIP | Masked token export (use `?reveal=1` to get full value for Render env) |
| `POST /gsc/refresh` | SuperVIP | Force-refresh metrics cache |
| `POST /gsc/disconnect` | SuperVIP | Revoke + clear KV |

---

## Key Answers

1. **Which CMS sections need GSC?** CTR / Impressions / Avg Position KPI cards, GSC panel, Alerts (non-indexed), SEO Reality sidebar widget.
2. **Which already call real API?** `seo-reality-gsc.js` calls `authApi() + /gsc/metrics` live. `cms/app.js` reads **static JSON only** — no live API call.
3. **Which use mock/static?** All CMS KPI cards + GSC panel → static `data/gsc-metrics.json`.
4. **GSC OAuth status?** Routes mounted OK. Backend has `gsc_configured: false` because `GSC_CLIENT_ID` and `GSC_CLIENT_SECRET` are not set in Render env.
5. **DB/KV storage?** `SqliteKV` in `/tmp` on Render (ephemeral on redeploy). Keys: `gsc:refresh_token`, `gsc:property`, `gsc:metrics_cache`, `gsc:cache_at`. Durable home = `GSC_REFRESH_TOKEN` env var on Render.
6. **Backend data fields?** Full bundle: `connected`, `property`, `clicks`, `impressions`, `ctr` (%), `avg_position`, `indexed_pages`, `non_indexed_pages`, `submitted_pages`, `sitemap_status`, `last_crawl`, `top_pages`, `top_queries`, `trend`, `executive_summary`, `previous_period`.
7. **Frontend calling correct endpoint?** `seo-reality-gsc.js` calls `authApi() + /gsc/metrics` ✓. `cms/app.js` calls `BASE/data/gsc-metrics.json` (static) — never calls live API.
8. **CORS/auth errors?** `/gsc/metrics` is public + CORS allows `seomoney.org` → no CORS issue. `credentials: "omit"` correct for public endpoint.
9. **Property mismatch?** Backend uses `DEFAULT_GSC_PROPERTY_URL = "sc-domain:seomoney.org"`. Secret `GSC_PROPERTY_URL` set 2026-06-20. Consistent with V19 doctrine.
10. **Missing steps to show live data?**
    - Set `GSC_CLIENT_ID` and `GSC_CLIENT_SECRET` as Render env vars on `blog-vipzone-api`
    - Run OAuth via `/gsc/oauth/start` (admin/supervip session) → Google consent → token saved to KV
    - Export token: `GET /gsc/refresh-token?reveal=1` → copy value
    - Set `GSC_REFRESH_TOKEN` as Render env var → Manual Blueprint Sync on Render
    - Set `GSC_REFRESH_TOKEN`, `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET` as GitHub repo secrets → `gsc-stats.yml` will write real data to `data/gsc-metrics.json`

---

## Bug Found (Dormant — activates when GSC connected)

**File:** `static/js/cms/app.js:193`
```js
// BUG: gsc_client returns ctr already as percentage (e.g. 5.25 for 5.25%)
// but app.js multiplies by 100 again → shows 525.0%
setKpi("ctr", (g.ctr * 100).toFixed(1) + "<small>%</small>", …);
// FIX: should be:
setKpi("ctr", Number(g.ctr).toFixed(1) + "<small>%</small>", …);
```

`seo-reality-gsc.js:283` uses `gsc.ctr + "%"` (no multiplication) — correct.

---

## What's Missing to Show Live GSC Stats in /cms/

1. **Secrets** (Render + GitHub): `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET`, `GSC_REFRESH_TOKEN`
2. **OAuth flow**: must be done once via `/gsc/oauth/start` on the live Render backend
3. **Token persistence**: export via `/gsc/refresh-token?reveal=1` → set as Render env var → Manual Sync (V24 doctrine)
4. **Fix CTR bug** in `static/js/cms/app.js:193` before going live (low risk, 1-line change)
5. *(Optional)* CMS `app.js` only reads static JSON; if real-time GSC in CMS dashboard is wanted, a live API call to `authApi() + /gsc/metrics` should be added (same pattern as `seo-reality-gsc.js`)
