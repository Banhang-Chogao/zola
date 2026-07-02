# Google Search Console - Direct Setup (Đơn Giản)

**Fetch dữ liệu TRỰC TIẾP từ GSC API — KHÔNG cần VIPZone backend!**

## ⚡ Quick Setup (3 bước)

### 1️⃣ Tạo Service Account (Google Cloud Console)

```bash
# Vào: https://console.cloud.google.com/iam-admin/serviceaccounts

# Bấm "Create Service Account"
# - Service account name: "gsc-blog" (hoặc tên bất kỳ)
# - Bấm "Create and Continue"

# Grant roles: "Viewer" (hoặc "Editor" nếu cần write)
# Bấm "Continue"

# Bấm "Create key" → JSON → Download credentials.json
```

### 2️⃣ Add vào GitHub Secrets

```bash
# Encode credentials file thành Base64:
cat ~/Downloads/credentials.json | base64 -w 0 > /tmp/creds.b64

# Copy nội dung từ /tmp/creds.b64
```

Trên GitHub:
- Vào repo → **Settings** → **Secrets and variables** → **Actions**
- Click **New repository secret**
- Name: `GSC_CREDENTIALS_B64`
- Value: (paste base64 content từ trên)
- Click **Add secret**

### 3️⃣ Add Service Account thành Owner trong Google Search Console

```
# Vào: https://search.google.com/search-console
# - Chọn property "seomoney.org"
# - Settings → Users and permissions
# - Invite user → (paste email của service account)
# - Role: "Owner" hoặc "Full"
# - Confirm
```

Email service account nằm ở: `credentials.json` → field `client_email`

**Example:**
```
gsc-blog@my-project-123456.iam.gserviceaccount.com
```

## ✅ Test

```bash
# Local test (nếu có credentials.json):
export GSC_CREDENTIALS_PATH=~/.gsc-credentials.json
python scripts/fetch_gsc_direct.py

# GitHub Actions test:
# Vào Actions → "Fetch GSC Stats (Direct)" → "Run workflow"
```

## 📊 Verify

Sau khi chạy, check `data/gsc-stats.json`:

```json
{
  "updated_at": "2026-07-02T15:30:00+00:00",
  "status": "connected",
  "totals": {
    "clicks": 1247,
    "impressions": 28456,
    "ctr_pct": 4.38,
    "position": 12.5
  },
  "top_page": "/tools/content-direction/"
}
```

Widget sẽ hiển thị data thật ✨

## 🔧 Troubleshooting

### "Credentials file not found"
- Check `GSC_CREDENTIALS_B64` secret được add đúng chưa
- Verify Base64 encode không có lỗi

### "Permission denied" / "Invalid credentials"
- Verify email service account được add vào Google Search Console với quyền "Owner"
- Check credentials.json có field `client_email` không

### "No GSC data returned"
- Site `seomoney.org` có được verify trong GSC chưa?
- Chờ 24h-48h để Google crawl + index

### Local test không chạy
```bash
# Kiểm tra có cài library không:
pip install google-auth google-auth-httplib2 google-api-python-client

# Rồi retry
python scripts/fetch_gsc_direct.py
```

## 📋 File Map

| File | Purpose |
|------|---------|
| `scripts/fetch_gsc_direct.py` | Fetch script (direct GSC API) |
| `.github/workflows/gsc-stats-direct.yml` | Workflow (hourly) |
| `data/gsc-stats.json` | Output data (cho template) |
| `templates/partials/google-snapshot.html` | Widget (reads gsc-stats.json) |

## ⚠️ KHÁC với VIPZone backend approach

| Aspect | VIPZone | Direct GSC |
|--------|---------|-----------|
| **Setup** | Complex (OAuth + Render) | Simple (Service Account) |
| **Dependencies** | VIPZone running | google-auth library |
| **Cost** | Render free tier | Free (Google free quota) |
| **Security** | Backend handles auth | Local credentials |
| **Speed** | Cached (VIPZone) | Real-time |

## 🚀 Next Steps

1. ✅ Create Service Account + Download credentials
2. ✅ Base64 encode → add `GSC_CREDENTIALS_B64` secret
3. ✅ Add service account email → Google Search Console
4. ✅ Run workflow (manual or wait for cron)
5. ✅ Verify `data/gsc-stats.json` has real data

Done! Widget will show live metrics. ✨
