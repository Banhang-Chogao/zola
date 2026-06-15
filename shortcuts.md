# Phím tắt & Quy trình làm việc với Claude

Source of truth cho các shortcut commands + nguyên tắc vận hành. Khi
user gõ shortcut, Claude THỰC THI NGAY, không hỏi lại, không giải thích
dài.

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

### `help` — Hiển thị danh sách tất cả phím tắt active

Khi user gõ `help` (hoặc `/help`), Claude output bảng tóm tắt tất cả
shortcuts hiện có trong file này với mô tả ngắn ≤1 dòng/shortcut.

Format bắt buộc:

| Shortcut | Mục đích |
|---|---|
| `gg` | Merge open PRs to production |
| `ad` | Full blog audit (perf+sec+seo+a11y) |
| `ff` | Full Fix & Deploy comprehensive |
| ... | ... |

Sau bảng có thể kèm 1-2 dòng note (vd: "Đầy đủ chi tiết tại
`/shortcuts.md`"). KHÔNG diễn giải dài, chỉ liệt kê.

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
4. Báo cáo ngắn: `Merged PR #X, #Y. Production deploy đang chạy.`

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

### `ff` — Full Fix & Deploy

Hành động:
1. **Liệt kê** tất cả failed workflow runs (≥ 24h gần nhất) +
   failed PR checks + failed deploy.
2. **Phân tích log** mỗi failed run theo logic `qa-failed.py`:
   - Đợi run status = `completed` (poll mỗi 30s, max 5 lần = 2.5 phút)
   - CHỈ fetch logs sau khi completed → tránh "still in progress" error
3. **Auto-fix** pattern đã biết:
   - `ModuleNotFoundError` → append dep vào requirements.txt
   - Tera/Zola syntax → chạy `qa_check.py --fix safe`
   - Git race non-fast-forward → escalate (không tự force push)
   - Workflow permission denied → escalate
   - Unknown pattern → tạo issue + escalate
4. **Push** fix lên `main` → trigger deploy lại.
5. **Báo cáo tổng kết** sau khi xong:
   - Failed runs found / fixed / escalated
   - Production deploy status

### `healing` — Kích hoạt QA-Healing thủ công

Hành động: chạy QA-Healing on-demand. Khác `ff`: ALWAYS chạy baseline
qa_check.py trước fix, output detail per step.

1. Liệt kê failed runs gần nhất (default 5).
2. **Baseline QA**: `python3 qa_check.py` trước intervention.
3. **Auto-fix** qa-failed.py pattern matching.
4. **Re-deploy**: commit + push main → trigger deploy.yml.
5. **Verify**: poll deploy run mới đến success (max 5 phút).
6. Nếu run mới vẫn fail sau heal → tạo issue label `healing-failed`.

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
| QA Gatekeeper | `.github/workflows/qa.yml` | (no schedule) | Trigger trên PR + push main |
| Security Audit | `.github/workflows/security-audit.yml` | `0 3 * * 6` | Thứ 7 hàng tuần 03:00 UTC |
| Self-Healing QA | `.github/workflows/self-healing.yml` | `0 */6 * * *` | Mỗi 6 tiếng |

Bonus columns nếu user muốn detail:
- Last run status (✅ success / ❌ failure / 🔄 in_progress)
- Next scheduled run (tính từ cron expression + now)
- Runs/tháng estimate

KHÔNG diễn giải dài, chỉ output bảng + 1 dòng summary.

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
   `@Banhang-Chogao` → GitHub tự gửi email đến tamsudev.com@gmail.com.

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

---

## 3. Workflow Auto-Heal — quy trình chuẩn

Mọi action/workflow failed PHẢI đi qua pipeline 3 bước:

```
[FAILED] ─→ QA check (qa_check.py + log analysis)
         ─→ Tự fix (qa-failed.py pattern matching)
         ─→ Re-deploy (commit + push → trigger deploy.yml)
```

**Claude tự quyết định** (không hỏi user):
- Phiên bản Node.js phù hợp với từng action (smart eval per section 1)
- Hướng xử lý lỗi tối ưu (conservative khi unknown, aggressive khi pattern rõ)
- Khi nào escalate qua issue thay vì cố fix mù

Workflow handler `.github/workflows/qa-failed-handler.yml` ĐÃ BỊ GỠ
(user request 11:37). `qa-failed.py` giữ lại — chạy manual qua các
shortcut `ff` / `healing`.

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

## 4.4. Link quản lý PR (cập nhật 13:22 ngày 15/06/2026)

**Source of truth**: https://github.com/Banhang-Chogao/zola/pulls

Claude PHẢI:
1. **Track tất cả PRs** tại link trên — đây là dashboard duy nhất, không
   được dựa vào cache local.
2. **Tự động đưa changes mới vào hàng đợi**: mỗi feature/fix mới →
   commit vào branch hiện tại → append vào PR đang open (nếu có) hoặc
   tạo PR mới.
3. **Gom đủ ~10 changes** trước khi user trigger `manual #<số PR>`.
4. **Quy trình phê duyệt**:
   - User tự vào https://github.com/Banhang-Chogao/zola/pulls
   - Click PR cần deploy → bấm nút **Approve** trực tiếp trên GitHub web
   - Sau Approve → user gõ `manual #<số PR>` cho Claude
   - Claude merge + deploy
5. **KHÔNG được merge** PR khi chưa thấy:
   - User gõ lệnh `manual #X`, HOẶC
   - User gõ `gg` + xác nhận, HOẶC
   - Lỗi HOTFIX critical (ngoại lệ documented)

Mỗi lần tạo PR mới, Claude PHẢI nhắc user link manage:
"PR #X created. Total open: N. Manage at: https://github.com/Banhang-Chogao/zola/pulls"

## 4.5. Quy trình Deploy (FINAL FINAL — cập nhật 16:00 ngày 15/06/2026)

**🚨 RULE MỚI (override tất cả rule deploy trước đó)**:

**TẠM NGƯNG QUYỀN AUTO-MERGE HOÀN TOÀN**. Claude tuyệt đối KHÔNG được
merge bất kỳ PR nào tự động. User PHẢI manually check + decide.

### Quy trình bắt buộc

1. **Mỗi commit = 1 PR riêng**:
   - Sau MỖI commit (content, fix, feature), Claude PHẢI tạo PR riêng
   - KHÔNG gom batch ≥10 nữa
   - KHÔNG đợi đủ commit count

2. **KHÔNG auto-merge dưới BẤT KỲ điều kiện nào**:
   - KHÔNG kể đủ 10 commits
   - KHÔNG kể `gg` shortcut
   - KHÔNG kể HOTFIX critical
   - CHỈ MERGE khi user gõ `manual #<số PR>` explicit

3. **User là gatekeeper duy nhất**:
   - User vào https://github.com/Banhang-Chogao/zola/pulls
   - Check PR manually (diff, CI status, description)
   - **User DECIDE** lên prod hay không
   - User gõ `manual #<số PR>` → Claude merge + deploy

4. **Override các shortcut hành vi**:
   - `gg`: chỉ LIST open PRs + URL, KHÔNG merge
   - `pp`: tạo PR hotfix, KHÔNG merge — user phải `manual #X`
   - `manual #X`: VẪN merge ngay (user explicit yêu cầu)
   - `ff`: phân tích + fix + tạo PR, KHÔNG merge

5. **HOTFIX critical** (deploy đỏ): Claude vẫn tạo PR fix, nhưng
   KHÔNG auto-merge. Output cảnh báo URGENT để user manual phê duyệt.

### Output sau mỗi commit

```
Commit #X created → PR #Y opened.
Manage at: https://github.com/Banhang-Chogao/zola/pulls
Để deploy: gõ `manual #Y` sau khi Approve trên GitHub.
```

## 4.6. Hard rules (KHÔNG được vi phạm)

- **KHÔNG auto-merge** kể cả khi đủ điều kiện cũ
- **CHỈ merge khi `manual #X`** explicit
- **KHÔNG tạo branch mới** cho mỗi content (commit vào branch dev chính)
- Output mỗi PR mới PHẢI nhắc link manage và lệnh `manual #X`

## 5. Format BÁO CÁO sau khi merge PR (BẮT BUỘC)

Sau MỌI lần merge PR thành công, Claude PHẢI output bảng 3 cột:

| PR | Title | Status |
|---|---|---|
| #X | <PR title ngắn gọn> | ✅ |
| #Y | <PR title ngắn gọn> | ✅ |

Quy tắc:
- Format MARKDOWN TABLE 3 cột chuẩn, KHÔNG dùng bullet list
- Cột Status: ✅ (merged) / ❌ (failed) / ⏳ (in progress)
- Nếu 1 turn merge nhiều PR → liệt kê HẾT trong cùng bảng
- Header "Tổng kết N PR vừa merged" trước bảng (N = số PR)
- Sau bảng có thể kèm 1-2 dòng note ngắn nếu cần (e.g., production deploy status)

KHÔNG dài dòng, KHÔNG diễn giải nội dung PR (đã có trong PR body).

## 6. Quy tắc thực thi shortcut

- Shortcut PHẢI single line, no extra context.
- Nếu user gõ shortcut KÈM context (e.g., `gg PR #82 only`) → exec scope hẹp.
- Shortcut KHÔNG hiệu lực giữa câu nói dài. Phải đứng ĐẦU message.
