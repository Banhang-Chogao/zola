# Paywall — bài viết trả phí

Hệ thống paywall cho blog Zola: teaser public, full content qua FastAPI backend, thanh toán Momo + admin approve thủ công.

## Kiến trúc

```text
Static (GitHub Pages)          Backend (FastAPI + SQLite)
─────────────────────          ───────────────────────────
Teaser HTML                    private_content/{post_id}.md
Paywall box UI        ──API──► Request / Unlock / Content
Form request/unlock            Admin generate code + SMTP email
```

**Không** publish full premium body vào `public/`. Script `paywall_prepare_build.py --strip` chạy trước `zola build` trong CI.

## Frontmatter bài premium

```toml
[extra]
premium = true
price = 29000
premium_post_id = "premium-fintech-001"
premium_title = "Tên hiển thị"
premium_teaser_words = 180
```

## Momo payment link

```text
https://me.momo.vn/G5T1CDFRuJFWfBCDiK/zPdywWy346xVaQr
```

Override qua env `MOMO_PAYMENT_LINK` trên backend.

## Backend setup

```bash
cd /path/to/zola
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

export PAYWALL_ADMIN_TOKEN="your-strong-token"
export PAYWALL_DB_PATH="./data/paywall.db"
export PAYWALL_CORS_ORIGIN="https://banhang-chogao.github.io"
export PAYWALL_BLOG_DOMAIN="banhang-chogao.github.io"
export PAYWALL_BLOG_NAME="Duy Nguyen Blog"

# SMTP (gửi approve code)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="..."
export SMTP_PASSWORD="..."
export SMTP_FROM="noreply@example.com"

uvicorn backend.paywall_app:app --host 0.0.0.0 --port 8787
```

Deploy backend cùng thư mục `private_content/` (sync sau mỗi lần thêm/sửa bài premium).

### Render (khuyến nghị)

Blueprint `render.yaml` khai báo service `blog-paywall-api` (`services/paywall/`).

1. Apply Blueprint trên Render Dashboard.
2. Điền `PAYWALL_ADMIN_TOKEN`, `SMTP_*` (sync: false trong blueprint).
3. Disk `/var/data` lưu SQLite (`PAYWALL_DB_PATH=/var/data/paywall.db`).
4. Copy URL API → `config.toml`: `paywall_api_url = "https://blog-paywall-api.onrender.com"`.
5. Redeploy static site.

## Frontend config

Trong `config.toml`:

```toml
paywall_api_url = "https://your-paywall-api.onrender.com"
```

## Admin

- Trang: `/admin/paywall/`
- Đăng nhập bằng `PAYWALL_ADMIN_TOKEN` (lưu sessionStorage, không public)
- Flow: xem pending requests → generate approve code → send email

CLI gửi email (nếu cần):

```bash
python3 scripts/paywall_send_email.py \
  --to reader@example.com \
  --title "Tên bài" \
  --url "https://banhang-chogao.github.io/zola/posting/.../" \
  --code ABCD1234EFGH \
  --expires "2026-06-25T00:00:00Z"
```

## API endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/paywall/request-access` | — |
| POST | `/api/paywall/unlock` | — |
| GET | `/api/paywall/content/{post_id}` | Bearer session |
| GET | `/api/paywall/admin/requests` | Admin token |
| POST | `/api/paywall/admin/generate-code` | Admin token |
| POST | `/api/paywall/admin/send-code-email` | Admin token |
| POST | `/api/paywall/log-print` | Bearer session |

## Build local

```bash
python3 scripts/paywall_prepare_build.py --strip
zola build
python3 scripts/paywall_prepare_build.py --restore   # khôi phục source md
```

## Tests

```bash
python3 -m unittest scripts.test_paywall -v
```

## Bảo mật & bản quyền

- Approve code lưu SHA256 hash, không plaintext trong DB
- Code bind `email + post_id`, có expiry và max_usage
- Read-only deterrent + watermark màn hình + watermark in/PDF
- Không hứa DRM tuyệt đối — mục tiêu deterrent + truy vết