# CLAUDE.md — Quy tắc làm việc

## Quy tắc Deploy & Production (MỚI NHẤT — PR-only, ghi đè mọi rule cũ)

> ⚠️ **Rule MỚI NHẤT (17/06/2026), hiệu lực CAO NHẤT.** Ghi đè hoàn toàn rule
> "auto-merge + auto-deploy" (16/06/2026), "rule 16:00", batch-merge tự động,
> và mọi hướng dẫn push thẳng `main` trong `shortcuts.md`. Khi mâu thuẫn → **LẤY rule này**.
> Chi tiết: `docs/OPERATIONS.md`, `.github/BRANCH-PROTECTION.md`.

### 1. Không được commit/push/merge trực tiếp vào `main`

Mọi thay đổi (code, content, config, workflow, automation, generated file) **phải qua Pull Request**.

**Tuyệt đối không:**
- Commit / push / merge trực tiếp vào `main`
- Auto-merge PR (kể cả CI xanh, kể cả `batch-merge.yml`)
- Bypass manual review
- Gom nhiều yêu cầu khác nhau vào một PR nếu không cùng tính năng

### 2. Quy trình bắt buộc (mỗi yêu cầu = một branch + một PR)

1. Tạo branch riêng từ `main`: `feature/`, `fix/`, `qa/`, `content/`, `chore/`, `policy/`
2. Commit toàn bộ thay đổi của yêu cầu đó vào branch
3. Push branch → tạo PR vào `main`
4. **Chờ user review và merge thủ công** — Claude/agent KHÔNG tự merge
5. Deploy production chỉ sau khi PR được merge (`deploy.yml` trigger push `main` từ merge)

### 3. Điều kiện merge (user quyết định, CI hỗ trợ)

Trước khi user merge, PR nên đạt:
1. `qa_check.py` / `qa.yml` pass (error/exit≠0 chặn)
2. `zola build` pass trên CI
3. PR Policy pass (title/body mô tả đủ)

**Claude KHÔNG tự merge** dù đủ điều kiện. Chỉ nhắc user review.

### 4. Build failed trên PR → fix trên cùng branch

- Chạy `ff` / `ff9` để diagnose + fix
- Commit fix vào **cùng branch/PR** — KHÔNG push `main`
- Lặp tới khi CI xanh → chờ user merge lại

### 5. Automation / bot

Workflow GitHub Actions **KHÔNG** `git push origin HEAD:main`. Dùng
`.github/scripts/push_via_pr.sh` → branch riêng → PR → user merge.
`main-guard.yml` chặn push trực tiếp (bot + human không qua PR).

### 4. THƯ VIỆN VACCINE — lỗi build đã biết → FIX NGAY theo cách đã chốt (auto)

> 💉 Bộ "vaccine" tích luỹ từ audit toàn bộ lịch sử CI. **Giao thức bắt buộc**:
> khi nhận sự kiện build/CI failed → so log lỗi với **Dấu hiệu** của từng vaccine
> dưới đây. KHỚP dấu hiệu → chạy NGAY **FIXER** tương ứng (không chẩn đoán lại từ
> đầu), commit + push, đợi xanh. KHÔNG khớp vaccine nào → mới chẩn đoán mới bằng
> `ff`/`ff9`, và sau khi tìm ra fix bền vững thì **APPEND thêm 1 vaccine mới** vào
> danh sách này (đánh số tiếp). Đây là bộ nhớ tự fix — càng dùng càng đầy.

**Tình trạng audit gần nhất (16/06/2026):** quét 17 workflow từ ngày lập repo →
chỉ 3 workflow từng fail (V1–V3 dưới đây), TẤT CẢ đã resolved + xanh. Không
workflow nào đang đỏ.

#### V1 — `build-related.yml` (Build Semantic Related Posts): HuggingFace 401

- **Dấu hiệu:** log `snapshot_download` báo `401 Client Error` + `Repository Not
  Found for url: https://huggingface.co/api/models/<tên-model>` +
  `Invalid username or password.` cho model SBERT.
- **Nguyên nhân:** model id để **trần** (thiếu org). `huggingface_hub.snapshot_download`
  KHÔNG tự thêm prefix `sentence-transformers/` như class `SentenceTransformer`
  → HF tra repo top-level không tồn tại → 401. KHÔNG phải lỗi mạng/quota, KHÔNG
  phải conflict với tool chấm điểm/SEO/QA.
- **FIXER:** trong `scripts/build_related.py`, đặt `MODEL_NAME` = repo-id ĐẦY ĐỦ
  kèm org: `"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"`. Quy
  tắc chung: mọi chỗ gọi `snapshot_download` / API HF Hub PHẢI dùng `org/model`,
  KHÔNG dùng tên trần. (Cron `*/5` → nếu sai sẽ spam fail mỗi 5 phút tới khi sửa.)

#### V2 — `slack-notify.yml` (Slack Commit Notification): sai input sau bump v1→v3

- **Dấu hiệu:** `##[error]Missing input! The webhook type must be 'incoming-webhook'
  or 'webhook-trigger'.` ngay sau khi Dependabot bump `slackapi/slack-github-action`
  từ v1 lên v3.x.
- **Nguyên nhân:** v3 đổi API: bỏ env `SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK`, đổi
  sang input `webhook-type:` + block `payload:` inline. Bump version làm vỡ cú pháp cũ.
- **FIXER:** trong `.github/workflows/slack-notify.yml`, dùng cú pháp v3:
  `with: webhook: ${{ secrets.SLACK_WEBHOOK_URL }}`, `webhook-type: incoming-webhook`,
  `payload: |` (JSON inline). Pin action `@v3.x` cụ thể. (Đã áp dụng, đang xanh.)

#### V3 — `perf-audit.yml` (Performance Audit): GitHub Actions không được tạo PR

- **Dấu hiệu:** `pull request create failed: GraphQL: GitHub Actions is not
  permitted to create or approve pull requests (createPullRequest)` ở step
  `gh pr create`.
- **Nguyên nhân:** repo setting "Allow GitHub Actions to create and approve pull
  requests" đang TẮT → `gh pr create` exit≠0 làm đỏ job (lỗi quyền, không phải lỗi code).
- **FIXER (chống đỏ CI):** bọc lệnh để nuốt exit code, in hướng dẫn tạo PR thủ
  công thay vì fail: `if ! gh pr create ...; then echo "<URL tạo PR thủ công>"; fi`.
  (Đã áp dụng — workflow không còn đỏ.)
- **Residual (KHÔNG đỏ, tùy chọn):** auto-PR sẽ không tự mở cho tới khi BẬT setting
  trên ở repo (Settings → Actions → General → Workflow permissions), hoặc cấp PAT
  `secrets.GH_PAT` (pull-requests: write) cho step. Việc này cần thao tác trên
  GitHub settings/secrets — Claude KHÔNG tự làm được bằng code, phải nhờ user bật.
  ĐÃ BẬT (16/06/2026) → auto-PR perf-audit hoạt động (vd PR #257).

#### V4 — `perf-audit` auto-fixer chèn `loading/decoding` vào `<img>` trong COMMENT

- **Dấu hiệu:** PR "🚀 Perf audit" sửa file `.html` nhưng diff chèn
  `loading="lazy" decoding="async"` vào GIỮA văn xuôi/comment, vd
  `dùng <img> thường` → `dùng <img loading="lazy" decoding="async"> thường`, hoặc
  thêm attr vào ví dụ `<img>` nằm trong block comment Tera `{# #}`.
- **Nguyên nhân:** trong `qa_check.py`, `_IMG_TAG_RE` match `<img` ở MỌI nơi, kể
  cả trong comment Tera `{# #}` và HTML `<!-- -->` → checker cảnh báo nhầm +
  fixer chèn rác vào tài liệu (may nằm trong comment nên không vỡ build).
- **FIXER:** `qa_check.py` đã loại trừ comment qua `_comment_spans()` +
  `_in_spans()` (regex `_COMMENT_SPAN_RE = \{#.*?#\}|<!--.*?-->`) trong cả
  `check_perf_html` lẫn `fix_perf_html`. Nếu fixer còn chèn nhầm chỗ khác → mở
  rộng `_COMMENT_SPAN_RE` / bỏ qua context tương ứng. KHÔNG merge PR perf-audit
  chứa edit rác trong comment; đóng PR + để run sau regenerate sạch.

## Bootstrap session GitHub (BẮT BUỘC — lần đầu mỗi session)

Khi Claude **kết nối repo GitHub `Banhang-Chogao/zola` lần đầu** trong một
session (GitHub MCP, `gh`, `git` trỏ repo này), PHẢI:

1. **Đọc** `shortcuts.md` (source of truth phím tắt).
2. **Liệt kê** bảng tóm tắt tất cả phím tắt active (`Phím tắt` · `Mô tả ngắn` +
   tổng số) — format giống `help` / `phimtat`.
3. **Thực thi** khi user gọi phím tắt: message bắt đầu bằng tên shortcut (single
   line) → làm NGAY theo section tương ứng trong `shortcuts.md`, không hỏi lại.

Nếu message đầu tiên đã là một phím tắt cụ thể → đọc file + thực thi shortcut đó
(có thể bỏ list đầy đủ nếu user chỉ cần tốc độ). Chi tiết: `shortcuts.md` §0.

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

## Quy tắc Tham chiếu cuối bài (References — BẮT BUỘC)

Mọi bài mới/cập nhật (`content/posting/`, `content/baochi/`, `content/pages/`)
tự động có block **「Tham khảo & Nguồn dữ liệu」** cuối bài (macro
`references::section`, data từ `scripts/build_references.py`).

1. **Liên kết ngoài** — quét markdown/HTML trong bài, dedupe, ưu tiên nguồn official.
2. **Liên kết nội bộ** — tổng hợp link tới bài/chuyên mục trong blog.
3. **Bản quyền & ghi nguồn** — tự sinh khi có nguồn ngoài; override qua frontmatter.

Frontmatter tùy chọn (`[extra]`):

- `references_skip = true` — ẩn toàn bộ block
- `references_skip_copyright = true` — bỏ mục bản quyền
- `references_copyright = "..."` — text bản quyền tùy chỉnh
- `[[extra.references_external]]` / `references_internal` — bổ sung nguồn thủ công:
  `{ title = "...", url = "..." }`

Chạy `python3 scripts/build_references.py` trước `zola build` (CI tự chạy).

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
  - Workflow tạo PR `content/scheduled-publish` (KHÔNG push `main`) NẾU **PASS QA**
    (`qa_check.py` + Zola build). Fail QA → KHÔNG đăng, mở issue + dùng `ff` để fix.
    User merge PR → deploy.
- Về Google/SEO: KHÔNG có rule bắt buộc trì hoãn; n+3 chỉ là buffer review, không
  hại SEO. Đăng đều đặn quan trọng hơn. Số ngày có thể chỉnh theo yêu cầu user.
- `bb9 <topic>` = biến thể "hẹn giờ" của `bb`, tự viết bài từ topic (vẫn tuân
  thủ rule Category + Ảnh WebP).

## Quy tắc Ảnh (WebP — BẮT BUỘC, phát hành duy nhất)

Áp dụng cho MỌI ảnh raster NỘI BỘ (lưu trong `static/...` hoặc `content/...`),
không áp dụng ảnh ngoài (picsum, CDN bên thứ ba — không kiểm soát được).

- Upload tạm `.jpg/.jpeg/.png` → workflow `optimize-images.yml` convert sang
  `.webp` và **xoá raster gốc** (`scripts/to_webp.py --replace`). Thủ công:
  `python3 scripts/to_webp.py --replace static/img`.
- **Phát hành / tham chiếu chỉ `.webp`** cho raster (templates, config, content
  URL, OG/Twitter/schema). Macro `thumb_src` / `picture_webp` chuẩn hoá legacy
  `.jpg/.png` → `.webp` khi render.
- KHÔNG convert `.svg` (vector) và `.gif` (giữ animation).
- **Tradeoff (chấp nhận):** browser cực cũ không hỗ trợ WebP hiếm gặp; OG/social
  dùng `.webp` (Facebook/X/Google đều hỗ trợ). Không giữ song song jpg/png trên
  site — giảm bandwith + thống nhất pipeline.

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
  fallback `img/og-default.webp` khi thumbnail là `.svg` (mạng xã hội không render SVG).
- **Fallback runtime (ảnh CÓ src nhưng load lỗi/404):** `base.html` có 1 listener
  `error` (capture phase) đổi mọi `<img>` load fail sang placeholder → KHÔNG bao
  giờ hiện icon "ảnh vỡ". Bổ trợ cho fallback server-side (chỉ lo bài THIẾU
  thumbnail). Bắt được cả ảnh do JS dựng sau (sidebar random/featured). Khi thêm
  chỗ render `<img>` mới KHÔNG cần lặp lại — listener toàn cục lo hết.

## Quy tắc Bảo mật (Static host — thực tế GitHub Pages)

- Blog là **Zola static site deploy GitHub Pages, repo public** → KHÔNG có
  server-side, KHÔNG thể chặn tải file hay "ẩn URL thật". Mọi file đã publish
  là URL công khai. **Friction client-side** (`media-guard.js`, CSS) chỉ giảm
  tải/sao casual — KHÔNG hứa chặn tuyệt đối; ai biết URL vẫn tải được.
- **Meta security** (CSP, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`) trong `base.html` — GitHub Pages không custom HTTP headers;
  Cloudflare trước Pages mới set HSTS / rate-limit / WAF thật (xem
  `SECURITY-GUIDE.md` §Cloudflare).
- **robots.txt:** Allow rõ `Googlebot`, `Bingbot`, `Mediapartners-Google`;
  Disallow chỉ `/editor/`, `/admin-author/`, `/data/` — KHÔNG chặn ảnh bài viết.
- `content/*.md` KHÔNG bị serve (Zola compile ra HTML). Chỉ file trong `static/`
  mới được copy nguyên trạng lên site → KHÔNG đặt file nhạy cảm trong `static/`.
- **Báo cáo (`??`) đã chuyển sang BACKEND-GATED (chặn THẬT, 16/06/2026):** file
  `.md` KHÔNG còn nằm trong `static/` hay repo public nữa. Nội dung lưu trong
  Redis của backend FastAPI (`services/visitor-counter/main.py`), chỉ tải được
  qua endpoint `GET /reports/{file}` sau khi `require_session` pass (OAuth GitHub
  + email whitelist `ADMIN_EMAILS`). Trang `/bao-cao-tong-ket/` + `bao-cao.js`
  gọi backend (login → `/auth/me` → `/reports`), tải bằng fetch+Blob (Bearer sid).
  - Đẩy báo cáo mới lên backend: `POST /reports` (auth). Phím tắt `??` sinh file
    `.md` rồi dùng `python3 scripts/push_report.py <file> --sid <sid>` để đẩy
    (KHÔNG commit .md report vào repo public nữa).
  - Vẫn đúng nguyên tắc gốc: chỉ những gì NẰM TRONG repo/static mới public. Report
    giờ nằm ngoài repo → khách không có URL trực tiếp để tải.
- KHÔNG hardcode secret trong repo/workflow. Đưa input từ `github.event.*` vào
  env var hoặc dùng context tin cậy (`github.sha`...), KHÔNG nội suy thẳng vào
  `run:`/payload (chống script injection).

### Dependabot — TẮT (không auto-dependency updates)

- **KHÔNG** dùng Dependabot / auto-bump dependency. Cập nhật action/deps thủ công
  qua feature branch → PR → review → user merge thủ công (từng PR).
