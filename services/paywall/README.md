# Paywall API (Render)

FastAPI backend cho premium posts — unlock, admin approve codes, SMTP email.

## Deploy (Render Blueprint)

File `render.yaml` ở repo root khai báo service `blog-paywall-api`.

Sau khi deploy:

1. Điền env vars từ `.env.example` (đặc biệt `PAYWALL_ADMIN_TOKEN`, `SMTP_*`).
2. Mount disk `/var/data` cho SQLite (`PAYWALL_DB_PATH`).
3. Copy URL → `config.toml`: `paywall_api_url = "https://blog-paywall-api.onrender.com"`.
4. Redeploy static site (GitHub Pages).

## Local

```bash
cd /path/to/zola
export PAYWALL_ADMIN_TOKEN=dev-token
uvicorn backend.paywall_app:app --reload --port 8787
```