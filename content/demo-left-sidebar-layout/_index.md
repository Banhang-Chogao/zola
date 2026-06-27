+++
title = "Demo Layout Blog"
description = "Trực quan giao diện left-sidebar blog layout 30/70 với 3 ad spots cố định, tối ưu cho AdSense."
sort_by = "date"
template = "posting-left-sidebar.html"

[taxonomies]
categories = ["Tất cả"]
tags = ["demo", "layout", "guideline"]
+++

Demo layout này hiển thị thiết kế **30/70 responsive layout** dành cho blog monetization với AdSense.

## Tính năng chính

✅ **Sidebar trái (30%)** — Sticky post widget, categories, date widget, ad spot 300×250  
✅ **Nội dung chính (70%)** — Sticky post, featured post, bài viết thường, pagination  
✅ **3 Ad spots** — 728×90 (header), 300×250 (sidebar), 728×90 (in-article) — cố định min-height, chống CLS  
✅ **Responsive an toàn** — Desktop: 30/70 grid → Mobile: 1 cột, sidebar xuống dưới  
✅ **Zero breaking changes** — Coexist với blog layout hiện tại, không affect trang khác

## Kiến trúc template

Template sử dụng **context detection** trong Tera để hoạt động an toàn với cả section context (trang này) và page context:

- **Section context** (trang demo): Hiển thị sidebar + main feed + pagination
- **Page context** (single page): Hiển thị single page content

Điều này đảm bảo template linh hoạt, tái sử dụng, không gây lỗi build.

## Test responsive trên thiết bị

- **Desktop (1024px+):** Sidebar trái, main content phải, 3 ad spots hiển thị đúng
- **Tablet (768px):** Grid collapse 1 cột, sidebar chuyển xuống dưới
- **Mobile (360–480px):** Single column, ad spots scale tương ứng, không horizontal scroll

## Tìm hiểu thêm

- Hướng dẫn chi tiết: [Zola responsive layout context detection Tera template](/posting/zola-responsive-layout-context-detection/)
- Kiến trúc template: [templates/posting-left-sidebar.html](https://github.com/Banhang-Chogao/zola/blob/main/templates/posting-left-sidebar.html)
- Audit compatibility: [LAYOUT_COMPATIBILITY_REPORT.md](https://github.com/Banhang-Chogao/zola/blob/main/docs/LAYOUT_COMPATIBILITY_REPORT.md)

---

*Demo này minh hoạ layout 30/70 left-sidebar được tối ưu cho AdSense với các ad spots cố định, chống layout shift.*
