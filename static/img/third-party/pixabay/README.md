# Pixabay (third-party) images — source-safe folder

Ảnh tải từ **Pixabay** (bên thứ ba) được lưu **chỉ** trong thư mục này:
`static/img/third-party/pixabay/<slug>/`.

## Vì sao thư mục riêng?

- Đây **không** phải ảnh do SEOMONEY tạo → **KHÔNG đóng watermark** `…_seomoney.org`.
  Thư mục này nằm **ngoài** owned-roots (`static/img/posting/`, `static/img/owned/`)
  của `scripts/watermark_blog_images.py`, nên watermarker bỏ qua hoàn toàn.
- Đóng watermark sở hữu lên ảnh bên thứ ba là **sai bản quyền** — tuyệt đối không làm.

## Mỗi ảnh phải đi kèm metadata

Cạnh mỗi ảnh có 1 sidecar `*.source.json` (sinh bởi `pixabay_image_assist.py confirm`)
ghi: `image_source`, `image_author`, `image_url`, `image_license_note`,
`image_downloaded_at`, `image_verified_manually`, `image_commercial_use_checked`.
**Không** ảnh nào được dùng nếu thiếu metadata này.

Chi tiết quy trình: `docs/pixabay-image-assist.md`.
