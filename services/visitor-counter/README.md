# Blog Backend — Visitor Counter + GitHub OAuth + News API

FastAPI + Redis service đa dụng cho blog: visitor counter, GitHub OAuth
cho CMS, RSS Checker, curated news feeds (Znews Du lịch).

---

## ⚡ Quick deploy (Render Blueprint — 3 phút)

File `render.yaml` đã có sẵn → Render tự dựng Redis + Web Service +
inject `REDIS_URL`. Bạn chỉ cần điền 3 env vars là chạy.

### Bước 1: Tạo GitHub OAuth App (~1 phút)

1. Vào https://github.com/settings/developers → **New OAuth App**
2. Điền:
   - Application name: `Blog CMS Auth`
   - Homepage URL: `https://seomoney.org`
   - Authorization callback URL:
     `https://blog-vipzone-api.onrender.com/auth/callback`
3. Register → màn hình hiển thị **Client ID** (copy)
4. Generate a new client secret → copy ngay (chỉ hiện 1 lần)

### Bước 2: Apply Blueprint trên Render (~1 phút)

1. Vào https://dashboard.render.com/blueprints
2. **New Blueprint Instance** → connect repo `Banhang-Chogao/zola`
3. Render đọc `render.yaml` ở repo root → preview 2 service sẽ tạo:
   `blog-redis` (Redis) + `blog-vipzone-api` (Web)
4. **Điền 3 env vars sync:false**:
   - `BACKEND_URL`: `https://blog-vipzone-api.onrender.com`
     (Render assign URL theo tên service)
   - `GH_CLIENT_ID`: dán từ Bước 1
   - `GH_CLIENT_SECRET`: dán từ Bước 1
5. **Apply** → Render build + deploy ~2-3 phút

### Bước 3: Bật trên blog (~1 phút)

Sửa `config.toml` ở repo root:
```toml
[extra]
visitor_api_url = "https://blog-vipzone-api.onrender.com"
```

Commit + push → CI auto-build → tất cả tính năng tự bật:
- Footer visitor counter clock chuyển từ DEMO → LIVE
- `/editor/` login GitHub OAuth hoạt động
- `/baochi/` RSS Checker tool sẵn sàng
- `/du-lich/` fetch cards Znews + cache 30 phút

---

## 📋 Manual deploy (nếu không dùng Blueprint)

FastAPI + Redis service tối giản đếm lượt truy cập real-time cho blog.

## Kiến trúc

```
Browser → POST /track  ↘
                        FastAPI → INCR Redis key
Browser → GET  /stats  ↗
```

- **FastAPI async** — non-blocking, handle nghìn req/s với 1 worker
- **Redis INCR atomic** — không cần lock, concurrent-safe
- **Bot filter** — regex single-pass, skip Googlebot, FB preview, curl, …
- **CORS** — chỉ allow blog origin gọi API

## Files

```
services/visitor-counter/
├── main.py             # FastAPI app + endpoints
├── requirements.txt    # fastapi, uvicorn, redis
├── Procfile            # Render/Railway start command
├── runtime.txt         # Python version pin
├── .env.example        # Template env vars
└── README.md           # File này
```

---

## 🚀 Deploy lên Render (free tier, ~5 phút)

### Bước 1: Tạo Redis instance

1. Vào https://dashboard.render.com/new/redis (cần đăng ký tài khoản free)
2. Điền:
   - **Name**: `blog-redis`
   - **Region**: gần bạn (Singapore cho VN)
   - **Plan**: **Free** (25MB — dư xài cho 1 counter)
   - **Maxmemory Policy**: `allkeys-lru`
3. Click **Create Redis**
4. Sau khi tạo xong, vào trang detail → copy **Internal Redis URL** (dạng
   `redis://red-xxx:6379`)

### Bước 2: Tạo Web Service

1. Vào https://dashboard.render.com/new/web
2. Chọn **Build and deploy from a Git repository**
3. Connect repo `Banhang-Chogao/zola` (cần authorize GitHub một lần)
4. Điền:
   - **Name**: `blog-vipzone-api`
   - **Region**: cùng region với Redis ở bước 1
   - **Branch**: `main`
   - **Root Directory**: `services/visitor-counter`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: (để trống — Procfile sẽ override)
   - **Plan**: **Free**

### Bước 3: Set Environment Variables

Trong section **Environment Variables** của Web Service:

| Key | Value |
|---|---|
| `REDIS_URL` | Paste Internal Redis URL từ bước 1 |
| `CORS_ORIGIN` | `https://seomoney.org` |
| `COUNTER_KEY` | `blog:visitors` (optional) |

Click **Create Web Service**. Render build + deploy ~2-3 phút. Sau đó được
URL kiểu `https://blog-vipzone-api.onrender.com`.

### Bước 4: Test endpoints

```bash
# Test track
curl -X POST https://blog-vipzone-api.onrender.com/track \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
# → {"ok":true,"counted":true,"count":1}

# Test bot filter
curl -X POST https://blog-vipzone-api.onrender.com/track \
  -H "User-Agent: googlebot"
# → {"ok":true,"counted":false}

# Test stats
curl https://blog-vipzone-api.onrender.com/stats
# → {"count":1}
```

### Bước 5: Tích hợp vào blog

Sửa `config.toml` ở repo zola (root):

```toml
[extra]
visitor_api_url = "https://blog-vipzone-api.onrender.com"
# cms_auth_url để trống = reuse visitor_api_url (cùng service FastAPI)
cms_auth_url = "https://blog-vipzone-api.onrender.com"
```

Commit + push → CI auto-deploy → footer blog hiển thị visitor count.

---

## 🔐 Setup GitHub OAuth (CMS auth)

Service này làm OAuth gateway cho `/editor/` (CMS) và `/tools/f-dashboard/`
(F-Dashboard). Cùng một GitHub OAuth App + callback — client chỉ khác
`return_to` (path tương đối). Whitelist email/username server-side (không
bypass client được).

### Bước 1: Tạo GitHub OAuth App

1. Vào https://github.com/settings/developers → **New OAuth App**
2. Điền:
   - **Application name**: `Blog CMS Auth` (hoặc tên gì cũng được)
   - **Homepage URL**: `https://seomoney.org`
   - **Authorization callback URL**:
     `https://blog-vipzone-api.onrender.com/auth/callback`
     (= `${BACKEND_URL}/auth/callback`, PHẢI MATCH EXACT)
3. **Register application** → màn hình hiển thị **Client ID**
4. Click **Generate a new client secret** → copy ngay (chỉ hiện 1 lần)

### Bước 2: Set env vars trên Render

Trong **Environment Variables** của Web Service:

| Key | Value |
|---|---|
| `GH_CLIENT_ID` | Client ID vừa lấy ở Bước 1 |
| `GH_CLIENT_SECRET` | Client Secret vừa lấy ở Bước 1 |
| `BACKEND_URL` | `https://blog-vipzone-api.onrender.com` |
| `BLOG_URL` | `https://seomoney.org` |
| `ADMIN_EMAILS` | `292648126+Banhang-Chogao@users.noreply.github.com` (comma-separated cho nhiều) |
| `ADMIN_USERNAMES` | `banhang-chogao` (fallback nếu email noreply chưa verify) |
| `SESSION_TTL` | `7200` (2 giờ idle, optional) |

Click **Save Changes** → Render auto-restart service.

### Bước 3: Test flow

**CMS:** `https://seomoney.org/editor/`  
**F-Dashboard:** `https://seomoney.org/tools/f-dashboard/`

1. Click "Đăng nhập với GitHub"
2. Authorize trên GitHub (lần đầu)
3. Nếu whitelist pass → redirect về **đúng trang** (`return_to`) với `#sid=...`
4. Nếu denied → `?auth_error=access_denied` trên trang gốc (không ép về `/editor/`)

`config.toml` — `cms_auth_url` phải nằm dưới `[extra]` (không trong `[extra.giscus]`)
để meta `vipzone-auth-api` render trên mọi trang.

### Mở rộng: thêm Contributor

Append email vào `ADMIN_EMAILS`:
```
ADMIN_EMAILS=292648126+Banhang-Chogao@users.noreply.github.com,other.contributor@example.com
```

Hoặc thay logic email white-list bằng GitHub Collaborator API check —
sửa hàm `_is_allowed_email()` trong `main.py`:

```python
def _is_allowed_email(verified_emails: set) -> bool:
    # TODO: thay bằng async call tới
    # GET /repos/{owner}/{repo}/collaborators/{username}/permission
    return bool(verified_emails & ADMIN_EMAILS)
```

### Bảo mật

- `client_secret` CHỈ trên Render env vars, không bao giờ bake vào client JS
- `access_token` của GitHub được giữ Redis-side, client chỉ có opaque `sid`
- `sid` là 32-byte URL-safe random → không brute-force trong session lifetime
- sessionStorage trên client → auto-clear khi đóng tab
- Redis `SETEX` TTL 2h → idle quá tự logout
- Email white-list check server-side, client KHÔNG thể bypass
- State param trong OAuth flow ngăn CSRF

---

## 🚂 Alternative: Railway

Tương tự Render nhưng Redis là plugin của service:

1. https://railway.app → New Project → Deploy from GitHub repo
2. Chọn root `services/visitor-counter`
3. Click **+ Add Plugin** → **Redis** (free tier)
4. Railway tự inject env var `REDIS_URL`
5. Add env vars khác trong **Variables** tab: `CORS_ORIGIN`, `COUNTER_KEY`
6. Settings → **Generate Domain** → có URL public
7. Tích hợp vào blog như bước 5 Render

---

## ⚠️ Lưu ý free tier Render

- **Web service tự sleep sau 15 phút** không có request → first request sau
  khi ngủ mất ~30s wake up. Visitor counter có thể "trễ" 1 lần.
- **Redis free 25MB** — counter chỉ dùng 1 key + 1 int ≈ vài chục byte,
  dư xài muôn đời.
- **Keep service awake**: setup UptimeRobot free ping `GET /` mỗi 10 phút.

## 🔒 Bảo mật

- CORS chỉ allow origin của blog → người khác không thể inflate count từ
  domain họ
- Bot detection skip Googlebot/social previews → số liệu là user thật
- Không lưu IP, không lưu User-Agent → privacy friendly
- KHÔNG có authentication → ai biết URL cũng track được. Nếu cần
  ratelimit, thêm `slowapi` middleware (kèm Redis backend)
