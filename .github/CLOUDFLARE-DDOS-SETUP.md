# 🛡️ DDoS Protection — Cloudflare Setup Guide

## 📊 Status Hiện Tại

- **Blog URL:** `https://seomoney.org` (GitHub Pages)
- **DDoS Protection GitHub:** ✅ Đã có sẵn (miễn phí, bao gồm trong GitHub Pages)
- **Cloudflare Setup:** ⏳ Optional (nếu dùng custom domain)

---

## 🔴 Nếu Dùng Custom Domain (Ví Dụ: blog.yourdomain.com)

### **Bước 1: Tạo Cloudflare Account**
1. Đăng ký tại [cloudflare.com](https://cloudflare.com)
2. Chọn **Free Plan** ($0/tháng, đủ cho blog cá nhân)

---

### **Bước 2: Thêm Domain Vào Cloudflare**
1. Cloudflare Dashboard → **Add a domain**
2. Nhập domain (vd: `yourdomain.com`)
3. Chọn **Free Plan**
4. Cloudflare sẽ scan nameservers của domain

---

### **Bước 3: Thay Đổi Nameservers**
1. Vào domain registrar (GoDaddy, Namecheap, v.v.)
2. Tìm **Nameservers / DNS**
3. Thay thế bằng Cloudflare nameservers:
   ```
   ns1.cloudflare.com
   ns2.cloudflare.com
   ```
4. Lưu thay đổi (đợi 24-48h propagate)

---

### **Bước 4: Trỏ Domain Tới GitHub Pages**

**Trong Cloudflare:**
1. **DNS** → **Records**
2. Thêm CNAME record:
   ```
   Type: CNAME
   Name: blog (hoặc @)
   Content: seomoney.org
   TTL: Auto
   Proxy: Proxied (màu cam) ← IMPORTANT!
   ```
3. Save

**Trong GitHub Repo Settings:**
1. Repo → **Settings** → **Pages**
2. Custom domain: `blog.yourdomain.com`
3. Enable **Enforce HTTPS**

---

### **Bước 5: Cấu Hình DDoS Protection Trên Cloudflare**

#### **A) Enable DDoS Protection (Free Plan)**
1. **Security** → **DDoS Protection**
2. Settings:
   ```
   Sensitivity Level: High (Medium default)
   ```

#### **B) WAF (Web Application Firewall)**
1. **Security** → **WAF**
2. Enable **OWASP ModSecurity Core Rules**
3. Mode: **Challenge** (yêu cầu CAPTCHA khi nghi ngờ)
4. Sensitivity: **Medium**

#### **C) Rate Limiting (Chống Brute-Force)**
1. **Rate Limiting** (Free Plan không có, Pro+ mới có)
2. **Alternative:** Dùng Cloudflare Workers (Free tier):
   ```javascript
   // workers/rate-limiter.js
   export default {
     async fetch(request) {
       const ip = request.headers.get('CF-Connecting-IP');
       const rateLimit = new URL(request.url).pathname;
       
       // Block nếu >50 requests/10s từ 1 IP tới /editor/
       if (rateLimit.startsWith('/editor/')) {
         const count = await RATE_LIMIT.get(ip) || 0;
         if (count > 50) {
           return new Response('Rate limit exceeded', { status: 429 });
         }
         await RATE_LIMIT.put(ip, count + 1, { expirationTtl: 10 });
       }
       
       return fetch(request);
     }
   };
   ```

#### **D) Firewall Rules (Chặn Request Xấu)**
1. **Security** → **Firewall Rules**
2. Tạo rules:

**Rule 1: Chặn scanner bot**
```
(cf.bot_management.score < 30) → Block
```

**Rule 2: Chặn country không mong muốn** (optional)
```
(ip.geoip.country in {"KP" "IR"}) → Block
```

**Rule 3: Protect /editor endpoint**
```
(http.request.uri.path eq "/editor/") and 
(cf.threat_score > 50) → Challenge
```

#### **E) Page Rules (Performance + Security)**
1. **Rules** → **Page Rules**
2. Tạo rule cho `/editor`:
   ```
   URL: yourdomain.com/editor/*
   Setting: 
     - Browser Cache TTL: 0 (No cache, luôn fresh)
     - Security Level: High
     - SSL: Flexible (GitHub Pages = HTTP, Cloudflare = HTTPS)
   ```

---

## 🟢 Nếu Dùng GitHub Pages URL (Hiện Tại)

**Blog URL:** `https://seomoney.org`

### **DDoS Protection Sẵn Có:**
- ✅ GitHub native DDoS protection (AWS Shield)
- ✅ Rate limiting tự động (GitHub blocks >1000 req/sec)
- ✅ HTTPS bắt buộc
- ✅ HSTS headers (chặn SSL stripping)

### **Kích hoạt Thêm:**
GitHub Pages tự động bảo vệ. **Không cần cấu hình thêm.**

**Kiểm tra:**
```bash
# Check HSTS header
curl -I https://seomoney.org | grep Strict-Transport

# Output: Strict-Transport-Security: max-age=31536000
```

---

## 📋 **Bảng So Sánh**

| Tính Năng | GitHub Pages (Hiện Tại) | Cloudflare (Custom Domain) |
|-----------|---|---|
| **DDoS Protection** | ✅ AWS Shield | ✅ Cloudflare DDoS |
| **Rate Limiting** | Auto (1000 req/s) | ✅ Pro+ hoặc Workers |
| **WAF** | ❌ Không | ✅ Free Plan |
| **Firewall Rules** | ❌ Không | ✅ Free Plan |
| **HTTPS** | ✅ Tự động | ✅ Tự động |
| **Cost** | $0 | $0 (Free Plan) |

---

## 🎯 **Khuyến Cáo**

### **Hiện Tại (GitHub Pages URL)**
- ✅ **An toàn đủ**, GitHub DDoS protection đủ mạnh
- Không cần Cloudflare ngay

### **Trong Tương Lai (Nếu Dùng Custom Domain)**
- ✅ **Setup Cloudflare** để extra protection
- Bật WAF + Firewall Rules
- Setup Workers cho rate limiting

---

## 🔧 **Test DDoS Protection**

```bash
# 1. Simulate DDoS attack (100 concurrent requests)
ab -n 1000 -c 100 https://seomoney.org/

# Expected: 
# - GitHub Pages returns 429 Too Many Requests
# - hoặc 503 Service Unavailable

# 2. Check logs
# GitHub Pages → Insights → Traffic

# 3. Monitor Cloudflare (nếu setup)
# Cloudflare Dashboard → Analytics → DDoS Attacks
```

---

## 📞 **Troubleshooting**

### "Cloudflare DNS change không hoạt động"
- Đợi 24-48h để DNS propagate
- Check: `nslookup blog.yourdomain.com`
- Phải thấy Cloudflare nameservers

### "GitHub Pages + Cloudflare lỗi SSL"
- Cloudflare SSL Mode = **Flexible** (GitHub = HTTP)
- Hoặc upgrade lên **Full** nếu GitHub support HTTPS origin

### "DDoS protection block users hợp pháp"
- Giảm **WAF Sensitivity** từ High → Medium
- Hoặc whitelist IP/country safe

---

## 📚 **Tài Liệu Tham Khảo**

- [Cloudflare DDoS Protection](https://www.cloudflare.com/ddos/)
- [GitHub Pages Security](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https)
- [Cloudflare Free Plan Features](https://www.cloudflare.com/plans/free/)

---

**Phiên bản:** 1.0  
**Cập nhật:** 2026-06-16
