# 🔐 Security Guide — Blog Bảo Mật

## 1. Backup Tự Động ✅

**Status: HOẠT ĐỘNG**

- **Cơ chế:** Mỗi commit lên GitHub = 1 version backup
- **Cách khôi phục:** `git revert <commit-hash>` hoặc GitHub restore from history
- **Tần suất:** Tự động với mỗi lần push
- **Không cần action:** Sẵn có, không cần cấu hình

---

## 2. Bảo Vệ `/editor` Endpoint

### **Status Hiện Tại: An Toàn** 🟢 **STATIC (NO LOGIN)**

```toml
cms_auth_url = ""  # Backend KHÔNG kết nối (cố ý)
```

**Quyết định:** `/editor` sẽ giữ **tĩnh (static), không có login**.

**Lý do:**
- ✅ Blog là static site (Zola/GitHub Pages) → không cần editor trực tuyến
- ✅ Nếu cần viết → edit Markdown locally + push GitHub
- ✅ Không cần backend phức tạp, DDoS attack, OAuth vulnerability
- ✅ `/editor` là demo UI, không activate login flow

**Cách sử dụng:**
- Viết bài locally: `zola serve` → preview locally
- Edit file Markdown: `content/posting/bai-moi.md`
- Commit + push GitHub → CI/CD auto-deploy

**Nếu Muốn Enable Login (Tương Lai):**
- Option: Supabase OAuth (không cần backend) - Recommend
- Xem `.github/EDITOR-LOGIN-OPTIONS.md` để so sánh 3 approaches

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
| **Backup Git** | ✅ Hoạt động | Tự động, mỗi commit → GitHub |
| **HTTPS** | ✅ Hoạt động | GitHub Pages cấp SSL miễn phí |
| **DDoS Protection** | ✅ Hoạt động | GitHub native AWS Shield (hiện tại) |
| **Dependabot** | ✅ Hoạt động | Auto-check + auto-merge patch/minor updates |
| **Editor (/editor)** | 🟢 **STATIC (NO LOGIN)** | Trang demo, không activate login flow |
| **Security Audit** | ✅ Workflows có | GitHub Actions scan code trên mỗi push |

---

**Tác giả:** Security Audit  
**Ngày:** 2026-06-16  
**Phiên bản:** 1.0
