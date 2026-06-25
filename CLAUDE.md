# CLAUDE.md — Quy tắc làm việc

# ZERO BARRIER MANIFESTO

> Chúng ta không babysit PR.
> Chúng ta không merge bằng cảm tính.
> Chúng ta không dùng human approval để thay thế QA.
>
> Máy kiểm tra.
> Máy sửa lỗi.
> Máy merge.
> Máy deploy.
>
> Con người chỉ quyết định sản phẩm.

## Dòng chảy chuẩn

Code
→ Push Branch
→ Auto PR Gatekeeper
→ Merge Conflict Preflight
→ QA Gatekeeper
→ Auto Merge
→ Deploy Production

## Temporary: Auto Vaccine/Hotfix PR Generators Disabled

Auto vaccine/hotfix PR generators are temporarily disabled. Do not re-enable or create new auto-remediation PR spam unless explicitly requested. Use the PR-first deploy strategy: bounded fix → QA/build → PR → checks → squash merge → deploy main → production verify.

The following workflows are affected (manual `workflow_dispatch` only now):
- `vaccine-hotfix.yml` — previously auto-triggered on QA/deploy/auto-merge failures
- `vaccine-autofixer.yml` — previously scheduled daily (06:00 ICT)
- `build-failure-handler.yml` — previously auto-triggered on critical workflow failures
- `self-healing.yml` — previously scheduled every 6h

## Branch hợp lệ

- feat/**
- fix/**
- hotfix/**
- claude/**
- codex/**
- vaccine-hotfix/**

## Luật bất biến

Không được bypass:

- Merge Conflict
- Secret Leak
- Broken Links Blocker
- Build Failure
- QA Failure
- High-Risk Vaccine Failure

CI xanh mới được merge.

## QA Doctrine

QA là cổng kiểm soát duy nhất.

Nếu QA đỏ:

1. Đọc log
2. Tự chẩn đoán
3. Tự sửa
4. Commit
5. Push lại

Không chờ người duyệt.

## Định nghĩa DONE

DONE chỉ tồn tại khi:

Branch đã push
+
PR đã mở
+
Preflight pass
+
QA xanh
+
Auto-merge đã được attempt

## Hạ tầng liên quan

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

## Deploy Queue Policy (ZERO_BARRIER_DEPLOY_QUEUE — effective 2026-06-19)

> Bổ sung ZERO_BARRIER auto-merge/deploy. Nhiều PR/commit xanh cùng lúc → **KHÔNG**
> dispatch nhiều deploy song song (tránh GitHub/Pages API rate-limit burst). Merge
> nhanh nhưng **tuần tự**.

- **Enqueue, đừng burst:** CI/QA xanh → xếp hàng theo thời điểm push/PR ready; xử lý
  **FIFO** (item xanh cũ nhất trước).
- **1 pipeline tại 1 thời điểm:** chỉ một merge/deploy chạy; item kế tiếp bắt đầu **sau**
  khi `deploy.yml` của item trước đạt trạng thái **terminal** (success/failure).
- **Concurrency lock (đã patch):**
  - `deploy.yml` → `concurrency: { group: production-deploy, cancel-in-progress: false }`
    (queue, không cancel → không spam deploy, không burst Pages API; thay V5 cancel-on-storm).
  - `auto-merge.yml` → `concurrency: { group: auto-merge-main, cancel-in-progress: false }`
    (khóa merge toàn cục → merge tuần tự → main nhận 1 push/lần → 1 deploy/lần).
- **Retry, đừng restart:** deploy fail / rate-limited → retry **exponential backoff**;
  KHÔNG chạy lại job đã success, KHÔNG restart queue từ đầu.
- **1 change = 1 PR** (giữ PR sạch).
- **Behavior:** QA green → queued → tới lượt → merge main → deploy → chờ terminal → PR kế tiếp.
- **Summary sau mỗi merge/deploy trong queue:**

  ```text
  Deploy Queue Summary
  PR: #<id>
  Status: ✅/❌
  Queue position: <n>
  Merged: <sha>
  Deploy: <status>
  Next: <next PR or none>
  ```

- **Acceptance:** không deploy song song; không rate-limit burst; PR xanh merge/deploy
  đúng thứ tự; nhanh nhưng tuần tự; build pass.

## Knowledge Promotion Rule (effective 2026-06-21 — anti-bloat governance)

> Repo tiến hóa từ "fix-per-incident" sang "hệ vaccine trưởng thành" (V1–V26). CLAUDE.md
> phải vẫn là **Doctrine + Policy**, không thành "Changelog + private strategy". Quy tắc
> này phân loại tri thức và chỉ định nơi lưu để giữ CLAUDE.md sạch, dễ đọc, đúng scope.

### 4 loại tri thức

| Loại | Định nghĩa | Lưu ở | Tuổi thọ | Ví dụ |
|------|-----------|-------|----------|--------|
| **Incident** | Lỗi ngắn hạn, xuất hiện 1 lần hoặc fix point | `data/`, changelog PR, GitHub issue | Tạm thời (tháng) | Lỗi deploy #387 cancelled; 404 link sao chép; migration URL `github.io→seomoney.org` |
| **Vaccine** | Cùng nhóm lỗi tái phát 2+ lần OR dự phòng | V-number (§4, detector, autofixer, test) | Vĩnh viễn | V1 HF model, V5 rate-limit, V8 Tera syntax, V10 merge race |
| **Doctrine** | Quy tắc vận hành, kiến trúc vĩnh viễn, policy | **§ CLAUDE.md CHÍNH** | Vĩnh viễn | ZERO_BARRIER, Task Priority, SEO CONTENT SYSTEM, Premium Paywall Rules |
| **Private Knowledge** | SEO/affiliate/monetization strategy, prompt, vận hành cá nhân | `CLAUDE_PRIVATE.md` + `docs/private/` | Công ty (không public) | Affiliate program, SEO chủ đề mục tiêu, pricing private, team runbook |

### Quy trình — từ Incident → Vaccine → Doctrine

```
1. Incident Reported
   └─ Quét Vaccine library (§4 V1–V26) ↓
   
2. Match Vaccine?
   ├─ YES → Run FIXER (không chẩn lại)
   │        Log vào "Autofixer Conflict Learning Log" / "Merge Session"
   │        Chỉ append vào CLAUDE.md nếu Vaccine nay cần tuỳnh chỉnh
   └─ NO → Chẩn đoán từ đầu với `ff`/`ff9`
          └─ Recurring Issue (2+ lần)?
             ├─ YES → Create New Vaccine
             │        Detector + FIXER + Unit test
             │        Append block `#### V<N> —` vào §4
             └─ NO → Fix once, log Learning Log
                     Đừng làm Vaccine nếu chỉ vài lần
```

### Incident → Report (KHÔNG vào CLAUDE.md)

- **Khi:** lỗi 1 lần, fix mau, không tái phát dễ dàng
- **Lưu ở:**
  - GitHub PR/Issue description + comments
  - Commit message (lý do fix)
  - `data/merge-report.json` (cho Merge Session)
  - `data/qa-*.json` reports (dashboard tracing)
- **Ví dụ:**
  - "#387 build cancelled do concurrency — không phải fail" → append vào "Build Dashboard Learning" chỗ đó
  - Link `/zola/` migration từ `github.io` → fix + log "Domain Migration" learning

### Vaccine (§4 + detector + test)

- **Khi:** lỗi xuất hiện 2+ lần, pattern rõ, fix bền vững
- **Ghi vào:** CLAUDE.md `#### V<N> —` block, **tuyệt đối KHÔNG đổi số**
- **Cặp theo:** detector (`qa_vaccines.py` check), fixer script, autofixer workflow, unit test
- **Ví dụ:** V5 rate-limit → V5 detector FAIL khi `deploy.yml` concurrency sai → V5 FIXER rerun deploy

### Doctrine (vĩnh viễn)

- **Khi:** quy tắc vận hành, kiến trúc không đổi, policy repo-wide
- **Ghi vào:** CLAUDE.md §đầu (Policy, Rules, Standards)
- **Cấp độ:**
  - **Cao nhất:** `## Automation Policy` (ZERO_BARRIER), `## Deploy Queue Policy`
  - **Trung:** `## QA Rules`, `## Git Rules`, `## SEO Content System Rule`
  - **Chi tiết:** subsection trong § lớn
- **Ví dụ:** "Auto-merge CI xanh mà không hỏi" = Doctrine → `## Auto-Merge Policy`

### Private Knowledge (ngoài repo public)

- **Khi:** bí mật kinh doanh, strategy, credentials, internal process
- **KHÔNG ghi:** CLAUDE.md, README, tài liệu public
- **Lưu ở:** `CLAUDE_PRIVATE.md` + `docs/private/` (private repo or env-gated)
- **Ví dụ:**
  - Affiliate link + commission rate
  - Target niche/SEO pillars (hạn chế publish)
  - Monetization roadmap (NDA)
  - Team member names, roles (privacy)
  - Internal Slack/email template (công ty)

### Anti-Bloat Checklist (trước khi append CLAUDE.md)

**Trước khi thêm section nào vào CLAUDE.md, hỏi:**

1. ✅ Đây là **policy vĩnh viễn** hay **learning từ 1 incident**?
   - Policy → CLAUDE.md
   - Incident → learning log / PR notes
2. ✅ Có **reuse 2+ lần** rồi hay **mới lần đầu**?
   - Dùng lại 2+ → ghi Vaccine
   - Lần đầu → fix + learning log, chờ tái phát
3. ✅ Đây có phải **private strategy** không?
   - Có → `CLAUDE_PRIVATE.md`
   - Không → đúng vị trí trong CLAUDE.md
4. ✅ Có **xung đột** với section nào khác?
   - Có → merge vào section cũ, không tạo section trùng
   - Không → tạo section mới

### Vaccine Governance

- **Mỗi vaccine = 1 số duy nhất** (`V<N>`), **KHÔNG bao giờ đổi số**.
- **Rename vaccine** → chỉ đổi tiêu đề `####` hoặc nội dung, giữ nguyên `V<N>`.
- **Deprecate vaccine** → đánh dấu `[DEPRECATED — xem V<N+M> thay thế]`, KHÔNG xoá.
- **Detector + Test bắt buộc** khi thêm vaccine mới. Nếu không thể detect tĩnh → vaccine thuộc type **Process** (ví dụ V10/V12 "Dirty PR" — chỉ phát hiện thời PR bị conflict).

### Learning Log Lifecycle

- **Autofixer Conflict Learning Log:** append tự động sau mỗi lần `autofix_conflicts.py` thành công
- **Merge Session Learning Log:** append thủ công sau mỗi phiên maintenance merge
- **Build/Compliance Dashboard Learning:** append khi phát hiện dashboard logic bug hoặc false-positive
- **Max 10 entries** per log (archive cũ → docs nếu lịch sử dài)

### File Map

| Loại tri thức | File chính | Lưu chỗ khác | Config |
|----------------|-----------|-------------|--------|
| **Doctrine** | `CLAUDE.md` §0–§ rules | — | — |
| **Vaccine** | `CLAUDE.md` §4 `#### V<N>` | detector: `qa_vaccines.py` · test: `test_qa_vaccines.py` · autofixer: workflow `.yml` | data auto-increment `next_free_vaccine_number()` |
| **Incident** | — | PR / Issue / Merge Report / Dashboard JSON | `data/merge-report.json` history |
| **Learning Log** | `CLAUDE.md` tail sections | — | append-only (không xoá) |
| **Private** | `CLAUDE_PRIVATE.md` (nếu có) | `docs/private/*` | env-gated, không push `main` |

### Khi thêm Vaccine mới

1. Bổ sung block `#### V<N> —` vào §4 (CLAUDE.md).
2. Viết detector trong `CLAUDE.md` → implement trong `scripts/qa_vaccines.py` → register `DETECTORS[]`.
3. Viết autofixer (nếu safe) hoặc FIXER thủ công (nếu risky).
4. Viết unit test: negative (phát hiện bug), positive (current `main` = PASS).
5. Chạy `qa_vaccines.py` → confirm vaccine PASS trên `main`.
6. Đừng tăng số vaccine vừa tạo nếu có vaccine khác chờ pending (queue by discovery order).

### Khi lỡ ghi sai chỗ

- **Incident ghi vào CLAUDE.md:** xoá, đưa vào PR/learning log thay vì CLAUDE.md chính
- **Vaccine số trùng:** đánh dấu deprecated, gán số tiếp trong queue
- **Private ghi vào public:** revert, move `CLAUDE_PRIVATE.md`, xoá khỏi git history (`git filter-repo`)
- **Vaccine không có detector:** append detector vào `qa_vaccines.py` ngay (không để pending)

## Task Priority Policy (effective 2026-06-18)

> Bổ sung `docs/OPERATIONS.md` — **không** thay auto-merge / deploy rules. Áp dụng khi
> agent hoặc automation chạy **đồng thời** tác vụ user và tác vụ nền.

### Priority tiers

| Tier | Class | Examples |
|------|-------|----------|
| **P0 — Foreground** | User-triggered tasks/features | Bài viết, fix bug user báo, publish, editor save, PR user yêu cầu, hotfix urgent |
| **P1 — Background** | Scheduled / bot / audit jobs | `perf-audit`, `seo11`, QA checker, compliance crawl, `build-dashboard`, `merge-report`, `pagespeed`, `security-audit`, `build-related`, image optimize, data refresh bots |

### Rules (mandatory)

1. **Never block P0 for P1** — background job đang chạy KHÔNG được giữ user chờ (no
   `input()`, no “đợi audit xong”, no serial gate trước user action).
2. **P0 may preempt P1** — user task đến giữa chừng → pause/yield background ngay,
   xử lý P0 trước.
3. **P1 continues asynchronously** — background resume sau khi P0 xong; không drop
   schedule cron (`workflow` `schedule:` giữ nguyên).
4. **Auto-resume paused P1** — job pause phải có checkpoint; khi P0 drain → tiếp tục
   từ checkpoint (không restart từ đầu trừ khi idempotent).
5. **Resource budget** — P1 giới hạn song song (vd 1 heavy script local); không spawn
   nhiều crawl/audit cùng lúc khi P0 active. CI: `concurrency.cancel-in-progress` ưu
   tiên deploy/content PR (đã có V5) — bot burst không cướp quota P0.
6. **Preserve schedules** — không đổi cron/interval của P1 để “nhường” P0; chỉ defer
   *instance đang chạy*, không hủy lịch.

### Agent protocol

- Message/ticket từ user = **P0 ngay** — interrupt P1 đang làm trong session.
- Phím tắt / explicit user command > bot maintenance trong cùng turn.
- P1 chỉ chạy khi: (a) user không có P0 pending, hoặc (b) chạy nền không chặn P0
  (parallel CI OK).
- Kết thúc P0 → log ngắn P1 resumed; không hỏi user trước khi resume.

### Validation

- Simulation: `python3 -m unittest scripts.test_task_priority -v`
- Pass criteria: P0 hoàn thành trước P1 bị preempt; P1 resume sau P0 drain.

## Failure Priority Policy (effective 2026-06-21)

> Doctrine vĩnh viễn cho **triage lỗi CI**. Khi pipeline đỏ với **nhiều** failure
> cùng lúc, KHÔNG sửa tràn lan — chỉ sửa **failure REQUIRED trên HEAD mới nhất**,
> theo đúng thứ tự ưu tiên dưới. Bổ sung ZERO_BARRIER + Vaccine library (§4),
> **không** thay auto-merge / QA / deploy. Engine: `scripts/failure_priority.py`.

### Rule (BẮT BUỘC)

1. **Chỉ sửa REQUIRED failure trên LATEST HEAD trước.** Bỏ qua failure **stale**
   (từ commit cũ hơn HEAD) và workflow **report-only** (observer/audit/dashboard/
   bot — V3/V5/V7: observer KHÔNG tự đỏ).
2. **Thứ tự ưu tiên (sửa trên → xuống):**

   | # | Tier | Phạm vi |
   |---|------|---------|
   | 1 | **secrets / security** | secret leak, credential, quyền workflow |
   | 2 | **merge conflict** | conflict markers, `dirty`, non-fast-forward |
   | 3 | **build / syntax** | `zola build`, Tera/SCSS/YAML/TOML/Python/JS syntax, dep |
   | 4 | **QA / vaccine** | QA Gatekeeper (`qa-check`), vaccine detector FAIL, unit test |
   | 5 | **links** | internal link / `qa-404-checker` (gate cứng) |
   | 6 | **runtime route / API** | backend route 404 (`/cms`,`/gsc`,`/auth`,`/api`), deploy |
   | 7 | **SEO / AdSense** | schema, meta, sitemap, AdSense |
   | 8 | **UI** | CSS, responsive, layout, styling |

3. **Auto-fixer chỉ sửa lỗi DETERMINISTIC** (theo §4 Vaccine FIXER / `ai_diagnose.py`);
   **KHÔNG bao giờ bypass vaccine** (không tắt detector, không `--no-vaccines` để qua gate).
4. **Auto-merge CHỈ khi mọi required check xanh**; **deploy CHỈ sau khi merge `main`**.

### Cách dùng

```bash
# Triage list failure (JSON từ gh/CI) → kế hoạch sửa theo ưu tiên, bỏ stale/report-only
gh ... | python3 scripts/failure_priority.py --head "$(git rev-parse HEAD)" --json
echo '[{"workflow":"qa","check":"qa-check","log":"merge conflict","head_sha":"H"}]' \
  | python3 scripts/failure_priority.py --head H
```

- Input: list `{workflow, check, conclusion, head_sha, pattern_id, log, title}`
  (mọi field optional; `pattern_id` từ `ai_diagnose.py` được ưu tiên khi phân loại).
- Output: `fix_first` (1 failure sửa trước) + `ordered_fixes[]` + `dropped[]`
  (kèm `dropped_reason`: stale / report-only / passing).
- Exit 1 nếu còn ≥1 required failure actionable; exit 0 nếu sạch.

### File map & Validation

| Thành phần | Path |
|------------|------|
| Engine | `scripts/failure_priority.py` (`classify` · `is_stale` · `is_report_only` · `triage` · `build_plan`) |
| Tests | `scripts/test_failure_priority.py` |
| Required checks | `data/auto-merge-policy.json` → `required_checks` (canonical: `qa-check`) |
| Diagnose pair | `scripts/ai_diagnose.py` (`pattern_id` → tier) |

- Validation: `python3 -m unittest scripts.test_failure_priority -v`
- Pass criteria: ladder đúng thứ tự (security → UI); stale + report-only bị loại
  khỏi plan; required check (`qa-check`) không bao giờ bị coi là report-only;
  input lỗi → plan rỗng, không crash.

## Post-Bugfix → Blog Draft Policy (effective 2026-06-21 — "Long Bugfix → Blog Draft")

> Doctrine: sau **mỗi bugfix dài / nhiều bước debug** (production bug, CI/CD fail,
> SEO/AdSense, dashboard regression, deploy fail, automation/vaccine pattern), khi
> task đã **substantially complete** hoặc đã có **bài học rõ ràng** → tự chuẩn bị
> **nháp blog case-study công nghệ SEO-safe** từ bài học kỹ thuật. Bổ sung ZERO_BARRIER
> + Knowledge Promotion Rule; **KHÔNG** thay QA / auto-merge / deploy. Shortcut + template
> đầy đủ: `shortcuts.md` §`bugblog`. Đây là tri thức **Doctrine** (vĩnh viễn), không phải Incident.

### Trigger (chỉ kích hoạt khi đủ điều kiện)

1. **Chỉ sau bugfix/debug task** đã substantially complete **hoặc** có bài học rõ.
   KHÔNG chạy cho thay đổi nhỏ/cosmetic; KHÔNG chạy giữa lúc còn đang debug dở.
2. **"Done" cần bằng chứng** — KHÔNG coi là xong cho tới khi có QA / build / commit /
   PR / deploy evidence. Thiếu bằng chứng → **chỉ tạo "blog draft notes"**, KHÔNG bài
   publish-ready.
3. **Đủ chất liệu factual** mới viết bài đầy đủ; thiếu → dừng ở ý tưởng/nháp.

### Hai chế độ output

| Mode | Khi nào | Output |
|------|---------|--------|
| **Draft notes** | Task chưa hoàn tất / thiếu evidence / chất liệu mỏng | Ghi chú nháp (bullet) — KHÔNG frontmatter publish, KHÔNG đưa vào `content/posting/` |
| **Full article** | Task xong + có evidence + đủ chất liệu | Zola Markdown ≥1000 từ tiếng Việt, ngôi thứ nhất, human, SEO-friendly |

### Bài viết phải có (full mode)

Problem · Symptoms · Root cause · Debugging steps · Fix · Vaccine/Prevention rule ·
Checklist · Lessons learned. Category mặc định **Công nghệ** (trừ khi user đổi).

### Safety guards (BẮT BUỘC)

- **Bỏ private/local:** KHÔNG machine path, secret, token, private URL, raw terminal log,
  account data, internal key. Ưu tiên **public-safe abstraction** thay vì lộ implementation nhạy cảm.
- **AdSense-safe:** không misleading claim, không clickbait, không overclaim tài chính/pháp lý,
  KHÔNG xúi người đọc click ads.
- **No fabrication:** KHÔNG bịa kết quả, KHÔNG tuyên bố "production success" khi chưa có evidence.

### Approval gate (no auto-publish)

- **KHÔNG tự đăng.** Bài chỉ chuyển vào `content/posting/` **sau khi user duyệt rõ ràng**.
- Trước khi duyệt: giữ ở dạng nháp (draft notes hoặc draft article chờ review) — KHÔNG đẩy
  vào luồng auto-merge/deploy như bài thường, KHÔNG đụng UI/UX hiện có.

## Conflict Resolution Priority

When resolving merge conflicts, classify files before editing:

1. Generated/report files
   - Examples: `changelog.json`, QA reports, 404 reports, deploy reports, uptime reports, generated metrics JSON.
   - Default action: prefer the version from `main`, then regenerate only if the PR explicitly owns that report.
   - Do not hand-merge generated/report JSON unless explicitly required.

2. Template/CSS/UI files
   - Examples: `templates/**/*.html`, `sass/**/*.scss`, `static/**/*.css`, UI JS.
   - Default action: inspect both sides and preserve the PR intent while keeping current `main` safety fixes.
   - Do not blindly choose one side.

3. Content files
   - Examples: `content/**/*.md`, taxonomy/front matter, article body.
   - Default action: do not rewrite or "fix" content during conflict resolution unless the PR specifically targets that content.
   - Stop and report ambiguity if the correct content version is unclear.

Rule of thumb:
Generated/report conflict → prefer main.
Template/CSS conflict → read carefully and preserve intent.
Content conflict → do not edit unless explicitly instructed.

### Case note: PR #846 changelog conflict

In PR #846, the only conflict was `changelog.json`.

Resolution:
- Treat `changelog.json` as a generated/report file.
- Prefer the version from `main`.
- Do not hand-merge generated JSON.
- After resolving, confirm with:

```bash
git diff --name-only --diff-filter=U
```

Expected output: empty.

Important:

- `mergeable` only means Git conflicts are resolved.
- It does **not** mean the PR is safe to merge.
- Required checks such as `qa-check`, preflight, and deploy gates must still pass.
- If `qa-check` is pending, cancelled, or failed, do not merge yet.

Rule reinforced:
Generated/report conflict → prefer `main`.
Template/CSS/UI conflict → inspect both sides and preserve PR intent plus main safety.
Content conflict → do not edit unless the PR explicitly targets that content.

### 4. THƯ VIỆN VACCINE — lỗi build đã biết → FIX NGAY theo cách đã chốt (auto)

> 💉 Bộ "vaccine" tích luỹ từ audit toàn bộ lịch sử CI. **Giao thức bắt buộc**:
> khi nhận sự kiện build/CI failed → so log lỗi với **Dấu hiệu** của từng vaccine
> dưới đây. KHỚP dấu hiệu → chạy NGAY **FIXER** tương ứng (không chẩn đoán lại từ
> đầu), commit + push, đợi xanh. KHÔNG khớp vaccine nào → mới chẩn đoán mới bằng
> `ff`/`ff9`, và sau khi tìm ra fix bền vững thì **APPEND thêm 1 vaccine mới** vào
> danh sách này (đánh số tiếp). Đây là bộ nhớ tự fix — càng dùng càng đầy.

**Tình trạng audit gần nhất (18/06/2026):** đọc log ~30 run Deploy gần nhất
(#728, #720, #715, #714, #712, #710, #708, #706…); tất cả failure thật = V5
(`configure-pages` API rate limit); `cancelled` = superseded/bão rate-limit;
run #729 success xác nhận fix V5. Quét 50 run repo-wide: không pattern mới ngoài
V1–V7 (lỗi CI run). Bổ sung thêm **V8** (series registration + Tera `replace`
syntax → vỡ `zola build`), **V9** (docs-only PR fail do base cũ) và **V10**
(dirty PR / merge race) — đều thuộc quy trình build/PR, không phải lỗi workflow run mới.


## 4. THƯ VIỆN VACCINE — lỗi build đã biết → FIX NGAY theo cách đã chốt (auto)

> 💉 Bộ "vaccine" tích luỹ từ audit toàn bộ lịch sử CI. **Giao thức bắt buộc**:
> khi nhận sự kiện build/CI failed → so log lỗi với **Dấu hiệu** của từng vaccine
> dưới đây. KHỚP dấu hiệu → chạy NGAY **FIXER** tương ứng (không chẩn đoán lại từ
> đầu), commit + push, đợi xanh. KHÔNG khớp vaccine nào → mới chẩn đoán mới bằng
> `ff`/`ff9`, và sau khi tìm ra fix bền vững thì **APPEND thêm 1 vaccine mới** vào
> danh sách này (đánh số tiếp). Đây là bộ nhớ tự fix — càng dùng càng đầy.

**Tình trạng audit gần nhất (18/06/2026):** đọc log ~30 run Deploy gần nhất
(#728, #720, #715, #714, #712, #710, #708, #706…); tất cả failure thật = V5
(`configure-pages` API rate limit); `cancelled` = superseded/bão rate-limit;
run #729 success xác nhận fix V5. Quét 50 run repo-wide: không pattern mới ngoài
V1–V7 (lỗi CI run). Bổ sung thêm **V8** (series registration + Tera `replace`
syntax → vỡ `zola build`), **V9** (docs-only PR fail do base cũ) và **V10**
(dirty PR / merge race) — đều thuộc quy trình build/PR, không phải lỗi workflow run mới.


#### V1 — `build-related.yml` (Build Semantic Related Posts): HuggingFace 401
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V2 — `slack-notify.yml` (Slack Commit Notification): sai input sau bump v1→v3
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V3 — `perf-audit.yml` (Performance Audit): GitHub Actions không được tạo PR
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V4 — `perf-audit` auto-fixer chèn `loading/decoding` vào `<img>` trong COMMENT
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V5 — `deploy.yml` (Build & Deploy): `configure-pages` "API rate limit exceeded for installation"
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V6 — bot data refresh (`push_to_main.sh`): `git stash pop` CONFLICT trên `data/*.json` regenerate
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V7 — `build-failure-handler.yml` / `qa-failed.py`: bot remediation TỰ ĐỎ khi không chẩn được
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V8 — Series Registration + Tera Syntax: conflict-free PR vẫn vỡ `zola build`
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V9 — Docs-only PR Can Fail Due to Stale Base
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V10 — Dirty PR / merge race: PR turns `dirty` after QA already passed (stale branch base)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V11 — Daily Vaccine Autofixer (manual shortcut `vacxin11` + cron 06:00 ICT)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V12 — Semantic Conflict Auto-Fix: shared infra files (`templates/base.html` + `sass/_footer.scss`)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V13 — Scheduled Forward-Reference: future-dated drafts wrongly flagged as broken links
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V14 — Fabricated topic-cluster cross-links: `/zola/bai-N-<title-slug>/` 404s block the QA gate
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V16 — Static-site ↔ backend split-brain: CI green but VIP premium still locked (Render not redeployed)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V17 — VIPZone admin OAuth loop + Content Picker hidden on Edge/Safari
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V18 — Runtime Artifact Conflict: volatile state/log/report files committed to hotfix PRs
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V19 — GSC Domain Property: must use sc-domain:seomoney.org (not URL-prefix)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V10 — Compliance Heading Focus: pages with 0 `<h1>` (feed-anchor + homepage pagination)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V11 — Compliance Taxonomies: `feed-anchor-*.md` stubs untagged
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V12 — Compliance Article Depth: thin `feed-anchor` bodies (0 chars)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V19 — Domain Migration Drift: stale `github.io/zola` refs in operational files after apex-domain migration
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V20 — Search UI raw/unstyled: BEM markup with no structural CSS (only colour tints)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V22 — Editor S-DNA visual layer: keep `/editor/` emoji-free + KPI cards, logic intact
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V21 — No Floating Bar / Stable Nav Vaccine: desktop nav must stay in normal flow
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V22 — Editor save→GitHub: CMS save must commit (not draft-only download), edit needs SHA, SEO rail hydrates, sticky single-active
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V23 — SEO Identity / Homepage Migration: brand + canonical root must stay `https://seomoney.org/`
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V25 — Split-backend 404: frontend route on `blog-vipzone-api` exists only in undeployed `services/visitor-counter`
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V24 — GSC OAuth refresh token acquired but not persistable after redeploy (operator export path)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V26 — "On This Page" TOC rail: blog posts need the sticky scroll-spy right rail (B-DNA pattern)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V27 — GA stats module: build-time analytics, never fake numbers, pending when not configured
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V28 — Conflict-safe vaccine registry merge: keep ALL main detectors/rules, append only the PR delta
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V29 — External Prod Verification / Manual Backend Deploy: GitHub Pages deploy ≠ Render backend deploy
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V30 — Public /tools/* route preservation: SEO/section optimization must be non-destructive (no silent dashboard removal)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V31 — Shortcut registry preservation: restructuring operation guidelines must not delete existing user shortcuts (required: `bb`)
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

#### V32 — Series sort crash: `sort(attribute="extra.series_part")` vỡ `zola build` khi 1 bài trong series thiếu `series_part`
**Dấu hiệu:** `zola build` đỏ với `Failed to render 'section.html'` → `Filter call 'sort' failed`
→ `attribute 'extra.series_part' does not reference a field`. Nguyên nhân: macro
`series-listing.html` gom các bài cùng `extra.series` rồi `| sort(attribute="extra.series_part")`;
Tera `sort` yêu cầu **MỌI** phần tử có thuộc tính đó → chỉ cần 1 bài (vd trang "tổng quan"
của series) khai báo `extra.series` mà **thiếu** `extra.series_part` là vỡ toàn bộ build.
**FIXER (đã chốt):** (1) Hardening template — lọc trước khi sort:
`{% set sortable = group_pages | filter(attribute="extra.series_part") %}` rồi
`sortable | sort(...)` (áp cho cả nhánh manifest lẫn orphan trong `series-listing.html`);
(2) Bài thuộc series phải có `extra.series_part` — trang tổng quan/intro đặt `series_part = 0`
(badge `{% if %}` coi 0 là falsy nên không hiện "Bài 0/N"). Detector tĩnh `qa_vaccines.py`
(`check_v32_series_part_sort_guard`): FAIL nếu template còn `sort(attribute="extra.series_part")`
không qua `filter` trước. Test: `scripts/test_qa_vaccines.py`.
→ See `docs/vaccine-archive.md` for FIXER & validation steps.


#### V33 — Post-Conflict Artifact Hygiene: accidental backup/temp/unrelated files committed alongside conflict-resolution work
→ See `docs/vaccine-archive.md` for FIXER & validation steps.

## Daily Vaccine Autofixer (BẮT BUỘC — chạy 06:00 GMT+7)

> **Tự động quét repo hàng ngày**, phát hiện pattern issue đã biết từ Vaccine library
> (V1–V11), apply safe fix, create PR cho risky fix, lưu log. UI insights hiển thị timeline.

### Hoạt động (Flow)

1. **Khi chạy** (daily 06:00 GMT+7): workflow `.github/workflows/vaccine-autofixer.yml`
2. **Script** `scripts/vaccine_autofixer.py` thực thi:
   - Đọc CLAUDE.md §4 extract vaccine definitions (V1–V11)
   - Scan CI logs lần gần nhất để phát hiện matching pattern
   - Scan repo files (`build_related.py`, `slack-notify.yml`, …) để detect issues
   - Match pattern với vaccine rules (KHÔNG re-diagnose)
   - **Auto-fix safe issues** (vd V1 HF model ID, internal-link 404 `--fix`,
     references) — deterministic, idempotent
   - **Mọi thay đổi đi qua PR flow** (workflow mở PR `chore/vaccine-autofixer-*`) —
     KHÔNG push thẳng `main`; risky/ambiguous → để review trên PR
   - Run QA/build validation
   - Lưu report → `data/vaccine-autofixer-report.json` (flat summary + `history[]`)
3. **Report được published** qua `deploy.yml` → site `/zola/insights/` hiển thị

### Config

| Thành phần | Path | Ghi chú |
|-----------|------|--------|
| Workflow | `.github/workflows/vaccine-autofixer.yml` | Cron `0 23 * * *` (UTC) = 06:00 GMT+7 + `workflow_dispatch`; `concurrency` chống chạy đồng thời; artifact upload + step summary + PR flow |
| Script | `scripts/vaccine_autofixer.py` | Engine: parse vaccine library (`load_vaccines`) + safe fixer steps + CI-log diagnosis (`gh`, report-only) + lock chống chạy trùng + QA/build + report. Tests: `scripts/test_vaccine_autofixer.py` |
| Report | `data/vaccine-autofixer-report.json` | Flat summary (cho Insights panel) + `history[]` 30 mốc + `latest` (cho workflow summary). Lock: `-state.json`; log: `.log` |
| Insights UI | `templates/insights.html` (`.vaccine-panel`) + `sass/_vaccine-autofixer.scss` | Last run · Next scheduled · chip vaccine khớp · fixed count · chip QA/Build/Prod · nút Run |


## Vaccine Hotfix (conflict-safe pipeline self-heal — BẮT BUỘC)

> Engine: `scripts/vaccine_hotfix.py` · Workflow: `.github/workflows/vaccine-hotfix.yml`
> · Report: `data/vaccine-hotfix-report.json` (**"Autofixer_report_by Vacxin"**) ·
> State/lock + anti-loop: `data/vaccine-hotfix-state.json` · Log: `data/vaccine-hotfix.log`.
>
> Khi pipeline **đỏ thật** (build/deploy/auto-merge/conflict/required-check) → tự kích
> hoạt: chẩn lỗi → mở/cập nhật branch `vaccine-hotfix/<issue-id>` → sửa **delta tối thiểu**
> → re-run QA/build/test → lặp tới khi xanh → cập nhật PR → **auto-merge CHỈ khi mọi
> required check xanh**. Đây là lớp self-heal **bổ sung** ZERO_BARRIER, **không** thay
> auto-merge / QA / deploy / Daily Vaccine Autofixer (V11).

### Conflict-safe precheck (chạy TRƯỚC mỗi lần kích hoạt)

`audit_rules()` quét rule CI/PR/merge/deploy hiện có và phát hiện xung đột với
manual-approval · branch-protection · auto-merge · QA · deploy. **Giữ nguyên safety
gate cho `main`**, chỉ cho `vaccine-hotfix/*` auto-fix + auto-update PR:

- **KHÔNG** bypass required checks — re-chạy `qa_check.py`; merge giao cho
  `try_auto_merge.py` (auto-merge.yml) → chỉ merge khi `qa-check` xanh.

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

## QA Vaccine Gate (rào chắn production từ thư viện Vaccine — BẮT BUỘC)

> Lớp **gia cố** của QA Gatekeeper: biến toàn bộ **THƯ VIỆN VACCINE** (§4, V1–V12 +
> bộ compliance) thành **static detector** chạy TRƯỚC khi lên production. Mục tiêu:
> chặn các **bug tái phát đã biết** sớm hơn (trước cả `zola build`), với chẩn đoán rõ,
> cách sửa chính xác và tham chiếu đúng vaccine. **Không** thay/bỏ check QA cũ — chỉ cộng thêm.

### Cách hoạt động

- `python3 qa_check.py` (full-repo scan, non-fix) chạy các check cũ (conflict/secret/SEO/SCSS)
  **rồi** gọi QA Vaccine Gate và in **「QA Vaccine Summary」** ở CUỐI. Vaccine FAIL → exit 1 →
  job `qa.yml` đỏ → chặn auto-merge/deploy. Đây là **gate bắt buộc** trước production.
- Engine: `scripts/qa_vaccines.py` — `load_vaccines()` đếm mọi block `#### V<N> — …` trong
  CLAUDE.md; `DETECTORS[]` chạy detector tĩnh cho từng vaccine statically-checkable.
- Phân mức (calibrate để `main` hiện tại = 0 FAIL): **FAIL** = vỡ build/production thật
  (Tera `replace(old=/new=)` thay vì `from=/to=`, lệch block `{% if/for/block/macro %}`,
  workflow YAML / `config.toml` hỏng, `data/*.json` dashboard hỏng, JS SyntaxError, bài
  `premium=true` thiếu `private_content/<id>.md`); **WARN** = consistency/resilience
  (V5 deploy, đăng ký series, category "Tất cả" đầu mảng, asset thiếu, schema/OG, paywall id);
  **SKIP** = không áp dụng (node/yaml vắng) hoặc vaccine *process* (V9/V10 PR-time).

### Output (bắt buộc in ở cuối qa-check)

```text
QA Vaccine Summary
- Total vaccines loaded:        # số block #### V<N> trong CLAUDE.md
- Passed:                       # detector PASS
- Failed:                       # detector FAIL → chặn deploy
- Warnings:                     # detector WARN
- Production readiness score:   # 0–100; FAIL → ≤60 = NOT production-safe
```

### Lệnh

```bash


---

## 📚 Full Documentation

**Vaccine Details:** `docs/vaccine-archive.md` - Complete V1-V29 with all FIXER steps, evidence, validation procedures

**QA System:** `scripts/qa_vaccines.py` + `scripts/test_qa_vaccines.py` - Automatic vaccine gate for CI/QA

**Important:** All vaccine numbers (V1-V29) and headers are immutable per Knowledge Promotion Rule. Summaries above reference archive for details.

---

# Additional Sections (Reference)

For full details on remaining sections (F-Dashboard, Premium Paywall, Security, Quy tắc hoá giao dịch, etc.), see the full `CLAUDE.md` or `docs/vaccine-archive.md` archive.
## QA Rule Checker Learning

**Date:** 2026-06-25T00:16:30Z

**Conflict:** Slug trùng: bi-kip-xin-visa-han-quoc-5-nam-de (MEDIUM)

**Root Cause:** content/baochi/bi-kip-xin-visa-han-quoc-5-nam-de.md; content/posting/bi-kip-xin-visa-han-quoc-5-nam-de.md… vs Mỗi slug nên unique trong site…

**Resolution:** Đổi slug hoặc merge bài trùng.

**Prevention:** Chạy `qa-auto-rule-checker.py` mỗi 48h (schedule); đồng bộ CLAUDE.md khi đổi policy.

## Release Pipeline Rule

SEOMONEY uses a severity-based release pipeline.

Only production-breaking issues may block PR/deploy:
build failures, template crashes, syntax errors, conflict markers, leaked secrets, missing required assets, broken required internal links, and accidental public exposure of private/admin/auth/editor pages.

SEO/content/dashboard issues must become warnings or reports unless they expose private pages or break production:
orphan posts, weak internal links, thin clusters, empty categories, missing FAQ/TLDR, low GSC data, non-indexed pages, dashboard data gaps, and content opportunity suggestions.

Claude must always distinguish:
- local preflight
- PR hard gate
- deploy
- production verification

A task is not truly done until production verification confirms the real site is live.

## Vaccine Autofixer PR Spam Rule

Vaccine/autofixer workflows must not spam duplicate PRs.

Rules:
- Only one open `deploy_fail` hotfix PR is allowed at a time.
- When a newer `deploy_fail` PR is created, older open `deploy_fail` PRs must be closed as superseded.
- Maximum auto-fix retry per failing workflow: 2.
- After 2 failed retries, stop creating PRs and write a report only.
- Warning-only QA issues must not trigger `vaccine-hotfix` PRs.
- Do not batch-fix unrelated PRs.
- Do not touch content unless the PR is explicitly content-scoped.
- Do not touch payment/premium/paywall logic unless explicitly requested.
- If the issue is duplicate, stale, or already fixed on main, close the PR with a clear comment instead of creating another fix PR.

Expected behavior:
Autofixer should reduce noise, protect production, and surface only real blockers.
