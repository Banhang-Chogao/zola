## Vì sao static site + backend paywall?

Blog Zola build ra HTML tĩnh — cực nhanh, cực rẻ host, SEO tốt.
Nhưng static site **không thể** giấu nội dung premium trong cùng file
markdown nếu bạn publish full body ra `public/`. Giải pháp chuẩn:

1. **Teaser** (~150–250 từ) render trong HTML public.
2. **Full body** lưu ở `private_content/` hoặc DB, chỉ backend trả sau
   khi validate approve code.
3. **Paywall box** trên trang hướng user: Momo → request → chờ admin →
   nhận code qua email → unlock read-only.

Kiến trúc này không phải DRM tuyệt đối (user vẫn có thể chụp màn hình),
nhưng kết hợp watermark động + log access + cảnh báo bản quyền tạo
**deterrent** đủ mạnh cho mô hình blog cá nhân.

## Checklist triển khai (phần premium)

### 1. Định giá và positioning

- Chọn **một** bài pilot có insight rõ, không trùng free content.
- Đặt giá cố định (VD: 29.000đ) — đơn giản hơn subscription.
- Teaser phải trả lời: *bài này giải quyết vấn đề gì* và *sau khi trả
  phí bạn nhận được gì*.

### 2. Quy trình thanh toán thủ công (Momo)

- Link Momo cá nhân/doanh nghiệp nhỏ — không cần cổng thanh toán ngay.
- User gửi request kèm email + ghi chú giao dịch.
- Admin đối soát sao kê Momo → approve → generate code → gửi email.

Ưu điểm: triển khai trong 1 ngày, không phí cổng. Nhược: không scale
khi volume lớn — lúc đó mới nâng cấp webhook tự động.

### 3. Approve code — ràng buộc bảo mật tối thiểu

Mỗi code phải bind:

- `email` + `post_id` (không dùng code global).
- `expires_at` (7 / 30 ngày / lifetime).
- `max_usage` (giới hạn số lần unlock).

Lưu **hash** trong DB, không lưu plaintext. Session token ngắn hạn
(4h) cho việc fetch content.

### 4. Read-only + watermark

- Disable selection / copy trong vùng premium (deterrent).
- Overlay watermark: `blog • email_hash • post_id • trace_code`.
- Print/PDF: `@media print` chèn watermark `trace_code_domain` mỗi trang.

### 5. Vận hành và metric

Theo dõi:

- Conversion: view teaser → request → paid → unlock.
- Thời gian admin approve (SLA mục tiêu < 24h).
- Usage count per code (phát hiện chia sẻ code).

## Mẫu email gửi approve code

Sau khi admin xác nhận thanh toán, email cần có: tiêu đề bài, link,
code, hạn dùng, hướng dẫn 4 bước, cảnh báo bản quyền ngắn. Python SMTP
đọc config từ env — không hardcode secret trong repo.

## Kết luận

Paywall trên blog static không cần platform phức tạp. Cần **kỷ luật
kiến trúc**: không leak full HTML, quy trình admin rõ, trải nghiệm
unlock mượt. Bài demo này minh họa end-to-end flow — từ teaser bạn
đang đọc đến phần checklist và playbook triển khai phía trên.

*Nếu bạn đã thanh toán, nhập approve code ở khối paywall bên dưới để
mở khóa toàn bộ nội dung.*