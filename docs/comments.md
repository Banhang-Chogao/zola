# Hệ thống bình luận (Google login) — SEOMONEY

Thay thế **Giscus (đăng nhập GitHub)** bằng hệ thống bình luận **native, đăng nhập
Google**, có kiểm duyệt, an toàn cho AdSense.

## Vì sao không dùng Giscus + Google?

Giscus chạy trên GitHub Discussions và **chỉ** cho đăng nhập GitHub — không thể thay
bằng Google bên trong Giscus. Vì vậy bình luận được xây lại native trên backend
VIPZone (`services/vipzone`) với Google OAuth/OIDC sẵn có.

Giscus **không bị xoá**: chỉ ẩn. Đặt `config.extra.giscus.legacy_enabled = true` để
hiện lại comment GitHub cũ (read-only) nếu owner muốn.

## Phân tách vai trò (BẮT BUỘC)

| Vai trò | Điều kiện | Quyền |
|---------|-----------|-------|
| **admin** | email ∈ `GOOGLE_ADMIN_EMAILS` (hoặc GitHub admin) | Editor/CMS + kiểm duyệt bình luận |
| **commenter** | bất kỳ tài khoản Google đã xác minh (hoặc domain trong `COMMENTS_ALLOWED_DOMAINS`) | **Chỉ** bình luận — KHÔNG vào Editor/CMS |

Commenter session: `is_super=false`, `username=""` (không trùng `ADMIN_USERNAMES`),
`account_type="commenter"`. Các guard admin (`require_admin`, `require_owner`) chặn
thẳng `account_type=commenter` (defense-in-depth) + không có GitHub `access_token`
→ `/cms/save-post` luôn 401.

## Luồng đăng nhập

- Admin/CMS: `/auth/google/start` → callback yêu cầu email ∈ allowlist (**không đổi**).
- Bình luận: `/auth/comment/start` → cùng client OIDC (`openid email profile`, không
  có Gmail scope), state gắn tiền tố `gc:` → callback chia nhánh "comment mode":
  nhận mọi tài khoản Google đã xác minh, gán `commenter` (hoặc `admin` nếu trùng
  allowlist).

## API (VIPZone — `config.extra.cms_auth_url`)

| Route | Auth | Mô tả |
|-------|------|-------|
| `GET /comments?path=/url/` | public | bình luận đã duyệt (KHÔNG lộ email) |
| `POST /comments` | session bất kỳ | gửi bình luận; sanitize + rate-limit; mặc định `pending` |
| `GET /auth/me` | session | thêm `account_type` + `comment_role` (admin/commenter) |
| `GET /admin/comments` | admin | danh sách kiểm duyệt |
| `POST /admin/comments/{id}/approve` · `/hide` · `DELETE /admin/comments/{id}` | admin | duyệt / ẩn / xoá |

## Lưu trữ

SQLite VIPZone (`data/vipzone.db`), bảng `comments`. **Không** lưu email thô — chỉ
`author_email_hash` (sha256) + `author_sub_hash`. `ip_hash`/`user_agent_hash` chỉ
phục vụ chống lạm dụng.

## Bảo mật / AdSense

- Bình luận mới = `pending` (chờ duyệt) → không lên public tới khi admin duyệt.
- Strip control chars + `<` `>`; render bằng `textContent` (không innerHTML).
- Độ dài tối đa `COMMENTS_MAX_LENGTH` (mặc định 1500); chặn rỗng; rate-limit/author.
- Không bình luận ẩn danh (POST yêu cầu session, 401 nếu chưa đăng nhập).

## Env (Render — service `blog-vipzone-api`)

```
COMMENTS_ENABLED=true
COMMENTS_AUTH_PROVIDER=google
COMMENTS_DEFAULT_STATUS=pending
COMMENTS_MAX_LENGTH=1500
COMMENTS_ALLOWED_DOMAINS=        # trống = mọi tài khoản Google
```

Reuse `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_ADMIN_EMAILS` / `AUTH_PROVIDER=dual`
đã có. **Không** thêm callback Google mới — `/auth/google/callback` dùng chung.

## File map

| Thành phần | Path |
|------------|------|
| Storage | `services/vipzone/db.py` (bảng `comments` + CRUD) |
| Auth | `services/vipzone/cms_auth.py` (`/auth/comment/start`, comment-mode callback) |
| Router | `services/vipzone/comments.py` |
| Mount + guard | `services/vipzone/main.py`, `services/vipzone/personal_data.py` |
| Tests | `services/vipzone/test_comments.py` |
| Macro | `templates/macros/comments.html` (gọi trong `templates/page.html`) |
| JS | `static/js/comments.js` |
| Styles | `sass/_comments.scss` |
| Config | `config.toml` `[extra.comments]` + `extra.giscus.legacy_enabled` |
