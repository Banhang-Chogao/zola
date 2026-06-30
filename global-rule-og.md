# Global OG / Image / Alt-text / AdSense-safe Rule

Source of truth bắt buộc cho mọi bài viết mới của SEOMONEY, bất kể bài được tạo
từ shortcut, CMS-V2, Editor, Content Creator hay workflow khác. Rule riêng chỉ
được bổ sung, không được làm yếu rule này.

## Ảnh và metadata chuẩn

- Mỗi bài phải có ảnh đại diện/OG hợp lệ. Không để social preview trống, hỏng,
  sai domain hoặc trỏ tới file không tồn tại.
- Field ảnh phổ biến/chuẩn của bài hiện tại là `[extra].thumbnail`. Resolver cũng
  hỗ trợ `[extra].image` và `[extra].cover`, theo thứ tự ưu tiên `image` → `cover`
  → `thumbnail`; metadata bổ trợ là `image_alt`, `image_source` và
  `image_license`. Không dựa riêng vào `og_image` vì resolver hiện không đọc field
  đó, và không tự tạo field khác.
- Chỉ dùng URL public thuộc `https://seomoney.org` hoặc path local đúng cấu trúc
  site. Không dùng domain cũ, `/zola/`, hotlink hoặc path local của máy.
- Ảnh OG riêng ưu tiên 1200x630. Ảnh body phải vừa layout, được tối ưu dung lượng
  và web-friendly; không thêm dependency hay đổi pipeline chỉ để xử lý ảnh.

## Fallback bắt buộc

- Nếu không có ảnh riêng đạt chuẩn, dùng chuỗi owned-image fallback hiện có của
  `templates/macros/img.html`; không tạo fallback mới.
- Fallback site-level của bài là `/img/og-default.webp`
  (`static/img/og-default.webp`). Guard OG mặc định trong `templates/base.html`
  là `/img/placeholders/OG-Image-place-holer.webp`
  (`static/img/placeholders/OG-Image-place-holer.webp`) để social preview không
  bao giờ trống/hỏng. Cover/placeholder SVG phải dùng twin `.og.webp` khi làm OG.
- Nếu không xác minh được license, nguồn, ngữ cảnh, chất lượng hoặc mức an toàn
  AdSense của ảnh, bắt buộc bỏ ảnh đó và dùng fallback nội bộ.

## Alt-text

- Mọi ảnh nội dung, ảnh chính và ảnh đại diện khi hiển thị trong bài phải có
  alt-text tiếng Việt mô tả đúng nội dung/ý nghĩa trong ngữ cảnh.
- Không để alt trống cho ảnh nội dung, không dùng tên file, không nhồi từ khóa và
  không dùng mô tả chung chung như “ảnh minh họa”, “hình ảnh”, “image”, “photo”.
- Ảnh thuần trang trí chỉ được dùng `alt=""` khi template hỗ trợ accessibility
  đúng chuẩn. Ảnh chính và ảnh minh họa không thuộc ngoại lệ này.
- Trước publish, kiểm tra mọi ảnh Markdown có dạng
  `![alt-text tiếng Việt rõ nghĩa](image-url)`, không có `![](image-url)`.

## Bản quyền, nguồn và AdSense safety

Thứ tự ưu tiên: (1) ảnh SEOMONEY tự tạo/sở hữu; (2) ảnh SEOMONEY tạo bằng công
cụ thiết kế/AI, không xâm phạm thương hiệu, bản quyền hay người thật; (3) public
domain/nguồn chính thức cho phép reuse; (4) Creative Commons cho phép commercial
use; (5) stock uy tín có license thương mại đã xác minh; (6) fallback nội bộ.

- Ảnh phải đúng ngữ cảnh, có chất lượng, không giật gân, gây hiểu nhầm, chỉ để
  trang trí SEO hoặc làm bài trông như nội dung copy/low-value.
- Không lấy ảnh trực tiếp từ Google Images. Không dùng ảnh báo điện tử, Facebook,
  TikTok, YouTube thumbnail, forum, Pinterest hoặc website khác khi chưa có quyền
  rõ ràng. Không dùng watermark/logo nguồn khác hay ảnh không rõ license.
- Không dùng ảnh người nổi tiếng, sự kiện, thương hiệu, sản phẩm, bản đồ, tài
  liệu hoặc screenshot có rủi ro quyền hình ảnh/bản quyền khi chưa xác minh.
- Với bài dựa trên báo/nguồn tin, không copy ảnh gốc; dùng ảnh owned, ảnh thay thế
  license-safe hoặc fallback SEOMONEY.
- Unsplash, Pexels, Pixabay, Creative Commons và public domain chỉ được dùng sau
  khi kiểm tra license cho website thương mại/monetized tại trang nguồn.
- Mỗi ảnh ngoài phải ghi nguồn/license và attribution (nếu yêu cầu) trong
  `## Bản quyền và ghi nguồn`. Không ghi “Nguồn: Internet”, nguồn mơ hồ hay nguồn
  chưa xác minh. Không xác minh được thì không dùng ảnh.

## Pre-publish checklist

- [ ] Có OG/ảnh đại diện hợp lệ; đúng ngữ cảnh và không làm bài trông stock/copy?
- [ ] Nguồn/license cho phép commercial use đã được xác minh và ghi minh bạch?
- [ ] Nếu còn nghi ngờ về license/AdSense, đã chuyển sang fallback nội bộ?
- [ ] Dùng đúng field template; path/domain hiện tại; không domain cũ hay `/zola/`?
- [ ] Mọi ảnh nội dung có alt tiếng Việt rõ nghĩa; không còn `![](...)`?
- [ ] Ảnh có dung lượng và tỉ lệ web-friendly?
