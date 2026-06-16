# CLAUDE.md — Quy tắc làm việc

## Quy tắc Deploy & Production (MỚI NHẤT — ghi đè TẤT CẢ rule deploy/auto-merge trước đó)

> ⚠️ **Rule này là MỚI NHẤT (16/06/2026), hiệu lực CAO NHẤT.** Nó **ghi đè hoàn toàn** mọi rule deploy cũ: "rule 16:00", "TẠM NGƯNG QUYỀN AUTO-MERGE", và mọi câu "KHÔNG auto-merge" rải rác trong `shortcuts.md` (§4.5, §4.6, các loop `morning` / `seo10` / `gg` / `prm`...). Khi mâu thuẫn → LẤY rule này.

### 1. Auto hết — không thao tác tay

Để tiết kiệm thời gian, MỌI thay đổi lên GitHub đều tự động, user KHÔNG phải làm tay:

- **Auto commit** — commit thẳng, message rõ ràng.
- **Auto merge** — tự merge vào `main`. KHÔNG đợi `manual #X`, KHÔNG gom batch, KHÔNG chờ 16:00.
- **Auto deploy** — merge vào `main` → workflow `deploy.yml` tự build & deploy lên production (GitHub Pages).

### 2. Điều kiện cho lên production (cả 3 PHẢI đạt)

1. **Commit/push thành công** (không lỗi git).
2. **QA checker approve** — `qa_check.py` (workflow `qa.yml`) pass; chỉ error/exit≠0 mới chặn, warning KHÔNG chặn.
3. **Build KHÔNG failed** — `deploy.yml` build xanh.

Đủ cả 3 → auto merge + auto deploy, KHÔNG hỏi lại.

### 3. Build failed → LẬP TỨC chạy `ff` / `ff9` (BẮT BUỘC, tự động)

> ⚠️ Rule sự kiện, hiệu lực cao nhất. **MỖI LẦN** có sự kiện bản build bị
> **failed** thì PHẢI **LẬP TỨC** chạy 1 trong 2 phím tắt để fix — KHÔNG hỏi,
> KHÔNG bỏ mặc, KHÔNG để build đỏ nằm im.

**Sự kiện kích hoạt** (bất kỳ cái nào):
- `deploy.yml` build đỏ (fail trên `main` hoặc PR).
- `qa.yml` / `qa_check.py` exit ≠ 0 (error chặn).
- Bất kỳ CI check nào của PR chuyển sang trạng thái `failure`.

**Hành động bắt buộc, ngay khi nhận sự kiện**:

- **`ff`** — Full Fix & Deploy (với Python lib picker).
- **`ff9`** — Smart Conflict Resolver (Python-powered) — ưu tiên khi lỗi do
  merge conflict.

**Quy tắc lặp ("fix cho bằng được")**: chạy `ff`/`ff9` → đợi build lại → nếu
VẪN failed thì re-diagnose và chạy lại, lặp tới khi build **xanh**. Một vòng
chưa xong không phải là dừng. Chỉ dừng khi build xanh, HOẶC lỗi thực sự ngoài
phạm vi (lúc đó báo lại chẩn đoán + chỗ kẹt, không im lặng).

Sau khi `ff` / `ff9` fix xong và build xanh → auto merge + auto deploy lên
production, KHÔNG cần `manual #X`.

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

## Quy tắc SEO QA cho mỗi bài blog (BẮT BUỘC)

Áp dụng cho MỌI lần viết hoặc sửa bài viết trong `content/` (đuôi `.md`,
không tính trang `_index`).

### 1. Luôn tối ưu SEO khi viết bài

Mỗi bài mới PHẢI có đủ tín hiệu SEO on-page trong front matter + nội dung:

- `title` (20–65 ký tự, chứa từ khoá chính ở nửa đầu).
- `description` (50–160 ký tự) — KHÔNG để Zola tự cắt summary.
- `[extra] seo_keyword = "..."` — khai báo từ khoá chính để chấm điểm chính xác.
- `[extra] thumbnail` (og:image), slug chữ-thường-nối-gạch-ngang không dấu.
- Từ khoá chính xuất hiện ở: title, đoạn mở đầu, ít nhất 1 heading H2.
- ≥ 2 heading H2, ≥ 3 tag, ≥ 1 internal link + ≥ 1 external link uy tín.
- Độ dài ≥ 600 từ, đoạn văn không quá dài (readability).

### 2. Hệ thống tự chấm điểm + lưu DB

Mỗi lần viết/sửa bài, hệ thống TỰ chấm SEO qua `scripts/seo_qa_checker.py`
(thang 100 điểm bám tiêu chí on-page của Google) và lưu điểm + lịch sử vào
**DB `data/seo-qa-scores.json`**. Việc này chạy tự động qua PostToolUse hook
(`scripts/seo_qa_hook.py`, cấu hình ở `.claude/settings.json`).

- Chấm thủ công 1 bài: `python3 scripts/seo_qa_checker.py content/<đường-dẫn>.md`
- Chấm lại toàn bộ: `python3 scripts/seo_qa_checker.py --all`
- Bài < 70 điểm → script exit code 2 (CI có thể dùng để chặn).

### 3. Trang Insights điểm SEO (về sau)

DB `data/seo-qa-scores.json` là nguồn dữ liệu để dựng trang Insights "điểm SEO
của blog" sau này. KHÔNG xoá file này; mỗi lần chấm chỉ append thêm mốc lịch sử
(`history`, giữ tối đa 20 mốc/bài).

## Quy tắc Category (BẮT BUỘC)

- Category **"Tất cả"** là category mặc định của MỌI bài viết (slug `tat-ca`,
  URL `/categories/tat-ca/`). Menu "Tất cả bài viết" trỏ tới URL này.
- Mỗi bài viết PHẢI có `"Tất cả"` đứng ĐẦU mảng `categories`, kèm theo các
  category chuyên mục khác (nếu có) mà người viết chọn. Ví dụ:
  - Bài thường: `categories = ["Tất cả"]`
  - Bài có chuyên mục: `categories = ["Tất cả", "Du lịch"]`,
    `["Tất cả", "Banking"]`, `["Tất cả", "Công nghệ"]`…
- KHÔNG dùng lại category cũ tên `"Posting"` (đã đổi thành `"Tất cả"`).
- Giá trị phải khớp CHÍNH XÁC chuỗi `"Tất cả"` (chữ "c" thường) để Zola gom
  đúng một taxonomy term, tránh lỗi trùng slug.
- **Bài viết qua phím tắt `bb`** (nhánh `baochi`, `content/baochi/`) PHẢI có
  thêm category mặc định `"Báo chí"` (slug `bao-chi`) — đứng ngay sau `"Tất cả"`,
  trước category theo content. Ví dụ: `["Tất cả", "Báo chí", "Banking"]`.
- Danh sách category hợp lệ cho editor/CMS khai báo trong `categories.json`.

## Quy tắc Đăng bài hẹn giờ (Scheduled publish — phím tắt `bb9 <topic>`)

Cú pháp BẮT BUỘC: **`bb9 <topic>`** — luôn kèm chủ đề. `bb9` tự **sáng tác bài
mới** từ topic (khác `bb` là dán báo chí có sẵn). Gõ `bb9` trống → hỏi lại topic.
Cho phép viết bài bất cứ lúc nào nhưng đăng tự động sau N ngày (mặc định **n+3**,
vào **buổi tối 20:00 GMT+7**), chỉ lên production khi vượt qua QA.

- Bài hẹn giờ lưu dạng **draft**: frontmatter có `draft = true` +
  `[extra] publish_at = "<ISO8601 +07:00>"`. Zola build bỏ qua draft → KHÔNG lên
  site cho tới khi tới hạn (kể cả khi draft đã nằm trên `main`).
- `date` của bài hẹn = ngày dự kiến đăng (n+3) để hiển thị đúng ngày.
- Workflow `scheduled-publish.yml` (cron 20:00 GMT+7) chạy `scripts/scheduled_publish.py`:
  bài nào `publish_at <= now` → flip `draft=false`, set `date`, xoá `publish_at`.
  - **CHỈ** commit + push lên `main` (→ deploy) NẾU **PASS QA** (`qa_check.py` +
    Zola build). Fail QA → KHÔNG đăng, mở issue + dùng `ff` để fix.
- Về Google/SEO: KHÔNG có rule bắt buộc trì hoãn; n+3 chỉ là buffer review, không
  hại SEO. Đăng đều đặn quan trọng hơn. Số ngày có thể chỉnh theo yêu cầu user.
- `bb9 <topic>` = biến thể "hẹn giờ" của `bb`, tự viết bài từ topic (vẫn tuân
  thủ rule Category + Ảnh WebP).

## Quy tắc Ảnh (WebP — BẮT BUỘC)

Áp dụng cho MỌI ảnh raster NỘI BỘ (lưu trong `static/...` hoặc `content/...`),
không áp dụng ảnh ngoài (picsum, CDN bên thứ ba — không kiểm soát được).

- Sau khi upload/thêm ảnh `.jpg/.jpeg/.png` trong lúc viết bài → PHẢI sinh bản
  `.webp` **song song** cùng tên cạnh bên (giữ nguyên file gốc, KHÔNG xoá/đổi).
  - Tự động (LUÔN BẬT): workflow `optimize-images.yml` chạy (a) khi push ảnh
    raster lên `main`, và (b) quét định kỳ hằng ngày 11:00 GMT+7 → bắt cả ảnh
    cũ còn sót chưa có `.webp`. Mục tiêu: mọi ảnh raster nội bộ đều có `.webp`.
  - Thủ công / trong shortcut `bb`: chạy `python3 scripts/to_webp.py <path>`.
- Hiển thị ảnh nội bộ qua macro `picture_webp` (`templates/macros/img.html`):
  render `<picture>` ưu tiên `.webp` + fallback file gốc cho browser cũ.
- KHÔNG convert `.svg` (vector) và `.gif` (giữ animation).
- `og:image` / ảnh social meta giữ định dạng gốc (`.jpg/.png`) cho tương thích;
  KHÔNG thay bằng webp ở thẻ meta OG/Twitter.

### Ảnh Placeholder mặc định (bài KHÔNG có ảnh)

- KHÔNG dùng ảnh random ngoài (vd `picsum.photos`) làm thumbnail — nội dung
  không liên quan bài viết. KHÔNG nhúng chữ baked cứng lên ảnh minh hoạ.
- Bài/section nào thiếu `[extra] thumbnail` → template TỰ chèn placeholder
  thương hiệu (gradient xanh `#38bdf8 → #1d4ed8`, KHÔNG chữ) qua macro
  `img::thumb_src` (`templates/macros/img.html`). Alt text lấy từ tiêu đề bài.
- Bộ placeholder cố định ở `static/img/placeholder/` (sinh bằng
  `python3 scripts/make_placeholder.py`): `placeholder.svg` (3:2, thumbnail),
  `placeholder-wide.svg` (16:9, ảnh trong bài), `placeholder-square.svg` (1:1).
- SVG là vector → ảnh dùng `object-fit: cover` tự crop mọi kích thước. OG/social
  vẫn fallback `img/og-default.jpg` (raster) vì mạng xã hội không render SVG.

## Quy tắc Bảo mật (Static host — thực tế GitHub Pages)

- Blog là **Zola static site deploy GitHub Pages, repo public** → KHÔNG có
  server-side, KHÔNG thể chặn tải file hay "ẩn URL thật". Mọi file đã publish
  là URL công khai. Đừng hứa/giả lập "chặn download" bằng JS client-side (vô
  tác dụng — ai biết URL vẫn tải được).
- `content/*.md` KHÔNG bị serve (Zola compile ra HTML). Chỉ file trong `static/`
  mới được copy nguyên trạng lên site → KHÔNG đặt file nhạy cảm trong `static/`.
- File báo cáo `static/data/reports/*.md` là public theo thiết kế; chỉ ẩn khỏi
  search qua `robots.txt`. Muốn chặn tải THẬT phải đưa qua backend có auth
  (FastAPI/Cloudflare Worker) — đây là việc lớn, chỉ làm khi user yêu cầu rõ.
- KHÔNG hardcode secret trong repo/workflow. Đưa input từ `github.event.*` vào
  env var hoặc dùng context tin cậy (`github.sha`...), KHÔNG nội suy thẳng vào
  `run:`/payload (chống script injection).

### Dependabot (BẬT qua `.github/dependabot.yml`)

- Dependabot CHỈ mở PR cập nhật dependency (GitHub Actions + Python deps), gom
  nhóm, weekly. Nó **KHÔNG push thẳng vào `main`** → không tự làm đỏ production.
- **KHÔNG gây xung đột build site**: Zola binary pin cứng version trong
  `deploy.yml`, Dependabot không đụng tới. Nó chỉ bump action versions + deps
  của script/service phụ.
- **Quy tắc merge PR Dependabot** (gate bắt buộc, cùng chuẩn deploy):
  1. PR phải PASS `qa-check` + build xanh → mới được merge. PR đỏ → KHÔNG merge.
  2. Nếu một bump làm fail CI/build → chạy phím tắt **`ff`** (Full Fix & Deploy)
     để auto-fix; fix xong + xanh → merge. Nếu không fix được → ĐÓNG PR đó, giữ
     version cũ, KHÔNG ép merge.
  3. Tuyệt đối KHÔNG auto-merge PR Dependabot khi đang đỏ chỉ để "cho xong".
