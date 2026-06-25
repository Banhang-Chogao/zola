# Tổng hợp tính năng đã triển khai — Phiên làm việc 18–19/06/2026

- **Repo:** [Banhang-Chogao/zola](https://github.com/Banhang-Chogao/zola)
- **Production:** https://seomoney.org/
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

1. [V-Plus & V-Advance là gì?](https://seomoney.org/posting/vietinbank-v-plus-v-advance-la-gi/)
2. [V-Plus chi tiết quyền lợi](https://seomoney.org/posting/vietinbank-v-plus-chi-tiet-quyen-loi/)
3. [V-Advance đặc quyền](https://seomoney.org/posting/vietinbank-v-advance-nang-tam-trai-nghiem/)
4. [So sánh V-Plus vs V-Advance](https://seomoney.org/posting/so-sanh-v-plus-va-v-advance-chon-goi-nao/)
5. [Đăng ký trên iPay](https://seomoney.org/posting/dang-ky-v-plus-v-advance-tren-ipay/)

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
| **AdSense code thật** | Chỉ có placeholder — xem [adsense-ad-placement-report.md](./adsense-ad-placement-report.md) |
| **Ẩn placeholder quảng cáo giả** | Khuyến nghị trước khi nộp AdSense |
| **ads.txt** | Sau khi được duyệt publisher |
| **AdSense placement in-article** | Chưa có slot — trong roadmap báo cáo placement |
| **1 cảnh báo internal links** | Report only, không chặn deploy |
| **Bài AdSense series 7–15** | Planned trong `data/adsense-foundation-series.json` |

---

## 5. Báo cáo liên quan (file `.md`)

| File | Nội dung |
|------|----------|
| [adsense-ad-placement-report.md](./adsense-ad-placement-report.md) | **Báo cáo đầy đủ vị trí quảng cáo AdSense** (2 slot hiện tại + roadmap) |
| [adsense-site-readiness-audit.md](./adsense-site-readiness-audit.md) | Audit site-readiness 78/100 — UX, policy, SEO |
| [rule-conflict-report.md](./rule-conflict-report.md) | Xung đột rule CI/bot |

---

## 6. Liên kết nhanh

- **Site:** https://seomoney.org/
- **Deploy log:** https://github.com/Banhang-Chogao/zola/actions/runs/27796087713
- **Series AdSense (đã publish 6/15):** https://seomoney.org/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/

---

*Tài liệu tổng hợp phiên triển khai 18–19/06/2026. Cập nhật khi có PR/deploy mới.*