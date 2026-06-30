# Ghi chú về kết bài

Các section kết bài (Liên kết nội bộ, Liên kết bên ngoài, Bản quyền và ghi nguồn,
FAQ) được template và macro tự động render — không cần viết tay trong content.

- `references::section` (macro) tự sinh block tham khảo & nguồn dữ liệu
- `[[extra.faq]]` (frontmatter) tự render FAQ + JSON-LD schema
- `page.lower`/`page.higher` (template) tự tạo điều hướng bài kế tiếp

Bài viết chỉ cần tập trung vào nội dung chính; không cần thêm heading kết bài thủ công.
