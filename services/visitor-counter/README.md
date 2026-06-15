# Blog Visitor Counter

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
   - **Name**: `blog-visitor-api`
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
| `CORS_ORIGIN` | `https://banhang-chogao.github.io` |
| `COUNTER_KEY` | `blog:visitors` (optional) |

Click **Create Web Service**. Render build + deploy ~2-3 phút. Sau đó được
URL kiểu `https://blog-visitor-api.onrender.com`.

### Bước 4: Test endpoints

```bash
# Test track
curl -X POST https://blog-visitor-api.onrender.com/track \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
# → {"ok":true,"counted":true,"count":1}

# Test bot filter
curl -X POST https://blog-visitor-api.onrender.com/track \
  -H "User-Agent: googlebot"
# → {"ok":true,"counted":false}

# Test stats
curl https://blog-visitor-api.onrender.com/stats
# → {"count":1}
```

### Bước 5: Tích hợp vào blog

Sửa `config.toml` ở repo zola (root):

```toml
[extra]
visitor_api_url = "https://blog-visitor-api.onrender.com"
```

Commit + push → CI auto-deploy → footer blog hiển thị visitor count.

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
