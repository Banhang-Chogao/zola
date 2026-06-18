# CLAUDE.md — Quy tắc làm việc

## Repository Automation Policy (effective 2026-06-18 — ZERO_BARRIER_AUTOMATION)

> **100% tự động:** CI pass → auto-merge `main` → deploy production. Không kiểm duyệt trung gian.
> Config: `data/auto-merge-policy.json` · Engine: `scripts/auto_merge_policy.py` · Runner: `auto-merge.yml`.

| | |
|--|--|
| **Auto-merge** | Mọi PR — chore, qa, fix, feature, content, policy, workflows, auth, payment, bot maintenance |
| **Manual review** | ❌ Không — blog sạch, không protected domain, không label chặn |

Chi tiết: `docs/OPERATIONS.md`, `.github/BRANCH-PROTECTION.md`, `.github/ACTIONS-PERMISSIONS.md`.

## Auto-Merge Policy (ZERO_BARRIER — ghi đè mọi rule PR-only / manual merge cũ)

> CI pass → **auto-merge `main` ngay** → `deploy.yml` production. Không chờ human approval.

### 1. Vẫn qua PR — không push thẳng `main`

Mọi thay đổi **phải qua Pull Request** (branch → PR). **Không** commit/push trực tiếp `main`.

### 2. Auto-merge khi CI xanh

1. Tạo branch: `feature/`, `fix/`, `chore/`, …
2. Push → mở PR vào `main`
3. **`auto-merge.yml`** merge tự động khi **qa-check** pass (QA Gatekeeper — không PR Policy)
4. `deploy.yml` chạy sau merge → GitHub Pages

**Không hỏi user** trước khi merge. Không dùng label chặn auto-merge.

### 3. Merge Report (thay review thủ công)

- Script: `scripts/fetch_merge_report.py` → `data/merge-report.json`
- Workflow: `merge-report.yml` (sau push `main` + hourly)
- Mỗi entry: PR #, title, summary_vi, change_type, merged_at, build_run_number
- Đọc report thay vì duyệt từng PR

### 4. Build failed trên PR → fix trên cùng branch

- Fix trên **cùng branch/PR** — không push `main`
- CI xanh → auto-merge

### 5. Automation / bot

- Bot **không** `git push origin HEAD:main` trực tiếp
- Data refresh: `push_via_pr.sh` → PR → auto-merge khi CI pass
- `main-guard.yml`: cho phép bot merge qua PR (auto-merge commit)

### 5a. Workflow permissions (2026-06-18)

| Loại workflow | Chạy tự động? | Ghi chú |
|---------------|---------------|---------|
| QA / chore bot PR | ✅ | `workflow_run` relay hoặc `WORKFLOW_BOT_PAT` |
| Human PR (same repo) | ✅ | `pull_request` bình thường |
| Fork PR | ⏳ approval | GitHub Settings — giữ bảo vệ |
| Deploy production (`github-pages` env) | ✅ push `main` only | Không gate QA PR |
| `manual-approval` / `pr-approval.yml` | ❌ removed | Không thêm lại |

**Settings:** `.github/ACTIONS-PERMISSIONS.md` — Workflow permissions = Read and write; fork approval chỉ cho outside collaborators.

### 5b. Auto-merge Bot-created Maintenance PRs

- Bot-created PRs auto-merge khi checks pass và không conflict — mọi loại thay đổi.
- Nếu không merge được, bot phải **comment lý do cụ thể** thay vì im lặng (`try_auto_merge.py` → `post_skip_comment`).
- **GITHUB_TOKEN PR gate / "workflows awaiting approval":** Không dùng `pull_request` trigger — CI qua `push` branch + `workflow_dispatch` + `workflow_run`. `push_via_pr.sh` → push → QA tự chạy. Chi tiết: `.github/ACTIONS-PERMISSIONS.md`, `docs/ROOT-CAUSE-ACTION-REQUIRED.md`.
- **PR Policy removed:** `pr-policy.yml` đã xóa — chỉ `qa-check` để auto-merge.
- **Không** dùng lại `pr-approval.yml` / job `manual-approval` — đã xóa (fail giả trên mọi PR).

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

#### V5 — `deploy.yml` (Build & Deploy): `configure-pages` "API rate limit exceeded for installation"

- **Dấu hiệu:** bước `actions/configure-pages` đỏ với `Get Pages site failed ... API
  rate limit exceeded for installation`; **`zola build` vẫn PASS** (lỗi ở khâu Pages,
  KHÔNG phải build/Tera); nhiều deploy run liên tiếp đỏ/huỷ trong thời gian ngắn.
- **Nguyên nhân:** "bão deploy" làm cạn quota API **theo giờ** của GitHub App
  installation — mỗi bot refresh (~10 workflow) gọi `push_to_main.sh` → dispatch
  `deploy.yml`; cộng burst nhiều PR merge cùng giờ; mỗi deploy còn chạy
  `build_github_activity.py` (gọi GitHub API nặng). KHÔNG phải lỗi code. Ngày thường
  (ít merge) không chạm ngưỡng nên "trước không bị, nay mới bị".
- **FIXER (đã áp 18/06):** `deploy.yml` → `concurrency.cancel-in-progress: true`
  (gộp bão, chỉ run mới nhất chạy tới cùng) + `configure-pages` `enablement: true`
  (đúng khuyến nghị action cho lỗi này) + `schedule: cron '0 */6 * * *'` (publish data
  bot định kỳ thay vì mỗi refresh tự dispatch). `push_to_main.sh` → **BỎ tự dispatch
  deploy** sau mỗi bot push (chỉ dispatch khi `DISPATCH_DEPLOY=true`). Đang đỏ tạm
  thời → đợi quota hồi (theo giờ); deploy push/cron kế tiếp sẽ xanh. Content (PR
  merge) vẫn deploy ngay; data bot trễ ≤6h (chấp nhận được). `cancelled` do
  concurrency = bình thường, KHÔNG phải fail.

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

### Mỗi thay đổi = 1 PR riêng, tự auto-merge (2026-06-18 — user request)

> ⛔ **KHÔNG GỘP** nhiều thay đổi độc lập vào cùng 1 PR — user phải chờ lâu nếu gộp.

- Mỗi thay đổi logic riêng (1 bài viết · 1 fix workflow · 1 sửa CSS · 1 update rule)
  = **1 PR riêng**, để mỗi thứ **tự merge lên `main` ngay khi QA xanh**, không bắt
  user chờ cả lô.
  - ✅ Đúng: bài A → PR A; fix deploy → PR B (2 PR song song, auto-merge độc lập).
  - ❌ Sai: gộp bài A + fix deploy + update rule vào 1 PR.
- Mỗi thay đổi **tự merge** qua `auto-merge.yml` (QA xanh → squash-merge). **KHÔNG
  merge tay** trừ khi auto-merge thật sự hỏng.
- Session bị giới hạn 1 branch dev → làm xong 1 thay đổi: mở PR → reset branch về
  `origin/main` → làm thay đổi kế tiếp (PR mới). KHÔNG tích nhiều thay đổi trên cùng
  branch/PR.

### Quy tắc chung

- Làm xong BẤT KỲ việc gì → **LUÔN mở Pull Request** về `main`. Không để thay đổi
  nằm im trên feature branch mà thiếu PR.
- Mỗi PR phải có tiêu đề rõ ràng + mô tả tóm tắt thay đổi và cách verify.
- Chỉ push thêm commit vào PR đang mở khi đó là **sửa/hoàn thiện CHÍNH thay đổi của
  PR đó** (vd fix CI đỏ) — KHÔNG nhét thay đổi MỚI không liên quan vào PR đang có.

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

## Autofixer Conflict Resolver (Python — `scripts/autofix_conflicts.py`)

> Workflow: `.github/workflows/autofix-conflicts.yml` — cron mỗi 30 phút + `workflow_dispatch`.
> State dedup: `data/autofix-conflicts-state.json`.

### Mục tiêu

Tự động quét PR open bị merge conflict với `main`, resolve an toàn, chạy QA/build,
tạo PR fix riêng `autofix/conflict-pr-<N>` để user review thủ công.

### Quy tắc BẮT BUỘC (autofix)

- **KHÔNG** commit/push trực tiếp vào `main`.
- **KHÔNG** force-push vào branch của người khác.
- PR autofix auto-merge khi CI pass (ZERO_BARRIER — không label chặn).
- **KHÔNG** tự sửa file nhạy cảm (`.env`, secrets, tokens, keys).
- Nếu không chắc chắn → đánh dấu `needs manual review`, comment trên PR gốc.

### Chiến lược resolve (ưu tiên)

| Loại file | Chiến lược |
|-----------|------------|
| `content/posting/*.md` (bài mới) | Giữ nội dung PR; merge frontmatter (title/date/slug/category/tags từ PR) |
| `config.toml`, `.github/`, deploy/security | Giữ `main` |
| sidebar/menu/nav/category/series JSON | Merge cả hai bên, dedupe, sort |
| Template/HTML | Merge dòng nếu overlap cao; logic khác → manual |
| SCSS/CSS | Merge rules không trùng; structural conflict → manual |
| Không chắc | **Manual** — không đoán |

### Validation sau resolve

1. `python3 qa_check.py`
2. `python3 scripts/build_references.py`
3. `zola build` (cần `ZOLA_GH_TOKEN`)
4. `python3 scripts/check_internal_links.py`

Chỉ tạo autofix PR khi **tất cả** bước pass và **không còn** conflict markers.

### Dedup / state

- Key: `source_pr_head_sha` + `main_head_sha` trong `data/autofix-conflicts-state.json`.
- Bỏ qua nếu đã có autofix PR open cho cùng head SHA.
- Re-run khi PR gốc có commit mới (head SHA đổi).

### Chạy thủ công

```bash
# Scan tất cả PR conflict
GH_TOKEN=... python3 scripts/autofix_conflicts.py

# Chỉ PR #280
GH_TOKEN=... python3 scripts/autofix_conflicts.py --pr 280

# Dry-run (chỉ scan)
python3 scripts/autofix_conflicts.py --dry-run
```

Hoặc: GitHub Actions → **Autofix Merge Conflicts** → **Run workflow** (optional `pr_number`).

### Khi AI agent gặp conflict thủ công

1. Đọc log dưới đây (`## Autofixer Conflict Learning Log`) trước khi resolve tay.
2. Sau khi resolve conflict (dù bằng autofix hay tay), **append** entry mới vào log.
3. Ưu tiên pattern đã học — không lặp lại lỗi resolve sai sidebar/config.

## Autofixer Conflict Learning Log

_(Entries được append tự động bởi `scripts/autofix_conflicts.py` sau mỗi lần xử lý.)_

### Action required on bot maintenance PRs (2026-06-18)

| Field | Detail |
|-------|--------|
| **Symptom** | PRs `github-actions[bot]` (#355–#361) — 0 check runs, UI **Action required**, auto-merge stuck |
| **Root cause** | (1) GITHUB_TOKEN không kích hoạt `pull_request` workflows; (2) relay `workflow_run` skip khi `head_branch == main`; (3) relay SHA trỏ `main` không phải PR head |
| **Fix** | `trigger_bot_pr_ci.sh` dispatch QA Gatekeeper sau `push_via_pr`; skip `pull_request` cho bot actor; `resolve_open_bot_pr.sh`; `actions: write` trên maintenance workflows |
| **Doc** | `docs/ROOT-CAUSE-ACTION-REQUIRED.md`, `.github/ACTIONS-PERMISSIONS.md` |
| **Test** | `python3 scripts/test_bot_pr_ci_relay.py` |
| **Prevention** | Không dùng relay `head_branch != main` cho schedule workflows; luôn dispatch CI từ `push_via_pr` khi không có `WORKFLOW_BOT_PAT` |

### PR #353 — `feature/prompt-support-token-engine` (2026-06-18)

| Field | Detail |
|-------|--------|
| **Files conflict** | `static/js/prompt-support.js`, `sass/_prompt-support.scss`, `templates/prompt-support.html` |
| **Nguyên nhân** | `main` đã merge Prompt Support **v2** (PR #346: Compact/Standard/Full, scores, compare cơ bản) trong khi PR #353 xây **v3 Token Engine** từ base cũ hơn — cùng 3 file được sửa song song → conflict toàn file |
| **Cách resolve** | Giữ **v3** từ PR #353 (superset của v2): Token Optimization Engine, Auto/Ultra/Compact/Standard/Full, Lint, Compare+diff, token budget, copy variants. Không lấy v2 từ `main` vì thiếu Ultra Compact, Auto Token Saver, compression ratio, Risk Coverage. Restore sạch từ commit `2eae856` (không dùng conflict markers) |
| **Validation** | `node --check static/js/prompt-support.js` PASS; `zola build` PASS; built `/prompt-support/` có `data-psupport-budget`, `data-psupport-copy-ultra`, mode Auto |
| **Rule mới** | Khi 2 PR cùng feature area (prompt-support v2 rồi v3): merge `main` vào branch mới **trước** review; ưu tiên phiên bản feature cao hơn nếu superset rõ ràng; luôn restore từ commit PR sạch thay vì `checkout --ours` khi markers còn trong working tree |
| **Rủi ro còn lại** | Không — v3 giữ SCSS variables blog (`$brand-*`), không đổi theme global |

### Prompt Support — Copy vs Lint UX (2026-06-18)

| Field | Detail |
|-------|--------|
| **Triệu chứng** | User nhầm **Lint Prompt** với copy; nút copy variant bị `disabled` (mờ/xám) trước khi Generate; bấm copy có thể bôi đen text selection |
| **Nguyên nhân** | v3 chỉ có copy theo mode (Ultra/Compact/…) sau Generate; Lint là kiểm tra chất lượng riêng — không copy clipboard |
| **Cách fix** | Thêm CTA **Cải thiện ngay** (primary, Ctrl/Cmd+Enter) + **Copy Prompt** (copy mode đang hiển thị); `user-select: none` + `blur()` sau copy; variant copy gom vào `<details>` |
| **Validation** | `node --check static/js/prompt-support.js` PASS; `zola build` PASS; built `/prompt-support/` có `data-psupport-improve`, `data-psupport-copy` |

### PR #284 — `feat/autofix-conflicts` (2026-06-17)

| Field | Detail |
|-------|--------|
| **Files conflict** | `CLAUDE.md` (duy nhất) |
| **Nguyên nhân** | PR #284 thêm section Autofixer + Dependabot rule cũ (`batch merge 10 PR`); `main` đã cập nhật policy PR-only (#272) — `user merge thủ công (từng PR)` nhưng chưa có section Autofixer |
| **Cách resolve** | Giữ wording Dependabot từ `main`; giữ nguyên toàn bộ section Autofixer Conflict Resolver + Learning Log từ PR #284; `README.md` auto-merge thành công |
| **Rule mới cho Autofixer** | Khi conflict chỉ ở `CLAUDE.md` policy/docs: **không chọn một bên** — lấy policy mới nhất từ `main`, append feature docs từ PR; không ghi đè section kỹ thuật đã thêm bởi PR |
| **Chú ý tương lai** | Sau PR #272, mọi chỗ ghi `batch merge` / auto-merge phải đồng bộ `user merge thủ công`; kiểm tra hot-search, deploy, workflow guards không bị rollback khi merge PR autofix |

## Build Dashboard / GitHub Actions Learning

### Build #388 and #387 — cancelled runs

| Field | Detail |
|-------|--------|
| **Symptom** | Dashboard hiển thị deploy run `conclusion: cancelled` (Build #388 `b38ba77` PR #287, Build #387 `f77c003` PR #285) như thẻ lỗi đỏ (`✗`, `--fail`) dù `stats.failure = 0` |
| **Root cause** | **Dashboard logic bug**, không phải lỗi workflow: `status_vi()` gán `cancelled → success: false`; template `insights.html` dùng `build.success` cho CSS/icon → cancelled bị render như failed. Deploy thật sự bị huỷ do **3 merge liên tiếp lên main** (~16:23–16:26 UTC): run pending bị thay bởi run mới trong concurrency group `pages` (hành vi GitHub bình thường khi `cancel-in-progress: false` — chỉ huỷ run **đang chờ**, không huỷ run đang chạy). `deploy.yml` **đã đúng** (`cancel-in-progress: false`). Build #389+ thành công — site health OK |
| **Resolution** | `scripts/fetch_build_dashboard.py`: thêm `status_normalized`, `gh_status`, `is_error`, `severity`, `cancel_reason`; phát hiện superseding run → message rõ; stats thêm `skipped`/`in_progress`. `templates/insights.html` + `sass/_insights.scss`: class `--cancelled`/`--skipped`/`--in_progress`, header hiện số đã huỷ. `scripts/test_build_dashboard.py` |
| **Prevention rule** | Không classify GitHub Actions `cancelled` là `failed`. Concurrency cancellation = non-critical trừ khi **mọi** deploy run mới nhất đều fail. Dashboard phải hiển thị `conclusion` thô và `status_normalized` riêng. Xác nhận deploy run mới nhất `success` trước khi đánh site health degraded |
| **Human review notes** | Build #387 (3s) bị thay bởi #388; #388 (110s) bị thay bởi #389 thành công. Không cần sửa `deploy.yml` concurrency |

## Compliance Dashboard Learning

### Internal links false “FAILED” (2026-06-17)

| Field | Detail |
|-------|--------|
| **Triệu chứng** | Dashboard 97.8 A+ nhưng Auto-fix log hiện `FAILED — Links: Internal links — Không tìm thấy pattern link hỏng đã biết` |
| **Root cause** | **Case 1 + Case 3**: Có 2 link hỏng thật; autofixer chỉ biết pattern cũ (prefix `/zola/`, changelog.json…). UI gắn nhãn `failed` của **autofix** khiến user tưởng compliance FAIL |
| **Link hỏng** | (1) `uranium-la-gi…` → `/posting/uranium-lam-giau-la-gi/` (Bài 2 chưa publish, còn trong `references.json`); (2) `scoring/` → draft `bi-kip-xin-visa…` trong `scores.json` |
| **Files** | `scripts/compliance_audit.py`, `scripts/compliance_fix.py`, `scripts/related_engine.py`, `templates/insights.html`, `content/posting/uranium-la-gi-tai-sao-quan-trong.md`, `data/scores.json`, `data/related.json` |
| **Resolution** | Audit ghi `data/compliance-link-report.json` + `broken[]` chi tiết; purge draft khỏi `scores.json`/`related.json`; sửa link series; dashboard hiện broken link cụ thể; autofix badge đổi thành `autofix` |
| **Prevention** | `related_engine.load_posts()` bỏ qua `draft=true`; chạy `build_references.py` **trước** `zola build`; kiểm tra `compliance-link-report.json` khi warn Links |

## Merge Session

**Date:** 2026-06-17T17:15:00Z

**Merged (rebase):**
- #313 — fix(dashboard): cancelled deploy runs Build #387/#388
- #309 — fix: compliance internal links (rebased, conflict CLAUDE.md + compliance-score.json)
- #311 — qa: compliance score refresh (regenerated 100/100, không rollback #309)
- #312 — chore: build dashboard refresh (giữ status_normalized từ #313)
- #310 — chore: changelog maintenance session entries

**Validation:**
- `zola build`: PASS
- `compliance_audit.py`: PASS (100/100 A+)
- `test_compliance_links.py`: PASS (3/3)
- `test_build_dashboard.py`: PASS (7/7)
- `check_internal_links.py`: PASS

**Lessons:**
- #309 conflict với #313 ở `CLAUDE.md` → giữ **cả hai** learning sections (Build Dashboard + Compliance)
- #311/#312 PR bot cũ chứa data stale — **không merge as-is**; regenerate từ main sau #313/#309
- Merge order: dashboard fix (#313) → compliance fix (#309) → data refresh (#311, #312) → changelog (#310)
- #314 merge tay sau maintenance — rebase + sửa `pr-policy.yml` whitelist `auto-merge.yml`

---

## Hệ thống tham khảo — Playbook phiên 2026-06-17

> **Mục đích:** Khi dashboard/CI báo lỗi hoặc cần merge khẩn nhiều PR, đọc section này **trước** khi sửa workflow hoặc merge. Chi tiết sâu: các section Build Dashboard, Compliance, Merge Session phía trên.

### 1. Chẩn đoán nhanh — Dashboard báo lỗi nhưng site vẫn chạy

| Triệu chứng | Đừng làm | Làm đúng |
|-------------|----------|----------|
| Build Dashboard thẻ đỏ `✗`, `conclusion: cancelled` | Sửa `deploy.yml` concurrency | Kiểm tra `stats.failure` — nếu `0` và deploy mới nhất `success` → **logic dashboard**, không phải site down |
| Compliance 97–100 A+ nhưng log `FAILED — Links` | Coi compliance FAIL | Phân biệt **autofix outcome** vs **compliance stats.fail**; đọc `data/compliance-link-report.json` |
| Nhiều deploy `cancelled` liên tiếp | Panic rollback | Bình thường khi **batch merge** — run pending bị thay trong group `pages`; xác nhận run **mới nhất** |

**Rule vàng:** Luôn kiểm tra **run/commit deploy mới nhất** trước khi đánh site health degraded.

### 2. Build Dashboard — cancelled ≠ failed

**Dấu hiệu:** `build.success: false` + `conclusion: cancelled` + card `--fail` đỏ.

**Root cause điển hình:** `fetch_build_dashboard.py` map `cancelled → success: false`; `insights.html` dùng `build.success` cho CSS.

**Fix pattern:**
- Field: `status_normalized` (`success` | `failed` | `cancelled` | `skipped` | `in_progress`)
- `is_error: true` **chỉ** khi `failed`
- UI: class `--cancelled` (vàng ⊘), không dùng `--fail`
- Message: phát hiện superseding run → `Đã huỷ do concurrency — run mới hơn (Build #N)`

**Workflow deploy:** `deploy.yml` giữ `concurrency.group: pages` + `cancel-in-progress: false` — **không đổi** trừ khi mọi deploy mới nhất đều fail thật.

**Test:** `python3 scripts/test_build_dashboard.py`

### 3. Compliance Dashboard — false “FAILED”

**Dấu hiệu:** Score A+ nhưng Auto-fix log đỏ; `stats.fail = 0`.

**Root cause điển hình:**
1. Link hỏng **thật** (series planned chưa publish, draft trong `scores.json`)
2. Autofixer không biết pattern mới → `outcome: failed` trên log, không phải compliance fail
3. UI gắn badge `failed` cho autofix → user hiểu nhầm

**Fix pattern:**
- `compliance_audit.py` → `data/compliance-link-report.json` với `broken[]` (source, target, reason)
- `related_engine.load_posts()` skip `draft=true`
- Purge draft khỏi `scores.json` / `related.json`
- Dashboard: hiện broken link cụ thể; badge autofix = `autofix` không phải `failed`
- Chạy `build_references.py` **trước** `zola build`

**Validation bundle:**
```bash
python3 scripts/build_references.py
python3 scripts/compliance_audit.py
python3 scripts/test_compliance_links.py
python3 scripts/check_internal_links.py
zola build
```

### 4. Maintenance merge — nhiều PR chồng chéo

**Thứ tự ưu tiên (đã chứng minh 17/06/2026):**

```
1. Fix logic (dashboard #313, compliance #309)
2. Rebase từng PR lên latest main
3. Data refresh bot (#311 compliance, #312 build-dashboard) — REGENERATE, không merge stale
4. Changelog/docs (#310)
5. Policy/infra (#314 auto-merge)
```

**Merge method:** User yêu cầu debug history → **rebase merge**, không squash cả batch.

**Conflict thường gặp:**

| File | Chiến lược |
|------|------------|
| `CLAUDE.md` | **Append** learning sections — không chọn một bên |
| `data/compliance-score.json` | Giữ bản **score cao hơn / fix mới hơn** (#309 → 100.0) |
| `data/build-dashboard.json` | Giữ schema mới (`status_normalized`) từ fix #313, rồi refresh timestamp |
| `templates/insights.html` | Merge cả build dashboard + compliance UI blocks |
| `templates/base.html`, `series-nav.html`, `page.html` | Thêm `elif` cho **mỗi** series manifest — không thay thế series cũ |

**PR bot data (`qa/compliance-auto`, `chore/build-dashboard-data`):**
- Chỉ đổi timestamp trên data **cũ** → merge sẽ **rollback** fix logic
- Cách đúng: `git checkout -B <branch> origin/main` → chạy `compliance_audit.py` hoặc migrate `build-dashboard.json` → push → merge

### 5. Multi-series template pattern

Khi thêm series mới (`adsense-foundation`, `science-uranium`, …):

```
base.html, macros/series-nav.html, page.html:
  {% if page.extra.series == "seo-foundation" %} → seo-foundation-series.json
  {% elif page.extra.series == "adsense-foundation" %} → adsense-foundation-series.json
  {% elif page.extra.series == "science-uranium" %} → science-uranium-series.json
```

`page.html` hub: `page.extra.hub_series` cho cluster related posts (science-uranium).

### 6. Auto-merge policy (#314) — bẫy PR Policy

**Triệu chứng:** PR `auto-merge.yml` pass qa-check nhưng **policy FAIL**.

**Root cause:** `pr-policy.yml` grep `auto-merge` chặn **cả** file `.github/workflows/auto-merge.yml`.

**Fix:** Whitelist trong `pr-policy.yml`:
- `.github/workflows/auto-merge.yml`
- `.github/workflows/merge-report.yml`
- `scripts/try_auto_merge.py`
- `scripts/fetch_merge_report.py`

Vẫn chặn: dependabot, renovate, workflow auto-merge **không** whitelist.

**Sau merge #314:** Branch protection `main` → Required approvals = **0** (`.github/BRANCH-PROTECTION.md`).

**Auto-merge:** mọi PR CI xanh — không label chặn, không lệnh `manual #N` (deprecated).

### 7. Validation checklist — trước và sau merge

| Bước | Lệnh | Pass khi |
|------|------|----------|
| Build site | `zola build` | exit 0 |
| References | `python3 scripts/build_references.py` | Wrote data/references.json |
| Internal links | `python3 scripts/check_internal_links.py` | OK |
| Compliance | `python3 scripts/compliance_audit.py` | 100/100, 0 broken |
| Compliance tests | `python3 scripts/test_compliance_links.py` | 3/3 |
| Dashboard tests | `python3 scripts/test_build_dashboard.py` | 7/7 |
| Merge report tests | `python3 scripts/test_merge_report.py` | 4/4 |

**Lưu ý:** `qa_check.py` có thể báo false positive conflict marker trong `.venv-related/` — không phải lỗi repo; CI `qa.yml` là nguồn truth trên PR.

### 8. Khi user báo "build failed" trên Grok Build Dashboard

```
1. Lấy run_id / build # từ data/build-dashboard.json
2. GitHub API: conclusion = cancelled | failure | success ?
3. cancelled + deploy mới hơn success → NON-CRITICAL (ghi dashboard)
4. failure → đọc log job, tra Vaccine library (§4 CLAUDE.md)
5. Không sửa deploy.yml concurrency chỉ vì cancelled history
```

### 9. File map — ai sở hữu gì

| Vấn đề | Script / file chính | Data output |
|--------|---------------------|-------------|
| Build history UI | `fetch_build_dashboard.py`, `insights.html`, `_insights.scss` | `data/build-dashboard.json` |
| Merge history UI | `fetch_merge_report.py`, `insights.html` | `data/merge-report.json` |
| Compliance score | `compliance_audit.py`, `compliance_fix.py` | `data/compliance-score.json`, `compliance-link-report.json` |
| Internal links | `check_internal_links.py`, `build_references.py` | `data/references.json` |
| Auto-merge | `try_auto_merge.py`, `auto-merge.yml` | label `auto-merged` trên PR |
| Bot data PR | `push_via_pr.sh` | branch `chore/*`, `qa/*` |

### 10. Prevention rules (ghi nhớ lâu dài)

1. **Không** classify GitHub `cancelled` là `failed` trên dashboard.
2. **Không** merge PR bot data nếu chỉ refresh timestamp trên schema/score cũ.
3. **Không** rollback fix logic mới hơn khi resolve conflict JSON data.
4. **Luôn** rebase PR lên `origin/main` trước maintenance merge.
5. **Luôn** append `CLAUDE.md` learning sau mỗi phiên điều tra — không ghi đè section cũ.
6. **Phân biệt** 3 lớp: GitHub `conclusion` thô → `status_normalized` → UI severity (`is_error`).
7. Confirm **latest deploy run success** trước khi báo production degraded.
8. Series template: mỗi series = một `elif` + một `data/*-series.json` — không hardcode một manifest.

### 11. PR đã xử lý trong phiên này (tham chiếu)

| PR | Kết quả | Ghi chú |
|----|---------|---------|
| #313 | Merged | Dashboard cancelled status |
| #309 | Merged | Compliance links + diagnostics |
| #311 | Merged | Regenerated compliance 100/100 |
| #312 | Merged | Dashboard refresh giữ status_normalized |
| #310 | Merged | Changelog + Merge Session |
| #314 | Merged (manual) | Auto-merge + Merge Report + pr-policy whitelist |
| #325–#330, #332 | Merged (manual) | Bot maintenance — CI `action_required` → owner approve workflows |
| #335–#338 | Merged (manual) | Cùng root cause: 0 check runs; data-only chore/qa refresh |
| #280 | Fixed (session trước) | Series template conflict adsense + science-uranium |

## F-Dashboard

Trang công cụ tài chính cá nhân tại `/tools/f-dashboard/` — upload sao kê Excel VietinBank, phân tích thu/chi, sức khỏe tài chính, biểu đồ và AI insights.

### Product spec (Frontend)

| Pillar | Requirement |
|--------|-------------|
| **Auto-Download & Wipe** | Nút «Export JSON» và «Export PDF Infographic». Trigger download → **xóa ngay** toàn bộ IndexedDB. **Không** persistent online storage (không GitHub, không server, không `/static`). |
| **Access Control** | Chỉ user **GitHub-authenticated** (reuse CMS OAuth: `cms_auth_url`, session `zola-cms-session-id`, `/auth/me`). Trang login trước dashboard. |
| **UI/UX — Health tiers** | Hiển thị rõ 5 cấp Financial Health (Excellent → Danger) kèm score range + mô tả; highlight tier hiện tại. |
| **PDF watermark** | Watermark trace (opacity ~0.08–0.16, lặp chéo + trung tâm): `{16hex_lowercase}_{blog_url_no_protocol}` trên mọi trang PDF. JSON export gồm `series_id` + `watermark`. |

**Kiến trúc (static site):** Blog Zola trên GitHub Pages không có server upload. Luồng chạy **100% client-side**:

```text
GitHub OAuth gate (auth-gate.js)
      ↓
Excel VietinBank (browser)
      ↓ SheetJS parser (parser.js)
      ↓ SHA256 deduplicate
      ↓ AES-GCM encrypted IndexedDB (storage.js) — ephemeral session only
      ↓ Insights + Charts (insights.js, charts.js)
      ↓ Export JSON/PDF (export.js) → auto-download → wipe storage
```

Python scripts (`scripts/f_dashboard_parse_excel.py`, `scripts/f_dashboard_insights.py`) mirror logic cho test/CI — **không** lưu dữ liệu người dùng.

### VietinBank Parser Rules

- Bỏ qua metadata đầu file (VietinBank, số TK, khoảng ngày, loại tiền).
- Tìm dòng header bảng: `STT`, `Ngày`, `Nội dung`, `Số tiền GD`, `Số dư` (không phân biệt hoa/thường, có/không dấu).
- Parse ngày: `DD/MM/YYYY HH:MM:SS` → ISO `YYYY-MM-DDTHH:MM:SS`.
- Parse số tiền: bỏ dấu phẩy, ưu tiên dấu `+`/`-` trên chuỗi.

### Thu / Chi (Income / Expense)

Ưu tiên (không phụ thuộc màu Excel):

1. `amount < 0` → `expense`
2. `amount > 0` → `income`
3. Màu font Excel (đỏ/xanh) chỉ là tín hiệu phụ khi `amount === 0`

### Deduplicate Rules

```text
transaction_id = SHA256(date + "|" + description + "|" + amount + "|" + balance)
```

- Đã tồn tại `transaction_id` → **SKIP**
- Chưa có → **INSERT**
- Upload cùng file N lần không nhân đôi dữ liệu.

### Financial Health Rules

- **Saving Rate:** `(Tổng thu - Tổng chi) / Tổng thu`
- **Expense Ratio:** `Tổng chi / Tổng thu`
- **Net Cash Flow:** `Thu - Chi`
- **Financial Score:** 0–100 từ saving rate, expense ratio, net flow, độ dài dữ liệu
- **Tiers (UI + PDF):**

| Tier | Score | Ý nghĩa |
|------|-------|---------|
| Excellent | ≥ 85 | Tích lũy mạnh, chi tiêu kiểm soát |
| Good | 70 – 84 | Cân bằng tốt, tiết kiệm đủ |
| Average | 50 – 69 | Trung bình, cần theo dõi chi |
| Risky | 30 – 49 | Chi gần/vượt thu |
| Danger | &lt; 30 | Thâm hụt kéo dài |

### Security Rules

- **Không** public file Excel, JSON sao kê, database dump.
- **Không** lưu trong `/static`, `/public`, hoặc commit git.
- Dữ liệu chỉ trên **IndexedDB local**, mã hóa **AES-GCM** (key sinh per-browser).
- Không gửi sao kê lên server — parse hoàn toàn trong trình duyệt.
- **Auth:** `/tools/f-dashboard/` — GitHub OAuth only (CMS flow).

### OAuth / Login (F-Dashboard + CMS)

| Config | Vị trí | Ghi chú |
|--------|--------|---------|
| `cms_auth_url` | `config.toml` → **`[extra]`** (không nest trong `[extra.giscus]`) | Render meta `zola-cms-auth-api` |
| Backend | `services/visitor-counter` (`blog-visitor-api.onrender.com`) | `/auth/login`, `/auth/callback`, `/auth/me` |
| Session key | `sessionStorage` → `zola-cms-session-id` | Chung CMS + F-Dashboard |
| `return_to` | Client gửi `location.pathname` (vd `/zola/tools/f-dashboard/`) | Backend strip `/zola` prefix → redirect `#sid=...` |
| Whitelist | `ADMIN_EMAILS` + `ADMIN_USERNAMES` (Render env) | Email verified **hoặc** GitHub login `banhang-chogao` |
| OAuth callback | GitHub App → `{BACKEND_URL}/auth/callback` | **Không** cần thêm callback riêng cho F-Dashboard (cùng app CMS) |
| Lỗi auth | `?auth_error=...` trên **đúng** `return_to` | Không ép về `/editor/` |

**F-Dashboard flow:** `auth-gate.js` → `GET {cms_auth_url}/auth/login?return_to=/zola/tools/f-dashboard/` → GitHub → callback → redirect `https://banhang-chogao.github.io/zola/tools/f-dashboard/#sid=...` → `fetchMe()` → hiện dashboard.
- **Ephemeral:** `exportAndWipe()` — download → `clearAll()` ngay; no persistent online storage.
- **PDF watermark (trace):** `SHA256-style 16 hex lowercase` + `_` + `banhang-chogao.github.io/zola` (no `https://`).

## F-Dashboard PDF Export Rules

- Always embed Unicode-capable Vietnamese fonts.
- Prefer Nokia Pure/Nokia Headline for F-Dashboard reports.
- Do not rely on browser fallback fonts for PDF.
- Use landscape A4 for bank-style transaction reports.
- Watermark must be visible enough for copyright tracing but not block content.
- Authenticated F-Dashboard users must never see the login CTA again after successful login.

### File map

| Thành phần | Path |
|------------|------|
| Trang | `content/tools/f-dashboard.md`, `templates/f-dashboard.html` |
| Styles | `sass/_f-dashboard.scss` |
| Client JS | `static/js/f-dashboard/*.js` (`auth-gate.js`, `export.js`, …) |
| PDF fonts | `static/fonts/nokia-pure/*.ttf` (Nokia Pure/Headline, embedded via jsPDF) |
| Python parser | `scripts/f_dashboard_parse_excel.py` |
| Python insights | `scripts/f_dashboard_insights.py` |
| Tests | `scripts/test_f_dashboard.py` |
| Deps | `scripts/requirements-f-dashboard.txt` (`openpyxl`) |

## QA Auto Rule Checker

Bot phát hiện rule/policy/workflow/automation xung đột — chạy mỗi **8 giờ** (`qa-rule-checker.yml`).

| Thành phần | Path |
|------------|------|
| Agent | `scripts/qa-auto-rule-checker.py` |
| Tests | `scripts/test_qa_auto_rule_checker.py` |
| Workflow | `.github/workflows/qa-rule-checker.yml` |
| Reports | `reports/rule-conflict-report.json`, `reports/rule-conflict-report.md` |
| State / anti-loop | `data/qa-rule-checker-state.json` |

**Quét:** CLAUDE.md · `.github/workflows/*` · `scripts/` · dashboards · content/SEO rules.

**Severity:** LOW · MEDIUM · HIGH · CRITICAL.

**Auto-fix:** chỉ khi `confidence >= 90%` → branch `qa/rule-checker-auto-*` → PR **auto-merge** khi CI pass.

**Anti-loop:** dừng khi cùng conflict auto-fix ≥3 lần hoặc >2 PR rule-checker mở.

**Manual:** `python3 scripts/qa-auto-rule-checker.py --dry-run`

## QA Rule Checker Learning

**Date:** 2026-06-17T19:34:37Z

**Conflict:** Auto-merge vs chặn merge thủ công (HIGH)

**Root Cause:** auto_merge: scripts/auto_merge_policy.py, scripts/try_auto_merge.py… vs block_merge: .github/scripts/push_via_pr.sh…

**Resolution:** Làm rõ precedence trong CLAUDE.md; gắn no-auto-merge cho bot report-only.

**Prevention:** Chạy `qa-auto-rule-checker.py` mỗi 8h; đồng bộ CLAUDE.md khi đổi policy.

## Premium Paywall Rules

- Never publish full premium content in static HTML.
- Premium posts render teaser only (`paywall_prepare_build.py --strip` trước `zola build`).
- Frontmatter: `premium = true`, `price`, `premium_post_id` (vd `premium-fintech-001`).
- Full premium body: `private_content/{premium_post_id}.md` — backend only, không commit vào `public/`.
- Unlock requires email + approve code + post_id validation.
- Approve code must be hashed in database (SHA256), không lưu plaintext.
- Admin confirmation is manual after Momo payment.
- Docs: `docs/paywall.md` · Admin: `/admin/paywall/` · API: `backend/paywall_app.py`
- Deploy: `services/paywall/` + `render.yaml` → `blog-paywall-api` · set `paywall_api_url` in `config.toml`.

## Momo Payment Rules

- Payment link mặc định (premium paywall **và** donate): `https://me.momo.vn/G5T1CDFRuJFWfBCDiK/YQdJ8k98OO4vaOG`
  - Cấu hình: `config.toml` → `momo_payment_link` (paywall) + `donate_momo_link` (donate, key riêng để đổi độc lập). Hiện cùng tài khoản nhận tiền.
  - Đồng bộ ở: `config.toml`, `templates/macros/paywall.html` (fallback), `backend/paywall_app.py` (`MOMO_LINK` default), `render.yaml` (`MOMO_PAYMENT_LINK`), `docs/paywall.md`. Khi đổi link → cập nhật TẤT CẢ chỗ này.
- Override qua env `MOMO_PAYMENT_LINK` trên backend.
- Flow: đọc teaser → thanh toán Momo → gửi yêu cầu (email) → admin xác nhận → generate approve code → gửi email.
- Không có webhook Momo — xác nhận thanh toán thủ công qua admin panel.

## Watermark Rules

- Dynamic watermark overlay khi đọc online: `blogName • emailHash • postId • traceCode`.
- Print/PDF: `@media print` chèn watermark `{traceCode16}_{blogDomain}` + bản quyền.
- Ví dụ in: `A9F328BC71D06E2A_banhang-chogao.github.io` + «Bản quyền thuộc blog. Không được sao chép hoặc phân phối lại.»
- `POST /api/paywall/log-print` ghi log khi user in.

## Security Rules (Paywall + F-Dashboard)

- **F-Dashboard:** không public Excel/JSON/dump; dữ liệu chỉ IndexedDB mã hóa AES-GCM trên browser; không upload server.
- **Paywall:** không hardcode SMTP secrets — `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
- **Paywall:** admin token qua `PAYWALL_ADMIN_TOKEN`; `/admin/paywall/` disallow trong `robots.txt`.
- Read-only protection (disable copy/right-click) là deterrent, không phải DRM tuyệt đối.

## Quy chuẩn Mục lục (TOC) — global tự động, BẮT BUỘC

TOC render **tự động ở template** (`templates/page.html`) từ **native `page.toc`** của Zola. KHÔNG viết tay `## Mục lục` trong markdown nữa (sẽ tạo TOC trùng + lọt RSS).

- **Khi nào hiện:** bài có **≥ 3 heading** (H2/H3 — đếm cả con). Bài ngắn/ít heading → không hiện.
- **Tắt cho 1 bài:** frontmatter `[extra] toc = false`.
- **Vị trí:** đầu `.post-single__content`, trước nội dung (native render 1 block; không tách giữa intro/H2 để khỏi cần JS).
- **Anchor:** dùng `id` heading thật — custom (`## Tiêu đề {#id}`) hoặc auto của Zola → luôn khớp, KHÔNG tạo heading trùng.
- **Scroll:** smooth + offset sticky navbar đã set global ở `sass/_reset.scss` (`html { scroll-behavior: smooth; scroll-padding-top: calc(60px + env(safe-area-inset-top)) }`). KHÔNG thêm JS, KHÔNG sửa lại scroll global.
- **RSS/summary:** TOC ở template (ngoài `page.content`) → feed KHÔNG bị chèn TOC. (TOC viết tay trong `.md` lọt RSS — đã gỡ khỏi 14 bài series AdSense/uranium.)
- **Style:** `sass/_toc.scss`, scope `.post-single__content .toc`, dùng semantic token (`var(--c-*)`) → đúng cả light/dark; responsive ≤720px. Import sau `@import "post"` trong `site.scss`.
- **Lợi ích SEO:** jump links tăng UX + dwell time; Google có thể hiện anchor/sitelinks trong SERP; cấu trúc heading rõ.
- **Mở rộng sau:** muốn sticky/scroll-spy → thêm JS riêng (chưa cần); đổi ngưỡng → sửa `toc_total >= 3` trong `page.html`.


## QA Domain Selector

Bot gợi ý **tên miền** cho blog "Chợ Gạo" (banhang-chogao) — chạy mỗi **2 giờ** (`qa-domain-selector.yml`) + `workflow_dispatch`.

### Cách hoạt động

1. **Quét niche:** đọc title/description + `[taxonomies]` categories/tags trên `content/posting` + `content/baochi` + `content/pages` + `content/tools` → phân tích tần suất (stdlib, không lib ngoài) ra top keywords, chủ đề chính (công nghệ · báo chí · ngân hàng · du lịch…), tông thương hiệu.
2. **Sinh ứng viên (V2 — bám CONTENT, KHÔNG khóa brand cũ):** base sinh từ **niche tokens** quét được × pool brandable `{blog, seo, tech, congnghe, kiemtien, hoc, tuhoc, viet, money, fintech, saoke, web, so}` + modifier `{viet, hoc, tao, tu, online, lab, hub, blog}` (combo ≤14 ký tự, VN-readable) + seed tên tác giả (`config.author`). **KHÔNG** dùng `chogao`/repo slug nữa. TLD `.com .vn .com.vn .net .blog`. Blocklist nhãn hiệu mở rộng (google, adsense, blogger, wordpress, vietinbank, momo, liobank, msb, bidv…) → loại base dính trademark.
3. **Chấm điểm 0–100 (rubric V2)** từ sub-scores có trọng số: `content_relevance 0.25` · `keyword_value 0.20` · `brandability 0.20` · `memorability 0.15` · `expansion_potential 0.12` · `trademark_safety 0.08`. (`brand_fit` cũ đã BỎ — domain phải phản ánh content thật.) `availability` là badge riêng, không vào 100 điểm. Sort desc. top5 = 5 base khác nhau (TLD tốt nhất mỗi base).
4. **Availability (adapter):** nếu env `DOMAIN_CHECK_API_KEY` set → hook `check_via_api()` (hiện STUB trả `None` → cần nối provider thật); else **fallback DNS** `socket.getaddrinfo`, **timeout cứng 3s/domain**, chỉ kiểm tra **shortlist ≤15** domain điểm cao nhất. DNS độ chính xác THẤP (resolve→taken, NXDOMAIN→available; domain đã đăng ký nhưng chưa trỏ DNS vẫn báo available). Lỗi/timeout → `unknown`.

> ⚠️ ANTI-HANG: timeout 3s/domain + cap 15 domain + mọi check bọc try/except. Script **không bao giờ crash build**: lỗi network/parse → giữ report cũ (cache) + exit 0.

### Chạy thủ công

```bash
python3 qa-domain-selector.py            # DNS fallback (3s/domain, ≤15 domain)
python3 qa-domain-selector.py --offline  # KHÔNG network → availability=unknown (nhanh)
python3 qa-domain-selector.py --limit 8  # giới hạn số domain check availability
```

### API config

- Env `DOMAIN_CHECK_API_KEY` (secret) → bật nhánh `check_via_api(domain)` trong `qa-domain-selector.py`. Hook hiện trả `None` (stub) → tự fallback DNS cho tới khi nối API thật (domainr / whoisxml / namecheap…). Workflow truyền `DOMAIN_CHECK_API_KEY: ${{ secrets.DOMAIN_CHECK_API_KEY }}`.

### Đọc report `data/qa-domain-selector-report.json`

`{ generated_at (ISO GMT+7), method (api|dns-fallback|offline), note, niche_summary, keywords[], topics[], tags[], weights{}, candidate_count, checked_count, domains:[{domain, tld, total_score, subscores{...}, availability, reason}], top5:[...] }` — sort theo `total_score` desc. Insights hiển thị `top5` (domain · score · badge availability · reason · last-scan `%H:%M %d/%m/%Y` GMT+7).

### File map

| Thành phần | Path |
|------------|------|
| Script | `qa-domain-selector.py` (REPO ROOT) |
| Report | `data/qa-domain-selector-report.json` |
| Workflow (cron 2h) | `.github/workflows/qa-domain-selector.yml` |
| Insights UI | `templates/insights.html` (block `.insights__domains`), `sass/_insights.scss` |

## QA 404 / Broken-Link Checker

`qa-404-checker.py` (REPO ROOT, stdlib) — crawl `public/` sau `zola build`, soi link hỏng theo chuẩn SEO. Chạy mỗi **2 giờ** (`qa-404-checker.yml`) + `workflow_dispatch`.

- **OFFLINE-SAFE (mặc định KHÔNG network → không bao giờ treo):** chỉ check link **nội bộ** bằng resolve vào file trong `public/` (xử lý prefix `/zola` theo `base_url`). Skip alias/redirect stub (`http-equiv=refresh`).
- **Link ngoài chỉ khi `--external`:** HEAD→GET urllib, timeout 8s/URL, ≤5 redirect, dedupe, cap ≤200, mọi request try/except → lỗi/timeout ghi `error_type` rồi tiếp. External fail = warn, KHÔNG fail build.
- **`--fix`:** tự sửa link **nội bộ** 404 khi suy được URL đúng gần nhất (theo `compliance_fix.py`), sửa **source `content/*.md`**, KHÔNG đụng `public/`, KHÔNG sửa link ngoài.
- **Report `data/qa-404-report.json`:** `summary{broken_count, checked, status}` + `links[]{source_page, source_file, href, target, status, error_type, suggestion, kind}`.
- **Exit code:** `2` nếu còn link **nội bộ** hỏng (CI gate); `0` nếu sạch. Thiếu `public/` / lỗi bất ngờ → giữ cache + exit 0 (không crash CI).

### Cách phát hiện & fix (kinh nghiệm)

- **Nguyên nhân hay gặp:** ref tới asset không tồn tại (vd `/img/header-banner.webp`, `/img/banner.webp` trong `base.html`/`page.html` — ảnh thiếu trong `static/`), hoặc link nội bộ sai prefix (`/zola/pages/privacy/` thay vì `/zola/privacy/`).
- **Cách fix:** link bài sai → `--fix` tự nắn về URL đúng gần nhất; ảnh/asset thiếu → tạo file `webp/svg` trong `static/` hoặc gỡ ref (checker KHÔNG tự bịa ảnh).
- **Chạy lại:** `python3 qa-404-checker.py` (nội bộ, nhanh) · `--external` (thêm link ngoài) · `--fix` (tự sửa nội bộ).

### File map

| Thành phần | Path |
|------------|------|
| Script | `qa-404-checker.py` (REPO ROOT) |
| Report | `data/qa-404-report.json` |
| Workflow (cron 2h) | `.github/workflows/qa-404-checker.yml` |

## O-Dashboard (Liobank by OCB — sao kê PDF)

Trang `/tools/o-dashboard/` — phân tích sao kê **Liobank by OCB** dạng **PDF**. Clone kiến trúc **L-Dashboard** (LPBank PDF), chỉ khác parser + branding. UI/UX + flow export PDF + OAuth gate giống F/L-Dashboard; theme Sembcorp.

- **Parser:** `static/js/o-dashboard/liobank-parser.js`. Bảng chính 6 cột: `Ngày GD · Nội dung · Số tiền ghi có · Số tiền ghi nợ · Phí · Số dư`. Date `DD-MM-YYYY HH:MM:SS` → ISO. Số tiền VN (`1.296.314`), `-` = 0. **`amount = credit − debit − fee`** (+ thu, − chi). Bỏ qua header metadata + bảng phụ "Tiết kiệm tự động (TKTG)".
- **Schema giao dịch** (khớp L-Dashboard): `{transaction_id, date, description, credit, debit, fee, balance, amount, type}` + `statement` + `reconciliation`.
- **Tách biệt F/L:** namespace `ODashboard*`, id `od-`, IndexedDB riêng `o-dashboard-db` — KHÔNG trộn dữ liệu với F/L. Dữ liệu chỉ local (AES-GCM), không upload server (như F-Dashboard security rules).
- **Insights/Charts:** dùng đúng engine nâng cấp của L (balance timeline · daily net · top txns · gauge · donut · AI insights rule-based). Export PDF: full 5 chart + fallback "Chưa đủ dữ liệu", header "Liobank by OCB".

| Thành phần | Path |
|------------|------|
| Trang | `content/tools/o-dashboard.md`, `templates/o-dashboard.html` |
| Styles | `sass/_o-dashboard.scss` (import sau `l-dashboard` trong `site.scss`) |
| JS | `static/js/o-dashboard/*.js` (`liobank-parser.js`, `app.js`, `export.js`…) |
