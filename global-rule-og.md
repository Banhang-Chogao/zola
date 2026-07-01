# Global OG / Image / Alt-text / AdSense-safe Rule

Source of truth bắt buộc cho mọi bài viết mới của SEOMONEY, bất kể bài được tạo
từ shortcut (`bb`, `bb9`, `bb10`, …), CMS-V2, Editor, Content Creator hay bất kỳ
workflow nào. Rule riêng chỉ được bổ sung, không được làm yếu rule này. Rule này
có hiệu lực cao hơn mọi template, prompt, shortcut hay workflow riêng lẻ.

## Field ảnh chuẩn của SEOMONEY

- **Field ảnh canonical duy nhất của SEOMONEY là `[extra].thumbnail`** trong
  frontmatter. Đây là field mà `templates/macros/img.html` đọc và tự động resolve
  ra fallback chain. Luôn dùng field này cho ảnh đại diện/thumbnail.
- Resolver hỗ trợ thêm `[extra].image` (ưu tiên cao nhất) và `[extra].cover`
  (ưu tiên giữa), theo thứ tự `image` → `cover` → `thumbnail`. Metadata bổ trợ:
  `image_alt` (alt-text ghi đè), `image_source` (nguồn ảnh), `image_license`
  (license ảnh).
- **Không tự bịa field mới** nếu template không dùng. Không dùng `og_image` vì
  resolver hiện không đọc field đó. Nghi ngờ → tra `templates/macros/img.html`.
- Đường dẫn ảnh phải đúng cấu trúc public site (`https://seomoney.org/path/to/image`
  hoặc path local tương đối). Không dùng domain cũ, không dùng `/zola/`, không
  hotlink, không dùng path local máy tính.

## Ảnh và OG hợp lệ

- Mỗi bài phải có ảnh đại diện/OG hợp lệ. Không để social preview trống, hỏng,
  sai domain hoặc trỏ tới file không tồn tại.
- OG image ưu tiên tỉ lệ 1200x630. Ảnh body phải vừa layout, tối ưu dung lượng
  và web-friendly. Không thêm dependency hay đổi pipeline chỉ để xử lý ảnh.
- Không sinh link ảnh dạng `/zola/`. Không dùng domain cũ.

## Fallback OG bắt buộc

- Nếu không có ảnh riêng đạt chuẩn, dùng chuỗi owned-image fallback hiện có của
  `templates/macros/img.html`; không tạo fallback mới.
- Mỗi bài không có cover riêng sẽ tự động nhận 1 trong 20 OG fallback template
  (đường dẫn `/img/og-fallbacks/og-fallback-{0..19}.svg`), chọn theo
  `page.slug | length % 20`. Mỗi template có gradient + hoạ tiết riêng.
  Fallback cũ (`og-default.webp`) đã được thay thế.
- Guard OG mặc định trong `templates/base.html` là
  `/img/placeholders/OG-Image-place-holer.webp`
  (`static/img/placeholders/OG-Image-place-holer.webp`) — social preview không
  bao giờ trống/hỏng. Cover/placeholder SVG phải dùng twin `.og.webp` khi làm OG.
- **Nếu không chắc license, không rõ nguồn, không đạt AdSense-safe, không phù hợp
  nội dung hoặc có rủi ro bản quyền/quyền hình ảnh, bắt buộc dùng fallback OG
  image chuẩn của SEOMONEY.**
- Nếu không xác minh được nguồn, không dùng ảnh đó và chuyển sang fallback OG.
- Trong mọi trường hợp không chắc chắn, dùng fallback OG image chuẩn có sẵn của
  SEOMONEY.

## Alt-text

- Mọi ảnh nội dung, ảnh chính và ảnh đại diện khi hiển thị trong bài phải có
  alt-text tiếng Việt mô tả đúng nội dung/ý nghĩa trong ngữ cảnh. Alt-text phải
  rõ nghĩa, giúp người đọc hiểu ảnh nói gì mà không cần nhìn ảnh.
- Không để alt trống cho ảnh nội dung. Không dùng tên file làm alt-text.
  Không nhồi từ khóa. Không dùng mô tả chung chung như “ảnh minh họa”,
  “hình ảnh”, “image”, “photo”.
- Ảnh thuần trang trí chỉ được dùng `alt=""` khi template hỗ trợ accessibility
  đúng chuẩn. Ảnh chính và ảnh minh họa không thuộc ngoại lệ này.
- Markdown image PHẢI có dạng `![alt-text tiếng Việt rõ nghĩa](image-url)`.
  **Không được để dạng `![](image-url)`.** Trước publish, kiểm tra toàn bộ bài.

## Bản quyền, nguồn và AdSense safety

- Ảnh phải phù hợp nội dung bài. Không dùng ảnh ngẫu nhiên, sai ngữ cảnh.
  Ưu tiên ảnh tự tạo, ảnh SEOMONEY sở hữu, public domain, Creative Commons
  hoặc ảnh có license rõ ràng cho website thương mại/monetized blog.
- Không lấy ảnh trực tiếp từ Google Images nếu chưa xác minh license tại nguồn.
  Không dùng ảnh báo điện tử, Facebook, TikTok, YouTube thumbnail, forum,
  Pinterest hoặc website khác khi chưa có quyền rõ ràng.
- Không dùng ảnh watermark/logo nguồn khác. Không dùng ảnh không rõ license.
- Không dùng ảnh người nổi tiếng, sự kiện, thương hiệu, sản phẩm, bản đồ, tài
  liệu hoặc screenshot có rủi ro quyền hình ảnh/bản quyền khi chưa xác minh
  quyền dùng.
- Không dùng ảnh giật gân, gây hiểu nhầm, sai ngữ cảnh, kém chất lượng hoặc
  làm bài trông copy/low-value. Không dùng ảnh chỉ để trang trí SEO.
- Với bài dựa trên báo/nguồn tin (shortcut `bb`, `bb9`, `bb10`…), **không copy
  ảnh gốc từ báo**; dùng ảnh owned, ảnh thay thế license-safe hoặc fallback
  SEOMONEY.
- Unsplash, Pexels, Pixabay, Creative Commons và public domain chỉ được dùng
  sau khi kiểm tra license cho website thương mại/monetized tại trang nguồn.
- Mỗi ảnh ngoài phải ghi nguồn/license và attribution (nếu yêu cầu) trong
  frontmatter `[extra]` → `references_copyright` (macro tự render vào section
  "Bản quyền & Ghi nguồn" cuối bài). Không ghi "Nguồn: Internet", không ghi
  nguồn mơ hồ hay nguồn chưa xác minh. **Không ghi nguồn nếu thực tế không
  xác minh được.** Không xác minh được nguồn → không dùng ảnh đó → chuyển
  sang fallback OG.

Thứ tự ưu tiên ảnh (cao → thấp):

1. Ảnh tự tạo hoặc ảnh SEOMONEY sở hữu.
2. Ảnh SEOMONEY tạo bằng công cụ thiết kế/AI an toàn (không xâm phạm thương
   hiệu, bản quyền hay người thật).
3. Ảnh public domain hoặc nguồn chính thức cho phép reuse.
4. Ảnh Creative Commons có license phù hợp cho commercial use.
5. Ảnh stock miễn phí (Unsplash, Pexels, Pixabay) nếu kiểm tra được license.
6. Fallback OG image chuẩn của SEOMONEY.

## Tích hợp vào workflow

Rule này phải được áp dụng ở mọi nơi có tạo/sửa bài:

| Nơi áp dụng | Yêu cầu cụ thể |
|-------------|----------------|
| **`shortcuts.md`** và mọi shortcut (`bb`, `bb9`, `bb10`, …) | Luôn apply rule không copy ảnh báo gốc. Nếu bài dựa trên nguồn tin, không dùng ảnh gốc; fallback OG hoặc ảnh owned. Mặc định bài viết mới nhận fallback OG trừ khi có ảnh riêng đạt chuẩn. |
| **CMS-V2** (`static/js/editor.js`) | Phải nhắc kiểm tra ảnh, alt-text, fallback OG, nguồn/license trước publish. Nhắc không được để `![](image-url)`. |
| **Editor / Content Creator** | Áp dụng checklist ảnh trước publish. Kiểm tra alt-text từng ảnh. |
| **Prompt templates** | Phải ghi rõ rule ảnh vào prompt, đặc biệt là alt-text và fallback OG. |
| **Rule registry** | Rule này là source of truth cao nhất cho toàn bộ yêu cầu về ảnh. |
| **Agent docs** | Agent phải đọc và tuân thủ rule này khi tạo/sửa bài có ảnh. |
| **Content pipeline docs** | Pipeline phải đảm bảo bài output có đủ OG/ảnh đại diện hợp lệ. |

## Pre-publish checklist ảnh

Trước khi publish bất kỳ bài viết nào, kiểm tra tất cả các mục sau:

- [ ] Bài có OG image/ảnh đại diện hợp lệ? (không trống, không hỏng, không sai domain)
- [ ] Ảnh có đúng ngữ cảnh bài? (không ngẫu nhiên, không gây hiểu nhầm)
- [ ] Nguồn ảnh có rõ ràng? (tự tạo / stock xác minh license / fallback OG)
- [ ] License ảnh có cho phép dùng trên website thương mại/monetized blog?
- [ ] Nếu không chắc license hoặc AdSense-safe, đã chuyển sang fallback OG?
- [ ] Fallback OG image hiện tại của SEOMONEY: 20 template tại `/img/og-fallbacks/og-fallback-{0..19}.svg`, chọn theo slug length % 20
- [ ] Frontmatter image field đúng `[extra].thumbnail` (hoặc `image`/`cover`)?
- [ ] Đường dẫn ảnh đúng domain/cấu trúc hiện tại (`seomoney.org`, không `/zola/`)?
- [ ] Đã tránh domain cũ và `/zola/` hoàn toàn?
- [ ] Mọi ảnh trong bài đã có alt-text tiếng Việt rõ nghĩa?
- [ ] Markdown image không ở dạng `![](image-url)`? Mọi ảnh đều là `![alt](url)`?
- [ ] Ảnh đã được tối ưu dung lượng, tỉ lệ web-friendly, không làm chậm trang?
- [ ] Ảnh không làm bài trông stock/low-value/copy (không ảnh trang trí SEO)?
