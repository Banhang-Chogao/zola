+++
title = "AD-Report"
description = "Báo cáo vị trí AdSense và tổng hợp tính năng phiên 18–19/06."
date = 2026-06-19
template = "ad-report.html"
aliases = ["/ad-report/"]

[extra]
seo_keyword = "adsense placement report zola blog"
source_commit = "784f5d701440a4222bb92259b2472e45e51ca14a"
+++

> **Nguồn:** Commit `784f5d7` — *docs(reports): báo cáo vị trí AdSense + tổng hợp tính năng phiên 18–19/06*.
> Bản gốc lưu tại `reports/adsense-ad-placement-report.md` và `reports/features-delivered-2026-06-19.md`.

## Phần I — Tổng hợp tính năng phiên 18–19/06

- **Repo:** [Banhang-Chogao/zola](https://github.com/Banhang-Chogao/zola)
- **Production:** https://banhang-chogao.github.io/zola/
- **Deploy cuối:** GitHub Actions **#745** — success — commit `c4bc703`
- **Nhánh:** `main` (tất cả PR đã merge)

---

## 1. Bảng tổng quan PR đã merge

| # | Tính năng | PR | Trạng thái |
|---|-----------|-----|------------|
| 1 | Compliance V10–V12, pagination URLs, Content Creator, README | [#460](https://github.com/Banhang-Chogao/zola/pull/460) | ✅ Merged + Live |
| 2 | Series VietinBank V-Plus & V-Advance (5 bài) | [#454](https://github.com/Banhang-Chogao/zola/pull/454) | ✅ Merged + Live |
| 3 | Breadcrumb UI (`Trang chủ › Chuyên mục › Bài`) | [#457](https://github.com/Banhang-Chogao/zola/pull/457) | ✅ Merged + Live |
| 4 | Font WOFF2 self-host | [#461](https://github.com/Banhang-Chogao/zola/pull/461) | ✅ Merged + Live |
| 5 | Daily Vaccine Autofixer V11 + shortcut `vacxin11` | [#458](https://github.com/Banhang-Chogao/zola/pull/458) | ✅ Merged + Live |

---

## 2. Chi tiết từng tính năng

### 2.1. Compliance V10–V12 (#460)

- Nâng cấp bộ compliance checker (V10, V11, V12) cho nội dung và link nội bộ.
- Sửa URL phân trang feed (`/page/N/`) đúng chuẩn.
- Công cụ **Content Creator** tại `/zola/tools/content-creator/`.
- Cập nhật README vận hành.

**Verify production:** Content Creator load form; compliance link report `0 broken` / 622 links.

---

### 2.2. Series VietinBank (#454)

5 bài series xuất bản và hiển thị đầu feed:

1. [V-Plus & V-Advance là gì?](https://banhang-chogao.github.io/zola/posting/vietinbank-v-plus-v-advance-la-gi/)
2. [V-Plus chi tiết quyền lợi](https://banhang-chogao.github.io/zola/posting/vietinbank-v-plus-chi-tiet-quyen-loi/)
3. [V-Advance đặc quyền](https://banhang-chogao.github.io/zola/posting/vietinbank-v-advance-nang-tam-trai-nghiem/)
4. [So sánh V-Plus vs V-Advance](https://banhang-chogao.github.io/zola/posting/so-sanh-v-plus-va-v-advance-chon-goi-nao/)
5. [Đăng ký trên iPay](https://banhang-chogao.github.io/zola/posting/dang-ky-v-plus-v-advance-tren-ipay/)

**Verify production:** Homepage **Trang 1/16** — 5 bài VietinBank trên cùng.

---

### 2.3. Breadcrumb UI (#457)

- Nav breadcrumb hiển thị: `Trang chủ › {Category} › {Tiêu đề}`.
- JSON-LD `BreadcrumbList` (SEO).
- Template: `templates/page.html`.

**Verify production:** `/zola/posting/vietinbank-v-plus-v-advance-la-gi/` — có class `breadcrumb` + `Trang chủ`.

---

### 2.4. Font WOFF2 (#461)

- Self-host font WOFF2 giảm phụ thuộc CDN / cải thiện tải font.
- Liên quan mục tiêu LCP mobile (AdSense readiness).

---

### 2.5. Daily Vaccine Autofixer V11 (#458)

- Panel vaccine trên trang Insights — phát hiện & sửa issue tự động (V11).
- Shortcut CLI: `vacxin11`.
- Script: `scripts/compliance_content_vaccine.py`, data: `data/vaccine-autofixer-report.json`.

**Verify production:** `/zola/insights/` — có nội dung `vaccine`, `V11`, `vacxin11`.

---

## 3. Trạng thái production (19/06/2026)

| Kiểm tra | URL | Kết quả |
|----------|-----|---------|
| Homepage + pagination | `/zola/`, `/zola/page/2/` | ✅ Trang 1/16, 2/16 |
| Series VietinBank | `/zola/posting/vietinbank-*` | ✅ 5 bài live |
| Breadcrumb | Bài posting bất kỳ | ✅ Nav + JSON-LD |
| Content Creator | `/zola/tools/content-creator/` | ✅ |
| Vaccine V11 | `/zola/insights/` | ✅ |
| Deploy | Actions #745 | ✅ success |

---

## 4. Hạng mục **chưa** implement (non-blocking)

| Hạng mục | Ghi chú |
|----------|---------|
| **AdSense code thật** | Chỉ có placeholder — xem [adsense-ad-placement-report.md](#phan-ii-bao-cao-vi-tri-adsense) |
| **Ẩn placeholder quảng cáo giả** | Khuyến nghị trước khi nộp AdSense |
| **ads.txt** | Sau khi được duyệt publisher |
| **AdSense placement in-article** | Chưa có slot — trong roadmap báo cáo placement |
| **1 cảnh báo internal links** | Report only, không chặn deploy |
| **Bài AdSense series 7–15** | Planned trong `data/adsense-foundation-series.json` |

---

## 5. Báo cáo liên quan (file `.md`)

| File | Nội dung |
|------|----------|
| [adsense-ad-placement-report.md](#phan-ii-bao-cao-vi-tri-adsense) | **Báo cáo đầy đủ vị trí quảng cáo AdSense** (2 slot hiện tại + roadmap) |
| [adsense-site-readiness-audit.md](https://github.com/Banhang-Chogao/zola/blob/main/reports/adsense-site-readiness-audit.md) | Audit site-readiness 78/100 — UX, policy, SEO |
| [rule-conflict-report.md](https://github.com/Banhang-Chogao/zola/blob/main/reports/rule-conflict-report.md) | Xung đột rule CI/bot |

---

## 6. Liên kết nhanh

- **Site:** https://banhang-chogao.github.io/zola/
- **Deploy log:** https://github.com/Banhang-Chogao/zola/actions/runs/27796087713
- **Series AdSense (đã publish 6/15):** https://banhang-chogao.github.io/zola/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/

---

*Tài liệu tổng hợp phiên triển khai 18–19/06/2026. Cập nhật khi có PR/deploy mới.*

---

## Phần II — Báo cáo vị trí AdSense

- **Site production:** https://banhang-chogao.github.io/zola/
- **Ngày báo cáo:** 19/06/2026
- **Trạng thái AdSense:** Chưa cài mã `adsbygoogle` — đang ở giai đoạn **pre-application** (placeholder + chuẩn bị layout)
- **Báo cáo liên quan:** [adsense-site-readiness-audit.md](https://github.com/Banhang-Chogao/zola/blob/main/reports/adsense-site-readiness-audit.md) (audit tổng thể site-readiness 78/100)

---

## 1. Tóm tắt điều hành

| Chỉ số | Giá trị |
|--------|---------|
| **Slot quảng cáo đã dựng sẵn (placeholder)** | **2** |
| **Slot AdSense thật đã triển khai** | **0** |
| **Mã `adsbygoogle` trong repo** | **0 lần** |
| **`static/ads.txt`** | **Chưa có** (thêm sau khi được duyệt) |
| **Auto Ads** | **Chưa bật** |
| **Verdict placement** | ⚠️ **Layout sẵn sàng một phần** — có 2 vị trí banner placeholder; **chưa** có in-article, sidebar sticky, multiplex. Placeholder **nên ẩn** trước khi reviewer AdSense xem site (xem mục 6). |

---

## 2. Bản đồ vị trí quảng cáo hiện tại (đã implement)

### 2.1. Slot #1 — Header banner (toàn site)

| Thuộc tính | Chi tiết |
|------------|----------|
| **ID / class** | `.header-ad` (Slide A trong `.header-rotator`) |
| **File template** | `templates/base.html` (~dòng 481–494) |
| **File style** | `sass/_banner.scss` (`.header-ad`, `.header-rotator`) |
| **Xuất hiện trên** | **Mọi trang** dùng `base.html` (homepage, bài viết, category, tools, insights, …) |
| **Vị trí UI** | Header phải, cạnh logo — trong khối `.header-side` |
| **Kích thước thiết kế** | Mô tả copy: **728×90** (Leaderboard); CSS thực tế: grid `72px + 1fr + auto`, `min-height: 88px` (desktop), `64px` (mobile) |
| **Hành vi** | Luân phiên với block GitHub status mỗi **3 giây** (`data-rotate="true"`, `data-interval="3000"`). Slide Ad là `is-active` khi load trang |
| **Nội dung hiện tại** | Placeholder: nhãn `QUẢNG CÁO`, tiêu đề "Đặt banner của bạn tại đây", ảnh `placeholder-wide.svg`, link về trang chủ |
| **Lazy load** | `loading="lazy"` trên ảnh placeholder |
| **Trạng thái AdSense** | ❌ Chưa gắn unit AdSense — chỉ placeholder tự host |

**Ghi chú kỹ thuật:** Comment trong template hướng dẫn tắt banner: comment block "Slide A", đặt `data-rotate="false"`, trả `is-active` về Slide B (GitHub).

---

### 2.2. Slot #2 — Banner dưới header bài viết

| Thuộc tính | Chi tiết |
|------------|----------|
| **ID / class** | `.ad-banner` |
| **File template** | `templates/page.html` (~dòng 115–127) |
| **File style** | `sass/_banner.scss` (`.ad-banner`) |
| **Xuất hiện trên** | **Trang dùng template `page.html`** — bài `posting/`, `baochi/`, và các page content tương tự |
| **Vị trí UI** | Ngay **sau** `<header>` bài (meta, SEO badge, nút Sửa) — **trước** nội dung bài (`post-single__content`) |
| **Kích thước thiết kế** | Grid `160px + 1fr + auto`; ảnh vuông `aspect-ratio: 1/1` (không phải 728×90 thuần) |
| **Hành vi** | Cố định, không rotate |
| **Nội dung hiện tại** | Placeholder tương tự slot #1; `<h3>` trong banner (cần lưu ý heading hierarchy khi thay bằng ad unit) |
| **Lazy load** | `loading="lazy"` |
| **Trạng thái AdSense** | ❌ Chưa gắn unit AdSense |

**Trang KHÔNG có slot #2:** Homepage (`section.html`), category listing (`taxonomy_single.html`), insights, editor, dashboard tools — chỉ có slot #1 (header) nếu dùng `base.html`.

---

## 3. Ma trận trang × vị trí quảng cáo

| Loại trang | URL mẫu | Slot #1 Header | Slot #2 Post banner | Ghi chú |
|------------|---------|:----------------:|:-------------------:|---------|
| Trang chủ | `/zola/` | ✅ | ❌ | Feed bài viết |
| Phân trang | `/zola/page/2/` | ✅ | ❌ | |
| Bài posting | `/zola/posting/{slug}/` | ✅ | ✅ | Có breadcrumb + JSON-LD |
| Bài báo chí | `/zola/baochi/{slug}/` | ✅ | ✅ | |
| Category | `/zola/categories/{cat}/` | ✅ | ❌ | |
| Insights | `/zola/insights/` | ✅ | ❌ | Full-bleed, không sidebar |
| Content Creator | `/zola/tools/content-creator/` | ✅ | ❌ | |
| Editor / Admin | `/zola/editor/` | ✅* | ❌ | *Nếu dùng base; nên **không** hiển thị ad |
| Premium (paywall) | `/zola/posting/premium-*` | ✅ | ⚠️ | `.ad-banner` **có** trong template; paywall CSS ẩn khi in — **cần tắt ad khi có AdSense thật** |
| 404 | `/zola/404` | ✅ | ❌ | Không nên monetize |
| Policy pages | `/zola/pages/privacy/` | ✅ | ✅* | *Nếu render qua `page.html` |

---

## 4. Vị trí quảng cáo **chưa** implement (đề xuất sau duyệt AdSense)

Các vị trí sau **không có** trong codebase hiện tại — chỉ là đề xuất bám [Ad placement policies](https://support.google.com/adsense/answer/1346295):

| # | Vị trí đề xuất | Loại unit gợi ý | Template cần sửa | Ưu tiên | Policy note |
|---|----------------|-----------------|------------------|---------|-------------|
| A | Sau đoạn intro / trước TOC | In-article | `templates/page.html` | Cao | Không che heading; cách TOC ≥ 1 đoạn |
| B | Giữa bài (~50% word count) | In-article | `templates/page.html` hoặc shortcode MD | Cao | Chỉ bài ≥ 800 từ |
| C | Cuối bài, trước FAQ | Display / Multiplex | `templates/page.html` | Trung bình | Sau nội dung chính, trước author box |
| D | Sidebar desktop (nếu bật lại) | Display 300×250 / 336×280 | `templates/base.html` | Thấp | Insights/du-lich đã full-bleed — không có sidebar |
| E | Auto Ads (toàn site) | Google tự đặt | `templates/base.html` `<head>` | Tùy chọn | Bật thử sau 2–4 tuần; theo dõi UX |
| F | Anchor / Vignette | Auto formats | AdSense console | Thấp | Dễ vi phạm UX nếu quá aggressive |
| G | In-feed (homepage) | In-feed native | `templates/section.html` | Trung bình | Cần markup `data-ad-layout="in-feed"` |

---

## 5. Trang & khu vực **cấm** đặt quảng cáo AdSense

| Khu vực | Lý do | Hành động khi triển khai |
|---------|-------|--------------------------|
| `/editor/`, `/admin-author/`, `/admin/paywall/` | Công cụ nội bộ | `robots.txt` đã Disallow; **không** chèn ad snippet |
| Bài `premium = true` (paywall) | Nội dung trả phí / teaser | Ẩn `.ad-banner` + không Auto Ads trên URL premium |
| Trang lỗi 404 | Không có nội dung substantive | Không đặt ad |
| Popup / email / frame | Vi phạm Program policies | Không áp dụng |
| Trang chỉ để show ads | Policy violation | Site không có — OK |

**Paywall:** `sass/_paywall.scss` ẩn `.ad-banner` khi **in** (`@media print`) — chưa ẩn trên màn hình. Khi có AdSense, cần điều kiện `{% if not page.extra.premium %}` quanh slot #2 (và cân nhắc slot #1).

---

## 6. Đánh giá tuân thủ Ad placement policies

Tham chiếu: [AdSense Program policies — ad placement](https://support.google.com/adsense/answer/1346295), [UX guidelines](https://support.google.com/adsense/answer/2893020), bài series [Bài 3 — Website sẵn sàng cho AdSense](https://banhang-chogao.github.io/zola/posting/website-san-sang-cho-adsense/).

| Kiểm tra | Slot #1 Header | Slot #2 Post banner | Kết luận |
|----------|----------------|---------------------|----------|
| Không che nội dung chính | ✅ (header riêng) | ✅ (trên content, không sticky) | Pass layout |
| Không click-bait / misleading | ⚠️ Placeholder giả dạng quảng cáo | ⚠️ Tương tự | **Fail pre-review** — nên ẩn |
| Không quá nhiều ad trên viewport đầu | ⚠️ 1 banner header + 1 banner post = 2 trên fold (mobile) | ⚠️ | Cân nhắc chỉ 1 slot above-fold |
| Label quảng cáo rõ ràng | ✅ Có nhãn "QUẢNG CÁO" | ✅ Có nhãn | OK cho placeholder; AdSense tự label khi thật |
| Không đặt trong pop-up | ✅ | ✅ | Pass |
| Heading hierarchy | N/A | ⚠️ `<h3>` trong ad-banner | Đổi thành `<p>`/`<span>` khi production |
| Trang premium | Hiển thị header ad | Hiển thị post ad | **Cần fix** trước monetize |
| Nội dung đủ dài để in-article | N/A | N/A | 17 bài < 800 từ — chưa nên in-article |

### Rủi ro chính (từ audit site-readiness #3)

> **2 khu "quảng cáo giả"** — Google reviewer có thể coi là placeholder / under construction. **Khuyến nghị: ẩn cả 2 slot** cho đến khi có publisher ID và unit thật.

---

## 7. Hạ tầng kỹ thuật sẵn sàng cho AdSense

| Hạng mục | Trạng thái | File / vị trí |
|----------|------------|---------------|
| `robots.txt` Allow `Mediapartners-Google`, `AdsBot-Google` | ✅ | `static/robots.txt` |
| Privacy Policy mục AdSense + cookies | ✅ | `content/pages/privacy.md` |
| `ads.txt` | ❌ Chưa | Thêm `static/ads.txt` sau duyệt |
| Snippet `<script async src="...adsbygoogle.js">` | ❌ Chưa | Sẽ thêm `templates/base.html` |
| JSON-LD / SEO | ✅ | Không xung đột placement |
| Theme overrides cho ad blocks | ✅ | `sass/_theme-overrides.scss` (`.ad-banner`, `.header-ad`) |
| Media guard (ảnh ad) | ✅ | `sass/_media-guard.scss` |
| Series AdSense Foundation (nội dung) | ✅ 6/15 published | `data/adsense-foundation-series.json` |
| Bài #8 planned: UX & vị trí quảng cáo | 📋 Planned | `trai-nghiem-nguoi-dung-vi-tri-quang-cao-adsense` |

---

## 8. Kế hoạch triển khai AdSense (theo thứ tự)

### Giai đoạn 0 — Trước khi nộp đơn (hiện tại)

1. **Ẩn** slot #1 và #2 (comment template hoặc flag `config.toml` `show_ad_placeholders = false`).
2. Sửa email liên hệ thật (Contact/About) — không thuộc placement nhưng blocker duyệt.
3. Tối ưu LCP mobile < 2.5s — ad script sẽ cộng thêm JS.

### Giai đoạn 1 — Ngay sau khi được duyệt

1. Thêm `static/ads.txt`: `google.com, pub-XXXXXXXX, DIRECT, f08c47fec0942fa0`
2. Chèn AdSense script vào `templates/base.html` (trước `</head>`).
3. Thay placeholder slot #2 (post banner) bằng **Display unit** đầu tiên — ROI cao nhất trên bài dài.
4. Giữ slot #1 **tắt** hoặc thay bằng **728×90** thật sau 1–2 tuần theo dõi CLS.

### Giai đoạn 2 — Tối ưu (tuần 3–8)

1. Bật **Auto ads** thử nghiệm (chỉ in-page, tắt anchor/vignette ban đầu).
2. Thêm in-article sau đoạn 2 cho bài ≥ 1000 từ.
3. A/B: 1 vs 2 display units / bài — theo dõi RPM + bounce trong GA4.
4. Viết & publish **Bài 8 series**: `trai-nghiem-nguoi-dung-vi-tri-quang-cao-adsense`.

### Giai đoạn 3 — Vận hành dài hạn

1. Policy center monitoring (Bài 13–15 series).
2. Không đặt ad trên bài premium / restricted content (Bài 5 Restrictions).
3. Cập nhật báo cáo này mỗi khi thêm/xóa slot.

---

## 9. Checklist nhanh cho developer

```
[ ] Ẩn placeholder trước khi reviewer xem
[ ] Thêm ads.txt sau khi có pub-ID
[ ] Chèn adsbygoogle.js (async, defer)
[ ] Slot #2 page.html → ins.adsbygoogle + data-ad-slot
[ ] {% if not page.extra.premium %} quanh mọi ad unit
[ ] Loại <h3> trong ad-banner → span/p
[ ] Test CLS sau khi gắn ad (PageSpeed mobile)
[ ] Xác nhận không ad trên /editor/, /admin/
[ ] Cập nhật báo cáo này (version + ngày)
```

---

## 10. Nguồn dữ liệu & file tham chiếu

| Nguồn | Đường dẫn |
|-------|-----------|
| Template header ad | `templates/base.html` |
| Template post ad | `templates/page.html` |
| Styles | `sass/_banner.scss`, `sass/_theme-overrides.scss` |
| Paywall ad rules | `sass/_paywall.scss` |
| Audit tổng thể | `reports/adsense-site-readiness-audit.md` |
| Series manifest | `data/adsense-foundation-series.json` |
| PageSpeed | `data/pagespeed.json` (mobile LCP 6.9s, SEO 100) |
| Compliance links | `data/compliance-link-report.json` (0 broken) |
| Google official | [Ad placement policies](https://support.google.com/adsense/answer/1346295) |

---

*Báo cáo được tạo để inventory toàn bộ vị trí quảng cáo hiện có và lộ trình AdSense. Cập nhật lần cuối: 19/06/2026.*
