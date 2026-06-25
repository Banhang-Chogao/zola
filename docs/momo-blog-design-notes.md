# Blog MoMo — Ghi chú thiết kế (UI/UX reference)

> **Mục đích:** Lưu trữ tham khảo giao diện **Blog MoMo** (blog.momo.vn) làm một mẫu
> thiết kế blog/tin tức. Đây là tài liệu **tham khảo nội bộ**, KHÔNG sao chép nguyên
> bản quyền/thương hiệu MoMo vào sản phẩm.

## Metadata quan sát

| Mục | Giá trị |
|-----|---------|
| **Nguồn** | Blog MoMo ("Blog MoMo") |
| **Ngày ghi chú** | 2026-06-25 |
| **Chất liệu phân tích** | 2 ảnh chụp màn hình do người dùng cung cấp (desktop) |
| **Phạm vi ảnh 1** | Trang danh sách / trang chủ blog — phần đầu trang (header → hero → grid 3 cột) |
| **Phạm vi ảnh 2** | Trang chi tiết bài viết — phần đầu (breadcrumb → hero → tiêu đề → sapo) |
| **Độ phủ** | Chỉ phần **trên màn hình đầu tiên** của mỗi trang; footer, phân trang, thân bài, mobile **chưa quan sát được** (xem §9) |
| **Màu sắc** | Ước lượng bằng mắt từ screenshot — hex là **xấp xỉ**, không phải đo pixel chính xác |

---

## 1. Tổng quan & triết lý thiết kế

Phong cách **sạch, sáng, nhiều khoảng trắng (whitespace), bo góc mềm**. Toàn bộ giao diện
đặt trên nền trắng với **hoa văn watermark chìm rất nhạt** (line-art các khối/chữ cái cỡ
lớn — gợi logo "M"/"o" của MoMo) để tạo texture mà không gây rối. Điểm nhấn thương hiệu là
**màu hồng/magenta đặc trưng của MoMo**, dùng **rất tiết chế** (chỉ cho trạng thái active),
kết hợp **teal/cyan** cho nhãn chuyên mục. Typography **sans-serif đậm, tiêu đề to và nặng**,
tạo cảm giác hiện đại, dứt khoát.

Nguyên tắc nổi bật nhất: **mọi thumbnail/hero đều có một "thẻ tiêu đề" nền trắng bo góc
overlay lên ảnh** → vừa nhận diện thương hiệu, vừa đảm bảo tiêu đề luôn đọc được dù ảnh nền
phức tạp.

---

## 2. Cấu trúc layout — Trang danh sách (listing / home)

Thứ tự từ trên xuống:

1. **Tiêu đề trang** — chữ **"Blog MoMo"** cỡ rất lớn, **bold/extra-bold**, màu gần đen,
   căn trái. Đóng vai trò "site title" của khu vực blog.

2. **Thanh điều hướng chuyên mục (category tab bar)** — dải tab ngang ngay dưới tiêu đề:
   - Các tab quan sát được: **Mới nhất** (đang active) · Du lịch · Tài Chính - Bảo Hiểm ·
     Game - App · Đời sống · Ăn uống · Chọn MoMo · Mua sắm · Bảo mật · Chứ… (bị cắt).
   - Tab **active ("Mới nhất")**: chữ màu **hồng/magenta MoMo** + **gạch chân** (underline
     indicator) màu hồng bên dưới.
   - Tab inactive: chữ xám đậm/đen, weight thường.
   - **Nút mũi tên tròn "→"** ở mép phải → thanh tab **cuộn ngang được** (carousel), gợi ý
     còn chuyên mục khác (tab cuối "Chứ…" bị cắt cụt xác nhận điều này).

3. **Hero / bài nổi bật (featured)** — bố cục **2 cột**:
   - **Cột trái:** ảnh lớn bo góc, có **thẻ caption nền trắng overlay** ở góc dưới-trái
     (icon nhỏ màu đỏ/cam + tiêu đề ngắn 2 dòng in đậm: *"Chi phí mổ trĩ khi có Bảo hiểm Y tế"*).
   - **Cột phải:** nhãn chuyên mục **"Tài Chính - Bảo Hiểm"** màu **teal** (eyebrow) →
     **tiêu đề lớn in đậm** gần đen (*"Chi phí mổ trĩ có bảo hiểm y tế là bao nhiêu? Mức
     hưởng chi tiết"*) → **đoạn mô tả/sapo** màu xám 2 dòng.

4. **Lưới bài viết (grid)** — **3 cột** card bên dưới hero, mỗi card là **ảnh bo góc + thẻ
   caption trắng overlay góc dưới-trái** (icon nhỏ + tiêu đề đậm). Quan sát 3 card:
   *"Khám tổng quát có được Bảo hiểm Y tế chi trả không?"*, *"Chi phí cắt amidan khi có Bảo
   hiểm Y tế"*, *"Hướng dẫn thủ tục khám BHYT trái tuyến"*.

5. **Widget nổi (floating)** — bong bóng chat **"Zalo"** (hình tròn xanh) góc dưới-phải.

**Tóm tắt phân cấp:** `Site title → Category tabs (scroll ngang) → 1 Hero 2-cột → Grid 3-up`.

---

## 3. Cách hiển thị danh sách bài viết

- **Mô hình "1 nổi bật + lưới":** một bài hero cỡ lớn (ảnh trái / chữ phải) đứng trên, theo
  sau là lưới các bài thứ cấp đồng kích thước.
- **Card thứ cấp** = thumbnail bo góc + **thẻ tiêu đề trắng** overlay (không hiển thị riêng
  meta như ngày/tác giả ở mức card — tối giản, để ảnh + tiêu đề kể chuyện).
- **Nhãn chuyên mục** chỉ xuất hiện ở bài hero (eyebrow teal); các card lưới dựa vào thẻ
  tiêu đề trắng.
- **Đặc trưng "title-plate":** thẻ tiêu đề trắng (nền trắng, bo góc, đổ bóng nhẹ, có **icon
  marker nhỏ màu đỏ/cam** bên trái) **dường như được ghép sẵn vào ảnh featured** — vì xuất
  hiện y hệt trên cả thumbnail listing lẫn hero trang chi tiết. Đây là pattern nhận diện
  thương hiệu rất nhất quán.

---

## 4. Cấu trúc layout — Trang chi tiết bài viết

Thứ tự từ trên xuống (cột nội dung **căn giữa, bề rộng giới hạn** cho dễ đọc):

1. **Breadcrumb** — `🏠 (home) > Blog > Tài Chính - Bảo Hiểm > [tiêu đề bài]`, chữ xám,
   dấu phân tách kiểu chevron `>`. Thể hiện phân cấp Home → Blog → Chuyên mục → Bài.

2. **Hero banner** — ảnh lớn **bo góc** (hơi phủ sáng/nhạt), mang **thẻ caption trắng**
   overlay (giống listing) — tính nhất quán cao giữa thumbnail và trang bài.

3. **Hàng meta** (dưới ảnh):
   - **Trái:** nhãn chuyên mục **"Tài Chính - Bảo Hiểm"** (teal) + **"8 phút đọc"**
     (reading-time) xếp chồng.
   - **Phải:** nút **"Chia sẻ →"** dạng **pill bo tròn viền mảnh** (label + icon mũi tên).

4. **Tiêu đề bài** — heading **rất lớn, bold**, gần đen (*"Khám tổng quát hết bao nhiêu
   tiền? Có được bảo hiểm y tế chi trả không?"*).

5. **Sapo / standfirst** — đoạn dẫn **in nghiêng (italic), màu xám** (*"Cập nhật chi phí
   khám tổng quát hết bao nhiêu tiền…"*).

6. **Đường kẻ ngang mảnh (divider)** ngăn phần dẫn với thân bài (thân bài nằm dưới — ngoài
   khung ảnh quan sát).

---

## 5. Màu sắc (palette — hex xấp xỉ)

| Vai trò | Mô tả | Hex ước lượng |
|---------|-------|---------------|
| **Primary / brand** | Hồng–magenta MoMo (tab active + underline) | `#A50064` – `#D8217F` |
| **Secondary / accent** | Teal–cyan (nhãn chuyên mục "eyebrow") | `#00AEC7` ± |
| **Text — heading** | Gần đen, tương phản cao | `#1A1A1A` ± |
| **Text — body/sapo** | Xám trung tính | `#6E6E73` ± |
| **Nền trang** | Trắng / off-white | `#FFFFFF` |
| **Watermark trang trí** | Line-art xám rất nhạt (chữ/khối cỡ lớn) | `#F0F0F2` ± |
| **Thẻ caption** | Nền trắng + bóng nhẹ + icon marker đỏ/cam | `#FFFFFF` / marker ~`#E8552D` |

> ⚠️ Hex là **ước lượng bằng mắt** từ screenshot. MoMo nổi tiếng với hồng thương hiệu
> quanh `#A50064`; cần xác minh bằng color-picker trên trang thật nếu muốn chính xác tuyệt đối.

---

## 6. Typography

- **Họ chữ:** sans-serif xuyên suốt, dáng geometric/humanist (gợi cảm giác như
  Montserrat / Avenir / SF Pro — **chưa xác nhận tên font cụ thể**, chỉ là so sánh trực quan).
- **Tiêu đề ("Blog MoMo", title bài):** weight **rất nặng (bold/extra-bold ~700–800)**,
  cỡ lớn, tracking hơi chặt → hiện đại, mạnh.
- **Nhãn chuyên mục (eyebrow):** nhỏ, semibold, **màu teal** — phân biệt rõ với tiêu đề.
- **Sapo:** trang chi tiết dùng **italic xám**; trên listing là **regular xám**.
- **Thẻ caption trên ảnh:** tiêu đề **bold, gần đen**, 1–2 dòng.
- **Phong cách chữ tổng thể:** ưu tiên độ tương phản (đen đậm trên trắng) + khoảng trắng
  rộng → dễ đọc, "thoáng".

---

## 7. Thành phần UX nổi bật

- **Category tab bar cuộn ngang** có **nút mũi tên tròn** affordance + **underline** đánh dấu
  tab active (màu brand).
- **Color-coding chuyên mục:** nhãn eyebrow màu teal làm điểm tựa thị giác phân loại.
- **Title-plate trắng overlay ảnh** (signature) — đảm bảo tiêu đề luôn đọc được trên mọi ảnh.
- **Breadcrumb** đầy đủ phân cấp ở trang chi tiết.
- **Reading-time** ("8 phút đọc") — tín hiệu UX thân thiện, đặt cạnh chuyên mục.
- **Nút "Chia sẻ"** dạng pill bo tròn, có icon — gọn, dễ thấy.
- **Sapo italic** tách bạch phần dẫn với thân bài.
- **Bo góc mềm + đổ bóng nhẹ** nhất quán (card, ảnh, nút).
- **Floating chat (Zalo)** — kênh liên hệ nổi góc phải.

---

## 8. Pattern đặc trưng có thể tái sử dụng

1. **Hero "1 nổi bật + grid 3-up"** cho trang danh sách — phân cấp nội dung rõ ràng.
2. **Title-plate trắng overlay trên thumbnail** — vừa branding vừa giải bài toán tiêu đề
   khó đọc trên ảnh nền.
3. **Eyebrow chuyên mục màu accent** đặt **trên** tiêu đề (thay vì badge rời).
4. **Tab chuyên mục cuộn ngang + arrow** thay cho dropdown — gọn cho nhiều chuyên mục.
5. **Meta tối giản ở trang chi tiết:** chuyên mục + reading-time + share, không nhồi nhét.
6. **Nền trắng + watermark line-art chìm** — thêm texture thương hiệu mà không phá khoảng trắng.

---

## 9. Những gì CHƯA quan sát được (giới hạn của tài liệu)

Hai screenshot chỉ phủ **phần trên** của trang. **Chưa** có dữ liệu về:

- **Footer** (cấu trúc, link, social, bản quyền).
- **Phân trang / "Xem thêm" / infinite scroll** ở trang danh sách.
- **Ô tìm kiếm (search)** — không thấy trong vùng ảnh.
- **Danh sách chuyên mục đầy đủ** (vài tab bị cắt: "Chứ…").
- **Thân bài chi tiết** (TOC, heading trong bài, ảnh inline, CTA, related posts, comment).
- **Sidebar** (nếu có) ở trang chi tiết.
- **Giao diện responsive / mobile.**
- **Trạng thái hover/focus, animation, micro-interaction.**
- **Tên font chính xác & mã màu đo pixel.**

> Khi có thêm screenshot (footer, mobile, thân bài) hoặc HTML source, có thể bổ sung các
> mục trên để hoàn thiện tài liệu tham khảo.

---

## 10. Gợi ý áp dụng (tham khảo — KHÔNG bắt buộc)

Một vài ý có thể cân nhắc cho blog Zola (không thực hiện ở đây, chỉ là gợi ý reference):

- Thử pattern **hero 1 bài + grid 3-up** cho trang section/taxonomy.
- Cân nhắc **eyebrow chuyên mục màu accent** trên tiêu đề card để tăng nhận diện phân loại.
- **Reading-time + breadcrumb + share pill** ở trang bài là các thành phần UX nhẹ, dễ thêm.
- Giữ **nền sáng + accent dùng tiết chế** để nội dung "thở".

*(Lưu ý: chỉ áp dụng màu/branding riêng của SEOMONEY — không dùng lại bộ nhận diện MoMo.)*
