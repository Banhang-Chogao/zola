# CLAUDE.md — Quy tắc làm việc

## Quy tắc tối ưu hoá giao diện (CSS / Responsive)

Quy tắc bắt buộc, có hiệu lực với mọi yêu cầu liên quan đến CSS/UI/layout.

### 1. Phân tách phạm vi xử lý (Mobile ≠ Desktop)

Responsive (Mobile) và Desktop là **2 quy trình độc lập**.

- Khi user yêu cầu "tăng cường responsive", "tối ưu mobile", "sửa giao diện điện thoại":
  → **CHỈ** được phép thêm/sửa code bên trong `@media (max-width: 720px)`, `@media (max-width: 540px)`, `@media (max-width: 380px)`, hoặc các media query mobile khác.
  → **KHÔNG** được sửa selector global (không media query bao quanh).

- Khi user yêu cầu "sửa giao diện desktop", "layout máy tính":
  → **CHỈ** sửa selector global hoặc `@media (min-width: 721px)`.
  → **KHÔNG** đụng vào media query mobile.

### 2. Không thay đổi Desktop ngoài phạm vi

Tuyệt đối không sửa các thuộc tính CSS global hoặc layout đang chạy ổn định trên desktop nếu không có yêu cầu cụ thể.

Cấm các pattern sau khi không được yêu cầu:
- Sửa `html { ... }`, `body { ... }`, `*` selector
- Sửa `.container`, `.navbar` (selector trần không media query)
- Sửa thuộc tính `overflow`, `height`, `position`, `display` ở scope global

### 3. Ưu tiên ổn định scroll

Mọi thay đổi liên quan đến `height`, `overflow`, `position`, `max-width`, `100vh`, `100vw` PHẢI kiểm tra kỹ:

- **Cấm anti-pattern** `html, body { overflow-x: hidden }` (cả 2 cùng lúc → khoá scroll iOS Safari + xung đột `position: sticky`).
- **Cấm** `overflow: hidden` ở scope global trên `body` mà không có scope mobile-only (`@media (max-width: 720px)`).
- **Cấm** `height: 100vh` trên `body`/`html` không cần thiết.
- **Cấm** `position: fixed` toàn màn hình mà không có override mobile-only.

Nếu cần sửa các thuộc tính trên → ưu tiên scope vào media query cụ thể, đảm bảo desktop scroll luôn tự nhiên.

### 4. Quy trình code khi sửa cả Desktop + Mobile

Khi user yêu cầu sửa cả 2:
- Chia code thành **2 block tách biệt rõ ràng**, có comment header phân định.
- Mỗi block tự đóng tự mở, không cross-dependency.

Ví dụ:
```scss
/* ===== DESKTOP (global) ===== */
.navbar {
  background: #111;
}

/* ===== MOBILE (≤ 720px) ===== */
@media (max-width: 720px) {
  .navbar {
    background: rgba(17, 17, 17, 0.88);
    backdrop-filter: blur(14px);
  }
}
```

### 5. Test plan bắt buộc trước khi PR

Trước khi tạo PR cho thay đổi CSS:
- Mental check: thay đổi này có ảnh hưởng desktop scroll không?
- Mental check: thay đổi này có ảnh hưởng mobile menu open/close không?
- Nếu sửa `overflow`, `height`, `position` → ghi rõ trong PR description vì sao thay đổi an toàn.

## Quy tắc hiển thị thời gian (Timezone & Date format)

Áp dụng cho MỌI nơi hiển thị ngày/giờ trên blog (templates Tera, static JS,
script Python sinh nội dung public).

### 1. Timezone bắt buộc: GMT+7 (Asia/Ho_Chi_Minh)

- Mọi filter `date` trong Tera template PHẢI có `timezone="Asia/Ho_Chi_Minh"`.
  Ví dụ: `{{ page.date | date(format="%d/%m/%Y", timezone="Asia/Ho_Chi_Minh") }}`
- JS hiển thị giờ dùng `toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", ... })`.
- Script Python format datetime công khai → `ZoneInfo("Asia/Ho_Chi_Minh")`
  (chuẩn stdlib `zoneinfo`).

### 2. Định dạng ngày tháng năm: kiểu Việt Nam

- **Ngày**: `dd/mm/yyyy` (ví dụ `15/06/2026`). KHÔNG dùng `Jun 15, 2026`,
  `June 15, 2026`, hay `2026-06-15` cho display.
- **Giờ kèm ngày**: `HH:MM dd/mm/yyyy` (ví dụ `23:39 15/06/2026`).
- **Tera format string**: `%d/%m/%Y` (date) hoặc `%H:%M %d/%m/%Y` (datetime).
- **JS**: `toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })`.
- **ISO 8601** (`2026-06-15T...`) chỉ dùng cho `datetime` attribute (machine
  readable), `data-date` JS sort, hoặc frontmatter — KHÔNG bao giờ là text
  hiển thị cuối cùng.

### 3. Quy trình khi thêm code mới có hiển thị ngày/giờ

- Mental check: code mới này có hiển thị thời gian trên blog không?
- Nếu có → áp dụng 2 rule trên trước khi commit.
- Sửa code cũ có English format (`%b`, `%B`, `Jan/Feb/...`) → convert sang VN.

## Quy tắc Git / Pull Request

Bắt buộc với MỌI task có thay đổi code (đã commit + push).

- Làm xong BẤT KỲ việc gì → **LUÔN mở Pull Request** về `main` cho branch
  vừa làm. Không để thay đổi nằm im trên feature branch mà thiếu PR.
- Mỗi PR phải có tiêu đề rõ ràng + mô tả tóm tắt thay đổi và cách verify.
- Nếu task đã có PR mở sẵn cho branch đó → push thêm commit vào branch, không
  cần tạo PR trùng.
