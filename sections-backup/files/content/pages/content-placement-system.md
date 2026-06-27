+++
title = "Content Placement System — hướng dẫn admin"
date = 2026-06-27
description = "Hướng dẫn Placement Registry, content blocks và render theo placement_id trên SEOMONEY. Quản lý tại /tools/momo-url/."
path = "content-placement-system"
template = "page.html"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["content-placement", "cms", "zola", "momo", "admin"]

[extra]
seo_keyword = "content placement system"
toc = true

[[extra.faq]]
q = "Content Placement System là gì?"
a = "Đây là lớp quản lý nội dung hiển thị theo vị trí cố định (placement ID). Admin tạo content block (CTA, banner, notice…) và gắn vào placement — template render tự động khi build."

[[extra.faq]]
q = "Admin quản lý ở đâu?"
a = "Trang /tools/momo-url/ (đăng nhập Google admin). Tab Vị trí hiển thị liệt kê placement registry; tab Content blocks cho phép tạo/sửa/xóa block."

[[extra.faq]]
q = "Dữ liệu lưu ở đâu?"
a = "File data/content-placements.json trong repo. API VIPZone ghi file và commit qua GitHub để deploy.yml rebuild site."

[[extra.faq]]
q = "Block mới có hiện ngay trên site không?"
a = "Chỉ khi enabled=true và placement đã có hook trong template. Hai block MoMo mẫu mặc định tắt (enabled=false) để không đổi hàng loạt link donate đang chạy."

[[extra.faq]]
q = "MoMo URL audit còn hoạt động không?"
a = "Có. Tab MoMo URL vẫn quét link me.momo.vn trong config, template và content; cột Content blocks hiển thị block nào dùng URL đó."
+++

Mình gom phần **quản lý nội dung theo vị trí** vào cùng trang admin MoMo URL để không phải nhớ nhiều công cụ. Luồng chuẩn:

```text
Placement Registry → Content Blocks → Render theo placement_id
```

## Placement Registry là gì?

Mỗi **placement ID** là một điểm inject cố định trong template (vd `post_after_intro`, `footer_above`). Registry mô tả scope, template gợi ý và trạng thái hook — admin **không** gõ mô tả vị trí bằng tay khi tạo block.

Ví dụ placement đã gắn hook:

| Placement ID | Vị trí |
|------------|--------|
| `global_header_below` | Dưới header toàn site |
| `home_hero_after` | Sau hero trang chủ |
| `post_after_content` | Sau nội dung bài viết |
| `tools_momo_admin_notice` | Banner trong trang admin |

Danh sách đầy đủ xem tab **Vị trí hiển thị** tại [Quản lý MoMo URL](/tools/momo-url/).

## Content block

Một block gồm: `id`, `placement_id`, `type`, `title`, `body`, CTA (`button_text` + `url`), `priority`, `pages` / `exclude_pages`, `enabled`.

Type hỗ trợ: `momo_cta`, `donate_box`, `notice`, `banner`, `link_card`, `html_safe` (chỉ nội dung tin cậy).

## Render trên site

Macro `templates/macros/placement.html` đọc `data/content-placements.json` lúc build:

- Không có block enabled → không render gì (an toàn).
- Nhiều block cùng placement → sort theo `priority` tăng dần.
- `pages` / `exclude_pages` lọc theo prefix `page.path`.

## MoMo URL + placement

Tab **MoMo URL** vẫn audit link `https://me.momo.vn/…`. API bổ sung `content_blocks`, `placement_ids`, `display_text` để thấy block nào trỏ tới URL đó — không thay thế chức năng thay link thủ công.

## QA & deploy

CI chạy `python3 scripts/validate_content_placements.py` trước `zola build`. Sửa registry/blocks qua admin → commit JSON → auto deploy GitHub Pages.

## Bước tiếp theo

- Mở [Quản lý MoMo URL](/tools/momo-url/) → tab Content blocks → bật block mẫu nếu muốn thử CTA donate.
- Đọc thêm [Giới thiệu](/about/) và [Insights](/insights/) để theo dõi deploy/QA.