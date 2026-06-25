# Nokia Blog — Ghi chú thiết kế tham khảo

> **Mục đích:** Lưu trữ phong cách thiết kế của **Nokia Blog** (`https://www.nokia.com/blog/`)
> làm tài liệu tham khảo cho blog SEOMONEY — một hướng thẩm mỹ **corporate-tech tối giản**,
> khác với phong cách Apple. Tương tự cách lưu reference cho theme Kodama.
>
> ⚠️ **Đây là TÀI LIỆU THAM KHẢO (reference-only).** KHÔNG áp dụng vào template/CSS/UI
> hiện tại của dự án. Không có file `templates/**`, `sass/**`, `static/**` nào bị thay đổi
> khi tạo ghi chú này.

## Phương pháp & nguồn

- `https://www.nokia.com/blog/` trả về **HTTP 403** khi fetch tự động (bot-protection của
  site doanh nghiệp), nên các chi tiết **bố cục** dưới đây tổng hợp từ **quan sát trực tiếp**
  của người dùng (mô tả trong yêu cầu) cộng với **brand research đã được kiểm chứng** về hệ
  thống nhận diện Nokia.
- Các giá trị thuộc **bộ nhận diện thương hiệu Nokia** (màu, typeface, design language) là
  **dữ kiện đã xác minh** qua nguồn công khai — xem mục [Nguồn tham khảo](#nguồn-tham-khảo).
- Các giá trị **hex chính xác của riêng trang blog** nên được xác nhận lại bằng DevTools nếu
  cần token màu tuyệt đối; phần dưới ghi rõ đâu là **brand token đã verify** và đâu là **mô tả
  định tính** từ quan sát.

---

## 1. Tổng quan thẩm mỹ

Nokia Blog đi theo ngôn ngữ thiết kế **Nokia Pure** — minimalist, modular, dựa trên **grid**,
tạo cảm giác **digital-first, sạch sẽ, nhiều khoảng trắng**. Tinh thần chủ đạo:

| Đặc trưng | Mô tả |
|-----------|-------|
| **Tông cảm** | Corporate-tech, chuyên nghiệp, tin cậy; không màu mè, không skeuomorphism |
| **Bố cục** | Grid nghiêm ngặt, căn lề rõ ràng, module hoá (card lặp lại) |
| **Khoảng trắng** | Rất nhiều — để nội dung "thở", tách biệt section bằng padding lớn |
| **Màu** | Trung tính (trắng) làm nền, **xanh đen** cho chữ/hero, **xanh sáng** làm accent |
| **Tương tác** | Tinh tế — hover nhẹ, motion mượt (logo/identity tối ưu cho motion) |

---

## 2. Hero Section

- **Tiêu đề lớn (H1)**: chữ cỡ rất lớn, weight đậm, đặt trên nền sáng hoặc nền xanh đậm.
- **Mô tả/subtitle**: 1–2 câu dẫn nhập ngắn, cỡ chữ vừa, màu nhạt hơn tiêu đề (giảm tương phản
  để phân cấp thị giác).
- **Bố cục**: căn trái hoặc giữa, **nhiều padding trên/dưới**, tách hẳn khỏi grid bài viết phía dưới.
- **Không** dùng ảnh nền rối; nếu có nền thì là **màu phẳng** (flat color) hoặc gradient xanh
  nhẹ — đúng tinh thần "bright secondary hues để build gradient" của brand Nokia.

```
┌─────────────────────────────────────────────┐
│                                             │
│   Tiêu đề lớn (H1, đậm)                      │   ← nhiều whitespace
│   Mô tả ngắn 1–2 dòng, màu nhạt hơn         │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 3. Card Grid Layout (3 cột)

Khu vực bài viết là **lưới 3 cột** (desktop), mỗi item là một **card** đồng nhất:

| Thành phần card | Ghi chú |
|-----------------|---------|
| **Ảnh (thumbnail)** | Trên cùng, tỉ lệ đồng nhất (thường 16:9 hoặc 3:2), bo góc nhẹ hoặc vuông |
| **Metadata** | Category / chủ đề / ngày — chữ nhỏ, thường in hoa nhẹ hoặc màu xanh accent |
| **Tiêu đề bài** | Đậm, 2–3 dòng, là phần nổi bật nhất của card |
| **Mô tả ngắn** *(tuỳ chọn)* | Đoạn trích vài dòng, màu xám/đen nhạt |
| **CTA ngầm** | Cả card là link; hover làm nổi tiêu đề hoặc ảnh (zoom/độ sáng nhẹ) |

**Hành vi responsive (suy luận theo Nokia Pure grid + chuẩn web hiện đại):**

- Desktop: **3 cột**
- Tablet: **2 cột**
- Mobile: **1 cột**
- Khoảng cách giữa card (gap) đều nhau, lề trái/phải canh theo container chính.

```
┌────────┐  ┌────────┐  ┌────────┐
│ [ảnh]  │  │ [ảnh]  │  │ [ảnh]  │
│ meta   │  │ meta   │  │ meta   │
│ Tiêu đề│  │ Tiêu đề│  │ Tiêu đề│
└────────┘  └────────┘  └────────┘
┌────────┐  ┌────────┐  ┌────────┐
│  ...   │  │  ...   │  │  ...   │
└────────┘  └────────┘  └────────┘
```

---

## 4. Filter / Category Tabs

Phía trên grid có **hàng tab lọc/phân loại** theo nhóm đối tượng. Các nhãn tab quan sát được:

1. **AI and cloud providers**
2. **Mission-critical enterprises**
3. **Telecommunication providers**

Đặc điểm tab:

- Dạng **pill / underline tab** nằm ngang, tab đang active được làm nổi (gạch chân, đổi màu,
  hoặc nền đậm hơn).
- Bấm tab → **lọc** danh sách card hiển thị theo nhóm tương ứng (client-side filter, không
  reload toàn trang).
- Nhãn rõ ràng, hướng **đối tượng/khách hàng** (audience-based) thay vì chỉ phân loại chủ đề
  chung chung — đây là điểm đáng học cho blog định hướng theo nhóm độc giả.

---

## 5. Bảng màu (Color Palette)

> **Đã verify (brand token Nokia):** trắng + bright blue + classic blue, cộng các sắc xanh
> sáng phụ để tạo gradient/highlight. Hex riêng của trang blog nên confirm bằng DevTools nếu
> cần token tuyệt đối.

| Vai trò | Màu | Giá trị | Trạng thái |
|---------|-----|---------|-----------|
| **Nền chính** | Trắng | `#FFFFFF` (≈) | Quan sát + chuẩn brand |
| **Chữ/Hero (xanh đen)** | Xanh navy rất đậm | mô tả định tính — gần "classic blue" của Nokia | Quan sát |
| **Accent / link** | Bright blue (Moroccan Blue) | `#005AFF` | ✅ Brand token đã verify |
| **Chữ phụ / metadata** | Xám trung tính | `#5–6 mức xám` | Quan sát |
| **Đường kẻ / viền** | Xám rất nhạt | `#E…` (≈) | Quan sát |

**Nguyên tắc dùng màu:**

- Nền trắng chiếm đa số → tạo độ sạch và khoảng trắng.
- **Xanh đậm** chỉ dùng cho điểm nhấn lớn (hero, tiêu đề, vùng nhấn) — không lạm dụng.
- **Xanh sáng `#005AFF`** dành cho **link, tab active, CTA, accent** — điểm nhận diện thương hiệu.
- Tương phản cao giữa chữ đậm và nền trắng → dễ đọc, đạt chuẩn a11y.

---

## 6. Typography

- **Typeface thương hiệu:** **Nokia Pure** (Dalton Maag, ra mắt 2011) — sans-serif hình học,
  thiết kế cho **digital/mobile**, 3 weight cơ bản: *light · regular · bold*. (Web public có
  thể fallback sang sans-serif hệ thống nếu font brand không nhúng.)
- **Phân cấp rõ ràng (type scale):**
  - **H1 (hero):** rất lớn, bold → tạo điểm neo thị giác.
  - **H2 / tiêu đề card:** lớn vừa, bold/semibold.
  - **Body / mô tả:** regular, line-height thoáng để dễ đọc.
  - **Metadata:** nhỏ, light hoặc uppercase nhẹ, màu nhạt/xanh accent.
- **Tinh thần:** ít kiểu chữ, nhiều weight — phân cấp bằng **cỡ + độ đậm + màu**, không bằng
  nhiều font họ khác nhau. Chữ "kể chuyện rõ ràng", không trang trí.

---

## 7. Spacing & Whitespace

- **Khoảng trắng là nhân vật chính:** padding section lớn, gap giữa card đều, lề container rộng.
- **Nhịp dọc (vertical rhythm) nhất quán:** mỗi section cách nhau bằng padding lớn cố định.
- **Căn lề theo grid:** mọi phần tử bám cùng một lưới → cảm giác ngăn nắp, "kỹ thuật".
- **Card không bị nhồi nhét:** trong card cũng có padding nội bộ, ảnh–meta–tiêu đề tách bằng
  khoảng cách đều.

---

## 8. Navigation & Footer (tham khảo chung)

> Phần này mang tính khái quát theo chuẩn site doanh nghiệp Nokia (không phải trọng tâm yêu cầu).

- **Header/nav:** thanh điều hướng trên cùng, logo Nokia (logo 2023 — nét mảnh, hình học,
  "asks the eye to make missing connections"), menu chính tối giản, có thể có nền trong suốt/
  trắng và đổi trạng thái khi cuộn.
- **Footer:** nhiều cột link (sản phẩm, giải pháp, công ty, pháp lý), nền tối hoặc trắng, mật độ
  chữ cao hơn nhưng vẫn căn grid.

---

## 9. Bản đồ tham khảo → Zola *(chỉ là ghi chú, KHÔNG áp dụng)*

> Phần này phác hoạ **cách phong cách trên có thể ánh xạ** sang một site Zola **nếu** sau này
> muốn tham khảo — **không** phải code đang được thêm vào dự án. Mọi đoạn dưới chỉ minh hoạ.

| Yếu tố Nokia | Ý tưởng ánh xạ Zola (tham khảo) |
|--------------|-------------------------------|
| Hero title + mô tả | Block hero trong `index.html` / section template, lấy `section.title` + `section.description` |
| Grid 3 cột | `display: grid; grid-template-columns: repeat(3, 1fr); gap` (auto-fit cho responsive) |
| Card bài viết | Macro card lặp qua `paginator.pages` / `section.pages`: ảnh `page.extra.cover` + `page.title` + `page.date` |
| Tab lọc theo nhóm | Map sang **taxonomy** (vd `audiences`/`categories`) + filter client-side JS |
| Accent `#005AFF` | Một biến SCSS accent riêng (vd `$accent`) — chỉ dùng cho link/tab active/CTA |
| Nhiều whitespace | Tăng `padding` section + `gap` grid trong bảng spacing |

```css
/* MINH HOẠ THAM KHẢO — không thêm vào sass/ của dự án */
.nokia-ref-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); /* 3→2→1 cột */
  gap: 2rem;
}
```

---

## 10. Checklist rút gọn để tái hiện "phong cách Nokia"

- [ ] Nền **trắng** chủ đạo, **nhiều khoảng trắng**.
- [ ] **Hero**: H1 rất lớn + mô tả ngắn, padding lớn.
- [ ] **Grid 3 cột** card đồng nhất (ảnh → meta → tiêu đề), responsive 3→2→1.
- [ ] **Tab lọc theo nhóm độc giả**, tab active nổi bật, lọc không reload.
- [ ] Palette: trắng + **xanh đen** (chữ/hero) + **xanh sáng `#005AFF`** (accent/link).
- [ ] Typography: 1 họ sans-serif, phân cấp bằng **cỡ + weight + màu**, line-height thoáng.
- [ ] Tương tác tinh tế: hover nhẹ, motion mượt.

---

## Nguồn tham khảo

- [Nokia rebrand 2023 — Design Week](https://www.designweek.co.uk/issues/27-february-3-march-2023/nokia-rebrand-new-logo-lippincott/) — rebrand bởi Lippincott, ra mắt tại MWC 2023.
- [Nokia logo 2023 — It's Nice That](https://www.itsnicethat.com/news/nokia-logo-2023-graphic-design-270223) — logo mới "more digital", bỏ deep blue & letterform vuông cũ.
- [Nokia Brand Color Codes — BrandColorCode](https://www.brandcolorcode.com/nokia) & [SchemeColor](https://www.schemecolor.com/nokia.php) — palette trắng + bright/classic blue; Moroccan Blue `#005AFF`.
- [The Nokia Design System (Nokia Pure) — DesignMonks](https://www.designmonks.co/blog/the-nokia-design-system-a-comprehensive-guide-to-nokia-pure) & [designsystem.nokia.com](https://designsystem.nokia.com/) — hệ thống minimalist, modular, grid-based.
- [Nokia Pure typeface — Wikipedia](https://en.wikipedia.org/wiki/Nokia_Pure) — Dalton Maag, 2011, weights light/regular/bold, thiết kế cho digital/mobile.
- Bố cục blog (hero, grid 3 cột, các tab lọc, màu, whitespace): **quan sát trực tiếp của người
  dùng** trên `https://www.nokia.com/blog/` (trang chặn fetch tự động — HTTP 403).

---

*Ghi chú tạo ngày 2026-06-25. Tài liệu reference-only — không ảnh hưởng template/CSS/build.*
