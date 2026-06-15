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
| `cautruc9` | Show ASCII folder tree của blog |
| `SEO9` | Tu bổ SEO site-wide đạt Lighthouse 100/100 (Google Search Central) |
| `SEO10` | Loop audit + fix từng lỗi đến khi 0 issue (Google SEO Starter Guide) |
| `SEO11` | Hybrid SEO9+SEO10: phase 1 bulk Lighthouse + phase 2 loop polish |
| `morning` | Chạy chuỗi tất cả shortcut (trừ chính nó) theo thứ tự non-conflict |
| ... | ... |

Sau bảng có thể kèm 1-2 dòng note (vd: "Đầy đủ chi tiết tại
`/shortcuts.md`"). KHÔNG diễn giải dài, chỉ liệt kê.

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

6. **Push** fix lên branch `claude/*` → tạo PR. **KHÔNG auto-merge**
   (rule 16:00). User gõ `manual #X` để deploy lại.

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
     (homepage, /posting/, 1 bài random, /branding/, /scoring/)
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

### `morning` — Macro chạy chuỗi tất cả shortcut

**Mục đích**: 1 lệnh sáng startup chạy toàn bộ shortcut khác để có
bức tranh trạng thái + tự apply audit/fix/SEO/security trong 1 lần.

**Quy tắc loại trừ**:
- Bỏ chính `morning` (tránh infinite loop).
- Bỏ shortcut cần **argument** mà không có default:
  - `topic:` (cần đề tài)
  - `manual #X` (cần PR number cụ thể)
  - `help` (chỉ render bảng — không có hành động)
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
