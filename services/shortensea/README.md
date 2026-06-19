# ShortenSEA API — Deploy Render

Backend lưu short link, tracking click, approve code. Frontend đã live tại
`https://banhang-chogao.github.io/zola/shortensea/` — cần API này để chạy production.

## ⚡ Nhanh nhất (~5 phút)

Bạn **đã có** `blog-vipzone-api` trên Render → chỉ cần thêm service mới từ blueprint.

### Bước 1: Sync Blueprint trên Render

1. Vào https://dashboard.render.com/blueprints
2. Chọn blueprint repo **Banhang-Chogao/zola** (nếu chưa có → **New Blueprint Instance** → connect repo)
3. Bấm **Manual Sync** / **Sync Blueprint**
4. Render sẽ thấy service mới: **`blog-shortensea-api`** (+ disk `shortensea-data`)
5. **Apply** thay đổi → chờ build ~3–5 phút

### Bước 2: Thêm callback OAuth trên GitHub

Dùng **cùng** OAuth App đã tạo cho CMS (`Blog CMS Auth`):

1. https://github.com/settings/developers → chọn OAuth App
2. **Authorization callback URL** — thêm dòng (giữ URL cũ):

   ```
   https://blog-shortensea-api.onrender.com/auth/callback
   ```

   GitHub cho phép nhiều callback nếu tách bằng newline hoặc tạo app riêng.

### Bước 3: Điền 3 env vars (service `blog-shortensea-api`)

Vào Render → **blog-shortensea-api** → **Environment**:

| Key | Value |
|-----|-------|
| `SHORTENSEA_BACKEND_URL` | `https://blog-shortensea-api.onrender.com` |
| `GH_CLIENT_ID` | Copy từ service `blog-vipzone-api` (cùng giá trị) |
| `GH_CLIENT_SECRET` | Copy từ service `blog-vipzone-api` (cùng giá trị) |

Save → Render tự redeploy.

### Bước 4: Kiểm tra

```bash
curl https://blog-shortensea-api.onrender.com/
# → {"service":"shortensea","status":"ok",...}
```

Mở blog: https://banhang-chogao.github.io/zola/shortensea/

- Đăng nhập GitHub → tạo link → copy short URL dạng `.../zola/s/{slug}`
- Truy cập short URL → redirect + log click
- Admin (`banhang-chogao`) thấy badge **Super VIP** + panel tạo approve code

`config.toml` đã có:

```toml
shortensea_api_url = "https://blog-shortensea-api.onrender.com"
```

Không cần sửa thêm sau khi API chạy.

---

## Luồng hoạt động

```
GitHub Pages (/shortensea/*)  →  JS gọi API (CORS)
GitHub Pages (/zola/s/{slug}) →  404.html → redirect.js → API /s/{slug} → 302 destination
```

## Endpoints chính

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/auth/login` | Bắt đầu OAuth (mọi user GitHub verified) |
| GET | `/auth/me` | Profile + plan (Bearer session) |
| POST | `/auth/cms-bridge` | Đổi CMS session → ShortenSEA session (admin) |
| GET/POST | `/api/shortensea/links` | List / tạo link |
| GET | `/s/{slug}` | Redirect + track click (public) |
| POST | `/api/shortensea/redeem-code` | Kích hoạt gói MoMo |
| POST | `/api/shortensea/admin/codes` | Admin tạo approve code |

## Local dev

```bash
cd services/shortensea
pip install -r requirements.txt
export SHORTENSEA_BLOG_URL=http://127.0.0.1:1111/zola
export SHORTENSEA_BACKEND_URL=http://127.0.0.1:8790
# GH_CLIENT_ID + GH_CLIENT_SECRET từ OAuth App (callback http://127.0.0.1:8790/auth/callback)
uvicorn main:app --reload --port 8790
```

Để test UI không cần API: xóa/để trống `shortensea_api_url` trong `config.toml` → dùng localStorage prototype.

## Troubleshooting

| Triệu chứng | Cách xử lý |
|-------------|------------|
| API trả 404 / Not Found | Service chưa deploy hoặc đang sleep (free tier ~50s cold start) |
| Đăng nhập GitHub lỗi `token_exchange_failed` | Sai `GH_CLIENT_SECRET` hoặc callback URL chưa khớp |
| Tạo link 401 | Session hết hạn — đăng nhập lại |
| Short URL không redirect | Kiểm tra API `/s/{slug}`; GitHub Pages cần `404.html` hook (đã có) |
