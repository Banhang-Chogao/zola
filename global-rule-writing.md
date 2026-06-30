# Global Writing Ending Rule

Source of truth bắt buộc cho mọi bài viết mới của SEOMONEY. Rule này bổ sung cho
SEO CONTENT SYSTEM RULE trong `CLAUDE.md` và áp dụng cho shortcut, CMS-V2,
Editor, Content Creator, prompt/template và mọi workflow viết hoặc rewrite bài.

Rule riêng của workflow/bài chỉ được bổ sung, không được bỏ hoặc làm yếu các yêu
cầu global. Ngoại lệ do user chỉ định trực tiếp vẫn không được vi phạm bản quyền
hoặc AdSense safety.

## Thứ tự kết bài bắt buộc

Mọi bài phải kết thúc bằng đúng bốn section sau, theo thứ tự:

1. `## Liên kết nội bộ`
2. `## Liên kết bên ngoài`
3. `## Bản quyền và ghi nguồn`
4. `## FAQ - Câu hỏi thường gặp`

Có thể thêm `## Đọc tiếp` trước `## Liên kết nội bộ` khi phù hợp. Không được làm
mất bốn section bắt buộc.

### Liên kết nội bộ

- Gợi ý bài/trang SEOMONEY liên quan; ưu tiên URL thật tới hub/category, bài cùng
  cluster/series hoặc tool liên quan. Anchor tự nhiên, không nhồi từ khóa.
- Không bịa URL, không dùng domain cũ hoặc `/zola/`. Nếu chưa tìm được link phù
  hợp, ghi `TODO: kiểm tra và bổ sung liên kết nội bộ trước publish`; TODO phải
  được xử lý trước khi xuất bản.

### Liên kết bên ngoài

- Chỉ dùng nguồn uy tín, liên quan và hỗ trợ xác minh nội dung. Bài dựa trên
  báo/tài liệu phải nêu nguồn chính rõ ràng.
- Không link rác, độc hại, affiliate trá hình hoặc nguồn không đáng tin; không
  thêm link chỉ để đủ số lượng.

### Bản quyền và ghi nguồn

- Nêu rõ nội dung được SEOMONEY biên tập, diễn giải hoặc phân tích khi có tham
  khảo; không sao chép nguyên văn dài và không gây hiểu nhầm về quyền sở hữu.
- Ghi nguồn nội dung và nguồn/license ảnh ngoài minh bạch. Không ghi nguồn giả,
  nguồn mơ hồ hoặc “Nguồn: Internet”.
- Nếu dùng fallback nội bộ, có thể ghi ngắn rằng ảnh đại diện/OG là hình minh họa
  nội bộ của SEOMONEY.

### FAQ - Câu hỏi thường gặp

- Có ít nhất 3 cặp câu hỏi-trả lời tự nhiên, đúng search intent; câu trả lời ngắn,
  rõ, không nhồi từ khóa và không bịa thông tin.
- Bài hướng dẫn ưu tiên lỗi thường gặp, điều kiện, chi phí/thời gian/rủi ro. Bài
  tin tức/phân tích ưu tiên bối cảnh, tác động và điều người đọc cần hiểu.
- Nếu site dùng `[[extra.faq]]` để sinh schema, nội dung FAQ frontmatter phải nhất
  quán với section FAQ hiển thị trong body.

## Pre-publish checklist

- [ ] Có đủ bốn heading bắt buộc, đúng thứ tự?
- [ ] Internal link có thật, đúng domain/path và anchor tự nhiên?
- [ ] External link uy tín, liên quan, không rác/affiliate trá hình?
- [ ] Nguồn nội dung và nguồn/license ảnh được ghi minh bạch?
- [ ] FAQ có ít nhất 3 Q&A tự nhiên, đúng intent và không bịa thông tin?
