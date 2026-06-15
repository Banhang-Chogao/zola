---
description: Audit toàn bộ component UI/UX chưa áp 3 theme mới (Z-X, E-X, Hila Ericsson), áp dụng override ngay
---

Khi user gõ `/thememoi` (hoặc `thememoi` plain text), thực thi quy trình
sau **NGAY**, không hỏi lại, không xác nhận:

## 1. Audit phase

1. Grep tất cả file SCSS trong `sass/` tìm hardcoded BrandingX colors:
   `$brand-signal-red`, `$brand-hot-pink`, `#ec4899`, `#d63d3d`, `$brand-ink-900`.
2. Loại trừ các file: `_brand-vars.scss`, `_momo-tokens.scss`, `_branding.scss`,
   `_zx-tokens.scss`, `_ex-tokens.scss`, `_themes.scss`, `_theme-*.scss`
   (đây là token / theme definition, không phải component cần override).
3. Liệt kê các selector chính trong file còn lại (post-card, sidebar,
   featured-card, random-item, cat-list, related-card, author-box,
   pagination, tag-list, post-single, section-header, footer-tags,
   etc.) — đối chiếu với file theme override hiện có (`_theme-overrides.scss`
   hoặc `_theme-hila.scss`).
4. Output bảng `| Component | Z-X | E-X | Hila | Action |` cho thấy
   component nào đã có / thiếu override cho từng theme.

## 2. Apply phase

5. Mở file theme override duy nhất (`sass/_theme-overrides.scss` — tạo
   mới nếu chưa có) — chứa **SCSS mixin** `theme-overrides(...)` định
   nghĩa pattern override cho mỗi component, sau đó gọi mixin 3 lần
   cho `:root[data-theme="zx"]`, `[data-theme="ex"]`, `[data-theme="hila"]`
   với token sets tương ứng ($zx-*, $ex-*, $ex-* + kicker spacing wider).
6. Thêm/cập nhật mixin để bao gồm các component còn thiếu từ audit.
7. Verify SCSS compile pass (`npx sass sass/site.scss /tmp/site.css`).

## 3. Constraints (BẮT BUỘC tuân thủ)

- **CHỈ áp dụng giao diện + bố cục** — color, border, radius, shadow,
  spacing. **KHÔNG đổi content text, không đổi cấu trúc DOM, không xoá
  HTML/component**.
- Mọi override scoped dưới `:root[data-theme="..."]` → default
  (BrandingX, chưa toggle) state KHÔNG đổi → zero regression.
- Tuân thủ CLAUDE.md: KHÔNG sửa `html { }`, `body { }`, KHÔNG đụng
  `overflow`/`height`/`position` global. Mobile section (≤720px) tách
  block riêng tự đóng tự mở nếu có.

## 4. Output

Sau khi xong, output:
- Bảng "Component coverage matrix" sau khi fix.
- Tổng số component được themed.
- Commit message gợi ý: "Thememoi: full coverage 3 themes cho N components".
- Nhắc user: deploy + test 3 theme qua dropdown navbar góc phải.

**KHÔNG cần tạo PR riêng** — commit thẳng vào branch hiện tại.
