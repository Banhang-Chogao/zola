# VIPZone API — Deploy Render

Backend MoMo payment requests, approve codes, VIP users, content picker admin.
Frontend: `/tools/vipzone/` + `/tools/vipzone-admin/`.

## Deploy (~3 phút)

1. https://dashboard.render.com/blueprints → chọn repo **Banhang-Chogao/zola**
2. **Manual Sync** → Apply service mới **`blog-vipzone-api`**
3. Chờ build xong → kiểm tra:

```bash
curl https://blog-vipzone-api.onrender.com/
# → {"service":"vipzone","status":"ok",...}
```

Không cần env vars thêm — blueprint đã bake CORS, MoMo links, CMS auth URL.

Admin endpoints dùng **CMS session** (`blog-visitor-api` OAuth) — không cần OAuth riêng cho VIPZone.

## Sau deploy

Trong `config.toml`:

```toml
vipzone_api_url = "https://blog-vipzone-api.onrender.com"
```

Push → auto-merge → GitHub Pages nhận meta `zola-vipzone-api`.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/` | Public health |
| POST | `/api/vipzone/payment-request` | Public |
| POST | `/api/vipzone/redeem` | Public |
| GET | `/api/vipzone/admin/stats` | CMS admin Bearer |
| GET | `/api/vipzone/admin/picker` | CMS admin Bearer |
| PUT | `/api/vipzone/admin/picker` | CMS admin Bearer |
| POST | `/api/vipzone/admin/users/{email}/activate` | CMS admin Bearer |

## Local dev

```bash
cd services/vipzone
pip install -r requirements.txt
export VIPZONE_DB_PATH=/tmp/vipzone.db
uvicorn main:app --reload --port 8791
python3 -m unittest test_main.py -v
```