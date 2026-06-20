# Phím tắt & Quy trình làm việc với Claude

Source of truth cho các shortcut commands + nguyên tắc vận hành. Khi
user gõ shortcut, Claude THỰC THI NGAY, không hỏi lại, không giải thích
dài.

---

## 0. Bootstrap session GitHub (BẮT BUỘC — lần đầu mỗi session)

**Khi Claude kết nối / làm việc với repo GitHub `Banhang-Chogao/zola` lần
đầu tiên trong một session** (lần đầu dùng GitHub MCP, `gh`, hoặc `git` trỏ
repo này), Claude PHẢI:

1. **Đọc file này** (`shortcuts.md`) — source of truth duy nhất cho phím tắt.
2. **Liệt kê ngay** bảng tóm tắt tất cả phím tắt active (format giống `help` /
   `phimtat`): cột `Phím tắt` · `Mô tả ngắn`, kèm tổng số.
3. **Ghi nhớ** nội dung từng shortcut trong session — khi user gọi tên phím
   tắt (đứng đầu message, single line) → **THỰC THI NGAY** theo mô tả section
   tương ứng trong file này, không hỏi lại, không giải thích dài.

**Nhận diện "lần đầu connect"**: chưa đọc `shortcuts.md` trong session hiện tại,
hoặc user vừa mở task mới liên quan repo zola mà chưa thấy bảng phím tắt.

**Ngoại lệ**: user gõ thẳng một phím tắt ngay message đầu → đọc `shortcuts.md`
+ thực thi shortcut đó (có thể bỏ bước list đầy đủ nếu user chỉ muốn tốc độ).

Chi tiết từng phím tắt: §2 bên dưới. Canonical copy rule: `CLAUDE.md` §
"Bootstrap session GitHub".

---

## 1. Cơ chế chọn phiên bản Node.js (Thông minh & Linh hoạt)

KHÔNG force phiên bản Node mặc định cho mọi workflow. Khi sửa lỗi hoặc
tạo workflow mới, Claude phải tự đánh giá:

- **Ưu tiên Node.js 24+** nếu action hỗ trợ tốt (hầu hết @v4/@v5 của
  `actions/*` đã ổn định trên Node 24 từ tháng 6/2026).
- Dùng `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` env tạm thời đến
  16/06/2026 vì runner vẫn default Node 20. Sau ngày này → bỏ env.
- Dùng `actions/setup-node@v4 with: node-version: '24'` cho workflow có
  chạy shell commands `node`/`npm`.
- Kiểm tra runner warning log mỗi lần deploy fail → adapt nếu GitHub
  thay đổi guidance.

---

## 2. Phím tắt (Shortcuts)

### `phimtat` — Slash command `/phimtat` liệt kê tất cả phím tắt active

Slash command `.claude/commands/phimtat.md` — khi user gõ `/phimtat` trong
Claude Code, đọc file này và output bảng Markdown 2 cột (tên · mô tả).
Phiên bản canonical của `help` dưới dạng Claude Code slash command.

### `thememoi` — Slash command `/thememoi` audit + áp 3 theme mới

Slash command `.claude/commands/thememoi.md` — khi user gõ `/thememoi`,
Claude grep tất cả file SCSS tìm component chưa override theo 3 theme
(Z-X, E-X, Hila Ericsson), apply override scoped `:root[data-theme="..."]`,
verify SCSS compile. CHỈ giao diện + bố cục, KHÔNG đổi content/DOM.

### `help` — Hiển thị danh sách tất cả phím tắt active

Khi user gõ `help` (hoặc `/help`), Claude output bảng tóm tắt tất cả
shortcuts hiện có trong file này với mô tả ngắn ≤1 dòng/shortcut.

Format bắt buộc:

| Shortcut | Mục đích |
|---|---|
| `gg` | Merge open PRs to production |
| `ad` | Full blog audit (perf+sec+seo+a11y) |
| `ff` | Full Fix & Deploy comprehensive |
| `cautruc9` | Show ASCII folder tree của blog |
| `SEO9` | Tu bổ SEO site-wide đạt Lighthouse 100/100 (Google Search Central) |
| `SEO10` | Loop audit + fix từng lỗi đến khi 0 issue (Google SEO Starter Guide) |
| `SEO11` | Hybrid SEO9+SEO10: phase 1 bulk Lighthouse + phase 2 loop polish |
| `diemtoiuu` | Python chấm điểm SEO toàn site (public/) + in báo cáo chi tiết tại chỗ |
| `content9` | Auto chạy check_content_seo.py — soi front matter + ảnh thiếu alt trong content/ |
| `nangcap` | Quét + nâng cấp mọi bài cũ điểm SEO QA < 90 lên đạt chuẩn (≥90/A) |
| `morning` | Chạy chuỗi tất cả shortcut (trừ chính nó) theo thứ tự non-conflict |
| `runner` | Retry / tiếp tục lệnh, workflow, macro đang dở hoặc bị gián đoạn |
| `tieptuc8` | Tiếp tục & hoàn tất TẤT CẢ tác vụ đang dở (todo, push, PR, CI, macro) |
| `wip8` | Read-only workspace tracker — tái dựng task đang dở từ git status + file changes |
| `theodoi8` | Theo dõi LIÊN TỤC (auto-refresh) trạng thái các commit đang chạy trên GitHub Actions |
| `backend8` | So main SHA vs Render backend SHA — phát hiện split-brain static↔backend (V16) |
| `topic: <chủ đề>` | Research + viết 1 bài + deploy theo chủ đề user nhập |
| `baomoi <topic>` | Từ chủ đề → bài/series Markdown production-ready, category AI-driven, SEO Google |
| `topic10` | Viết 10 bài Du lịch (chủ đề ngẫu nhiên cùng cluster) — test topical authority |
| `pp` | Liệt kê toàn bộ rule/quy tắc + thư viện vaccine hotfix trong CLAUDE.md (để ghi nhớ) |
| `fixrule8` | Soi conflict giữa rule + vaccine trong CLAUDE.md → sinh PROMPT fix cho Claude/Grok (read-only) |
| ... | ... |

Sau bảng có thể kèm 1-2 dòng note (vd: "Đầy đủ chi tiết tại
`/shortcuts.md`"). KHÔNG diễn giải dài, chỉ liệt kê.

### `pp` — Liệt kê toàn bộ rule/quy tắc + thư viện vaccine trong CLAUDE.md

Khi user gõ `pp`, Claude **đọc `CLAUDE.md`** rồi **in ra màn hình tác vụ** một bản
tóm tắt đầy đủ MỌI rule/quy tắc + thư viện vaccine hotfix hiện có, để user ghi nhớ
nhanh mà không phải mở file. Mục đích: tra cứu tại chỗ.

**Hành động**:

1. Đọc `CLAUDE.md` (toàn bộ).
2. Output **theo nhóm**, mỗi rule 1 dòng ngắn gọn (tên rule · ý chính ≤1 dòng):
   - **Policy & Auto-merge** (ZERO_BARRIER, mỗi thay đổi = 1 PR riêng tự merge…)
   - **Git / Pull Request** (không gộp PR, branch dev…)
   - **CSS / Responsive** (Mobile ≠ Desktop, cấm anti-pattern scroll…)
   - **Timezone & Date** (GMT+7, dd/mm/yyyy…)
   - **SEO QA bài viết** (≥600 từ, seo_keyword, ≥2 H2…)
   - **Category** ("Tất cả" đầu mảng, "Báo chí" cho `bb`…)
   - **References / TOC / Ảnh WebP / Placeholder**
   - **Bảo mật** (static host, không hardcode secret…)
   - **Paywall / Momo / Watermark / F-L-O-Dashboard**
   - **🧪 Thư viện Vaccine** (V1…Vn): mỗi vaccine = `mã · dấu hiệu ngắn → fixer ngắn`.
3. Cuối cùng in **tổng số rule nhóm + tổng số vaccine**.
4. KHÔNG sửa file, KHÔNG chạy gì khác — chỉ ĐỌC + IN. Trình bày bảng/bullet gọn,
   ưu tiên dễ quét mắt (giống `help` nhưng cho RULE thay vì shortcut).

**Lưu ý**: `pp` giờ = "in rule + vaccine" (KHÔNG còn là HOTFIX deploy như nhắc cũ
trong macro `morning` Phase E — tham chiếu đó đã lỗi thời, sẽ dọn sau).

### `fixrule8` — Soi conflict rule + vaccine trong CLAUDE.md → sinh PROMPT fix cho Claude/Grok

**Mục đích**: Đọc TOÀN BỘ rule/quy tắc + thư viện vaccine (§4, V1–Vn) trong `CLAUDE.md`,
phát hiện **mâu thuẫn / chồng chéo / trùng lặp / lỗi thời** giữa các rule. Nếu CÓ conflict
→ **KHÔNG tự sửa**, mà xuất ra **1 PROMPT hoàn chỉnh, copy-paste được** để giao cho Claude
hoặc Grok thực thi việc fix. READ-ONLY: `fixrule8` chỉ phát hiện + sinh prompt, KHÔNG chỉnh
`CLAUDE.md`, KHÔNG commit, KHÔNG mở PR.

**Khác các shortcut gần giống**:
- `pp` — chỉ **liệt kê** rule + vaccine để ghi nhớ, KHÔNG soi conflict.
- `qa-auto-rule-checker.py` (workflow nền, cron 48h) — auto-detect + **auto-fix** conflict
  qua PR khi confidence ≥ 90%.
- `fixrule8` — phát hiện conflict **thủ công, on-demand** + **bàn giao bằng prompt** (để
  Claude/Grok quyết cách sửa). KHÔNG đụng tay vào file.

**Cú pháp**:
- `fixrule8` — quét toàn bộ rule + vaccine.
- `fixrule8 vaccine` — chỉ soi §4 Vaccine library (V1–Vn): trùng số hiệu, trùng dấu hiệu
  khác fixer, vaccine lỗi thời.
- `fixrule8 <từ khoá/section>` — chỉ soi 1 nhóm rule (vd `fixrule8 auto-merge`).

**Hành động**:

1. **Đọc** `CLAUDE.md` toàn bộ → tách thành "đơn vị rule" (mỗi heading/policy/vaccine = 1
   đơn vị, ghi lại **số dòng + tên section** để trích dẫn chính xác).
2. **Soi conflict** theo 5 loại:
   - **Contradiction** — 2 rule yêu cầu ngược nhau (vd "auto-merge ngay khi CI xanh" ↔
     "PR pending, chờ duyệt tay"; "KHÔNG canh PR" ↔ "theo dõi tới khi merge").
   - **Overlap / duplicate** — 2 section mô tả cùng việc bằng wording khác (vd 2 bản
     format "Báo cáo PR sau merge").
   - **Stale / superseded** — rule cũ đã bị rule mới ghi "ghi đè / override / ngày mới hơn"
     thay nhưng CHƯA gỡ → còn gây nhầm.
   - **Vaccine clash** — 2 vaccine trùng số hiệu (vd 2 khối `#### V10`), hoặc cùng dấu
     hiệu nhưng fixer khác nhau.
   - **Cross-file drift** — rule trong `CLAUDE.md` lệch với `shortcuts.md` / workflow / script.
3. **Phân loại severity**: CRITICAL (mâu thuẫn chặn pipeline/build) · HIGH (contradiction
   rõ) · MEDIUM (overlap/stale) · LOW (trùng wording nhẹ).
4. **Output**:
   - **0 conflict** → in `fixrule8: CLAUDE.md sạch — không phát hiện conflict.` + bảng số
     đã quét (rule N · vaccine M).
   - **Có conflict** → in (a) **bảng tóm tắt conflict**, rồi (b) **1 PROMPT hoàn chỉnh**
     trong code block ` ```text ` để user copy đưa cho Claude/Grok.

**Bảng conflict**:

| # | Loại | Rule/Vaccine (dòng) | Mô tả ngắn | Severity |
|---|---|---|---|---|
| 1 | Contradiction | Auto-merge (L40) ↔ `prn` pending (L1241) | ... | HIGH |

**Format PROMPT sinh ra** (luôn trong 1 code block, self-contained — người nhận không cần
mở repo vẫn hiểu phải làm gì):

```text
Bối cảnh: File CLAUDE.md của repo Banhang-Chogao/zola có các rule/vaccine bị conflict.
Nhiệm vụ: Sửa các conflict dưới đây, GIỮ rule mới nhất / đúng policy ZERO_BARRIER hiện
hành, hợp nhất hoặc gỡ rule cũ đã bị override, KHÔNG xoá nhầm vaccine còn dùng.

Conflict cần xử lý:
1. [HIGH] Contradiction — <Rule A (section, dòng)> ↔ <Rule B (section, dòng)>
   - Hiện trạng: "<trích dẫn ngắn A>" vs "<trích dẫn ngắn B>"
   - Hướng fix đề xuất: <giữ bên nào / hợp nhất ra sao + lý do>
2. ...

Đầu ra mong muốn: nội dung mục CLAUDE.md đã sửa (hoặc diff) + 1 dòng giải thích mỗi fix.
Ràng buộc: không đổi nghĩa policy đang hiệu lực; chỉ loại mâu thuẫn / trùng lặp / lỗi thời.
```

**Hard rules**:
- **READ-ONLY** — KHÔNG sửa `CLAUDE.md`, KHÔNG commit, KHÔNG mở PR. Chỉ đọc + in báo cáo + prompt.
- Mọi conflict báo ra PHẢI kèm **số dòng / tên section** để prompt actionable.
- **KHÔNG bịa conflict** — chỉ báo khi có bằng chứng 2 chỗ thật mâu thuẫn/trùng/lỗi thời.
- Prompt sinh ra phải **self-contained** + nêu rõ ràng buộc "giữ policy hiện hành".
- Conflict CRITICAL (chặn pipeline) → đưa lên ĐẦU bảng + đánh dấu rõ.

### `cautruc9` — Show folder structure của blog

Khi user gõ `cautruc9`, Claude render cấu trúc thư mục của repo theo
format **ASCII tree + emoji icon + inline comment Vietnamese** — kiểu
gọn-readable như screenshot user đã cung cấp.

**Quy tắc render**:

1. Root = `zola/` (tên repo).
2. Dùng ký tự ASCII: `├── `, `│   `, `└── ` (không dùng box-drawing
   Unicode kiểu khác).
3. Mỗi entry có **emoji icon** prefix hợp ngữ cảnh:
   - 📁 hoặc thiếu = folder
   - 📄 = config/markdown text
   - 🚀 = script shell helper (`push.sh`, `setup-hooks.sh`)
   - ⚙️ = workflow CI/CD (`.github/workflows/*.yml`)
   - 🎨 = SCSS / theme tokens
   - 📝 = CMS / editor
   - ⚡ = performance / vitals
   - 🔤 = fonts
   - 🧮 = converter / tool
4. Inline `# Vietnamese comment` ≤8 chữ giải thích mục đích mỗi entry
   quan trọng. KHÔNG comment trên entry trivial (file thường lệ).
5. **Gom files cùng nhóm** trên 1 dòng để gọn, vd:
   `_reset.scss / _layout.scss / _navbar.scss`.
6. **Liệt kê tới depth 2** mặc định (root + 1 lớp con). Nếu folder con
   quan trọng (`content/`, `templates/`, `sass/`, `static/js/`) → mở
   thêm 1 lớp nữa.
7. KHÔNG liệt kê: `node_modules/`, `__pycache__/`, `.git/`, `public/`,
   `target/`, hidden file trừ `.github/`, `.gitignore`.
8. Wrap toàn bộ trong code block ```` ``` ```` để monospace align.

**Output cuối**: ≤80 dòng, đọc 1 lần thấy ngay layer build-time
(Zola: content/templates/sass/data) + runtime (static/js) + external
(services/.github).

### `prm` — Merge TẤT CẢ open PRs nhanh nhất + cache bust

Override "TẠM NGƯNG AUTO-MERGE" rule — user explicit gọi `prm` =
quyết định batch merge mọi PR đang open.

**Hành động**:
1. List tất cả open PRs (`mcp__github__list_pull_requests state=open`)
2. **Sequential squash merge** từng PR (theo thứ tự tạo)
3. Sau khi merge hết → trigger deploy đợt cuối (push commit nhẹ vào main)
4. **Cache bust strategies**:
   - GitHub Pages tự serve fresh sau deploy (`Cache-Control: max-age=600`)
   - Site.css đã có hash qua `get_url()` Zola — auto cache bust
   - Bump version comment trong `config.toml` hoặc `static/version.txt`
     để force fresh CDN edge
5. **Hướng dẫn user** clear cache:
   - **Desktop**: `Ctrl+Shift+R` (Win/Linux) hoặc `Cmd+Shift+R` (Mac)
   - **iPhone Safari**: Settings → Safari → Clear History and Website Data
   - **DevTools Network**: tick "Disable cache" → reload

**Output** ngắn ≤100 words:

| PR | Status |
|---|---|
| #X | ✅ merged |
| #Y | ✅ merged |
| Total | N merged → deploy đang chạy |

Lý do tồn tại `prm` (vs `gg` chỉ list): `prm` là override TỐC ĐỘ.
Khi user muốn xem feature mới NGAY, không cần check từng PR.

### `gg` — Deploy to production

Hành động:
1. List tất cả PR đang mở (`mcp__github__list_pull_requests state=open`)
2. Với mỗi PR chưa merge:
   - Verify CI status (nếu CI failing → không merge bừa, escalate)
   - Squash merge vào `main` (trigger deploy.yml tự động)
3. Verify deploy mới nhất (`actions_list` deploy.yml) đang chạy
4. Output **một lần** báo cáo theo §5 (KHÔNG poll/canhc PR sau đó).

KHÔNG hỏi lại. KHÔNG giải thích flow.

### `ad` — Audit blog

Hành động:
1. Verify cron jobs `perf-audit.yml` + `security-audit.yml` còn active
   trên GitHub Actions. Nếu disabled → BÁO USER NGAY.
2. Trigger manual audit qua `workflow_dispatch` cho cả 2.
3. Chạy bổ sung tại chỗ:
   - Performance: Lighthouse mobile (LCP/CLS/INP/TBT)
   - Code quality: scripts/qa_check.py
   - Security: pip-audit + gitleaks dependencies
   - SEO: meta tags, alt tags, sitemap, structured data
   - Accessibility: ARIA, keyboard nav, contrast
4. Output punch list ≤200 words: done / warnings / errors, sorted severity.

### `ff` — Full Fix & Deploy (với Python lib picker)

Hành động:

1. **Liệt kê** tất cả failed workflow runs (≥ 24h gần nhất) +
   failed PR checks + failed deploy.

2. **Detect lỗi LẶP/CRITICAL** chặn deploy:
   - **Repeat**: cùng pattern stderr xuất hiện ≥ 2 failed run trong 24h
   - **Critical**: failed run trên `deploy.yml` chính (không phải workflow phụ)
   - Sort theo (repeat × 2 + critical × 3) priority — fix cái cao nhất trước.

3. **LIST PYTHON LIBRARIES HIỆN CÓ** (NEW per user rule):
   - Chạy `pip list --format=json` → parse name + version
   - Output bảng top 30 lib (sort theo relevance với failed pattern):

     | Lib | Version | Phù hợp fix pattern |
     |---|---|---|
     | anthropic | 0.109.1 | AI diagnose → scripts/ff.py |
     | loguru | 0.7.3 | Log structured để bắt lỗi sớm |
     | ruff | 0.15.8 | Auto-fix Python syntax/import |
     | mypy | 1.19.1 | Catch type bug trước commit |
     | pydantic | 2.13.4 | Validate config.toml + data/*.json schema |
     | pre-commit | 4.6.0 | Block commit có lỗi trước push |
     | ... | ... | ... |

4. **Pick library phù hợp nhất** cho repeated/critical pattern:

| Failed pattern | Lib gợi ý | Cách áp dụng |
|---|---|---|
| `ModuleNotFoundError` recurring | `pip-tools` / `pipdeptree` | Audit deps tree, pin version |
| Tera literal dict lặp lại (đã 3 lần) | `pydantic` | Define model cho data/*.json, fail-fast trước build |
| JSON parse error data/*.json | `pydantic` | Schema validation runtime |
| Python type error scripts/ | `mypy` (strict mode) | Run mypy trong pre-commit, block commit lỗi type |
| Python syntax/format inconsistent | `ruff --fix` | Auto-fix pre-commit hook |
| HTTP retry race condition | `tenacity` | Decorator @retry exponential backoff |
| Date/time parse issue | `python-dateutil` | Robust ISO 8601 parsing |
| Test flaky | `pytest-rerunfailures` | Retry tự động test fail intermittent |
| Slack webhook payload limit | (existing truncate step) | Verify cap 2500 chars chạy đúng |
| AI client timeout | `anthropic` + `tenacity` | Retry with backoff, switch model |

5. **Auto-fix** pattern đã biết (cập nhật mở rộng):
   - `ModuleNotFoundError` → append dep vào requirements.txt + `pip install`
   - Tera/Zola syntax → chạy `qa_check.py --fix safe`
   - **Tera lỗi lặp ≥3 lần** → tạo `pydantic` model validator + thêm vào
     pre-commit hook (block tương lai)
   - Git race non-fast-forward → escalate (không tự force push)
   - Workflow permission denied → escalate
   - Python type error → `mypy --strict` rồi `ruff --fix --unsafe-fixes`
   - Unknown pattern → tạo issue + escalate + gợi ý lib từ bảng 4

6. **Push** fix → auto-merge vào `main` khi build xanh (theo §4.5).
   Auto deploy lại production, KHÔNG cần `manual #X`.

7. **Báo cáo tổng kết** sau khi xong:
   - Failed runs found / fixed / escalated
   - Repeated patterns detected (lib gợi ý)
   - PR tạo + lệnh `manual #X`
   - Production deploy status hiện tại

**Tại sao step 3-4 mới**: user feedback — nhiều lỗi (vd Tera literal dict
lặp 3 lần) cần solution tổng thể, không fix-once-broken-again. Pick lib
phù hợp giải quyết tận gốc (vd: `pydantic` schema chặn build sớm) thay
vì fix file rồi mai lại sai chỗ khác.

### `healing` — Kích hoạt QA-Healing thủ công

Hành động: chạy QA-Healing on-demand. Khác `ff`: ALWAYS chạy baseline
qa_check.py trước fix, output detail per step.

1. Liệt kê failed runs gần nhất (default 5).
2. **Baseline QA**: `python3 qa_check.py` trước intervention.
3. **Auto-fix** qa-failed.py pattern matching.
4. **Re-deploy**: commit + push main → trigger deploy.yml.
5. **Verify**: poll deploy run mới đến success (max 5 phút).
6. Nếu run mới vẫn fail sau heal → tạo issue label `healing-failed`.

### `vacxin11` — Daily Vaccine Autofixer (chạy ngay, không đợi 06:00)

Trigger thủ công **Daily Vaccine Autofixer** (Vaccine V11) ngay lập tức thay vì
chờ lịch cron 06:00 (Asia/Ho_Chi_Minh). Cùng engine với lần chạy theo lịch.

Hành động:
1. **Đọc thư viện vaccine** trong `CLAUDE.md` (`scripts/vaccine_autofixer.py` → `load_vaccines`).
2. **Quét** repo/hệ thống tìm vaccine-class issue đã biết.
3. **Auto-fix** các lỗi AN TOÀN (reuse fixer sẵn có: model id HF, internal link
   404 `--fix`, references…).
4. **Chạy QA/build** (`qa_check.py` + `zola build`).
5. **Lưu log** (`data/vaccine-autofixer.log`).
6. **Cập nhật report** `data/vaccine-autofixer-report.json` (Autofixer report by
   Vacxin) → hiển thị ở trang Insights.

Cách chạy:
- CI (khuyến nghị): GitHub Actions → **Daily Vaccine Autofixer** → *Run workflow*
  (nút "Run Daily Vaccine Autofixer" trên trang Insights mở đúng tới đây).
- Local: `python3 scripts/vaccine_autofixer.py --trigger manual`
  (thêm `--dry-run` để chỉ quét, không sửa).

Quy tắc:
- **Không chạy đồng thời** — lock `data/vaccine-autofixer-state.json` (run đang
  chạy → run mới skip với exit 3). Workflow dùng `concurrency` để queue.
- **Code change đi qua PR flow** — workflow mở PR `chore/vaccine-autofixer-*`,
  auto-merge khi QA xanh → deploy production. KHÔNG push thẳng `main`.
- Theo dõi PR tới khi **MERGED + deploy xong** (như mọi feature).

### `sec` — Chạy Security Audit toàn bộ blog

Hành động:
1. Trigger `security-audit.yml` qua workflow_dispatch.
2. Poll run đến khi completed (max 3 phút).
3. Download summary artifact + parse:
   - Python deps vulnerabilities (backend + scripts)
   - Secret leaks (gitleaks)
   - Workflow permission misconfigs
4. Output report ≤200 words: severity HIGH/MEDIUM/LOW + top 3 issues.
5. Nếu HIGH ≥ 1 → tạo issue label `security` để follow up.

### `pef` — Chạy Performance Audit toàn bộ blog

Hành động:
1. Trigger `perf-audit.yml` qua workflow_dispatch.
2. Poll run đến khi completed (max 5 phút).
3. Đọc kết quả `qa_check.py --perf`:
   - Image loading attribute coverage
   - Lazy/eager loading issues
   - Missing width/height attributes
4. Nếu workflow tự tạo PR fix → review diff (no layout/scroll touch) → merge nếu safe.
5. Bonus tại chỗ: Lighthouse mobile estimate (LCP/CLS/INP) cho homepage + 1 post.
6. Output report ≤150 words: scores + auto-fix applied + remaining issues.

### `ll` — Liệt kê chu kỳ cron của 3 workflows trọng yếu

Hành động: output bảng cron schedule + ý nghĩa cho **3 workflow QA core**:

| Workflow | File | Cron | Ý nghĩa human-readable |
|---|---|---|---|
| QA Gatekeeper | `.github/workflows/qa.yml` | `0 4 * * *` + PR/push | Daily 11:00 GMT+7 + event-based |
| Security Audit | `.github/workflows/security-audit.yml` | `0 3 * * 6` + `0 4 * * *` | Thứ 7 weekly + Daily 11:00 GMT+7 |
| Self-Healing QA | `.github/workflows/self-healing.yml` | `0 */6 * * *` + `0 4 * * *` | Mỗi 6 tiếng + Daily 11:00 GMT+7 |

**Quy tắc daily 11:00 GMT+7** (set 2026-06-15 user request):
Cả 3 workflow QA core BẮT BUỘC có cron `0 4 * * *` (= 11:00 VN time)
để baseline check mỗi sáng — bất kể tuần lễ thường hay weekend.

Bonus columns nếu user muốn detail:
- Last run status (✅ success / ❌ failure / 🔄 in_progress)
- Next scheduled run (tính từ cron expression + now)
- Runs/tháng estimate

KHÔNG diễn giải dài, chỉ output bảng + 1 dòng summary.

### `diemtoiuu` — Chấm điểm SEO toàn site + báo cáo chi tiết

Hành động Claude khi user gõ `diemtoiuu`:

1. **Build site**: `zola build` (tạo `public/` mới nhất — chấm trên HTML
   thật mà crawler nhìn thấy, không chấm trên source `.md`).
2. **Chạm điểm**: `python3 scripts/seo_score.py` (stdlib only, không cần
   pip). Script quét MỌI trang HTML trong `public/`, tự **loại trang
   alias/redirect** (Zola stub `meta refresh`) để không kéo điểm oan.
3. **Hiển thị báo cáo chi tiết NGAY tại thời điểm chấm**, gồm:
   - Điểm SEO site `/100` + hạng (A+…F), thời điểm chấm (GMT+7, `HH:MM dd/mm/yyyy`).
   - Trạng thái hạ tầng: robots.txt · sitemap.xml · atom.xml · rss.xml.
   - Phân bố hạng + bảng từng trang (điểm thấp → cao) kèm vấn đề chính.
   - Top tín hiệu thiếu phổ biến (số trang dính) + gợi ý ưu tiên.

**Thang điểm mỗi trang (tổng 100)**: title(12) · meta description(14) ·
canonical(8) · og:title(6) · og:description(6) · og:image(8) · og:type(4) ·
twitter:card(6) · JSON-LD(10) · đúng 1 `<h1>`(10) · viewport(4) ·
`<html lang>`(4) · img alt coverage(8). Điểm site = TB trang × hệ số hạ
tầng (0.95–1.00 theo robots/sitemap/feed).

Thêm `--json` → ghi `data/seo-scores.json` (cho template/đồ thị về sau).
Exit code: `0` nếu điểm ≥ 70, `2` nếu < 70 (để CI gate nếu cần).

### `content9` — Chấm điểm SEO content (front matter + alt ảnh)

Khi user gõ `content9`, Claude chạy NGAY:

```
python3 scripts/check_content_seo.py
```

Script (stdlib only) quét mọi `content/**/*.md`:
- Front matter TOML (`+++`): báo file thiếu `title` hoặc `description`.
- Body: báo ảnh markdown `![](...)` và `<img>` thiếu/empty `alt`.

Output: **danh sách file lỗi + lý do**, dòng cuối tổng số file lỗi. Exit
`1` nếu có lỗi (gate CI được), `0` nếu sạch. Claude in nguyên kết quả +
1 dòng tóm tắt, KHÔNG giải thích lý thuyết.

Khác `diemtoiuu`: `content9` soi **source `.md`** (sửa được ngay tại
frontmatter), còn `diemtoiuu` chấm **HTML đã build** trong `public/`.

### `topic: <chủ đề>` — Tự research + viết bài + deploy

Format: `topic: <nội dung chủ đề>` (không quote, có dấu hai chấm).

Ví dụ user gõ:
- `topic: nên ghé thăm nơi nào ở Hàn Quốc thời điểm này`
- `topic: cách tối ưu Lighthouse score lên 100`
- `topic: phở Hà Nội vs phở Sài Gòn`

**Hành động Claude**:
1. **Research**: tự tổng hợp kiến thức về chủ đề. Nếu cần data thời sự
   (mùa, thời tiết, sự kiện hiện tại) → dùng WebSearch tool. Nếu là
   chủ đề kỹ thuật → dùng knowledge sẵn + web fetch authoritative
   source.
2. **Chọn category** phù hợp từ `categories.json`:
   - Du lịch / địa điểm → `Du lịch` hoặc `Ẩm thực`
   - Tech / coding → `Posting` hoặc `Ẩm thực`
   - Văn hóa / con người → `Posting`
3. **Tạo slug** kebab-case từ chủ đề (max 60 ký tự, bỏ dấu tiếng Việt).
4. **TOML frontmatter** chuẩn:
   ```toml
   +++
   title = "<Title hấp dẫn ≤70 ký tự>"
   date = <today>
   [taxonomies]
   categories = ["<category>"]
   tags = [<3-8 tags relevant>]
   [extra]
   thumbnail = "https://picsum.photos/seed/<slug>/600/400"
   featured = false
   +++
   ```
5. **Body markdown** 1500-2500 từ:
   - Đoạn mở đầu hook + `<!-- more -->` cho summary
   - 5-10 sections với H2/H3
   - Code snippets nếu là tech
   - Internal links sang ≥2 bài đã có (semantic relevance)
   - External authoritative links (paper, docs, official sites)
   - Kết thúc với call-to-action hoặc reference repo/source
6. **Commit + push + PR + merge** ngay, KHÔNG hỏi user.
7. Output bảng PR summary chuẩn format section 5.

**Quality bar**:
- Tiếng Việt tự nhiên, không Google Translate
- Có quan điểm cá nhân (1st person "mình"/"tôi"), không liệt kê khô
- Code snippets test được (nếu tech)
- Facts verify được (citation)

### `topic10` — Viết 10 bài Du lịch (cùng cluster, chủ đề ngẫu nhiên)

**Mục đích**: test giả thuyết Google **topical authority** — 10 bài
cùng lĩnh vực Du lịch, internal link chéo nhau, xem hệ thống ranking
có boost cụm bài này so với bài đơn lẻ không.

**Format**: user gõ đúng `topic10` (không cần argument). Lĩnh vực
mặc định fix cứng = **Du lịch**. Nếu muốn lĩnh vực khác, dùng biến
thể tương lai (chưa support, hiện chỉ Du lịch).

**Hành động Claude** (làm 1 lèo, KHÔNG hỏi user):

1. **Sinh 10 chủ đề ngẫu nhiên cùng cluster Du lịch**. Phân bố để đa
   dạng intent search nhưng vẫn cùng niche:
   - 3 bài **điểm đến trong nước** (Việt Nam: Đà Lạt, Hà Giang, Phú Quốc, Huế, Sa Pa, Côn Đảo, Mộc Châu…)
   - 2 bài **điểm đến nước ngoài** (Nhật, Hàn, Thái, Đài Loan, Bali…)
   - 2 bài **kinh nghiệm / mẹo du lịch** (đóng vali, săn vé rẻ, đi 1 mình, bảo hiểm, visa…)
   - 2 bài **du lịch theo mùa / chủ đề** (mùa thu, mùa hoa, lễ hội, food tour, trekking…)
   - 1 bài **so sánh / review** (Đà Lạt vs Sa Pa, homestay vs khách sạn, group tour vs tự túc…)

   KHÔNG trùng chủ đề với bài đã có trong `content/du-lich/`. Check
   slug existed trước khi chốt.

2. **Mỗi bài** tuân theo spec `topic:` (mục trên), riêng các điểm sau:
   - `categories = ["Du lịch"]` (fix cứng cho cả 10)
   - `tags`: 3-8 tag, **bắt buộc** có chung 1-2 tag pillar
     (`du-lich`, `kinh-nghiem-du-lich` hoặc `viet-nam`/`nuoc-ngoai`)
     + tag riêng theo địa điểm/chủ đề con
   - `date`: stagger lùi 0/1/2/3…/9 ngày để không cùng timestamp
     (Google ghét batch dump cùng giây)
   - Body 1200-2000 từ (ngắn hơn `topic:` đơn vì làm 10 bài cùng lúc,
     ưu tiên quantity + cross-link)

3. **Internal link cluster (BẮT BUỘC)** — đây là phần test topical
   authority:
   - Mỗi bài link sang **≥3 bài khác trong batch 10 này** (anchor
     text semantic, không generic "xem thêm")
   - 1 bài chọn làm **pillar** (thường là bài "kinh nghiệm du lịch"
     tổng quát nhất) → 9 bài còn lại đều link về pillar
   - Pillar link sang cả 9 bài con (hub-spoke pattern)

4. **Slug**: kebab-case không dấu, ≤60 ký tự, unique trong batch +
   không clash với `content/du-lich/*` hiện có.

5. **Thumbnail**: dùng `https://picsum.photos/seed/<slug>/600/400`
   với seed khác nhau từng bài (auto unique do slug unique).

6. **File location**: tất cả vào `content/du-lich/<slug>.md`.

7. **Commit strategy**:
   - 1 commit duy nhất cho cả 10 bài (atomic, dễ revert)
   - Commit message: `Thêm 10 bài Du lịch (topic10 cluster test topical authority)`
   - Body commit liệt kê 10 slug + tag pillar chung
   - Push lên branch dev `claude/friendly-hawking-x4bb5m`
   - **KHÔNG merge tự động** — user tự gõ `prm` hoặc `gg` khi muốn

8. **Output bảng tổng kết** sau khi push xong:

   | # | Slug | Title | Sub-cluster | Internal links | Words |
   |---|---|---|---|---|---|
   | 1 | da-lat-thang-12 | … | trong-nước | →2,5,7 | 1450 |
   | … | … | … | … | … | … |

   Cuối bảng: 1 dòng "Pillar = bài #X. Tổng từ = N. Tag chung = `du-lich`."

**Quality bar** (kế thừa `topic:` + bổ sung):
- 10 bài KHÔNG được paraphrase nhau → mỗi bài cần unique angle/data
- Tag pillar overlap nhưng tag con phải khác nhau (tránh duplicate
  taxonomy index)
- Internal anchor text không lặp ("xem bài này" ❌ → "kinh nghiệm
  săn vé rẻ tới Đà Nẵng" ✅)
- Stagger date để Google index tự nhiên, không nghi spam batch

**Lý do thiết kế** (trả lời câu hỏi user "hệ thống chấm điểm có liên
quan cùng chủ đề không"):

Có. Google từ 2022 (Helpful Content System) + 2023 (E-E-A-T
update) đánh giá **topical authority** — site nào có nhiều bài cùng
cluster + internal link chặt sẽ được boost so với site rải rác mỗi
chủ đề 1 bài. `topic10` mô phỏng đúng pattern "pillar + 9 cluster
posts" mà các SEO agency lớn dùng. Sau khi deploy 10 bài, đợi 2-4
tuần rồi check Search Console: nếu impression cluster Du lịch tăng
đáng kể so với baseline → confirm topical authority có hiệu lực.

### `bm` — Bảo mật check leak credentials/secrets toàn repo

Hành động full security audit cho leak:

1. **Scan patterns** (regex + gitleaks-style):
   - GitHub PAT: `ghp_*`, `github_pat_*`
   - AWS keys: `AKIA[0-9A-Z]{16}`, `aws_secret_access_key`
   - Google: `AIza[0-9A-Za-z_-]{35}`, Service Account JSON
   - OpenAI: `sk-[A-Za-z0-9]{48}`
   - Stripe: `sk_live_*`, `pk_live_*`
   - Slack: `xox[abp]-*`
   - Generic: `password=`, `secret=`, `api_key=`, `private_key=`,
     `bearer token`, `BEGIN PRIVATE KEY`
2. **Scope quét**:
   - File checked-in trên main branch
   - Git history 100 commits gần nhất (nếu leak rồi xoá → vẫn còn trong history)
   - File specific: `config.toml`, `*.env`, `.env.*`, `README.md`,
     `services/**`, `content/**`, `static/**`
3. **Nếu phát hiện leak**:
   - **Apply fix** ngay:
     - Replace secret bằng placeholder + commit
     - Thêm pattern vào `.gitignore`
     - Nếu trong history → suggest `git filter-repo` hoặc BFG
   - **Tạo GitHub Issue** với label `security` + tag `@user` để
     trigger email notification:
     - Title: `[BM] Security leak detected: <type> in <file>`
     - Body: chi tiết file/line/pattern + cách rotate credential
   - **Tạo PR cô lập** chứa fix:
     - Title: `Security fix: redact <type> in <file>`
     - Body: mô tả + warning user phải rotate credential
4. **Nếu KHÔNG phát hiện** → output: `BM scan clean. No leak detected.`
5. **Email notification**: thông qua GitHub Issue mention
   `@Banhang-Chogao` → GitHub tự gửi email đến 292648126+Banhang-Chogao@users.noreply.github.com.

CONSERVATIVE: chỉ flag pattern 95%+ confident (avoid false positive
như `secret=` trong tutorial code). Test mode trước khi flag prod.

### `??` — Tại sao chưa thấy tính năng lên production?

User hỏi 2 dấu hỏi liên tiếp = đang phàn nàn "đã commit xong nhiều rồi
mà tính năng chưa thấy trên blog real". Claude PHẢI:

1. **List 10 commits gần nhất** trên branch dev `claude/bold-gauss-51gh3c`
   (`git log origin/main..HEAD --oneline`) + commits đã merge vào main
   gần đây.

2. **Với mỗi commit**, check 4 trạng thái:
   - **A**: commit có trong branch dev nhưng CHƯA merge main → chờ batch
   - **B**: commit đã merge main, deploy đang chạy (in_progress) → đợi
   - **C**: commit đã merge main, deploy FAIL → vì sao (Tera bug, etc.)
   - **D**: commit đã merge main, deploy SUCCESS → tính năng đã live
     (user reload sai cache?)

3. **Output bảng thống kê** format:

| Commit | Title | Branch | Status | Nguyên nhân chưa live |
|---|---|---|---|---|
| #abc1234 | Mobile menu fix | dev | A | Chưa merge — chờ batch ≥10 commits |
| #def5678 | Slack workflow | main | C | Deploy fail: Tera literal dict (line 534) |
| #ghi9012 | Author-box | main | D | ✅ LIVE — user thử reload Ctrl+Shift+R |

4. **Hành động đề xuất** ngay cuối:
   - Nếu nhiều A → gợi ý `manual #X` hoặc đợi đủ 10
   - Nếu C → fix hotfix ngay (vì block deploy)
   - Nếu D nhưng user vẫn không thấy → hard reload + clear CDN cache

KHÔNG hỏi user, exec ngay.

### `score` — Trigger workflow Build Semantic Related Posts

Hành động: trigger manual `build-related.yml` qua workflow_dispatch.

1. `mcp__github__actions_run_trigger` với `workflow_id=build-related.yml`,
   `ref=main`
2. Output: "Triggered Build Semantic Related Posts. Check status với
   `run list build-related.yml` sau ~3 phút."
3. KHÔNG poll status — user tự check qua tab Actions hoặc gõ `run list`.

Use case: sau khi viết bài mới, gõ `score` để rebuild data/related.json
+ data/scores.json ngay, không đợi cron `*/5 * * * *`.

### `seo` — Tối ưu SEO cho bài blog mới trong 5h gần nhất

Hành động: Scan `content/posting/*.md` với frontmatter `date` ≥ now() − 5h
(hoặc file mtime ≥ 5h). Với mỗi bài match, apply checklist tối ưu SEO:

**Frontmatter checks:**
- `title` ≤ 70 ký tự (Google SERP cut-off). Quá dài → đề xuất rút gọn.
- `description` trong frontmatter (Tera template render meta description).
  Nếu thiếu → tự generate từ đoạn đầu body (max 160 ký tự).
- `[taxonomies] tags` ≥ 3 và liên quan keywords.
- `[extra] thumbnail` Open Graph image, aspect 1200×630 chuẩn.

**Body checks:**
- H1 chỉ 1 lần (Zola tự render từ `title` → trong body dùng H2+ thôi).
- H2/H3 chứa keyword chính phụ.
- Alt text trên `![...](url)` images không rỗng.
- Internal links tới ≥ 2 bài liên quan khác (cross-reference network).
- External authoritative links (paper, docs) → tăng E-E-A-T signal.

**Auto-actions Claude làm:**
1. Đọc `[taxonomies]` tags + suy ra keyword chính.
2. Thêm `description` field vào frontmatter nếu thiếu.
3. Generate JSON-LD Article schema (qua macro `seo.html` nếu chưa có).
4. Đề xuất 2-3 internal link tới bài đã có dựa trên semantic similarity
   (data/related.json).
5. Verify Open Graph meta + Twitter Card meta đang render.

**Output**: bảng tóm tắt mỗi bài:

| Slug | Title len | Description | Tags | Internal links | Status |
|---|---|---|---|---|---|
| post-A | 58 ✓ | added | 5 ✓ | 2 added | ✅ optimized |
| post-B | 78 ❌ | exists | 7 ✓ | 0 | ⚠ title too long |

Commit + push + PR + merge nếu auto-actions không cần user approval.

### `SEO9` — Tu bổ SEO toàn site đạt chuẩn Google 100%

Khác `seo` (chỉ bài mới 5h). `SEO9` là **site-wide audit + fix** nhắm
mục tiêu **Lighthouse SEO category = 100/100** dựa theo Google Search
Central guidelines (https://developers.google.com/search/docs).

**12 hạng mục bắt buộc kiểm + tự fix nếu phát hiện thiếu**:

| # | Yêu cầu Google | Implementation Zola |
|---|---|---|
| 1 | `<title>` ≤ 60 ký tự, unique mỗi page | Tera `{% block title %}` trong từng template; verify không trùng |
| 2 | `<meta name="description">` ≤ 160 ký tự | `base.html` render từ `page.description` / `section.description` / `config.description` |
| 3 | `<link rel="canonical">` | Render `{{ current_url }}` mỗi page trong `base.html` |
| 4 | `viewport` mobile-friendly | `<meta name="viewport" content="width=device-width, initial-scale=1">` đã có — verify |
| 5 | `lang` attribute trên `<html>` | `<html lang="vi">` trong `base.html` |
| 6 | Open Graph (og:title/description/image/url/type) | Macro `seo.html` render tất cả; image 1200×630 |
| 7 | Twitter Card (`summary_large_image`) | Cùng macro `seo.html` |
| 8 | JSON-LD structured data | Article schema cho post, BreadcrumbList cho section, Organization cho homepage |
| 9 | `sitemap.xml` valid + submit Search Console | Zola tự render `sitemap.xml`. Verify `<lastmod>` đúng + ping Google |
| 10 | `robots.txt` allow crawling | `static/robots.txt`: `User-agent: * Allow: / Sitemap: <url>` |
| 11 | Image `[alt]` non-empty | Grep `<img>` không có `alt=`; require alt cho mọi ảnh trừ decorative (`aria-hidden`) |
| 12 | Internal linking + crawl depth ≤ 3 | Mọi post reachable từ homepage trong ≤ 3 clicks |

**Hành động khi user gõ `SEO9`**:

1. **Audit**: scan tất cả `templates/*.html` + `content/**/*.md` +
   `config.toml`. Output bảng 12 dòng (yêu cầu / pass-fail / file ảnh hưởng).
2. **Auto-fix safe**:
   - Thiếu `description` page → generate từ summary 160 chars
   - Thiếu canonical → inject vào `base.html`
   - Thiếu lang="vi" → add
   - Thiếu OG/Twitter macro → tạo `templates/macros/seo.html` + include
   - Thiếu JSON-LD → render Article schema trong `page.html`
   - `robots.txt` thiếu sitemap → append
   - `<img>` thiếu alt → liệt kê file cần manual add (KHÔNG đoán nội dung alt)
3. **Pages-specific**:
   - Trigger PageSpeed Insights (`fetch_pagespeed.py`) cho 5 URL chính
     (homepage, /posting/, 1 bài random, /branding-guideline/, /scoring/)
   - Verify Mobile + Desktop scores SEO ≥ 95/100
4. **Trigger sitemap ping Google**: GET
   `https://www.google.com/ping?sitemap=<url>` sau khi deploy
5. **Output report** ≤ 300 words:

| # | Hạng mục | Before | After | File touched |
|---|---|---|---|---|
| 1 | Title length | 8 pages > 60 chars | 0 ❌ → user fix manual | content/posting/*.md |
| 2 | Meta description | 12 missing | 12 added | base.html, page.html |
| 3 | JSON-LD | none | Article + Breadcrumb | macros/seo.html (new) |
| ... | ... | ... | ... | ... |

**Final score**: ước tính Lighthouse SEO 100/100 sau khi merge fix PR.

**KHÔNG được auto-merge** — tuân thủ rule 16:00. Tạo PR + nhắc user
`manual #<số>`.

### `SEO10` — Loop audit + fix từng lỗi đến khi 0 issue

Khác `SEO9` (single-pass + auto-fix bulk). `SEO10` là **iterative loop**
chạy đến khi audit không còn lỗi nào.

**Nguồn chuẩn**: Google SEO Starter Guide chính thức
https://developers.google.com/search/docs/fundamentals/seo-starter-guide
(luôn fetch URL này MỖI lần invoke để lấy phiên bản mới nhất — Google
update guide định kỳ).

**Workflow loop**:

```
iter = 1
while iter ≤ MAX_ITER (default 20):
    1. Fetch Google SEO Starter Guide (WebFetch URL trên)
    2. Re-derive checklist từ guide hiện tại (không hardcode — dynamic)
    3. Audit toàn site: templates/ + content/ + config.toml + static/robots.txt
    4. Nếu issues_count == 0 → BREAK (success)
    5. Sort issues theo priority (Google's "Critical" → "Recommended" → "Optional")
    6. Pick TOP 1 issue (highest priority + đơn giản nhất → đảm bảo progress)
    7. Apply fix ĐÚNG 1 issue đó (1 commit / 1 file change)
    8. Verify: re-run zola build → pass
    9. Log iter N: { issue, file, before, after }
    10. iter++
```

**Hard rules trong loop**:

- **1 iter = 1 commit**. KHÔNG batch fix.
- **Mỗi iter** PHẢI verify `zola build` PASS trước khi tiếp.
- **Mỗi iter** PHẢI ghi log `.ff/seo10-log.jsonl` (audit trail).
- **MAX_ITER = 20** safety cap. Nếu chưa clean → escalate user với
  list issue còn lại.
- **KHÔNG đoán content** cho `<img alt>` — gặp alt thiếu → escalate
  với danh sách file user phải fill manual.
- **KHÔNG auto-merge** (rule 16:00). Cuối loop: tạo 1 PR gộp tất cả
  iter, nhắc user `manual #<số>`.

**Priority order theo Google Starter Guide**:

1. **Critical** (block index/crawl):
   - `robots.txt` block toàn site
   - Sitemap thiếu / invalid XML
   - `<title>` thiếu / duplicate / > 60 chars
   - `<meta description>` thiếu / > 160 chars
   - `noindex` meta tag sai trên content pages
2. **Important** (giảm SERP):
   - Canonical thiếu / sai
   - Open Graph thiếu (giảm CTR social)
   - JSON-LD Article thiếu (giảm rich snippet)
   - Heading hierarchy sai (H1 không có / nhiều H1)
   - URL có ký tự lạ / quá dài
3. **Recommended** (E-E-A-T + UX):
   - Image alt missing
   - Internal link descriptive text
   - hreflang nếu multi-lang
   - Mobile viewport
   - HTTPS verify
4. **Optional** (polish):
   - Twitter Card (legacy)
   - Schema.org thêm types (FAQPage, HowTo, BreadcrumbList)
   - Lazy load `<img loading="lazy">`

**Output sau loop**:

| Iter | Issue | File | Action | Status |
|---|---|---|---|---|
| 1 | Title > 60 chars | content/posting/foo.md | Rút "Cách quản lý..." → "Quản lý..." | ✅ Fixed |
| 2 | OG image missing | templates/base.html | Inject macro seo.html | ✅ Fixed |
| ... | ... | ... | ... | ... |
| N | (clean) | — | — | ✅ 0 issues remain |

**Final summary**:
- Total iters: N
- Critical fixed: X
- Important fixed: Y
- Recommended fixed: Z
- Escalated (need human): img alt × M files
- PR: #<số> đang chờ `manual #<số>` merge

**Use case khác `SEO9`**:
- `SEO9`: 1 lần audit → 1 PR fix safe → done, không re-verify
- `SEO10`: loop tới sạch 100% → mỗi fix là 1 commit để rollback dễ →
  cuối cùng PR có audit trail per-issue, code review dễ hơn

### `SEO11` — Hybrid 2-phase: bulk fix + loop polish

Tổng hợp hài hoà ưu điểm của `SEO9` (bulk + Lighthouse-aligned, nhanh)
và `SEO10` (loop + Starter Guide dynamic, sạch tới 100%). Mục tiêu:
**1 PR duy nhất** chứa 2 phase rõ ràng, code review nhẹ + Lighthouse
SEO = 100/100.

**Workflow 2 phase**:

```
PHASE 1 — Bulk safe-fix (SEO9 mode)
  1. Audit 12 hạng mục Lighthouse cố định (xem SEO9 table)
  2. Apply auto-fix safe trong 1 commit gộp
     - description / canonical / lang / OG macro / JSON-LD /
       robots.txt sitemap / viewport
  3. zola build PASS → commit "SEO11 phase 1: bulk Lighthouse fixes"

PHASE 2 — Iterative polish (SEO10 mode)
  4. Fetch Google SEO Starter Guide URL chính thức
     https://developers.google.com/search/docs/fundamentals/seo-starter-guide
  5. Re-audit dynamic checklist từ guide hiện tại
  6. Loop iter 1..MAX_ITER (default 15, thấp hơn SEO10 vì phase 1 đã quét bulk):
     a. Pick TOP 1 issue priority cao nhất còn lại
     b. Apply fix 1 issue → 1 commit nhỏ
        "SEO11 phase 2 iter N: <issue label>"
     c. zola build PASS verify
     d. iter++
  7. Nếu MAX_ITER hết mà còn issue → escalate user với punch list

PHASE 3 — Verification (chung)
  8. Trigger fetch_pagespeed.py cho 5 URL chính
  9. Verify SEO mobile + desktop ≥ 95
  10. Ping sitemap Google Search (nếu deploy thành công)
  11. Tạo 1 PR gộp tất cả commit phase 1 + 2
  12. Output summary report (xem bên dưới)
```

**Hard rules**:

- Phase 1 PHẢI thành công (≥10/12 hạng mục pass) MỚI sang phase 2.
  Nếu phase 1 fail >2 hạng mục → escalate user, không sang phase 2.
- Phase 2 mỗi iter = 1 commit (audit trail). KHÔNG batch.
- Phase 2 mỗi iter PHẢI `zola build` PASS trước khi commit.
- KHÔNG đoán content cho `<img alt>` → escalate user manual.
- KHÔNG auto-merge (rule 16:00). Tạo PR + nhắc `manual #<số>`.

**Output report cuối cùng**:

```
## SEO11 Hybrid Audit Report

### Phase 1 — Bulk fix (1 commit)
| # | Hạng mục Lighthouse | Before | After |
|---|---|---|---|
| 1 | Title length | 8 violation | 8 fixed |
| 2 | Meta description | 12 missing | 12 added |
| ... | ... | ... | ... |
Phase 1 result: 11/12 ✓ → sang phase 2

### Phase 2 — Iterative polish (N commits)
| Iter | Issue | File | Action | Status |
|---|---|---|---|---|
| 1 | OG image dimensions | base.html | Add 1200×630 ref | ✅ |
| 2 | Canonical absolute URL | base.html | Strip trailing / | ✅ |
| ... | ... | ... | ... | ... |
Phase 2 result: N iter, 0 issue remain

### Phase 3 — Verification
- PageSpeed Mobile SEO: 100/100 ✓
- PageSpeed Desktop SEO: 100/100 ✓
- Sitemap ping Google: triggered ✓
- Escalated to user: 3 img cần alt manual

### PR
#<số> — chờ `manual #<số>` merge
```

**Use case khác cả 2**:
- `SEO9`: quick win 1 shot. Tốt khi tin checklist Lighthouse đã đủ.
- `SEO10`: deep cleanup, tốn iter. Tốt khi nghi ngờ checklist cũ
  thiếu items mà Google mới update.
- `SEO11`: best-of-both. Phase 1 quick-win Lighthouse, phase 2 catch
  edge case Starter Guide mới. PR cuối có 2 section review riêng.

### `nangcap` — Nâng cấp bài viết cũ đạt chuẩn SEO/AdSense QA

**Mục đích**: quét lại TOÀN BỘ bài cũ bằng đúng bộ chấm điểm sẵn có
(`scripts/seo_qa_checker.py`, thang 100đ bám tiêu chí on-page Google — cũng là
chuẩn nội dung để qua AdSense review), tự **chọn** bài điểm thấp và **nâng cấp**
nội dung cho đạt chuẩn. Claude TỰ QUYẾT bài nào cần sửa, không hỏi lại.

Khác `content9` (chỉ soi front matter thiếu title/description/alt) và `SEO9/10/11`
(sửa template + meta site-wide): `nangcap` **sửa thẳng nội dung bài** (`content/**/*.md`)
để kéo điểm SEO QA từng bài lên. KHÔNG đụng template/CSS/desktop.

**Chuẩn đạt = 90 điểm (hạng A).** Bài đã ≥ 90 coi như đạt chuẩn → BỎ QUA.

**Cú pháp**:
- `nangcap` — quét & nâng cấp **TẤT CẢ** bài dưới chuẩn (< 90) trong 1 lần,
  KHÔNG giới hạn số lượng (sửa từ thấp điểm nhất lên). PR có thể lớn — chấp nhận.
- `nangcap N` — giới hạn N bài (ưu tiên thấp điểm nhất) nếu muốn chia nhỏ.
- `nangcap content/<đường-dẫn>.md` — ép nâng cấp đúng 1 bài chỉ định.

**Workflow**:

```
1. Refresh DB điểm: python3 scripts/seo_qa_checker.py --all
   → ghi data/seo-qa-scores.json (điểm + breakdown + issues mỗi bài).
2. Đọc DB, CHỌN bài cần nâng cấp: TẤT CẢ bài < 90 (chưa đạt chuẩn A), sửa từ
   THẤP NHẤT lên. Bỏ qua bài đã ≥ 90. Ưu tiên chú ý bài mất nhóm điểm lớn:
   keyword (20đ), word_count (10đ), description (10đ), headings (8đ).
3. Với MỖI bài đã chọn, sửa đúng tiêu chí bị mất điểm — SAFE, KHÔNG bịa:
   - [extra] seo_keyword: suy từ khoá chính theo title/chủ đề (mở khoá 20đ).
   - Đưa keyword vào: title (nửa đầu) · đoạn mở đầu · ≥ 1 heading H2.
     Chỉ chỉnh nhẹ câu chữ, GIỮ NGUYÊN ý + sự thật của bài.
   - description 50–160 ký tự, chứa keyword (không để Zola tự cắt summary).
   - Thêm ≥ 1 internal link (@/... tới bài/section liên quan) + ≥ 1 external
     link tới NGUỒN UY TÍN, CÓ THẬT (không bịa URL).
   - Đảm bảo: ≥ 2 heading H2 · ≥ 3 tag · [extra] thumbnail (og:image) ·
     mọi ảnh có alt · có date.
   - Bài < 600 từ → viết bổ sung đoạn ĐÚNG CHỦ ĐỀ cho đủ độ sâu (không nhồi
     keyword, không độn chữ vô nghĩa).
   - Đoạn > 150 từ → tách nhỏ cho readability.
   - Tuân thủ rule Category ("Tất cả" đầu mảng) + Ảnh WebP + Timezone GMT+7.
4. Re-score bài vừa sửa (PostToolUse hook tự chấm + lưu DB). Mục tiêu mỗi bài
   ≥ 90 (hạng A). Chưa đạt → chỉnh tiếp tới khi đạt hoặc chỉ còn tiêu chí ngoài
   tầm safe-fix (báo lại punch list).
5. zola build PASS (binary pin trong deploy.yml) + qa_check.py PASS.
6. Auto commit → auto merge → auto deploy theo CLAUDE.md §"Auto hết". Build đỏ
   → LẬP TỨC ff/ff9 cho tới xanh.
```

**Hard rules**:
- TUYỆT ĐỐI không bịa số liệu/sự kiện/nguồn để lấy điểm — thà điểm thấp còn hơn
  sai sự thật. external link phải là trang thật, uy tín, đúng ngữ cảnh.
- Không đổi ý nghĩa/giọng bài gốc; chỉ bồi đắp + chuẩn hoá tín hiệu SEO.
- `<img alt>` cần mô tả nội dung ảnh thật — nếu không suy được an toàn thì để
  alt mô tả chung theo title, KHÔNG bịa chi tiết ảnh.
- Mỗi bài nâng cấp = 1 commit rõ ràng (audit trail): `nangcap: <slug> C→A (76→92)`.

**Output report** (≤ 250 từ):

| Bài | Trước | Sau | Tiêu chí đã vá |
|---|---|---|---|
| baochi/f18-crash… | 70 (C) | 92 (A) | seo_keyword, internal+external link |
| posting/zola-vs-hugo | 78 (C) | 90 (A) | description, kw_heading |
| ... | ... | ... | ... |

Cuối report: số bài đã nâng, điểm trung bình trước→sau, bài còn < 90 (nếu có)
kèm lý do (ngoài safe-fix scope).

### `morning` — Macro chạy chuỗi tất cả shortcut

**Mục đích**: 1 lệnh sáng startup chạy toàn bộ shortcut khác để có
bức tranh trạng thái + tự apply audit/fix/SEO/security trong 1 lần.

**Quy tắc loại trừ**:
- Bỏ chính `morning` (tránh infinite loop).
- Bỏ shortcut cần **argument** mà không có default:
  - `topic:` (cần đề tài)
  - `baomoi` (cần topic)
  - `manual #X` (cần PR number cụ thể)
  - `help` (chỉ render bảng — không có hành động)
- Bỏ shortcut **sinh nội dung mới** (không thuộc cycle audit/deploy):
  - `topic10` (10 bài Du lịch — user chủ động gọi khi muốn test
    topical authority, không nên auto trong morning)
  - `baomoi` (bài/series từ topic — chỉ khi user chủ động gọi)
- Bỏ shortcut **overlap chức năng** (tránh chạy 2 lần work giống):
  - Giữ `SEO11` (hybrid), bỏ `SEO9` + `SEO10`
  - Giữ `ff`, bỏ `healing` (overlap pattern fix)
  - `pp` (HOTFIX) chỉ chạy nếu phát hiện deploy đỏ — conditional

**Thứ tự thực thi (non-conflict, 6 phase)**:

```
┌─ PHASE A — Snapshot (read-only, baseline state) ─────────────┐
│ 1. cautruc9   — folder tree (in ra để confirm structure)    │
│ 2. ??         — deploy status A/B/C/D table                  │
│ 3. run list   — workflow runs hiện tại                       │
└──────────────────────────────────────────────────────────────┘

┌─ PHASE B — Audit + trigger workflows (no state change) ─────┐
│ 4. bm         — security leak scan toàn repo + git history  │
│ 5. ad         — full blog audit (workflow_dispatch async)   │
│ 6. pef        — performance audit (Lighthouse mobile/desk)  │
│ 7. score      — trigger build-related.yml (rebuild SBERT)   │
└──────────────────────────────────────────────────────────────┘

┌─ PHASE C — Content optimize (create PRs, không merge) ───────┐
│ 8. seo        — optimize bài blog mới ≤5h                    │
│ 9. SEO11      — site-wide hybrid Lighthouse + Starter Guide  │
└──────────────────────────────────────────────────────────────┘

┌─ PHASE D — Fix failed runs (create PRs, không merge) ────────┐
│ 10. ff        — analyze failed workflow + auto-fix pattern   │
└──────────────────────────────────────────────────────────────┘

┌─ PHASE E — Conditional HOTFIX ───────────────────────────────┐
│ 11. pp        — CHỈ chạy nếu phase D detect deploy đỏ critical │
└──────────────────────────────────────────────────────────────┘

┌─ PHASE F — Merge gate (cuối cùng, consume PRs phases C+D) ──┐
│ 12. gg        — list PRs trạng thái (tuân rule 16:00 list-only) │
│ 13. prm       — override merge ALL open PRs (per shortcut)   │
└──────────────────────────────────────────────────────────────┘
```

**Tại sao thứ tự này tránh xung đột**:

| Risk | Mitigation |
|---|---|
| `ff` + `healing` cùng auto-fix → 2 PR cùng pattern | Skip `healing`, giữ `ff` |
| `SEO9/10/11` overlap | Giữ `SEO11` (hybrid), skip 2 cái còn lại |
| `prm` merge trước khi `ff`/`SEO11` tạo PR | `prm` ở phase F cuối → consume hết PR mới tạo |
| `ad` + `pef` cùng trigger performance audit | `ad` chỉ dispatch async; `pef` chạy local Lighthouse → bổ trợ |
| `score` rebuild related khi `seo` đang sửa bài | `score` chỉ async trigger; `seo` modify content. SBERT rebuild sau merge tự nhiên |
| `bm` phát hiện leak trong commit `ff` tạo | `bm` chạy phase B (trước `ff`) → baseline; nếu `ff` tạo leak mới sẽ bị catch lần `morning` sau |

**Output sau morning** (≤500 words, gộp tất cả phase):

```markdown
## ☀ Morning Brief — <timestamp>

### Phase A — Snapshot
- Repo structure: <cây folder gọn>
- Deploy status: X commits A, Y D
- Workflow runs: N pending / M failed

### Phase B — Audit
- Security: 0 leaks (or list)
- Audit workflows: dispatched (perf-audit + security-audit + pef)
- Score rebuild: triggered

### Phase C — Content + SEO
- New posts optimized: N (slugs)
- SEO11 PR: #<số> (phase 1: X fixes, phase 2: Y iter)

### Phase D — Fix
- ff PR: #<số> (Z failed runs analyzed)

### Phase E — HOTFIX
- (none) hoặc: pp PR #<số>

### Phase F — Merge
- gg: N open PRs listed
- prm: M PRs merged → deploy queued
```

**Skip điều kiện**:
- Nếu phase B `bm` phát hiện leak → BREAK toàn bộ morning, escalate
  user fix trước (security ưu tiên cao nhất).
- Nếu phase C `SEO11` phase 1 fail >2 hạng mục → skip phase 2 + phase D.
- Nếu phase D `ff` không có failed run → skip phase E.

**KHÔNG được skip rule 16:00 cho `gg`** — `gg` ở phase F chỉ list,
không merge. Chỉ `prm` (đã là override explicit) mới merge.

### `run list` — Hiển thị bảng workflow runs

Hành động: Output Markdown table 4 cột, format chuẩn để user audit workflow.

**Format bắt buộc**:

| Run ID | Workflow | Cause | Status |
|---|---|---|---|
| #<id1>, #<id2> (gộp nếu cùng cause + workflow) | <workflow name> | <root cause ngắn gọn> | ✅ Resolved by PR #X / ⚠ Pending / ❌ Active |

**Quy tắc nội dung**:
- Gộp nhiều run ID cùng workflow + cùng cause vào 1 row (e.g., `#A, #B, #C (3 runs)`)
- Cause: 1 dòng ≤ 60 ký tự, dùng inline code cho symbol (`default(value={})`)
- Status icons:
  - ✅ Resolved by PR #X — fix đã merge
  - ✅ Resolved — không tự trigger nữa (handler removed/disabled)
  - ⚠ Pending fix — đang work in progress
  - ❌ Active failure — chưa có hướng giải quyết
- Sort theo: Status (❌ trước, ⚠ giữa, ✅ sau) → recency desc

**Scope mặc định**: 20 run gần nhất trên `main`. Kèm context (e.g., `run list deploy.yml`) → filter theo workflow đó.

### `theodoi8` — Theo dõi LIÊN TỤC trạng thái commit đang chạy trên GitHub (auto-refresh)

**Mục đích**: Màn hình **theo dõi live tự cập nhật** trạng thái CI/CD của các commit
gần nhất trên GitHub Actions — commit nào đang `queued`/`in_progress`, commit nào đã
`success`/`failure`/`cancelled`. **KHÔNG phải snapshot 1 lần**: theodoi8 **tự động poll
GitHub liên tục** và in lại bảng mỗi vòng cho tới khi mọi commit về terminal (hoặc user
dừng). READ-ONLY, KHÔNG trigger lại, KHÔNG merge/push.

**Khác các shortcut gần giống**:
- `run list` — audit workflow runs theo cause + resolution (1 lần).
- `??` — vì sao feature chưa lên production (bảng commit A/B/C/D).
- `runner` — retry/tiếp tục task đang dở.
- `theodoi8` — **vòng lặp live, auto-refresh**, theo dõi TỪNG commit (queued/running/done)
  tới khi chạy xong; không phán xét cause, không sửa gì.

**Chế độ chạy** (mặc định = LIÊN TỤC — luật 2026-06-19 user request):
- `theodoi8` — **auto-refresh liên tục**: poll GitHub mỗi **~30–45s**, in lại bảng mỗi
  vòng, **tự dừng** khi không còn run `in_progress`/`queued` (mọi commit terminal) hoặc
  khi user gõ dừng/`unwatch`. **KHÔNG bắt user gõ lại** mỗi lần.
- `theodoi8 once` — chỉ **1 snapshot** rồi dừng (hành vi 1 lần).
- `theodoi8 deploy` — lọc chỉ commit chạy trên `deploy.yml` (vẫn auto-refresh).
- `theodoi8 <sha>` — soi đúng 1 commit + mọi run của nó (vẫn auto-refresh tới khi xong).

**Vòng lặp auto-refresh (mỗi ~30–45s)**:

1. **Lấy commit gần nhất** (mặc định 10): `mcp__github__list_commits` (per_page=10)
   trên `main` + commit `origin/main..HEAD` của branch dev (chưa merge) nếu có.
2. **Map commit → workflow run**: `mcp__github__actions_list`
   (`method=list_workflow_runs`, per_page≈30, mới nhất trước) → match theo `head_sha`.
   1 commit nhiều run (deploy/qa/…) → gộp theo commit. Kết quả thường > token cap →
   lưu file rồi parse bằng Python (slice theo ký tự).
3. **Đọc trạng thái live**: `status` (`queued`/`in_progress`/`completed`) +
   `conclusion` (`success`/`failure`/`cancelled`/`skipped`).
4. **In lại bảng** (snapshot mới đè nội dung cũ), sort: đang chạy trước (🔄/⏳) → mới
   nhất. **Đánh dấu commit vừa ĐỔI trạng thái** so với vòng trước (vd `🔄→✅`, `🔄→❌`).
5. **Tự dừng** khi mọi run terminal → in bảng cuối + tóm tắt. Còn run đang chạy → đợi
   interval rồi lặp lại bước 1.

| Commit | Message | Workflow (run #) | Trạng thái | Đổi? |
|---|---|---|---|---|
| `a1b2c3d` | feat: authority booster | Build & Deploy #767 | 🔄 in_progress | — |
| `e4f5g6h` | refresh merge report | QA Gatekeeper #1718 | ✅ success | 🔄→✅ |
| `i7j8k9l` | compliance auto-fix | Build & Deploy #766 | ⊘ cancelled | — |

   **Icon trạng thái**:
   - 🔄 `in_progress` · ⏳ `queued`/`waiting` — đang chạy
   - ✅ `success` — xong, pass
   - ❌ `failure` — xong, fail (gợi ý `ff` nếu trên `deploy.yml`/`qa`)
   - ⊘ `cancelled` (vàng) — bị huỷ; **KHÔNG phải lỗi thật** nếu có run mới hơn `success`
     (concurrency — xem Vaccine V5 / Build Dashboard rule)
   - ⏭ `skipped`

**Tóm tắt mỗi vòng** ≤1 dòng:
`theodoi8 [vòng N]: 🔄 A đang chạy · ✅ X pass · ❌ Y fail · ⊘ Z huỷ (HH:MM:SS dd/mm/yyyy GMT+7)`

**Hard rules**:
- **READ-ONLY** — chỉ đọc status, KHÔNG re-trigger / rerun / merge / push.
- **Auto-refresh, KHÔNG bắt user gõ lại**: tự lặp poll tới khi xong. Interval ~30–45s,
  **KHÔNG** < 20s/vòng (tránh GitHub API rate-limit — Vaccine V5).
- **Điều kiện dừng** (chống chạy vô hạn): dừng khi (a) mọi run terminal, hoặc (b) chạm
  cap an toàn **~30 vòng / ~20 phút** → hỏi user có tiếp tục không, hoặc (c) user gõ
  dừng/`unwatch`.
- `cancelled` ≠ `failed`: deploy run mới nhất `success` → site OK, đừng báo degraded.
- `failure` thật trên `deploy.yml`/`qa` → báo + gợi ý `ff`, KHÔNG tự sửa trong `theodoi8`.

**Ghi chú triển khai auto-refresh (Claude Code)**:
- Vòng lặp = agent poll lặp lại MCP (`actions_list`/`list_commits`) mỗi interval rồi in
  lại bảng — mỗi vòng là 1 lần cập nhật trên màn hình kết quả này.
- Rảnh tay/định kỳ nền: có thể dùng skill `/loop` (vd `/loop 1m theodoi8 once`) để chạy
  lại theo lịch mà không cần gõ tay.

### `runner` — Retry / tiếp tục lệnh đang dở

**Mục đích**: Khi có tác vụ đang chạy dở, bị gián đoạn, timeout, hoặc fail tạm
thời — user gõ `runner` để Claude **tiếp tục** hoặc **thử lại** thay vì bắt đầu
lại từ đầu.

**Hành động**:

1. **Quét trạng thái đang dở** (theo thứ tự):
   - Background shell tasks (terminals) — `in_progress`, `failed`, exit code ≠ 0
   - GitHub Actions runs `in_progress` / `queued` / `waiting` trên repo zola
   - Workflow runs `failure` gần nhất (≤1h) có khả năng retry (network, rate
     limit, race, runner timeout)
   - Chuỗi shortcut macro bị ngắt giữa chừng (vd `morning` dừng ở phase D)
   - Pipeline Claude đang thực thi bị interrupt hoặc context limit giữa chừng

2. **Output bảng snapshot** trước khi hành động:

| Task | Loại | Trạng thái | Hành động |
|---|---|---|---|
| deploy #123 | GH Actions | in_progress | Poll tiếp |
| zola build | Shell | failed (exit 1) | Retry |
| morning phase D | Macro | paused | Resume từ phase D |

3. **Retry / continue** (ưu tiên cao → thấp):
   - **GH Actions `in_progress`/`queued`**: poll `actions_get` đến `completed`
     (max 5 phút) — KHÔNG re-trigger
   - **GH Actions `failure` retryable**: `gh run rerun <id>` hoặc
     `actions_run_trigger` (workflow_dispatch) nếu run không rerun được
   - **Shell failed**: chạy lại lệnh cuối (cùng cwd + env), tối đa 3 lần,
     backoff 10s giữa các lần
   - **Macro shortcut dở**: resume từ phase/step cuối đã log — KHÔNG chạy lại
     phase đã ✅
   - **Không có gì dở**: báo `Không có task pending.` + gợi ý `run list` audit

4. **Hard rules**:
   - KHÔNG restart macro từ đầu nếu đã có progress log
   - KHÔNG `git push --force` hoặc merge để "unstick" — chỉ retry safe ops
   - KHÔNG retry lệnh destructive (`rm -rf`, force push) — escalate user
   - Mỗi retry ghi 1 dòng log: `task · attempt N/3 · result`

5. **Output cuối** ≤150 từ:

```
runner: retried N · continued M · still pending K · escalated E
```

Nếu vẫn stuck sau 3 lần → gợi ý `ff` (fix workflow) hoặc `??` (deploy status).

**Phạm vi mở rộng** (user kèm context):
- `runner deploy` — chỉ poll/retry workflow deploy
- `runner shell` — chỉ retry lệnh terminal gần nhất
- `runner morning` — resume macro `morning` từ phase dở

### `backend8` — So main SHA vs Render backend SHA (split-brain check, V16)

**Mục đích**: Phát hiện **split-brain static ↔ backend** — GitHub Pages luôn ship `main`
mới nhất, nhưng backend FastAPI trên Render (`blog-vipzone-api`) chỉ redeploy khi **Manual
Sync** thủ công. Khi backend tụt sau `main`, endpoint VIP premium tồn tại trong repo nhưng
**404 ở production** → "Premium gộp gói" hỏng âm thầm dù CI xanh.

**Lệnh**:

```bash
python3 scripts/backend_sha_check.py            # human summary + data/backend-status.json
python3 scripts/backend_sha_check.py --json      # machine JSON (cho theodoi8 / Insights)
python3 scripts/backend_sha_check.py --offline    # bỏ network → status unknown (nhanh)
python3 scripts/backend_sha_check.py --strict      # exit 2 nếu BACKEND_OUTDATED (gate tùy chọn)
```

**Cách hoạt động**:

- So `git rev-parse origin/main` với `/health.deployed_sha` của backend (Render inject
  `RENDER_GIT_COMMIT`, expose qua `services/vipzone/main.py`).
- Trạng thái: `in_sync` (không cần làm gì) · `outdated` → **BACKEND_OUTDATED** (Render →
  Blueprints → **Manual Sync `blog-vipzone-api`**) · `unknown` (dyno ngủ / chưa set
  `RENDER_GIT_COMMIT` → retry, **KHÔNG** báo success giả).
- **Report-only** (exit 0) — offline-safe, 1 GET `/health` + exponential backoff, cache
  `data/backend-status.json`. KHÔNG gate CI trừ khi `--strict`.

**Companion `deploysafe8`**: sau khi merge thay đổi backend (`services/**`) + deploy Pages
xanh → chạy `backend8` **TRƯỚC** khi coi là "done". Pages xanh + backend SHA cũ = **CHƯA
xong** (split-brain). Human action duy nhất: Render Manual Sync (Claude không deploy Render
được).

**Liên quan**: Vaccine **V16** (CLAUDE.md §4) · `theodoi8` surface `BACKEND_OUTDATED` sau deploy.

### `tieptuc8` — Tiếp tục & hoàn tất TẤT CẢ tác vụ đang dở

**Mục đích**: Một lệnh "dọn sạch việc dở" — khi có **nhiều** tác vụ còn dang dở
(chưa xong) tích lại trong session/repo, user gõ `tieptuc8` để Claude **tự rà soát
TOÀN BỘ** rồi **tiếp tục/hoàn tất từng cái cho tới khi xong hết**, không bỏ sót,
không hỏi lại từng bước.

**Khác `runner`**: `runner` retry **một** lệnh/workflow/macro vừa bị gián đoạn gần
nhất; `tieptuc8` **quét sạch backlog** — mọi việc còn ở trạng thái chưa-terminal
(todo còn mở, thay đổi chưa commit/push, commit chưa lên `main`, PR chưa merge, CI
đỏ, macro dở, background task đang chạy) — và **đẩy từng cái về trạng thái hoàn tất**.

**Hành động**:

1. **Rà soát toàn bộ tác vụ chưa xong** (theo thứ tự ưu tiên P0 → P1 — xem CLAUDE.md
   "Task Priority Policy"):
   - **Todo / checklist** của session hiện tại còn item `in_progress` / `pending`.
   - **Working tree**: thay đổi chưa commit; commit chưa push
     (`git status`, `git log origin/<branch>..HEAD`).
   - **Branch dev** có commit chưa lên `main` (chưa qua auto-merge).
   - **Open PRs** chưa merge (CI đang chạy / chờ auto-merge / conflict).
   - **GitHub Actions** `in_progress` / `queued` cần đợi; `failure` gần nhất (≤1h)
     cần fix.
   - **Macro shortcut** bị ngắt giữa chừng (vd `morning` dừng ở phase D).
   - **Background shell tasks** chưa kết thúc.

2. **Output bảng backlog** trước khi hành động:

   | # | Tác vụ | Loại | Trạng thái | Hành động tiếp |
   |---|---|---|---|---|
   | 1 | Bài "xyz" đang viết dở | Content | pending | Viết nốt + push |
   | 2 | fix CSS navbar | Working tree | chưa commit | Commit + push |
   | 3 | PR #501 | GitHub | CI chạy | Để auto-merge |
   | 4 | deploy #770 | GH Actions | in_progress | Poll tới xong |

3. **Tiếp tục / hoàn tất từng tác vụ** (P0 trước, P1 sau):
   - **Việc Claude làm dở** (viết bài, sửa code, fix) → **làm nốt cho xong** rồi
     push (automation tự đưa lên `main` theo ZERO_BARRIER).
   - **Thay đổi chưa push** → commit message rõ ràng + push.
   - **Macro dở** → resume từ phase/step cuối đã log (KHÔNG chạy lại phase ✅).
   - **GH Actions `in_progress` / `queued`** → poll tới `completed` (READ-ONLY,
     KHÔNG re-trigger).
   - **CI `failure`** trên `deploy.yml` / `qa` → tự chẩn + fix theo Vaccine §4 /
     `ff` / `ff9` trên **cùng branch** tới khi xanh.
   - **PR chờ auto-merge** → để pipeline lo (KHÔNG babysit, trừ khi user yêu cầu).

4. **Hard rules**:
   - **Hoàn tất, không bỏ dở**: mỗi tác vụ phải về terminal (done / merged / pushed /
     escalated) — KHÔNG để lửng lơ.
   - **P0 trước P1**: việc user yêu cầu xong trước, job nền (audit/bot) tiếp sau.
   - **KHÔNG restart từ đầu** nếu đã có progress — resume từ checkpoint.
   - **KHÔNG** thao tác destructive (`rm -rf`, force push, merge bừa khi CI đỏ) để
     "unstick" — escalate user.
   - Đẩy thay đổi xong = giao cho pipeline auto-merge (CLAUDE.md §Git) — KHÔNG canh
     PR trừ khi user chủ động yêu cầu.

5. **Output cuối** (checklist trạng thái, ≤150 từ):

   ```
   tieptuc8: hoàn tất A · tiếp tục B · đang đợi C · escalate D
   ```

   Liệt kê rõ cái nào ✅ xong, cái nào 🔄 còn chạy (CI/deploy), cái nào ⚠ cần user.
   Việc ngoài tầm safe-fix → nêu punch list 1 dòng/việc.

**Phạm vi mở rộng** (user kèm context):
- `tieptuc8 content` — chỉ hoàn tất các bài viết đang dở.
- `tieptuc8 ci` — chỉ poll/fix workflow + PR đang chạy.
- `tieptuc8 push` — chỉ commit + push các thay đổi chưa lên branch.

Nếu **không có tác vụ nào dở** → báo `tieptuc8: không có tác vụ pending.` + gợi ý
`run list` (audit workflow) hoặc `??` (deploy status).

### `wip8` — Read-only workspace tracker (tái dựng task đang dở)

**Mục đích**: Nhìn vào trạng thái workspace hiện tại (git status, file thay đổi,
commits gần nhất, open PRs, CI jobs) để **tái dựng task đang dở** mà không cần user
nhớ lại hay giải thích. **READ-ONLY hoàn toàn**: không sửa file, không commit, không
push, không mở PR, không deploy.

**Khác các shortcut gần giống**:
- `tieptuc8` — quét backlog rồi **tiếp tục/hoàn tất** task dở (có write operations).
- `runner` — retry lệnh/workflow đang fail.
- `theodoi8` — theo dõi live CI/CD trên GitHub Actions (auto-refresh).
- `wip8` — **read-only snapshot**: reconstruct "mình đang làm gì?" rồi dừng lại, không can thiệp.

**Hành động** (thứ tự):

> **Thu thập dữ liệu:** chạy `python3 scripts/wip8.py --data` (in JSON git status/
> diff/log/stash/branch, READ-ONLY) HOẶC các lệnh git thô bên dưới. **Render ra
> user = MARKDOWN GitHub-flavored** (harness tự vẽ bảng header xám + link xanh +
> emoji) — KHÔNG dán ANSI box của `rich` (xấu trong UI chat). `rich`/`pyfiglet`
> chỉ dùng khi chạy local terminal thật (`python3 scripts/wip8.py`).

1. `git status --short` — file staged / modified / untracked.
2. `git diff --stat HEAD` — xem quy mô thay đổi từng file.
3. `git log --oneline -8` — commits gần nhất để suy feature đang làm.
4. `git stash list` — có stash đang giữ lại không.
5. **Branch context** — branch hiện tại, ahead/behind so với upstream.
6. **Open PRs** trên GitHub cho branch hiện tại (qua MCP).
7. **Running jobs** — GitHub Actions đang `in_progress` / `queued` liên quan branch.
8. **Suy luận task** — từ diff, commit messages, tên file thay đổi, TODO markers trong code.
9. **Nhóm files** — gom file thay đổi theo feature/tính năng (không liệt kê flat).

**Output format bắt buộc — MARKDOWN GitHub-flavored, theo design discipline của
[B-DNA](/tools/b-dna/)** (calm enterprise: kicker đánh số · KPI nhấn số · health
meter · section có 1-dòng purpose · neutral làm nền, accent điểm nhấn). Mỗi
section mở đầu heading emoji + kicker `NN —`; dữ liệu bảng markdown (header tự
shade) + file path `link/inline-code`. KHÔNG plain code-block `# Header`, KHÔNG ANSI.

**Brand bar + Health meter (in TRƯỚC mọi section — bắt chước consistency-checker B-DNA):**

```
### wip8 · Workspace DNA tracker
🕒 <HH:MM dd/mm/yyyy> (GMT+7) · read-only snapshot

**Workspace health** ▰▰▰▰▰▰▰▰▰▰ 100% · ✅ CLEAN — <reason 1 dòng>
```

- Lấy từ `python3 scripts/wip8.py --data` → field `health` (`score/verdict/tone/
  meter/reason`). Verdict + màu: ✅ **CLEAN** (pass) · 🟡 **WIP/PENDING/BEHIND**
  (warn) · 🔴 **BLOCKED** (fail, có conflict). Meter dùng `▰`/`▱` (10 ô).
- Workspace tracker coi `dirty` = đang làm (WIP, không phải lỗi); chỉ conflict = BLOCKED.

**Bộ ICON chuẩn (chọn đúng ngữ cảnh — KHÔNG xài 1 icon cho mọi mục):**

| Ngữ cảnh | Icon | | Ngữ cảnh | Icon |
|---|---|---|---|---|
| Tổng quan / điều tra | 🔎 | | Branch | 🌿 |
| Upstream / package | 📦 | | Trạng thái / tiến độ | 📊 |
| Stash | 🗂️ | | Files changed | 📝 |
| File mới | 🆕 | | File sửa | ✏️ |
| File xoá | 🗑️ | | File rename | 🔀 |
| Untracked | ❓ | | Validation / test | 🧪 |
| Blockers | 🚧 | | Next step / việc tay | 🔧 |
| PR / link | 🔗 | | Deploy | 🚀 |
| Running jobs | 🛰️ | | **Vaccine (kim tiêm)** | 💉 |
| CI ok/chạy/fail/none | 🟢 🟡 🔴 ⚪ | | Time (GMT+7) | 🕒 |

Mỗi section = `#### NN — <emoji> <TITLE>` + blockquote 1 dòng purpose (như
`bdna__sec-desc`), rồi bảng/nội dung.

**`01 — 🔎 TỔNG QUAN`** · _purpose: branch context + trạng thái làm việc._

| Mục | Giá trị |
|---|---|
| 🌿 Branch | `<branch>` · **ahead N / behind M** (KPI nhấn số) |
| 📦 Upstream | `<origin/...>` |
| 📝 Task | <1–2 câu suy từ diff + commit messages> |
| 🗂️ Stash | <stash hoặc "không có"> |
| 🚧 Blockers | <điều đang chặn; "Không có"> |
| 🔧 Next step | <1 hành động rõ ràng tiếp theo> |

**`02 — 📝 FILES CHANGED`** · _purpose: gom thay đổi theo feature, không liệt kê flat._

| Nhóm / Feature | File | Loại |
|---|---|---|
| <feature> | `path/to/file` | 🆕 new / ✏️ modified / 🗑️ deleted |

> Sạch → in `✅ Working tree sạch — 0 file thay đổi.` thay bảng.

**`03 — 🔗 PR & CI`** · _purpose: PR mở + trạng thái pipeline cho branch._

| PR | Title | Branch | CI |
|---|---|---|---|
| #X | <title> | `<branch>` | 🟢 / 🟡 / 🔴 / ⚪ |

> Vaccine/hotfix → 💉; deploy → 🚀; job đang chạy → 🛰️.
> Không có PR/job → `Không có PR mở hay job đang chạy cho branch này.`

**Quy tắc trình bày**: heading emoji hợp ngữ cảnh từng section (🔎/📝/🔗/🧪/🔧);
icon vaccine LUÔN là 💉 (kim tiêm); bảng markdown có header; file path inline-code
hoặc link; thời gian GMT+7 `HH:MM dd/mm/yyyy` (prefix 🕒). KHÔNG văn xuôi dài cho
trường bảng hoá được; KHÔNG dán ANSI.

**Cú pháp mở rộng**:
- `wip8` — full workspace scan (mặc định) → render markdown.
- `wip8 quick` — chỉ status + branch (bỏ log).
- `wip8 <path>` — chỉ inspect file/folder cụ thể.
- Local terminal có màu: `python3 scripts/wip8.py [--quick] [<path>]` (rich/pyfiglet).
- Lấy data JSON: `python3 scripts/wip8.py --data`.

**Hard rules**:
- **READ-ONLY** — KHÔNG sửa, commit, push, deploy, mở PR. Chỉ đọc + in.
- **Markdown-first**: output cho user là markdown GitHub-flavored (harness render
  bảng/link/emoji đẹp). ANSI `rich` chỉ cho terminal local, KHÔNG dán vào chat.
- **Icon đúng ngữ cảnh** — theo bảng trên; vaccine = 💉.
- **Không đoán mò**: thiếu tín hiệu → báo `Không đủ context để suy task` thay vì bịa.
- **Chỉ chạy 1 lần** rồi dừng (dùng `theodoi8` nếu cần live feed CI).
- Kết quả là **snapshot tại thời điểm gọi** — gọi lại `wip8` để refresh.

### `manu9` — Auto-approve tất cả PRs do Claude tạo

**Mục đích**: Batch approve PRs pending do Claude/automation tạo, chuẩn bị cho merge.

**Hành động**:
1. List tất cả open PRs (`mcp__github__list_pull_requests state=open`)
2. Filter PRs có author = `github-actions[bot]` hoặc branch name chứa `claude/`
3. Submit approval review cho mỗi PR:
   - Method: `pull_request_review_write` với event=`APPROVE`
   - Body: "✅ Approved by automation"
4. Output bảng tóm tắt:

| PR | Title | Author | Status |
|---|---|---|---|
| #X | ... | github-actions[bot] | ✅ Approved |
| #Y | ... | claude/* | ✅ Approved |

**Scope**: Chỉ approve PRs do **automation/Claude** tạo, KHÔNG approve manual PRs từ user.

**Output cuối**: "N PRs approved. Sẵn sàng merge với `prm` hoặc `manual #X`."

KHÔNG auto-merge — chỉ approve, user quyết định merge.

### `prn` — PR Now (đẩy thay đổi hiện tại thành PR vào main)

**Mục đích**: Gom thay đổi hiện tại (uncommitted hoặc commit chưa lên main)
thành 1 PR vào `main`, chờ user duyệt tay. Tuân thủ rule Git ở CLAUDE.md.

**Hành động**:

1. **Detect**: scan working tree + commit chưa có trên `origin/main`.
   - Nếu KHÔNG có thay đổi nào → báo "không có gì để PR", dừng.

2. **Dùng NHÁNH CHUNG cố định** `claude/seo-1j0frj` (KHÔNG tạo nhánh lẻ
   mới — theo CLAUDE.md "10 PR 1 nhánh"):
   - `git fetch origin main` → reset nhánh về `origin/main` mới nhất.
   - Apply/commit thay đổi → push `claude/seo-1j0frj` (force-with-lease).

3. **Tạo PR**:
   - Title: mô tả thay đổi (≤70 chars).
   - Body: tóm tắt + phạm vi an toàn.
   - **Base branch: `main`** (mặc định của repo).
   - Status: **pending** (KHÔNG auto-merge, kể cả khi CI xanh).

4. **Output**:

```
✅ Pushed → claude/seo-1j0frj
✅ PR #X created → main (pending, chờ duyệt tay)
   Manage: https://github.com/.../pull/X
```

**Workflow**:
```
main (production)
  ↓ (user gõ `prn` — gom thay đổi)
claude/seo-1j0frj (nhánh làm việc chung)
  ↓ (PR to main, pending)
main  ← user gõ `manual #X` / `prm` / `gg` để merge tay
```

**NOT auto-merge** — luôn pending tới khi user gõ `manual #X` / `prm` / `gg`.

### `ff9` — Smart Conflict Resolver (Python-powered)

**Mục đích**: Tự động detect + analyze + resolve git conflicts trong open PRs.

**Hành động**:

1. **Scan conflicts**:
   - List tất cả open PRs
   - Checkout từng branch, merge main → detect conflicts
   - Report PRs có conflicts

2. **Analyze conflicts** (Python):
   - Dùng `libparse` / `ast` để parse conflicted files (JSON, TOML, Python, JS)
   - Identify conflict pattern:
     - **Merge conflict markers** (`<<<<<<<`, `=======`, `>>>>>>>`)
     - **Type**: Content conflict vs structural (Schema) conflict
     - **Severity**: Safe (whitespace/comment) vs Risky (logic)
   - Suggest resolution strategy:
     - `OURS` (keep main) / `THEIRS` (keep branch)
     - `MANUAL` (require human review)

3. **Auto-resolve** (safe patterns only):
   - Whitespace/formatting conflicts → normalize
   - TOML/JSON schema conflicts → merge-tool guided
   - Comment/doc conflicts → keep both
   - Code logic conflicts → escalate MANUAL

4. **Apply fixes**:
   - Commit resolve + push lên branch
   - Trigger GitHub to re-check merge status

5. **Output report**:

| PR | Branch | Files with conflict | Strategy | Status |
|---|---|---|---|---|
| #X | claude/foo | config.toml | AUTO (TOML merge) | ✅ Resolved |
| #Y | claude/bar | site.scss (2x) | MANUAL (logic) | ⚠️ Escalated |

**Final summary**: "X conflicts resolved auto, Y require manual review. Ready to merge."

**Safe fallback**: Nếu conflict quá phức tạp → output diff + escalate user manual review.

### `bb` — Xử lý bài báo từ Dân Trí / VnExpress (Interactive article processor)

**Mục đích**: Copy-paste nội dung bài báo từ Dân Trí/VnExpress → Claude tự viết lại theo phong cách blog cá nhân → auto-commit vào nhánh `baochi` → PR → merge ngay.

**Hành động**:

1. **Prompt user**:
   - Gõ `bb`
   - Claude hỏi: "📰 Dán nội dung bài báo (hoặc chỉ heading + URL):"
   
2. **Nhập liệu**:
   - User copy-paste full bài hoặc chỉ title + nội dung chính
   - Format chấp nhận: text thô hoặc đã format markdown
   - URL bài báo (optional, để tham khảo source)

3. **Parse + analyze**:
   - Extract title, publish date (nếu có), nội dung chính
   - Detect category theo content từ nội dung:
     - "Du lịch", "Ẩm thực", "Công nghệ", "Ngân hàng", "Thế giới", "Bảo hiểm", "Điện ảnh"… → map vào `categories.json`
   - **BẮT BUỘC**: mọi bài sinh bằng `bb` PHẢI có category mặc định `"Tất cả"`
     (đứng đầu) + `"Báo chí"`, kèm category auto-detect theo content. Ví dụ
     `categories = ["Tất cả", "Bảo hiểm", "Báo chí"]`.
     Nếu category mới chưa có trong `categories.json` → thêm vào file đó.
   - Sinh slug kebab-case từ title

4. **Rewrite engine**:
   - Claude viết lại bài từ đầu (KHÔNG paraphrase máy móc)
   - Giọng cá nhân: 1st person ("mình", "tôi"), quan điểm riêng
   - Tổng hợp kiến thức từ nội dung gốc → mở rộng góc nhìn độc lập
   - Thêm internal links tới 2-3 bài liên quan nếu có
   - Output tối thiểu ~1000 từ (lý tưởng 1000–1800), tự nhiên Tiếng Việt
     (xem "Tiêu chí AdSense-friendly" bên dưới)

5. **Build frontmatter** (tuân thủ rule SEO + rule Category trong CLAUDE.md):
   ```toml
   +++
   title = "<Tiêu đề hấp dẫn 20–65 ký tự, chứa từ khoá chính>"
   description = "<50–160 ký tự, chứa từ khoá chính>"
   date = <hôm nay>
   [taxonomies]
   categories = ["Tất cả", "<content-category auto-detected>", "Báo chí"]
   tags = [<3-6 tags relevant>]
   [extra]
   thumbnail = "https://picsum.photos/seed/<slug>/600/400"
   seo_keyword = "<từ khoá chính>"
   featured = false
   +++
   ```
   - **Bắt buộc**: bài viết bằng `bb` thuộc nhánh `baochi` → LUÔN có category
     mặc định `"Tất cả"` + `"Báo chí"`, kèm category theo content nếu detect được.
   - Nếu không detect được content-category → chỉ `["Tất cả", "Báo chí"]`.

6. **Auto-workflow**:
   - Checkout nhánh `baochi` (hoặc create nếu không tồn tại)
   - Write file `content/baochi/<slug>.md`
   - Commit: `feat: Add Dân Trí article — <short title>`
   - Push lên `baochi`
   - Tạo PR từ `baochi` → `main`
   - **MERGE NGAY** (bypass 16:00 rule vì là article aggregation, KHÔNG code)
   - Trigger deploy

7. **Output summary**:
   ```
   ✅ Bài báo xử lý thành công
   📝 Slug: <slug>
   🏷️ Category: <auto-detected>
   🔗 PR: #<số> → merged
   🚀 Deploy: in progress
   ```

**Quality checks**:
- Tiếng Việt tự nhiên, KHÔNG AI-generated flavor
- KHÔNG plagiarize từ bài gốc → trích dẫn source properly
- Có quan điểm cá nhân hoặc góc nhìn mới
- Internal links semantic (không generic "xem thêm")

**Tiêu chí AdSense-friendly (BẮT BUỘC — áp dụng cho cả `bb` và `bb9`)**:

> Mục tiêu: nội dung đủ chuẩn để Google AdSense duyệt + giữ E-E-A-T. Mọi bài
> sinh bằng `bb`/`bb9` PHẢI đạt:

- **Độ dài tối thiểu ~1000 từ** (nâng từ 800; lý tưởng 1000–1800). Bài mỏng
  < 800 từ KHÔNG đăng — viết sâu thêm hoặc gộp.
- **Nội dung gốc, nghiên cứu kỹ, giá trị thật** — không xào nấu máy móc, không
  chỉ tóm tắt 1 nguồn. Thêm phân tích/quan điểm/ví dụ của riêng mình.
- **Định dạng tốt**: ≥ 2 heading H2 (ưu tiên H2/H3 dạng câu hỏi để bắt PAA),
  đoạn ngắn dễ đọc, ≥ 1 ảnh minh hoạ có `alt`.
- **Block FAQ + `FAQPage` schema** (`[[extra.faq]]`, 3–5 câu) cho bài
  so-sánh/how-to/"là gì"/giá cả/du lịch/banking. Bài tin ngắn/quan điểm thì
  KHÔNG nhồi FAQ.
- **YMYL (tài chính/ngân hàng/bảo hiểm/y tế/pháp lý)**: nêu rõ "chỉ mang tính
  tham khảo, không phải lời khuyên chuyên nghiệp"; đối chiếu nguồn chính thức;
  link tới trang [Điều khoản & Miễn trừ](/terms/) khi cần.
- **Disclosure affiliate/referral (BẮT BUỘC khi bài có link giới thiệu/affiliate)**:
  chèn ngay sau `<!-- more -->` một blockquote minh bạch, ví dụ:
  `> 💡 **Minh bạch:** Bài này có chứa liên kết giới thiệu. Nếu bạn đăng ký qua
  liên kết, tác giả có thể nhận thưởng — bạn không mất thêm chi phí. Chi tiết
  tại [Điều khoản & Miễn trừ](/terms/).`
- **Tránh nội dung bị AdSense cấm/hạn chế**: không nội dung người lớn, cờ bạc,
  vi phạm bản quyền, gây hiểu lầm, hoặc kêu gọi click quảng cáo.
- **Internal + external links** uy tín, có thật (không bịa URL).

**Network fallback**:
- Nếu user cung cấp URL nhưng network blocked → skip crawl, dùng content họ paste
- Không vì không fetch được mà block shortcut

---

### `bb9 <topic>` — Viết bài theo chủ đề + hẹn giờ đăng (scheduled publish n+3, buổi tối)

**Cú pháp gọi (BẮT BUỘC)**: `bb9 <tên chủ đề>` — LUÔN kèm **tên chủ đề** ngay
sau phím tắt, KHÔNG gõ trơ `bb9`. Tên chủ đề chính là đề tài để Claude tự viết
bài (khác `bb` là dán sẵn nội dung báo). Ví dụ:
`bb9 ưu điểm thẻ tín dụng Liobank`, `bb9 mẹo tiết kiệm điện mùa hè`.
Nếu user gõ `bb9` mà thiếu tên chủ đề → HỎI lại "viết về chủ đề gì?", KHÔNG tự
bịa chủ đề.

**Mục đích**: Từ một chủ đề, tự viết bài mới BẤT CỨ LÚC NÀO nhưng KHÔNG đăng ngay
— lưu dạng **draft** và hẹn tự động đẩy lên production **3 ngày sau (n+3), vào
buổi tối**, với điều kiện vượt qua QA gate. Đây là biến thể "hẹn giờ" của `bb`.

> Về SEO/Google: Google KHÔNG có quy định bắt buộc phải trì hoãn đăng — bài mới
> được index nhanh là tốt. Trì hoãn n+3 chỉ là buffer để review/giãn lịch đăng,
> KHÔNG hại SEO; quan trọng hơn là đăng đều đặn (consistency). Mặc định n+3 ngày,
> có thể chỉnh số ngày nếu user yêu cầu.

**Hành động**:

1. Từ `<topic>` → viết bài mới (giọng cá nhân 1st person, **tối thiểu ~1000 từ**,
   tuân thủ đủ "Tiêu chí AdSense-friendly" ở mục `bb`), frontmatter SEO đầy đủ,
   category `["Tất cả", "<auto theo topic>", "Báo chí"]`, tự sinh slug kebab-case
   từ topic, ảnh nội bộ (nếu có) → sinh `.webp` theo rule Ảnh.
2. **Khác `bb`**: KHÔNG merge/đăng ngay. Frontmatter thêm:
   ```toml
   date = <ngày n+3, tức hôm nay + 3>
   draft = true
   [extra]
   publish_at = "<n+3>T20:00:00+07:00"   # 20:00 buổi tối, giờ VN
   ```
   - `draft = true` → Zola build BỎ QUA, bài không lên site.
   - `publish_at` = ngày viết + 3, lúc **20:00 GMT+7**.
3. Commit draft (`feat(draft): hẹn đăng <title> lúc <publish_at>`), push + merge
   vào `main` (draft nằm trên main vẫn AN TOÀN — không lên site vì `draft=true`).
4. **Tự động sau đó**: workflow `scheduled-publish.yml` chạy mỗi tối (cron 20:00
   GMT+7) → `scripts/scheduled_publish.py` flip bài tới hạn (`draft=false`, set
   `date`, xoá `publish_at`) → nếu **PASS QA** (`qa_check.py` + Zola build) thì
   commit + push → deploy production. **Fail QA → KHÔNG đăng**, mở issue để fix
   (chạy `ff`).

**Output summary**:
```
✅ Bài đã lưu draft + hẹn đăng
📝 Slug: <slug>
🗓️ Đăng tự động: <n+3> lúc 20:00 (GMT+7)
🔒 Trạng thái: draft (chưa lên site)
🤖 Gate: scheduled-publish.yml → QA pass mới lên production
```

**Đăng sớm thủ công**: chạy `python3 scripts/scheduled_publish.py` (sau khi sửa
`publish_at` về quá khứ) hoặc trigger workflow `scheduled-publish` (workflow_dispatch).

---

### `baomoi <topic>` — Bài/series từ chủ đề, category AI-driven, SEO Google

**Cú pháp (BẮT BUỘC)**: `baomoi <chủ đề>` — luôn kèm topic sau phím tắt.
Gõ `baomoi` trống → hỏi lại topic, KHÔNG tự bịa.

Ví dụ:
- `baomoi ChatGPT Agent mới của OpenAI`
- `baomoi Hàn Quốc tăng lương tối thiểu`
- `baomoi BHXH 1 lần 2026`

**Mục đích**: Từ một chủ đề user nhập, tự sinh **một bài hoàn chỉnh** hoặc
**chuỗi bài (series)** nếu chủ đề cần độ sâu/cluster — Markdown production-ready,
tuân Google SEO + E-E-A-T + Helpful Content, **không hardcode category**.

**Khác `bb` / `bb9` / `topic:`**:
- `bb` = dán sẵn nội dung báo; `bb9` = hẹn giờ draft; `topic:` = 1 bài posting đơn.
- `baomoi` = **topic-driven**, AI quyết định **đơn vs series**, **section** (`baochi` /
  `posting`), **category theo nghĩa nội dung** (không ép `"Báo chí"` nếu không phải tin).

#### Category policy (BẮT BUỘC)

1. Đọc `categories.json` → chọn category **khớp search intent & nghĩa chủ đề**.
2. **KHÔNG hardcode** category cố định (vd luôn Ngân hàng, luôn Báo chí).
3. Mảng frontmatter: `categories = ["Tất cả", "<category AI chọn>", …]` — `"Tất cả"`
   luôn đứng đầu (rule Category CLAUDE.md).
4. Thêm `"Báo chí"` **chỉ khi** bài là tin/thời sự đăng `content/baochi/`.
5. Category mới chưa có trong `categories.json` → **chỉ tạo khi thật sự cần**,
   append vào `categories.json`, dedupe sort.

#### Hành động Claude

1. **Parse topic** từ `baomoi <topic>`.
2. **Research** (WebSearch khi cần số liệu/thời sự 2026); E-E-A-T — nguồn chính
   thức, không bịa policy/số liệu.
3. **Quyết định scope**:
   - **Single** (~1500–2500 từ): chủ đề hẹp, FAQ/how-to, tin đơn.
   - **Series** (2–5 bài): chủ đề rộng/policy nhiều mảng — mỗi bài đủ depth,
     cross-link trong cluster, slug riêng; gắn `[extra].series` nếu khớp series
     manifest có sẵn.
4. **Chọn section**: tin nhanh/thời sự → `content/baochi/`; evergreen/guide/tool
   → `content/posting/`. AI quyết định theo intent, không mặc định một section.
5. **Viết nội dung** (GLOBAL WRITING RULES + SEO CONTENT SYSTEM RULE):
   - Tiếng Việt tự nhiên, giọng blogger (`mình`/`tôi`), không AI fluff.
   - Title ≤60 ký tự · description ≤155 · `seo_keyword` focus.
   - ≥2 H2 · ≥3 tag · **≥5 internal link** (gồm 1 hub chuyên mục
     `/categories/<slug>/`) · ≥1 external uy tín nếu có trích dẫn.
   - `[[extra.faq]]` 3–8 câu khi phù hợp snippet; CTA/next-step cuối bài.
   - YMYL (tài chính/BHXH/ngân hàng): disclaimer tham khảo + link `/terms/` khi cần.
   - **Ảnh**: KHÔNG picsum/CDN ngoài — bỏ `[extra] thumbnail` để placeholder hệ
     thống, hoặc ảnh user cung cấp.
   - **Copyright**: có nguồn ngoài → `[[extra.references_external]]` hoặc để macro
     `references::section` tự sinh sau `build_references.py`.
6. **Tránh duplicate**: grep slug/title tương tự trong `content/` — update bài cũ
   thay vì tạo trùng; series không lặp ý giữa các part.
7. **UI/UX**: không thêm CSS/JS — template `page.html` lo TOC/Related/FAQ schema.
   Tham chiếu S-DNA calm enterprise (`/tools/s-dna/`), Branding + Font Guideline.
8. **Quality gate** (trước commit):
   ```bash
   python3 scripts/build_references.py
   python3 scripts/seo_qa_checker.py content/<path>.md   # mỗi bài; ≥90 khuyến nghị
   python3 qa_check.py
   python3 scripts/check_internal_links.py
   ```
9. **Ship**: commit **chỉ file liên quan** (content, `categories.json` nếu đổi,
   `data/references.json` / `data/seo-qa-scores.json` nếu hook sinh) → push branch
   hiện tại → pipeline auto-merge/deploy (ZERO_BARRIER). **KHÔNG** mở PR thủ công.

**Output (summary only, ≤150 từ)**:
```
baomoi ✅
Topic: <topic>
Loại: single | series (N bài)
Files: <slug1.md>[, …]
Category: Tất cả · <AI category>[ · Báo chí]
SEO QA: <score>/100
QA: pass|fail
Push: <branch> → auto-merge
```

**Morning / runner**: `baomoi` cần argument → **loại** khỏi `morning` (giống `topic:`).

---

## 3. Workflow Auto-Heal — quy trình chuẩn

Mọi action/workflow failed PHẢI đi qua pipeline 3 bước:

```
[FAILED] ─→ Thu log (gh run view --log-failed)
         ─→ Đối chiếu vaccine (vaccine_rules.py ↔ CLAUDE.md)
         ─→ Safe fix (qa-failed.py)
         ─→ Branch fix/ci-auto-<run_id> → PR → QA.yml validate
         ─→ Chờ review thủ công (KHÔNG push main, KHÔNG auto-merge)
```

**Claude tự quyết định** (không hỏi user):
- Phiên bản Node.js phù hợp với từng action (smart eval per section 1)
- Hướng xử lý lỗi tối ưu (conservative khi unknown, aggressive khi pattern rõ)
- Khi nào escalate qua issue thay vì cố fix mù

Workflow handler cũ `qa-failed-handler.yml` đã gỡ (15/06/2026 11:37, PR #89).
Thay bằng `.github/workflows/build-failure-handler.yml` (16/06/2026):
trigger khi `deploy.yml` / `qa.yml` fail → `qa-failed.py` → branch
`fix/ci-auto-<run_id>` → PR (KHÔNG push main, KHÔNG auto-merge).
Vaccine rules: `scripts/vaccine_rules.py` ↔ CLAUDE.md V1–V4.

`qa-failed.py` vẫn chạy manual qua shortcut `ff` / `healing` khi cần.

Nguyên tắc khi chạy `qa-failed.py`:
- **Buffer + retry**: sleep 30s trước khi poll, max 5 lần × 30s
- **CHỈ** tạo issue khi exhaust retry HOẶC unknown pattern HOẶC fix fail
- **CONSERVATIVE**: KHÔNG đoán fix, không force-push để giải quyết race

Nếu user muốn re-enable handler workflow → restore file `qa-failed-handler.yml`
từ git history (commit trước 11:37 ngày 15/06/2026).

---

## 4. Nguyên tắc thực thi (BẤT BIẾN)

1. **KHÔNG vỡ scroll desktop**: cấm anti-pattern `html, body { overflow-x: hidden }`,
   cấm `overflow: hidden` body không scope mobile, cấm `height: 100vh` thừa.
   (chi tiết: `CLAUDE.md`)
2. **KHÔNG vỡ layout**: code mới phải verify Lighthouse CLS ≤ 0.1 trước merge.
3. **Responsive bắt buộc**: mọi thay đổi CSS phải có Mobile (≤720px) + Desktop
   tách biệt block, có comment header `/* ===== DESKTOP ===== */` + `/* ===== MOBILE ===== */`.
4. **Trách nhiệm ổn định**: Claude chịu trách nhiệm đảm bảo blog luôn green:
   - Deploy fail → fix ngay trong cùng turn
   - Verify CI status sau mỗi merge
   - Báo cáo proactively nếu phát hiện regression

---

## 4.4. Link quản lý PR (cập nhật 18/06/2026 — ZERO_BARRIER)

**Source of truth**: https://github.com/Banhang-Chogao/zola/pulls

Claude PHẢI:
1. **Track tất cả PRs** tại link trên — dashboard duy nhất, không cache local.
2. **Mỗi feature/fix** → branch riêng → PR vào `main`.
3. **CI pass → auto-merge ngay** qua `auto-merge.yml` — không chờ user.
4. **Deploy production** tự động sau merge (`deploy.yml`).
5. **Workflow fail trên main** → `build-failure-handler.yml` + `qa-rule-checker.yml`
   auto-trigger → auto-fix PR → auto-merge khi CI xanh.

Mỗi lần tạo PR mới:
"PR #X created. CI xanh → auto-merge → deploy. Track: https://github.com/Banhang-Chogao/zola/pulls"

## 4.5. Quy trình Deploy (MỚI NHẤT — ZERO_BARRIER, 18/06/2026)

**🚨 RULE (ghi đè mọi rule PR-only / manual merge trước đó)**:

**PR → auto-merge → deploy production.** Không kiểm duyệt trung gian.
Canonical: `CLAUDE.md`, `docs/OPERATIONS.md`, `data/auto-merge-policy.json`.

### Quy trình bắt buộc

1. **Một yêu cầu = một branch + một PR**:
   - `feature/`, `fix/`, `qa/`, `content/`, `chore/`, `policy/` + mô tả ngắn
   - Commit → push → tạo PR

2. **Auto-merge khi CI xanh**:
   - `qa-check` (QA Gatekeeper) pass — CI qua `push`, không `pull_request` (tránh approval gate)
   - `auto-merge.yml` squash-merge vào `main`

3. **Deploy production**:
   - Merge vào `main` → `deploy.yml` chạy ngay → GitHub Pages

4. **Build failed trên PR**:
   - `ff` / `ff9` fix trên **cùng branch/PR** — KHÔNG push `main`

5. **Build failed trên main**:
   - `build-failure-handler.yml` + `qa-rule-checker.yml` auto-trigger
   - Safe fix → PR → auto-merge → deploy lại

### Output sau khi tạo PR

```
PR #X created on branch <name>. CI pass → auto-merge → deploy production.
Track: https://github.com/Banhang-Chogao/zola/pulls
```

## 4.6. Hard rules (KHÔNG được vi phạm)

- **KHÔNG** commit/push trực tiếp `main` (human + bot) — luôn qua PR
- **PHẢI** auto-merge khi CI xanh — không chờ user
- **Một PR = một tính năng/fix** — không gom việc không liên quan
- **Build failed** → fix trên branch PR hoặc auto-remediation trên main
- Automation dùng `push_via_pr.sh` — không `git push origin HEAD:main`
- Sau mỗi lần merge PR PHẢI output bảng báo cáo (xem §5)

## 5. Format BÁO CÁO sau khi merge PR (BẮT BUỘC — 2026-06-19)

3 quy tắc: (1) **KHÔNG** canh PR liên tục sau merge; (2) **luôn** output **một lần**
summary cuối (success hoặc fail); (3) fail → tra §4 Vaccine library, đề xuất đúng fix
tool. Chi tiết vaccine: `CLAUDE.md` §4 + §"Báo cáo PR sau merge".

### Thành công

```text
Tổng kết 1 PR vừa merged

┌──────┬────────────────────────────────────────────────────────────┬────────┐
│ PR   │ Title                                                      │ Status │
├──────┼────────────────────────────────────────────────────────────┼────────┤
│ #487 │ feat(flight-db): time pickers, combinator sync, API enrich │ ✅     │
└──────┴────────────────────────────────────────────────────────────┴────────┘

• Merged: <commit_sha> lúc <HH:mm dd/mm/yyyy> (GMT+7)
• Deploy: deploy.yml tự chạy trên main → production

Track: https://github.com/Banhang-Chogao/zola/pulls
```

Nhiều PR → thêm dòng bảng; header `Tổng kết N PR vừa merged`.

### Thất bại

```text
Tổng kết PR lỗi

┌──────┬────────────────────────────────────────────────────────────┬────────┐
│ PR   │ Title                                                      │ Status │
├──────┼────────────────────────────────────────────────────────────┼────────┤
│ #487 │ <title>                                                    │ ❌     │
└──────┴────────────────────────────────────────────────────────────┴────────┘

• Error: <short error>
• Vaccine match: <V# từ CLAUDE.md §4>
• Suggested fix tool: <ff | ff9 | vacxin11 | script cụ thể>
• Next action: <một dòng>

Track: https://github.com/Banhang-Chogao/zola/pulls
```

KHÔNG dài dòng. KHÔNG ⏳ in-progress — chỉ ✅ merged hoặc ❌ fail.

## 6. Quy tắc thực thi shortcut

- Shortcut PHẢI single line, no extra context.
- Nếu user gõ shortcut KÈM context (e.g., `gg PR #82 only`) → exec scope hẹp.
- Shortcut KHÔNG hiệu lực giữa câu nói dài. Phải đứng ĐẦU message.
