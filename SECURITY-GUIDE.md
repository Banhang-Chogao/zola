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

**Manual Dependency Check:**

```bash
# Kiểm tra lỗ hổng hiện tại
cargo audit  # Rust/Zola

# Update dependencies
cargo update

# Check cho lỗ hổng (nếu có)
cargo audit fix
```

**Quy trình:**
- Định kỳ chạy `cargo audit` để kiểm tra security vulnerabilities
- Update dependencies khi cần thiết
- Review changelog trước khi cập nhật major versions

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

## 8. Security Standards & Checklist 📋

Những tiêu chuẩn bảo mật bắt buộc khi phát triển blog:

### **A) Code Security**
- ✅ **Mỗi commit phải review** trước merge vào main
- ✅ **Không commit secrets** (API keys, passwords)
  - Use `.gitignore` cho `.env`, `secrets.json`
  - Không commit GitHub token, Cloudflare API key
- ✅ **Dependencies up-to-date**
  - Chạy `cargo audit` định kỳ để check security vulnerabilities
  - Update dependencies khi cần thiết
- ✅ **Pre-commit hooks**
  - `.pre-commit-config.yaml` đã setup
  - Chạy trước commit để catch issues

### **B) Git Security**
- ✅ **Commit messages phải descriptive**
  - Good: `docs: Thêm security guide`
  - Bad: `update` hoặc `fix bug`
- ✅ **Never force-push to main**
  - `git push --force` chỉ dùng ngoại lệ, review trước
- ✅ **Regular backup**
  - Git history = automatic backup
  - Giữ 4 bản backup gần nhất

### **C) Deployment Security**
- ✅ **GitHub Pages HTTPS bắt buộc**
  - Settings → Pages → "Enforce HTTPS" = ON
  - Tự động renew certificate
- ✅ **Security headers bắt buộc**
  - `Strict-Transport-Security: max-age=31536000`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: SAMEORIGIN`
- ✅ **DDoS protection luôn bật**
  - GitHub Pages: tự động
  - Custom domain: dùng Cloudflare

### **D) Admin Access Security**
- ✅ **Admin account cần mạnh**
  - Password ≥ 16 ký tự, mix A-Z + 0-9 + special
  - Example: `K9@mPx#Lq2$vN8wZ`
- ✅ **GitHub 2FA bắt buộc**
  - Settings → Security → Two-factor authentication
  - Dùng authenticator app (không SMS)
- ✅ **Review repo collaborators**
  - Settings → Collaborators
  - Chỉ trusted users mới được access

### **E) Monitoring & Audit**
- ✅ **Enable GitHub audit logs**
  - Settings → Audit log
  - Review quy tăng kỳ (hàng tháng)
- ✅ **Monitor Dependabot alerts**
  - Notifications → Check ngày
  - Fix security patches trong 3 ngày
- ✅ **Check GitHub Actions logs**
  - Actions → security-audit.yml
  - Đảm bảo không có failures
- ✅ **Emergency procedure ready**
  - Biết cách recover từ git history
  - Backup restore plan sẵn sàng

### **F) Content Security**
- ✅ **Markdown files chỉ user tin tưởng mới edit**
  - Branch protection: require review
  - Settings → Branches → "Require pull request reviews" = ON
- ✅ **Blog configuration (config.toml)**
  - Không public sensitive config
  - `.gitignore` → exclude `.env` file
- ✅ **Assets/Images validation**
  - Check file size (>10MB = reject)
  - Check file type (whitelist: jpg, png, webp)

### **G) Khi Có Sự Cố (Incident Response)**
1. **Phát hiện sự cố** → git log xem lịch sử
2. **Ngay lập tức revert** → `git revert <bad-commit>`
3. **Push revert** → CI/CD auto-redeploy
4. **Post-mortem** → tìm nguyên nhân
5. **Update documentation** → update SECURITY-GUIDE.md

---

## Checklist Bảo Mật Hàng Ngày

```
HÀNG NGÀY:
☐ Review any new GitHub security alerts (2 min)

HÀNG TUẦN:
☐ Pull/rebase main branch locally (1 min)
☐ Review git log cho commits bất thường (2 min)

HÀNG THÁNG:
☐ Run 'cargo audit' để check dependencies (5 min)
☐ Check GitHub audit logs (5 min)
☐ Review collaborators list (2 min)
☐ Verify 2FA still enabled (1 min)
☐ Test recovery procedure (5 min)

HÀNG NĂM (hoặc khi cần):
☐ Full security audit
☐ Rotate sensitive credentials
☐ Review & update SECURITY-GUIDE.md
☐ Security training review
```

---

## Quick Reference — Bảo Mật Checklist Khi Publish

**Trước mỗi push:**
```bash
# 1. Kiểm tra code
git diff origin/main

# 2. Kiểm tra không có secrets
git log -p | grep -i "secret\|api_key\|password"

# 3. Kiểm tra dependencies
cargo audit  # hoặc tương đương

# 4. Commit với message chi tiết
git commit -m "Category: Brief description + why"

# 5. Push
git push origin <branch>

# 6. GitHub Actions tự chạy security-audit.yml
```

---

## Cloudflare (tùy chọn — trước GitHub Pages)

GitHub Pages **không** cho custom HTTP headers, rate-limit, hay hotlink block.
Khi bật Cloudflare proxy cho domain custom:

| Rule | Mục đích |
|------|----------|
| **Hotlink Protection** (Scrape Shield) | Giảm site khác nhúng trực tiếp `/img/*` |
| **WAF Managed Rules** | Chặn scan/brute path (`/wp-admin`, mass 404) |
| **Rate Limiting** | Giới hạn IP > N req/phút vào `/` (tránh scrape ồ ạt) |
| **Cache Rules** | `Cache Everything` cho `/img/*`, `/fonts/*` — TTL 7d+ |
| **Security Headers** (Transform Rules) | `Strict-Transport-Security`, `X-Content-Type-Options: nosniff` |

**Bypass (luôn Allow):** `Googlebot`, `Bingbot`, `Mediapartners-Google`, `AdsBot-Google`
(WAF → Skip rule hoặc Verified Bot).

**Không làm:** chặn toàn bộ `User-agent: *` trên `/img/` — phá Google Images + AdSense.

---

## Tóm Tắt Bảo Mật Hiện Tại

| Tính Năng | Status | Ghi Chú |
|-----------|--------|--------|
| **Backup Git** | ✅ Hoạt động | Tự động, mỗi commit → GitHub |
| **HTTPS** | ✅ Hoạt động | GitHub Pages cấp SSL miễn phí |
| **DDoS Protection** | ✅ Hoạt động | GitHub native AWS Shield (hiện tại) |
| **Dependency Management** | ✅ Manual | Sử dụng `cargo audit` định kỳ |
| **Editor (/editor)** | 🟢 **STATIC (NO LOGIN)** | Trang demo, không activate login flow |
| **Security Audit** | ✅ Workflows có | GitHub Actions scan code trên mỗi push |

---

**Tác giả:** Security Audit  
**Ngày:** 2026-06-16  
**Phiên bản:** 1.0
