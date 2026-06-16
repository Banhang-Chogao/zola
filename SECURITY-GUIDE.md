# 🔐 Security Guide — Blog Bảo Mật

## 1. Backup Tự Động ✅

**Status: HOẠT ĐỘNG**

- **Cơ chế:** Mỗi commit lên GitHub = 1 version backup
- **Cách khôi phục:** `git revert <commit-hash>` hoặc GitHub restore from history
- **Tần suất:** Tự động với mỗi lần push
- **Không cần action:** Sẵn có, không cần cấu hình

---

## 2. Bảo Vệ `/editor` Endpoint

### **Status Hiện Tại: An Toàn** 🟢

```toml
cms_auth_url = ""  # Backend chưa kết nối
```

- `/editor` page hiển thị tĩnh (HTML + JS)
- **Không có authentication endpoint** → an toàn
- Chỉ có form UI, không connect backend
- Khi user vào `/editor/` → thấy hint: "Backend auth chưa được cấu hình"

### **Khi Kết Nối Backend (Tương Lai)**

Nếu bạn setup FastAPI backend + GitHub OAuth, cần áp dụng:

#### **A) Email Whitelist (Bắt Buộc)**
```python
# Backend env variables
ADMIN_EMAILS=your_email@example.com,other_admin@example.com
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
JWT_SECRET=very_long_random_key_here
```

- Chỉ email trong whitelist mới được login
- Người khác vào `/editor/` sẽ bị reject

#### **B) Security Headers**
```python
# Backend responses khi /auth/* hoặc /editor
response.headers["X-Frame-Options"] = "SAMEORIGIN"  # Prevent clickjacking
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```

#### **C) Rate Limiting**
```python
# Block after 5 failed login attempts per IP in 15 minutes
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/15 minutes")
async def login(request: Request):
    # GitHub OAuth flow
    pass
```

#### **D) CSRF Token Validation**
```python
# Editor.js sẽ kèm CSRF token khi publish/delete
# Backend validate để prevent CSRF attacks
@app.post("/editor/posts")
async def publish(request: Request):
    csrf_token = request.headers.get("X-CSRF-Token")
    if not validate_csrf(csrf_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
```

#### **E) Audit Log**
```python
# Log tất cả hành động admin (publish, delete, edit)
# File: logs/editor-audit.log
2026-06-16 10:23:45 | your_email@example.com | CREATE | "Tiêu đề bài" | by @username
2026-06-16 10:24:12 | your_email@example.com | DELETE | "Bài cũ" | by @username
```

---

## 3. Bảo Mật Dependencies 🔄

### **Dependabot (Tự Động Check Updates)**

**Status: ✅ ĐÃ CẤU HÌNH**

File: `.github/dependabot.yml` (đã tạo)

**Cấu hình tự động:**
- Cargo (Rust): Weekly updates, mỗi Monday 3:00 AM
- GitHub Actions: Weekly updates, mỗi Monday 4:00 AM
- Auto-approve & auto-merge patch/minor updates
- Manual review reminder cho major updates

**Workflow tự động:**
- File: `.github/workflows/dependabot-setup.yml`
- Tự động approve & merge patch/minor updates
- Comment nhắc nhở trên major updates

**Cách hoạt động:**
- ✅ Mỗi tuần, Dependabot check updates mới
- ✅ Nếu có security patch → tự động create PR
- ✅ Workflow auto-merge patch/minor (tuỳ cấu hình)
- ✅ Bạn review major updates trước merge

**Hướng dẫn chi tiết:** Xem `.github/DEPENDABOT-SETUP.md`

### **Manual Check**
```bash
# Kiểm tra lỗ hổng hiện tại
cargo audit  # Rust/Zola

# Fix lỗ hổng bảo mật
cargo update
```

---

## 4. HTTPS & DDoS Protection 🛡️

### **HTTPS Status** ✅
- GitHub Pages tự cấp HTTPS miễn phí
- Tất cả traffic tới blog đều mã hóa
- HSTS header bắt buộc

### **DDoS Protection Status**
- **Hiện Tại (GitHub Pages URL):** ✅ AWS Shield (GitHub native)
  - Auto-block >1000 req/sec
  - Rate limiting tự động
  - Không cần cấu hình thêm

- **Nếu Dùng Custom Domain:** ⏳ Cloudflare (tùy chọn)
  - Đăng ký Cloudflare Free Plan ($0)
  - Bật WAF + Firewall Rules
  - Rate limiting qua Cloudflare Workers

**Hướng dẫn chi tiết:** Xem `.github/CLOUDFLARE-DDOS-SETUP.md`

**Tóm tắt:**
```
GitHub Pages URL (hiện tại)    → GitHub DDoS Protection ✅
Custom Domain (tương lai)      → Cloudflare DDoS + WAF ✅
```

---

## 5. Quy Trình An Toàn Khi Publish 🚀

**Trước khi push lên main:**

```bash
# 1. Kiểm tra dependencies
npm audit  # hoặc tương đương

# 2. Review code tương tự production
git diff origin/main

# 3. Commit với message chi tiết
git commit -m "Thêm bài blog: Tiêu đề — nội dung an toàn"

# 4. Push
git push origin main  # CI/CD tự trigger, build & deploy
```

**GitHub Actions Workflows (Đã Có):**
- `.github/workflows/deploy.yml` → Build & deploy Pages
- `.github/workflows/security-audit.yml` → Scan code lỗ hổng
- `.github/workflows/build-related.yml` → Pre-check before deploy

---

## 6. Checklist Hàng Ngày ✨

| Item | Frequency | Action |
|------|-----------|--------|
| Git backup | Automatic | ✅ Commit frequently |
| Dependabot alerts | Daily | 🔍 Check GitHub notifications |
| HTTPS validity | Auto-renew | ✅ GitHub Pages handles |
| `/editor` auth | Manual | 📧 Verify admin whitelist if backend connected |
| Code security | Automatic | 🔐 GitHub Actions runs on push |

---

## 7. Emergency Recovery 🆘

**Nếu blog bị hack / dữ liệu mất:**

```bash
# 1. Revert tất cả changes
git revert --no-edit <bad-commit>
git push origin main

# 2. Force rebuild
# GitHub Pages tự detect push → rebuild + redeploy (2 phút)

# 3. Check audit logs
git log --oneline --all | head -50

# 4. Review /admin-author page cho signs of tampering
```

---

## Tóm Tắt Bảo Mật Hiện Tại

| Tính Năng | Status | Ghi Chú |
|-----------|--------|--------|
| **Backup Git** | ✅ Hoạt động | Tự động, mỗi commit |
| **HTTPS** | ✅ Hoạt động | GitHub Pages bao gồm |
| **Dependabot** | ✅ Hoạt động | `.github/dependabot.yml` đã cấu hình, workflow auto-merge |
| **DDoS Protection** | ✅ Hoạt động | GitHub native (hiện tại), Cloudflare optional (custom domain) |
| **Editor Auth** | 🟡 Sẵn sàng (chưa kích hoạt) | Sẽ bảo vệ khi connect backend |
| **Security Audit** | ✅ Workflows có | GitHub Actions chạy trên mỗi push |

---

**Tác giả:** Security Audit  
**Ngày:** 2026-06-16  
**Phiên bản:** 1.0
