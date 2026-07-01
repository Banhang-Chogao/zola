# Global Writing Ending Rule

Source of truth bắt buộc cho mọi bài viết mới của SEOMONEY. Rule này bổ sung cho
SEO CONTENT SYSTEM RULE trong `CLAUDE.md` và áp dụng cho shortcut, CMS-V2,
Editor, Content Creator, prompt/template và mọi workflow viết hoặc rewrite bài.

Rule riêng của workflow/bài chỉ được bổ sung, không được bỏ hoặc làm yếu các yêu
cầu global. Ngoại lệ do user chỉ định trực tiếp vẫn không được vi phạm bản quyền
hoặc AdSense safety.

## Kết bài — do macro tự động render (BẮT BUỘC)

Bốn section cuối bài được **macro template `references::section` tự động render**
cho mọi bài viết — **KHÔNG hardcode các heading này
vào body markdown**:

1. `## Liên kết bên ngoài được sử dụng trong bài viết`
2. `## Liên kết nội bộ liên quan`
3. `## Bản quyền & Ghi nguồn`
4. `## FAQ - Câu hỏi thường gặp`

### Cung cấp dữ liệu cho macro

Macro tự động lấy dữ liệu từ những nguồn sau — writer chỉ cần đảm bảo các nguồn này
đầy đủ, KHÔNG viết heading thủ công:

- **Liên kết nội bộ & ngoài:** Viết link trực tiếp trong body markdown. Script
  `build_references.py` tự động trích xuất mọi link từ body và render vào macro.
  Link nên nằm rải rác trong nội dung chính (anchor tự nhiên, hợp ngữ cảnh).

- **Bản quyền:** Macro tự sinh từ nguồn ngoài trích xuất được. Nếu cần custom, ghi
  trong frontmatter: `[extra] references_copyright = "..."`.
  Fallback mặc định: `Bài viết được biên tập và tổng hợp bởi Duy Nguyen/SEOMONEY.
  Nội dung chỉ mang tính tham khảo, không thay thế nguồn chính thức hoặc tư vấn
  chuyên môn.`

- **FAQ:** Khai báo trong frontmatter `[extra]` dạng:
  ```toml
  [[extra.faq]]
  q = "Câu hỏi?"
  a = "Câu trả lời."
  ```
  Có ít nhất 3 cặp câu hỏi-trả lời tự nhiên, đúng search intent; câu trả lời ngắn,
  rõ, không nhồi từ khóa và không bịa thông tin.
  Nếu chưa có FAQ, macro hiển thị fallback: `"FAQ đang được cập nhật cho bài viết
  này."`

### Fallback behavior

| Section | Có dữ liệu | Không dữ liệu |
|---------|-----------|---------------|
| Liên kết ngoài | Render danh sách link | "Bài viết hiện chưa có nguồn ngoài được khai báo riêng." |
| Liên kết nội bộ | Render danh sách link | Bài trước/sau hợp lệ; nếu không có thì hiện ghi chú |
| Bản quyền | Render custom/frontmatter | Fallback mặc định SEOMONEY |
| FAQ | Render Q&A từ `[[extra.faq]]` | "FAQ đang được cập nhật cho bài viết này." |

### Cấm

- **KHÔNG** viết `## Liên kết nội bộ`, `## Liên kết bên ngoài`,
  `## Bản quyền & Ghi nguồn`, `## FAQ - Câu hỏi thường gặp` vào body markdown.
- **KHÔNG** viết `## Tham khảo & Nguồn dữ liệu`, `## Tuyên bố bản quyền`,
  `## Bản quyền và ghi nguồn` — tất cả đều do macro render.
- Vi phạm → `qa_check.py` cảnh báo và có thể block auto-merge.

## Pre-publish checklist
- [ ] Nguồn nội dung và nguồn/license ảnh được ghi minh bạch?
- [ ] FAQ có ít nhất 3 Q&A tự nhiên, đúng intent và không bịa thông tin?
