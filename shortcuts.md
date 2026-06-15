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
