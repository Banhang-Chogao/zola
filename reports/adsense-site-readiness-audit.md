# Báo cáo Audit AdSense / Site-Readiness / SEO — Blog "Duy Nguyen" (Zola)

- **Site:** https://banhang-chogao.github.io/zola/
- **Ngày audit:** 18/06/2026
- **Phạm vi:** Read-only. Không sửa code/nội dung, không build, không deploy.
- **Khung tham chiếu:** Checklist rút từ bài blog `content/posting/website-san-sang-cho-adsense.md` (bám tài liệu chính thức Google [Make sure your site's pages are ready for AdSense — 7299563](https://support.google.com/adsense/answer/7299563)) + 12 dimension theo yêu cầu.

---

## 1. Điểm tổng quan

| Hạng mục | Kết quả |
|---|---|
| **Điểm site-readiness tổng** | **78 / 100** |
| **Verdict** | ⚠️ **GẦN sẵn sàng — CHƯA nên nộp AdSense ngay.** Nội dung, navigation, policy pages và technical SEO đều rất mạnh (đủ điều kiện cốt lõi của Google). Nhưng 3 việc phải xử lý TRƯỚC khi nộp: (1) **hiệu năng mobile kém** (LCP 6.1s, Performance 71/100) — đúng tiêu chí "great user experience" Google nhấn mạnh; (2) **email liên hệ là địa chỉ `@users.noreply.github.com`** — không phải kênh liên hệ thật reviewer kỳ vọng; (3) **placeholder "QUẢNG CÁO — Đặt banner của bạn tại đây"** là quảng cáo giả/khu vực trống, Google khuyến nghị gỡ trước khi review. Sau khi sửa 3 điểm này, site đủ điều kiện nộp. |

### Checklist site-readiness (theo bài blog của chính blog) — đối chiếu nhanh

| Tiêu chí Google | Trạng thái | Ghi chú |
|---|---|---|
| **Unique & interesting content** | ✅ Tốt | 70 bài published, tiếng Việt gốc, series có chiều sâu (AdSense, SEO, Khoa học). SEO score toàn bộ ≥ 92 (37 bài A+, 2 bài A). |
| **Interesting & relevant** | ✅ Tốt | Chủ đề nhất quán (công nghệ, du lịch, ẩm thực, ngân hàng số). Median 915 từ/bài. |
| **Layout inviting** | 🟡 Khá | TOC tự động, FAQ, author box, ảnh có alt, placeholder thương hiệu. Nhưng có khu "quảng cáo giả". |
| **Navigation rõ ràng** (alignment/readability/functionality) | ✅ Tốt | Menu 3 nhóm dropdown (Bài viết / Công cụ / Giới thiệu), burger mobile, search. 0 link nội bộ hỏng. |
| **About / Privacy / Contact** | 🟡 Có đủ nhưng Contact yếu | 4 trang policy tồn tại + có trong menu. Privacy có hẳn mục Google AdSense + cookies. Contact chỉ có email noreply. |
| **Policies (no scraped/copyright)** | ✅ Tốt | Nội dung gốc, có block "Tham khảo & Nguồn dữ liệu" cuối bài, ghi nguồn rõ. |
| **Embed/UGC moderation** | ✅ OK | Giscus (GitHub Discussions) — UGC kiểm soát qua GitHub. |
| **Technical SEO** | ✅ Rất tốt | canonical, OG, Twitter, JSON-LD (Article/WebSite/Breadcrumb/FAQ), robots meta, sitemap, RSS/Atom, GSC verify, `lang="vi"`, viewport. PageSpeed SEO 100/100. |

---

## 2. Bảng vấn đề chi tiết

> Số liệu lấy từ: `data/seo-qa-scores.json` (39 bài chấm SEO), `data/compliance-link-report.json` (link), `data/pagespeed.json` (Lighthouse 17/06/2026), `config.toml`, `templates/`, `content/pages/`, `static/robots.txt`.

| # | Mức độ | Dimension | Mô tả | File / URL | Lý do ảnh hưởng AdSense / SEO |
|---|---|---|---|---|---|
| 1 | **High** | (6) Page speed / (5) UX mobile | **Mobile Performance = 71/100**, **LCP = 6.1s** (score 12/100), FCP 3.2s. Desktop tốt (99, LCP 0.9s) nhưng AdSense reviewer thường mở trên mobile. | `data/pagespeed.json` (mobile) | "Great user experience" là tiêu chí Google nêu trực tiếp ở 7299563. LCP > 2.5s = fail Core Web Vitals → ảnh hưởng cả duyệt AdSense lẫn ranking Search. |
| 2 | **High** | (4) About/Contact/Privacy | **Contact chỉ có email `292648126+Banhang-Chogao@users.noreply.github.com`** (địa chỉ noreply GitHub, không nhận thư thật một cách tự nhiên). About dùng cùng email này. | `content/pages/contact.md:14`, `content/pages/about.md:37` | Reviewer (và nhà quảng cáo) cần kênh liên hệ thật để xử lý vấn đề policy. Email noreply có thể bị coi là không có kênh liên hệ hợp lệ. |
| 3 | **High** | (11) Ads-ready layout / Policy | **2 khu "quảng cáo giả"**: header banner "QUẢNG CÁO — Đặt banner của bạn tại đây (728×90)" và ad-banner cuối header bài viết. Đây là placeholder rỗng link về trang chủ. | `templates/base.html` (header-ad, ~dòng 461–471), `templates/page.html:81-92` (ad-banner) | Bài blog của chính site cảnh báo: "quảng cáo giả (trước khi có AdSense thật) gây UX kém". Google không thích placeholder quảng cáo / "Under construction". Nên ẩn cho tới khi gắn AdSense thật. |
| 4 | **Medium** | (1)(8) Content / Thin content | **0 bài < 600 từ** (tốt), nhưng **11 bài ở 606–699 từ** và **17 bài < 800 từ** — vẫn mỏng so với ngưỡng "nội dung sâu" mà reviewer kỳ vọng. Mỏng nhất: `tu-dong-deploy-zola-github-actions.md` (606), `an-khuya-sai-gon.md` (617), `hieu-ve-gioi-han-su-dung-...claude.md` (619), `zola-vs-hugo.md` (638). | `data/seo-qa-scores.json` | Google đánh giá "đủ chiều sâu". Nhiều bài ngắn liên tiếp có thể bị xem là low-value content. Nên nâng các bài < 700 từ lên ≥ 800–1000. |
| 5 | **Medium** | (9) Duplicate content | **Cụm bài Liobank (affiliate) và Mỹ-Iran trùng chủ đề mạnh.** Có 2 bài cùng keyword "hòa bình Mỹ-Iran" (`my-iran-hoa-binh-trung-dong.md`, `my-iran-peace-deal-global-energy.md`) và 7+ bài Liobank (mở thẻ, hoàn tiền, bảo mật, giới thiệu bạn bè, app, là gì…). | `data/seo-qa-scores.json` (section baochi) | Nội dung cận-trùng + nặng affiliate/khuyến mãi 1 thương hiệu có thể bị Google coi là thin/commercial-intent content. AdSense + Search đều trừ điểm bài chủ yếu để đặt link affiliate. |
| 6 | **Medium** | (11) Ads-ready / Paywall | **Có nội dung Premium/Paywall** (`content/posting/premium-fintech-paywall-demo.md`, `premium = true`, render teaser + Momo payment). | `templates/page.html:94-98`, `config.toml` (paywall_api_url, momo) | AdSense cấm đặt quảng cáo trên/đan xen nội dung trả phí trá hình nếu không tách bạch. Cần đảm bảo trang premium KHÔNG hiển thị ad AdSense, tránh xung đột policy. |
| 7 | **Low** | (12) Technical SEO | **3 bài còn H1 (`#`) trong body** (title đã là H1) → cấu trúc heading sai. | `qa-gatekeeper-tu-fix-loi-blog.md`, `sentence-transformers-sbert-deep-dive.md`, `tao-blog-voi-zola.md` (issue trong `data/seo-qa-scores.json`) | Nhiều H1/trang gây nhiễu cho crawler hiểu cấu trúc. Ảnh hưởng nhẹ tới SEO on-page (mỗi bài tụt còn 96.8/100). |
| 8 | **Low** | (2) Navigation / Dead-ends | Menu "Công cụ" trỏ tới **nhiều trang công cụ nội bộ** (editor, scoring, f-dashboard, prompt-support, branding…) — không phải nội dung cho độc giả công khai; một số yêu cầu login. Menu cũng có **⭐ Premium** (`/categories/premium`) chỉ có 1 bài demo. | `config.toml` menu (dòng 74–93) | Reviewer click menu thấy nhiều trang tool/trống/đăng nhập có thể đánh giá site "chưa hoàn thiện" hoặc thiếu nội dung. Nên giảm tool công khai trong menu chính trước khi nộp. |
| 9 | **Low** | (12) Technical SEO | **1 slug dài 74 ký tự** (`lich-thi-dau-world-cup-2026-theo-gio-viet-nam-moi-nhat-messi-lap-hat-trick`, nên ≤ 60). | `data/seo-qa-scores.json` | Slug quá dài — ảnh hưởng nhẹ UX URL + SEO. |
| 10 | **Low** | (11) ads.txt | **Chưa có `ads.txt`** (đã có `static/.well-known/security.txt` nhưng không có ads.txt). | `static/` (thiếu `ads.txt`) | Không cản nộp đơn, nhưng **bắt buộc thêm NGAY SAU khi được duyệt** (`ads.txt` với publisher ID) để tránh cảnh báo "Earnings at risk" trong AdSense. |
| 11 | **Low** | (5) Accessibility | **Accessibility 80 (desktop) / 85 (mobile)** — chưa đạt 90+. | `data/pagespeed.json` | A11y kém (contrast, label) ảnh hưởng UX score Google nhìn vào; không chặn AdSense nhưng nên cải thiện. |
| 12 | **Info** | (11) AdSense code | **Chưa cài mã AdSense** (`adsbygoogle` = 0 lần trong templates/static). | toàn repo | ĐÚNG ở giai đoạn pre-application. Sau khi tạo tài khoản, cần chèn snippet AdSense (Auto ads hoặc đơn vị quảng cáo) — robots.txt đã sẵn sàng cho `Mediapartners-Google` + `AdsBot-Google`. |

### Điểm MẠNH (không cần sửa — ghi nhận)

- **Internal links: 0 link hỏng** trên 282 link unique đã kiểm (`data/compliance-link-report.json`, status `pass`). Dimension (3) và (7) đều xanh.
- **Technical SEO xuất sắc** (`templates/base.html`): canonical per-page, Open Graph đầy đủ + `og:image:width/height`, Twitter Card, JSON-LD Article + WebSite + BreadcrumbList + FAQPage, robots meta `index,follow,max-image-preview:large`, `<html lang="vi">`, viewport `viewport-fit=cover`, RSS + Atom feed, GSC verification (`google_site_verification` đã điền), sitemap.xml (Zola built-in). PageSpeed **SEO = 100/100** cả desktop lẫn mobile.
- **robots.txt chuẩn AdSense** (`static/robots.txt`): Allow rõ `Googlebot`, `Googlebot-Image`, `Mediapartners-Google`, `AdsBot-Google`, `Bingbot`; chỉ Disallow `/editor/`, `/admin-author/`, `/admin/paywall/`, `/data/`. Có khai báo Sitemap.
- **Privacy Policy đạt yêu cầu AdSense**: `content/pages/privacy.md` (653 từ) có hẳn mục "Google AdSense và quảng cáo bên thứ ba", cookies (DART), và cách từ chối quảng cáo cá nhân hóa — đúng yêu cầu Google.
- **Taxonomy sạch**: 13 category (`categories.json`) có cấu trúc, "Tất cả" là category mặc định, sidebar hiển thị danh mục + tag cloud.
- **Desktop performance gần như tuyệt đối**: Performance 99, LCP 0.9s, CLS ~0.

---

## 3. Chiến lược fix

### 🟢 Quick wins (nhanh, ít rủi ro — làm trong 1 buổi)

1. **Đổi email liên hệ thật** (vấn đề #2): thay `...@users.noreply.github.com` bằng email thực (Gmail/tên miền). Sửa `content/pages/contact.md` + `content/pages/about.md` + `config.toml` (`author`).
2. **Ẩn placeholder "quảng cáo giả"** (vấn đề #3): tạm comment/ẩn block `header-ad` (`templates/base.html`) và `ad-banner` (`templates/page.html`) cho tới khi gắn AdSense thật, hoặc thay bằng nội dung thật (CTA nội bộ).
3. **Sửa 3 bài còn H1 trong body** (vấn đề #7): đổi `#` → `##` trong body 3 bài → mỗi bài lên 100/100.
4. **Rút gọn slug 74 ký tự** (vấn đề #9) — lưu ý set redirect nếu bài đã được index.
5. **Tỉa menu công khai** (vấn đề #8): tạm ẩn các mục Công cụ nội bộ (editor, scoring, f-dashboard, l-dashboard, prompt-support, branding, font) và ⭐ Premium khỏi menu chính trong `config.toml` trước khi reviewer xem.

### 🔴 Cần fix TRƯỚC khi nộp AdSense (bắt buộc)

1. **Tối ưu LCP mobile xuống < 2.5s** (vấn đề #1) — quan trọng nhất:
   - Hero image của bài (`templates/page.html`, `loading="eager" fetchpriority="high"`) đang là LCP candidate nhưng mobile LCP = 6.1s → kiểm tra kích thước ảnh thực tế phục vụ mobile (đang nặng ~250KB ảnh + 235KB font).
   - Cân nhắc giảm số font tải (Google Fonts: Manrope 5 weights + Inter 3 + Be Vietnam Pro 2 = 235KB font), `font-display: swap` đã có nhưng tổng quá nặng.
   - 65KB JS không dùng đến từ `gtag.js` (GA4) — đã defer, ổn; CSS dư 34–35KB.
   - Mục tiêu: mobile Performance ≥ 80–90 trước khi nộp.
2. **Gỡ/ẩn quảng cáo giả** (vấn đề #3) — bắt buộc, không để placeholder khi reviewer xem.
3. **Email liên hệ thật** (vấn đề #2) — bắt buộc cho "kênh liên hệ hợp lệ".
4. **Tách bạch nội dung Premium khỏi AdSense** (vấn đề #6): xác nhận trang `premium = true` không render đơn vị AdSense khi triển khai.

### 🔵 Fix dài hạn (sau khi nộp / để tăng chất lượng)

1. **Nâng độ sâu bài mỏng** (vấn đề #4): viết thêm cho 11 bài 600–699 từ và 17 bài < 800 từ lên ≥ 800–1000 từ (ưu tiên các bài 606–638 từ).
2. **Hợp nhất/đa dạng hóa nội dung trùng** (vấn đề #5): gộp 2 bài "hòa bình Mỹ-Iran" hoặc phân hóa rõ góc nhìn; giảm mật độ bài affiliate Liobank (gộp thành 1–2 bài tổng hợp chất lượng thay vì 7+ bài cận-trùng nặng khuyến mãi).
3. **Thêm `ads.txt`** (vấn đề #10) NGAY SAU khi được duyệt — `static/ads.txt` chứa dòng `google.com, pub-XXXX, DIRECT, f08c47fec0942fa0`.
4. **Nâng Accessibility ≥ 90** (vấn đề #11): kiểm contrast, aria-label, alt text.
5. **Cài snippet AdSense** (vấn đề #12) sau khi tài khoản được tạo.

---

## 4. Top 10 việc nên fix trước (xếp hạng ưu tiên)

| Hạng | Việc | Mức độ | Vì sao ưu tiên |
|---|---|---|---|
| **1** | Tối ưu **LCP mobile < 2.5s** (giảm font/ảnh, Performance 71 → ≥ 80) | High | Rào cản UX lớn nhất; Google nhấn mạnh "great user experience"; ảnh hưởng cả duyệt lẫn ranking. |
| **2** | **Ẩn 2 khu "quảng cáo giả"** placeholder cho tới khi có AdSense thật | High | Chính bài blog cảnh báo; Google không duyệt site có placeholder quảng cáo / "under construction". |
| **3** | **Đổi email liên hệ** noreply → email thật (Contact + About + config) | High | "Kênh liên hệ hợp lệ" là thứ reviewer kiểm tra; noreply không hợp lệ. |
| **4** | **Tỉa menu**: ẩn tool nội bộ + Premium khỏi nav chính | Low (nhanh) | Giúp reviewer thấy site nội dung hoàn thiện, không phải tool/trang trống. |
| **5** | **Tách Premium khỏi AdSense** (xác nhận trang trả phí không gắn ad) | Medium | Tránh vi phạm policy "ad trên nội dung trả phí". |
| **6** | **Nâng 11 bài 600–699 từ** lên ≥ 800–1000 từ | Medium | Tăng chiều sâu, giảm rủi ro "thin content". |
| **7** | **Giảm/​gộp bài affiliate Liobank trùng** + gộp 2 bài Mỹ-Iran | Medium | Tránh duplicate + commercial-intent thin content. |
| **8** | **Sửa 3 bài H1-in-body** → 100/100 | Low | Cấu trúc heading đúng; nhanh gọn. |
| **9** | **Nâng Accessibility ≥ 90** (contrast, label, alt) | Low | UX signal Google quan tâm. |
| **10** | **Chuẩn bị `ads.txt`** (thêm ngay sau khi duyệt) + cài snippet AdSense | Low | Bắt buộc post-approval để tránh "Earnings at risk". |

---

## 5. Nguồn dữ liệu đã dùng

- `content/posting/website-san-sang-cho-adsense.md` — checklist gốc.
- `data/seo-qa-scores.json` — 39 bài chấm SEO (37 A+, 2 A; min 92; 0 bài < 600 từ; 11 bài 600–699; 17 bài < 800; median 915 từ).
- `data/compliance-link-report.json` — 282 link kiểm, **0 hỏng**, status `pass`.
- `data/pagespeed.json` — Lighthouse 17/06/2026: Desktop Perf 99 / A11y 80 / SEO 100 / LCP 0.9s; Mobile Perf 71 / A11y 85 / SEO 100 / LCP 6.1s.
- `content/pages/{about,contact,privacy,terms}.md` — 4 trang policy (about 334 từ, contact 194, privacy 653 có mục AdSense+cookies, terms 486).
- `config.toml`, `categories.json` — menu 3 nhóm + 13 category.
- `templates/base.html`, `templates/page.html` — technical SEO + ad placeholder slots.
- `static/robots.txt` — Allow `Mediapartners-Google` + `AdsBot-Google`; không có `static/ads.txt`.
- 70 bài published (39 posting + 18 baochi + tools/pages); 3 draft loại trừ khỏi site.
- AdSense code: `adsbygoogle` xuất hiện **0 lần** (chưa cài — đúng pre-application).
