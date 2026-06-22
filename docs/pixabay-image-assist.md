# Pixabay Image-Assist (No-API) — quy trình & ràng buộc

Trợ lý gợi ý ảnh **cover/OG** từ Pixabay cho luồng tạo bài, **không dùng API/API key**,
ưu tiên an toàn **bản quyền** và an toàn **AdSense**, và **không bao giờ tự đăng**.

- Engine: `scripts/pixabay_image_assist.py`
- Tests: `scripts/test_pixabay_image_assist.py`
- Thư mục ảnh bên thứ ba: `static/img/third-party/pixabay/<slug>/`
- Gợi ý (volatile, gitignored): `data/pixabay-suggestions/<slug>.json`

## 1. Chế độ No-API hoạt động ra sao

Không gọi Pixabay API. Helper chỉ **đọc trang search public** của Pixabay (HTML),
bóc 3–5 ứng viên **landscape** phù hợp làm cover/OG. Với mỗi ứng viên lưu/hiển thị:

- `title` / `alt`
- `author` (best-effort từ trang public; mặc định "Unknown (Pixabay contributor)")
- `source_url` (link trang ảnh Pixabay)
- `license_note` (Pixabay Content License — free for commercial use)
- `preview_url` (chỉ khi là HTTPS an toàn)
- `crawled_at` (timestamp crawl)

Quy tắc crawl (BẮT BUỘC):

- **Tôn trọng `robots.txt`** trước mỗi request (đọc được + cho phép mới crawl).
- **Rate-limit:** nghỉ ~1.5s giữa 2 request → không burst.
- **Chỉ trang public** — không login, không CAPTCHA, không endpoint riêng tư, không mass-scrape.
- **Bị chặn / không đọc được robots / lỗi mạng → dừng êm** (`status="blocked"`), không raise.

> Trong môi trường chặn egress (CI), helper trả `blocked`/`no_candidates` ngay và
> **giữ nguyên OG fallback/placeholder** — việc tạo bài **không bao giờ fail**.

## 2. Xác nhận thủ công (manual confirmation)

`suggest` **chỉ gợi ý** — không tải, không sửa cover. Muốn dùng 1 ảnh phải **người
duyệt thủ công** rồi chạy `confirm` với cả hai cờ xác nhận:

```bash
# 1) Gợi ý (ghi data/pixabay-suggestions/<slug>.json)
python3 scripts/pixabay_image_assist.py suggest --slug my-post \
    --title "Tiêu đề bài" --keyword "seo onpage" --category "Công nghệ" --tags "seo,onpage"

# 2) Sau khi xem & duyệt ứng viên [i]: tải đúng ảnh đó
python3 scripts/pixabay_image_assist.py confirm --slug my-post --index 0 \
    --yes --commercial-ok --article content/posting/my-post.md
```

- Thiếu `--yes` (đã duyệt) **hoặc** `--commercial-ok` (đã kiểm tra quyền dùng thương mại)
  → **từ chối tải** (exit 2).
- Chỉ ảnh **đã xác nhận** được tải về. Tải xong ghi **sidecar metadata** + chèn
  frontmatter `image_*` vào bài (nếu truyền `--article`).

## 3. Vì sao ảnh bên thứ ba KHÔNG đóng watermark

Ảnh Pixabay là **của bên thứ ba** → đóng watermark sở hữu `…_seomoney.org` lên là
**sai bản quyền**. Vì vậy ảnh Pixabay lưu vào `static/img/third-party/pixabay/`, **nằm
ngoài owned-roots** (`static/img/posting/`, `static/img/owned/`) của
`scripts/watermark_blog_images.py` → watermarker **bỏ qua tự động**.

`assert_third_party()` chặn cứng việc lỡ ghi ảnh Pixabay vào thư mục owned/watermark.

## 4. Tích hợp luồng tạo bài

- **Bài-by-prompt (`content_creator.py`):** sau khi sinh mỗi bài, nếu `auto_image` bật
  (mặc định) thì **gợi ý** ảnh Pixabay vào `data/pixabay-suggestions/<slug>.json`
  (không tải, không sửa cover). Best-effort — lỗi/chặn → bỏ qua, bài vẫn ra bình thường.
- **Shortcut-based (`bb`, `baomoi`, …):** sau khi soạn bài + có slug, chạy `suggest`,
  trình 3–5 ứng viên cho người duyệt; chỉ `confirm` khi được duyệt. Không thay đổi
  approval-gate của shortcut.

## 5. Opt-out

Tắt gợi ý ảnh cho luồng tạo bài:

```bash
python3 scripts/content_creator.py --topic "..." --no-auto-image
```

Hoặc trong job-file JSON:

```json
{ "topic": "...", "auto_image": false }
```

## 6. Metadata bắt buộc (sidecar + frontmatter)

Mỗi ảnh đã dùng **phải** kèm các field (sidecar `*.source.json` cạnh ảnh, và frontmatter
`[extra]` của bài). Thiếu bất kỳ field nào → `confirm` từ chối, không tải:

| Field | Ý nghĩa |
|-------|---------|
| `image_source` | luôn `"Pixabay"` |
| `image_author` | tác giả (hoặc "Unknown (Pixabay contributor)") |
| `image_url` | link trang ảnh Pixabay |
| `image_license_note` | ghi chú giấy phép/nguồn |
| `image_downloaded_at` | thời điểm tải |
| `image_verified_manually` | `true` — người đã duyệt |
| `image_commercial_use_checked` | `true` — đã kiểm tra quyền thương mại |

## 7. Giới hạn pháp lý / AdSense (guard)

- **Không** dùng nhãn hiệu/logo/brand dễ nhận diện làm cover trừ khi **người duyệt xác
  nhận context-safe** — ứng viên có dấu hiệu brand bị đánh dấu `needs_brand_review`.
- **Không** gợi ý/dùng ảnh adult, bạo lực, thù ghét, gây hiểu lầm, rủi ro y tế/tài chính,
  nhạy cảm — query/ứng viên khớp danh sách unsafe bị loại.
- **Không** ngụ ý hợp tác/đồng bảo trợ với thương hiệu nào.
- **Không** tuyên bố "free = không rủi ro"; luôn lưu metadata nguồn. Attribution có thể
  không bắt buộc theo giấy phép, nhưng **metadata nguồn nội bộ là bắt buộc**.

## 8. Kiểm thử

```bash
python3 -m unittest scripts.test_pixabay_image_assist -v
```

Bao phủ: crawl-blocked fallback · no-candidate fallback · metadata bắt buộc trước khi
dùng · ảnh đã confirm tồn tại sau build · ảnh Pixabay third-party không bị watermark ·
guard legal/AdSense (unsafe loại, brand đánh dấu).
