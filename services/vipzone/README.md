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

Blueprint bake CORS, MoMo links, `VIPZONE_BACKEND_URL`. Cần set **`GITHUB_CLIENT_ID`** + **`GITHUB_CLIENT_SECRET`**
(sync: false) — copy từ OAuth App GitHub (callback `https://blog-vipzone-api.onrender.com/auth/callback`).

Admin OAuth chạy **trên chính `blog-vipzone-api`** (`/auth/login`, `/auth/callback`, `/auth/me`) — không dùng `blog-visitor-api`.

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
| GET | `/auth/login` | Public → GitHub OAuth |
| GET | `/auth/callback` | GitHub redirect |
| GET | `/auth/me` | Bearer session (`role`: user/vip/supervip) |
| POST | `/auth/logout` | Bearer session |
| POST | `/api/vipzone/payment-request` | Public |
| POST | `/api/vipzone/redeem` | Public |
| GET | `/api/vipzone/picker` | Public — sparse access map (`public` / `premium` / `admin_only`) |
| GET | `/api/vipzone/admin/stats` | CMS admin Bearer |
| GET | `/api/vipzone/admin/picker` | CMS admin Bearer |
| PUT | `/api/vipzone/admin/picker` | CMS admin Bearer — body `{ items: [{ url, access }] }` |
| POST | `/api/vipzone/admin/users/{email}/activate` | CMS admin Bearer |

## Local dev

```bash
cd services/vipzone
pip install -r requirements.txt
export VIPZONE_DB_PATH=/tmp/vipzone.db
uvicorn main:app --reload --port 8791
python3 -m unittest test_main.py -v
```
