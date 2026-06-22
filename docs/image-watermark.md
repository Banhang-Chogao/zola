# Blog Image Watermark — chính sách & quy trình

Watermark sở hữu nhúng sẵn cho ảnh blog **do SEOMONEY tự tạo**, định dạng:

```
<16-chữ-số>_seomoney.org      ví dụ 7154228153006839_seomoney.org
```

Hash 16 chữ số là **deterministic** từ (đường dẫn ảnh + bytes): cùng ảnh → cùng
watermark; ảnh đổi nội dung → hash mới. Dấu được vẽ nhỏ, mờ, góc dưới-phải; giữ
nguyên kích thước ảnh; không phá thumbnail/layout/SEO.

## Nguyên tắc sở hữu (quan trọng)

> Chỉ đóng watermark lên ảnh **mình sở hữu / có quyền dùng rõ ràng**. Tuyệt đối
> không stamp `seomoney.org` lên screenshot app/ngân hàng, ảnh thẻ, logo, ảnh
> quảng cáo bên thứ ba, ảnh remote hay ảnh không rõ nguồn.

Cơ chế **folder-based + bảo thủ**:

| Loại | Hành vi |
|------|---------|
| `static/img/posting/**` | **Tự động watermark** (ảnh bài viết gốc) |
| `static/img/owned/**` | **Tự động watermark** (ảnh gốc khác — bỏ ảnh mới vào đây) |
| `static/img/covers/**`, `brand/`, `og/`, `placeholder/`, `icons/` | **Bỏ qua** |
| `*.og.webp`, tên chứa `logo/favicon/icon/sprite/-mark/placeholder` | **Bỏ qua** |
| `.svg .gif .ico` | **Bỏ qua** |
| Ảnh ngoài thư mục owned / không rõ nguồn | **Bỏ qua (mặc định)** |

**Mặc định: không rõ nguồn ⇒ không watermark.**

## Override (tuỳ chọn) — `data/watermark-policy.json`

Không bắt buộc. Khi cần tinh chỉnh:

```json
{
  "owned_roots": ["static/img/owned-extra"],
  "include":     ["static/img/x/anh-goc-cua-toi.webp"],
  "exclude":     ["static/img/posting/bai/anh-ben-thu-ba.webp"]
}
```

- `owned_roots`: thêm thư mục owned (auto-watermark).
- `include`: ép watermark 1 ảnh owned (tương đương `watermark: true`).
- `exclude`: bỏ watermark 1 ảnh (tương đương `watermark: false`) — dùng khi screenshot
  bên thứ ba lỡ nằm trong thư mục owned.

## Quy trình cho bài viết mới (không cần thao tác từng ảnh)

1. Ảnh **gốc của mình** → đặt trong `content`/`static/img/posting/<slug>/` hoặc
   `static/img/owned/` → tự động watermark khi build.
2. Ảnh **bên thứ ba** (screenshot app/ngân hàng/logo) → để **ngoài** thư mục owned
   (vd `static/img/covers/`) hoặc thêm vào `exclude` → không bị stamp.
3. Tham chiếu ảnh trong Markdown ở dạng `.webp` (pipeline `to_webp.py --replace`
   xoá `.jpg` trên `main`).

## Lệnh

```bash
python3 scripts/watermark_blog_images.py --apply     # đóng dấu + cập nhật manifest
python3 scripts/watermark_blog_images.py --check     # CI gate: fail nếu ảnh owned thiếu dấu
python3 scripts/watermark_blog_images.py --dry-run   # xem trước, không đổi gì
```

## Hạ tầng

| Thành phần | Path |
|-----------|------|
| Engine | `scripts/watermark_blog_images.py` |
| Tests | `scripts/test_watermark_blog_images.py` |
| Manifest | `data/image-watermark-manifest.json` (path → hash16 → text → sha256 → time) |
| Policy override | `data/watermark-policy.json` (tuỳ chọn) |
| QA gate | `qa_check.py` → **Blog Image Watermark Gate** (ảnh owned thiếu dấu ⇒ QA đỏ) |
| Pipeline | `.github/workflows/optimize-images.yml` (watermark **sau** `to_webp`) |

> Lưu ý pháp lý: watermark giúp **nhận diện thương hiệu** và **giảm tái sử dụng
> tuỳ tiện**, nhưng **không** đảm bảo bảo hộ bản quyền tuyệt đối.
