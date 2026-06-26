# Google OAuth (Gmail) login cho CMS/Editor — Hướng dẫn cài đặt

Tài liệu này hướng dẫn bật **đăng nhập bằng Google** cho Editor/CMS, chạy song song
với GitHub OAuth (chế độ `dual`) rồi chuyển hẳn sang Google (`google`) khi đã ổn.

> Backend: FastAPI tại `services/visitor-counter/` (Render service
> `blog-visitor-api`). Frontend: `templates/editor.html` + `static/js/editor.js`
> + `static/js/auth.js`.

Mọi thay đổi **code** đã xong trong repo. Chỉ còn **3 việc tay** bên ngoài:

1. Tạo Google OAuth Client trong Google Cloud Console.
2. Thêm Client ID/Secret + env vars trên Render.
3. Bấm đăng nhập và cấp quyền Google.

---

## 1. Google Cloud Console

### 1.1 Tạo OAuth Client

1. Vào <https://console.cloud.google.com/> → chọn (hoặc tạo) một project.
2. **APIs & Services → OAuth consent screen**:
   - User type: **External** (hoặc Internal nếu dùng Google Workspace nội bộ).
   - App name, support email, developer contact → điền.
   - **Scopes:** chỉ thêm `openid`, `.../auth/userinfo.email`,
     `.../auth/userinfo.profile`. **KHÔNG** thêm scope Gmail (đọc/gửi mail).
   - Test users: thêm các Gmail admin nếu app đang ở chế độ *Testing*.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Web application**.

### 1.2 Authorized JavaScript origins

```
https://seomoney.org
https://blog-visitor-api.onrender.com
```

### 1.3 Authorized redirect URI

Phải khớp **CHÍNH XÁC** với `GOOGLE_REDIRECT_URI` trên backend:

```
https://blog-visitor-api.onrender.com/auth/google/callback
```

> Nếu backend của bạn deploy ở domain khác (vd `blog-vipzone-api.onrender.com`),
> dùng đúng domain đó cho cả origin lẫn redirect URI, và set `GOOGLE_REDIRECT_URI`
> trùng giá trị này. `redirect_uri` lệch dù một ký tự → Google trả `redirect_uri_mismatch`.

### 1.4 Lấy thông tin

Sau khi tạo, copy **Client ID** và **Client Secret**.

---

## 2. Render env vars

Trên Render dashboard của service backend → **Environment** → thêm:

```env
AUTH_PROVIDER=dual
GOOGLE_CLIENT_ID=xxxxxxxxxxxx-xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=https://blog-visitor-api.onrender.com/auth/google/callback
GOOGLE_ADMIN_EMAILS=admin@gmail.com
```

Giữ nguyên các biến GitHub đang chạy:

```env
GH_CLIENT_ID=...
GH_CLIENT_SECRET=...
ADMIN_EMAILS=...
```

`GOOGLE_ADMIN_EMAILS` là **allowlist comma-separated** — chỉ những email này mới
vào được CMS:

```env
GOOGLE_ADMIN_EMAILS=duy@example.com,admin@example.com
```

> Nếu để trống `GOOGLE_ADMIN_EMAILS`, backend fallback dùng `ADMIN_EMAILS`.

Lưu env → **Manual Deploy / Restart** service.

---

## 3. Chế độ rollout

| `AUTH_PROVIDER` | Nút hiển thị ở Editor | Ghi chú |
|-----------------|-----------------------|---------|
| `github` | Chỉ GitHub | Mặc định, hành vi cũ |
| `dual`   | **Google** (chính) + GitHub (phụ) | Rollout an toàn — test Google nhưng vẫn có GitHub fallback |
| `google` | Chỉ Google | Khi đã tin tưởng Google flow |

**Khuyến nghị:** bật `dual` trước → đăng nhập thử bằng Google → khi ổn đổi
`AUTH_PROVIDER=google`.

---

## 4. Luồng kỹ thuật

```
Editor → "Đăng nhập bằng Google"
      → GET {backend}/auth/google/start?return_to=/editor/
      → Google consent (scope: openid email profile)
      → GET {backend}/auth/google/callback?code=...&state=...
         · validate state (CSRF)
         · exchange code → token (gồm id_token)
         · verify id_token (Google tokeninfo: chữ ký + exp + aud + iss)
         · require email + email_verified + email ∈ GOOGLE_ADMIN_EMAILS
         · tạo session Redis (TTL = SESSION_TTL)
      → redirect {blog}/editor/#sid=<opaque>
      → editor.js đọc #sid → sessionStorage → GET /auth/me
```

`/auth/me` trả về normalized user:

```json
{
  "authenticated": true,
  "provider": "google",
  "email": "admin@gmail.com",
  "name": "Admin Name",
  "avatar_url": "https://lh3.googleusercontent.com/..."
}
```

(Khi provider là GitHub, các field `username`/`avatar` cũ vẫn trả về để tương thích.)

---

## 5. Bảo mật

- `client_secret` **chỉ** ở server (Render env) — không bao giờ về frontend.
- **Không** log OAuth token / id_token / claims.
- `state` chống CSRF (lưu Redis 10 phút, dùng một lần).
- `id_token` verify server-side: chữ ký + hạn + `aud == GOOGLE_CLIENT_ID` + `iss` Google.
- Bắt buộc `email_verified == true` và email thuộc allowlist.
- Scope chỉ `openid email profile` — **không** đụng Gmail API.

---

## 6. Hạn chế đã biết

- Session Google **không** có GitHub `access_token`. Nếu admin đăng nhập bằng
  Google rồi **publish bài trực tiếp** từ Editor (`/cms/save-post`, push qua GitHub
  Contents API), endpoint đó vẫn cần GitHub token → sẽ thiếu. Khi cần publish
  trực tiếp, dùng GitHub login (vẫn còn ở chế độ `dual`), hoặc cấu hình một
  GitHub PAT phía server cho luồng publish (việc nâng cấp riêng, ngoài phạm vi PR này).

---

## 7. Rollback

Đổi env trên Render và restart:

```env
AUTH_PROVIDER=github
```

GitHub OAuth vẫn nguyên vẹn → đăng nhập trở lại như trước. Không cần revert code.
