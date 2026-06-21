# GA Vacxin System — Production Implementation Guide

**Date:** 2026-06-21  
**Status:** Production-Ready  
**Security:** ✅ No raw env vars · ✅ File-based credentials · ✅ Public-safe output

## Overview

The GA Vacxin system monitors Google Analytics 4 (GA4) health hourly, ensuring:
- Configuration matches canonical identity (property 542421812 / G-SMTFZVC0XN)
- Service account has valid access to GA4 property
- Recent data exists (last 7 days)
- Cache isolation (no old property leakage)
- Site tag (gtag.js) is correctly deployed

Output: Public-safe JSON snapshot to `data/ga-health.json` and `static/data/ga-health.json`

## Security Architecture

### Before (Unsafe ❌)
```bash
# Raw JSON passed as environment variable (visible in logs, CI history, etc.)
export GA_SERVICE_ACCOUNT_KEY='{"type":"service_account","private_key":"..."}'
python scripts/ga_vacxin.py
```

### After (Secure ✅)
```bash
# Credential file written temporarily, referenced via standard env var
echo '{"type":"service_account",...}' > /tmp/ga-cred.json
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/ga-cred.json
python scripts/ga_vacxin.py
# File cleaned up after workflow completes
```

**Benefits:**
- Standard Google Cloud authentication (works with all Google libraries)
- Credentials never visible in workflow logs or CI history
- Temporary file lifecycle is controlled (cleanup guaranteed)
- Works with `google.auth` and `google-analytics-data` libraries automatically

## Setup Instructions

### Step 1: Obtain Service Account JSON

**Option A: If you already have the key file**
- You have: `ga-service-account-key.json` (file on disk)
- Go to Step 2

**Option B: Create a new service account in Google Cloud Console**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (must have GA4 property 542421812)
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
   - Name: `zola-ga-reader`
   - Description: `GA4 read-only access for Zola blog`
5. Click **Create and Continue**
6. On the next screen, click **Create Key**
   - Type: JSON
   - This downloads `<project>-<id>.json`
7. Go to **Manage keys** → Grant the service account **Viewer** role on GA4 property 542421812:
   - In [Google Analytics Admin](https://analytics.google.com/)
   - Property 542421812 → Admin → Property Access Management
   - Add email: `zola-ga-reader@<project>.iam.gserviceaccount.com`
   - Role: **Viewer**

### Step 2: Store Secret in GitHub

1. Go to repo **Settings** → **Secrets and variables** → **Actions**
2. Create a new repository secret:
   - **Name:** `GA_SERVICE_ACCOUNT_KEY_JSON`
   - **Value:** (contents of the JSON file)

**Example secret value:**
```json
{
  "type": "service_account",
  "project_id": "my-project",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "zola-ga-reader@my-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### Step 3: Verify Integration

#### Test 1: Run GA Vacxin health check
```bash
# Local test (offline — no GA API calls)
python3 scripts/ga_vacxin.py --offline

# Expected output:
# GA Vacxin → status=pending · property=542421812 · Chưa xác minh kết nối GA...
```

#### Test 2: With credentials (if you have the key.json locally)
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/ga-service-account-key.json
python3 scripts/ga_vacxin.py

# Expected output (if GA is wired correctly):
# GA Vacxin → status=ok · property=542421812 · GA hoạt động bình thường...
```

#### Test 3: Check workflow runs
- Go to repo **Actions** → **GA Vacxin**
- Latest run should show status ✅ (green)
- Check `data/ga-health.json` for recent timestamp

## System Architecture

### Files

| File | Purpose |
|------|---------|
| `scripts/ga_vacxin.py` | Health monitor (checks, no write to blog data) |
| `scripts/fetch_ga_stats.py` | Fetch real metrics (writes `data/ga-stats.json`) |
| `.github/workflows/ga-vacxin.yml` | Hourly health check (runs at :30) |
| `.github/workflows/ga-stats.yml` | Hourly metric fetch (runs at :00) |
| `data/ga-health.json` | Public-safe health snapshot (cache-baked) |
| `static/data/ga-health.json` | Mirror (client refresh) |
| `data/ga-stats.json` | Real GA metrics (footer widgets) |

### Data Flow

```
[Google Analytics 4 · Property 542421812]
         ↓
    (Real-time API)
         ↓
[GitHub Actions workflow (service account auth)]
         ↓
   ga_vacxin.py          fetch_ga_stats.py
   (Health check)        (Fetch metrics)
         ↓                    ↓
   data/ga-health.json   data/ga-stats.json
   (5 checks)             (Today/Week/Month)
         ↓                    ↓
   [Zola build]
         ↓
   data/load_data   +   templates/base.html
   (Health banner)      (Footer widgets)
         ↓
   [GitHub Pages deployment]
```

## Health Status States

| Status | Meaning | UI | Action |
|--------|---------|----|----|
| **ok** | GA connected, data flowing | ✅ Subtle green chip | None |
| **pending** | Not verified yet (offline / no credentials) | ℹ️ Info note | Set `GA_SERVICE_ACCOUNT_KEY_JSON` secret |
| **disconnected** | Auth failed (invalid key / permission denied) | ⚠️ Warning banner | Check secret + GA permissions |
| **error** | Wrong property / stale cache / site tag issue | ❌ Error banner | See details + fix link |

## Troubleshooting

### Issue: Status shows "pending"
**Diagnosis:** Credentials not available (offline mode or missing secret)

**Fix:**
1. Verify `GA_SERVICE_ACCOUNT_KEY_JSON` secret exists in GitHub
2. Re-run workflow: **Actions** → **GA Vacxin** → **Run workflow**
3. Check latest run output in **Step: Run GA Vacxin health check**

### Issue: Status shows "disconnected"
**Diagnosis:** Service account key is invalid or has no GA4 access

**Fix:**
1. Verify the JSON in `GA_SERVICE_ACCOUNT_KEY_JSON` is valid (no truncation, valid JSON)
2. Verify service account email in Google Analytics has **Viewer** role on property 542421812
3. Check Google Cloud Console for any permission errors
4. Re-run workflow

### Issue: Status shows "error" with property mismatch
**Diagnosis:** `config.toml` property ID doesn't match 542421812

**Fix:**
1. Check `config.toml`:
   ```toml
   [extra]
   ga_property_id = "542421812"
   ga_measurement_id = "G-SMTFZVC0XN"
   ```
2. If values are wrong, update and commit
3. Re-run workflow

### Issue: Site tag check fails
**Diagnosis:** `gtag.js` not deployed or wrong measurement ID on site

**Fix:**
1. Check homepage HTML has correct measurement ID:
   ```bash
   curl -s https://seomoney.org/ | grep -o 'G-[A-Z0-9]*'
   ```
2. Verify `config.toml` `ga_measurement_id = "G-SMTFZVC0XN"`
3. Re-deploy site if needed

## Monitoring Checklist

- ☐ Workflow runs hourly without errors
- ☐ `data/ga-health.json` has recent timestamp
- ☐ Status field is `"ok"` (not `pending` / `disconnected` / `error`)
- ☐ `data/ga-stats.json` exists with today's data
- ☐ Footer widgets on site show real metrics (users/pageviews)
- ☐ GitHub Actions secrets are masked (never visible in logs)

## Migration from Old System

If migrating from `GA_SERVICE_ACCOUNT_KEY` (raw JSON env var):

1. **Create new secret** `GA_SERVICE_ACCOUNT_KEY_JSON` (same value)
2. **Update workflows** to use new approach ✅ (already done)
3. **Remove old secret** `GA_SERVICE_ACCOUNT_KEY` (optional; won't hurt if left)
4. **Test:** Run health check, verify status is not "pending"

## API Quotas & Rate Limiting

GA4 Data API has generous quotas:
- **Standard:** 10,000 requests/day per property
- **Batch reporting:** 10 reports per request

Current usage:
- GA Vacxin (hourly): ~48 requests/day (property access check)
- Fetch GA Stats (hourly): ~6 requests/day (multiple metric queries)
- **Total:** ~54 requests/day (well within limit)

No action needed unless usage spikes.

## Rollback (If Needed)

To revert to the old system (not recommended):
1. Restore `GA_SERVICE_ACCOUNT_KEY` secret (raw JSON)
2. In workflows, set env var: `GA_SERVICE_ACCOUNT_KEY: ${{ secrets.GA_SERVICE_ACCOUNT_KEY }}`
3. Revert `ga_vacxin.py` and `fetch_ga_stats.py` to use `GA_SERVICE_ACCOUNT_KEY`

**Warning:** Raw JSON env vars are a security risk and visible in logs.

## References

- [Google Analytics API Docs](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [Service Account Auth](https://cloud.google.com/docs/authentication/application-default-credentials)
- [ga_vacxin.py](../scripts/ga_vacxin.py) — Health monitor source
- [fetch_ga_stats.py](../scripts/fetch_ga_stats.py) — Metrics fetch source
