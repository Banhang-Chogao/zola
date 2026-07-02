# Google Snapshot Setup Guide

## Overview

Google Snapshot widget (`templates/partials/google-snapshot.html`) displays real-time data từ Google:
- **Search Performance** (clicks, impressions, CTR, avg position) from Google Search Console
- **Site Speed** (Lighthouse mobile score, LCP) from PageSpeed API
- **Top Page** (7-day top performing page) from GSC + GA

Dữ liệu được fetch bằng workflow hourly (`gsc-stats.yml`, `pagespeed.yml`) và lưu vào:
- `data/gsc-stats.json`
- `data/pagespeed.json`
- `data/ga-stats.json`

## Current Status

❌ **GSC (Google Search Console) — NOT CONFIGURED**

`render.yaml` lines 123-131 định nghĩa 3 environment variables cần điền:
```yaml
GSC_CLIENT_ID        # ← Missing
GSC_CLIENT_SECRET    # ← Missing
GSC_REFRESH_TOKEN    # ← Missing
```

Khi các env vars này trống, VIPZone backend `/gsc/metrics` endpoint trả về `status: "not_connected"`.

## Setup Steps

### 1. Create Google Cloud OAuth Credentials

1. Vào https://console.cloud.google.com
2. Tạo project hoặc chọn project hiện tại
3. **Enable APIs:**
   - Google Search Console API
   - PageSpeed Insights API
   - Google Analytics API (nếu dùng GA)
4. **Create OAuth 2.0 credential (Web Application):**
   - Go to Credentials → Create Credential → OAuth 2.0 Client IDs
   - Application type: Web application
   - Authorized redirect URIs:
     - `https://api.seomoney.org/auth/google/callback` (production)
     - `http://localhost:8000/auth/google/callback` (local dev, optional)
   - Click Create
   - Copy **Client ID** and **Client Secret**

### 2. Get GSC Refresh Token

Option A: Using OAuth Playground (quickest for first-time setup)

```bash
# 1. Go to https://developers.google.com/oauthplayground
# 2. Gear icon (top-right) → "Use your own OAuth credentials"
# 3. Paste Client ID and Client Secret from step 1
# 4. Left panel → Select "Google Search Console API v1" → Scopes:
#    - https://www.googleapis.com/auth/webmasters.readonly
#    - https://www.googleapis.com/auth/webmasters
# 5. Click "Authorize APIs"
# 6. Follow Google login flow
# 7. Click "Exchange authorization code for tokens"
# 8. Copy Refresh Token (will show in response)
```

Option B: Manual token generation (Python)

```python
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    'https://www.googleapis.com/auth/webmasters',
    'https://www.googleapis.com/auth/webmasters.readonly',
]

# credentials.json = OAuth client JSON from Google Cloud Console
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json',
    scopes=SCOPES,
    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
)

auth_url, _ = flow.authorization_url(prompt='consent')
print(f"Authorize at: {auth_url}")

auth_code = input("Paste auth code: ")
flow.fetch_token(code=auth_code)

refresh_token = flow.credentials.refresh_token
print(f"Refresh Token: {refresh_token}")
```

### 3. Add Credentials to Render Dashboard

1. Vào https://dashboard.render.com
2. Chọn service **blog-vipzone-api**
3. Go to **Environment** tab
4. Add/Update env variables:

| Key | Value |
|-----|-------|
| `GSC_CLIENT_ID` | (paste from step 1) |
| `GSC_CLIENT_SECRET` | (paste from step 1) |
| `GSC_REFRESH_TOKEN` | (paste from step 2) |

5. Click **Save Changes**
6. Service sẽ tự restart (wait ~2-3 minutes)

### 4. Verify Setup

1. Run workflow manually:
   - Vào GitHub Actions → **Fetch GSC Stats**
   - Click "Run workflow" → Run
   - Wait for completion

2. Check output:
   - `data/gsc-stats.json` should now have real data
   - Instead of `"status_note": "not_connected"`, should show:
     ```json
     {
       "updated_at": "2026-07-02T15:30:00+00:00",
       "totals": {
         "clicks": 1234,
         "impressions": 28456,
         "ctr_pct": 4.38,
         "position": 12.5
       },
       "top_page": "/some-page/"
     }
     ```

3. Verify on production:
   - Build locally: `zola build`
   - Check `/changelog/` or any page → scroll footer
   - Google Snapshot widget should show real Search Performance

## Troubleshooting

### "Backend returned HTTP 403"
- **Cause:** Refresh token expired or invalid
- **Fix:** 
  1. Re-generate refresh token (step 2)
  2. Update `GSC_REFRESH_TOKEN` on Render
  3. Run workflow again

### "GSC_PROPERTY_URL not found"
- **Cause:** Site not verified in Google Search Console
- **Fix:**
  1. Vào https://search.google.com/search-console
  2. Add property `seomoney.org` (Domain type)
  3. Verify ownership (add DNS record or HTML file)
  4. Wait 24h for GSC data to populate

### "token_expired" or "invalid_grant"
- **Cause:** Refresh token is stale (>6 months without use)
- **Fix:** Re-authenticate using OAuth Playground or Python script

### Widget still shows "Search Console chưa kết nối"
1. Check `data/gsc-stats.json` in repo → what's the `status_note` or error?
2. Tail Render service logs:
   - Dashboard → **blog-vipzone-api** → Logs
   - Look for `/gsc/metrics` request
3. If backend is running but still returning `not_connected`:
   - Check if env vars are set correctly
   - Restart service from Render dashboard
   - Wait 2-3 minutes for service to be online

## Testing with Dummy Data

If you're waiting for OAuth setup, you can test widget rendering with dummy data:

```json
// data/gsc-stats.json
{
  "updated_at": "2026-07-02T15:30:00+00:00",
  "totals": {
    "clicks": 1247,
    "impressions": 28456,
    "ctr_pct": 4.38,
    "position": 12.5
  },
  "top_page": "/tools/content-direction/"
}
```

Then `zola build` and verify widget displays without errors. Replace with real data once OAuth is configured.

## File Map

| Component | Path | Notes |
|-----------|------|-------|
| Widget template | `templates/partials/google-snapshot.html` | Renders GSC/PageSpeed/GA data |
| Fetch script | `scripts/fetch_gsc_stats.py` | Calls VIPZone backend /gsc/metrics |
| Workflow | `.github/workflows/gsc-stats.yml` | Runs hourly, executes fetch script |
| Data file | `data/gsc-stats.json` | Commit this after OAuth setup |
| Backend config | `render.yaml` lines 123-131 | Where env vars are defined |
| Backend code | `services/vipzone/gsc.py` | VIPZone GSC integration logic |

## References

- [Google Search Console API](https://developers.google.com/webmasters/documentation/v1/get-started)
- [OAuth 2.0 for Server-to-Server](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [Google Cloud Console](https://console.cloud.google.com)
