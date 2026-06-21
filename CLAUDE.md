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

#### V6 — bot data refresh (`push_to_main.sh`): `git stash pop` CONFLICT trên `data/*.json` regenerate

- **Dấu hiệu:** workflow refresh data (vd **Fetch Merge Report**, build-dashboard,
  trends…) đỏ với log: `Saved working directory ... push_to_main: pre-pull` →
  `git pull --rebase` cập nhật `data/*.json` → `CONFLICT (content): Merge conflict
  in data/<file>.json` (vd `data/merge-report.json`) → `The stash entry is kept` →
  `##[error]Process completed with exit code 1`. **KHÔNG phải lỗi build/Tera.**
- **Nguyên nhân:** bot regenerate `data/*.json` ở local → `stash` → `pull --rebase`
  (main đã regenerate cùng file ấy) → `stash pop` đụng nhau. `set -euo pipefail` →
  `git stash pop` exit≠0 làm chết script → workflow đỏ giả. Cùng họ với 💉 VACCINE
  "Conflict ở DATA FILE CI/HOOK TỰ SINH" (Learning Log) nhưng ở **luồng push của bot**.
- **FIXER (đã áp):** `.github/scripts/push_to_main.sh` bọc `git stash pop` trong
  `if ! git stash pop; then` → với mỗi file unmerged (`--diff-filter=U`) lấy bản
  **bot vừa regenerate** (`git checkout --theirs` / fallback `git checkout stash@{0}`),
  `git add`, rồi `git stash drop`. Bot data mới nhất = bản publish → conflict KHÔNG
  còn kéo sập workflow. (Bản chất: data CI tự sinh → không bao giờ để conflict làm đỏ.)

#### V7 — `build-failure-handler.yml` / `qa-failed.py`: bot remediation TỰ ĐỎ khi không chẩn được

- **Dấu hiệu:** workflow **Build Failure Auto-Remediation** đỏ; log `qa-failed.py`:
  `get_run_status error: Expecting value: line 1 column 3 (char 2)` (gh trả non-JSON)
  → `poll #1/5 ... status=unknown` → `gh issue create ... timeout` →
  `##[error]Process completed with exit code 1`. Bot đi sửa lỗi run khác lại **tự
  fail**.
- **Nguyên nhân:** (1) `get_run_status` parse `gh run view --json` không bền (gh in
  non-JSON khi rate-limit/output bẩn) → `unknown`; (2) `wait_for_completion` **bail
  ngay** khi `unknown` → tạo issue "timeout" giả; (3) `qa-failed.py` exit≠0 ở mọi
  nhánh escalate + step workflow **không** `continue-on-error` → chính workflow
  remediation đỏ (noise, có thể tự trigger lại). Trái triết lý V3/V5 (observer/
  remediation KHÔNG được tự đỏ).
- **FIXER (đã áp):** (a) `qa-failed.py wait_for_completion` **retry** khi `unknown`
  (gh tạm lỗi) thay vì bail — chỉ bỏ cuộc sau hết attempts; (b) step "Analyze
  failure" trong `build-failure-handler.yml` thêm `continue-on-error: true` (nuốt
  exit code như V3; step sau vẫn gate `steps.fix.outputs.pushed`). Quy tắc chung:
  **mọi workflow observer/remediation/QA report-only → `continue-on-error` hoặc nuốt
  exit**, chỉ để CI gate thật (qa-check, zola build) mới được đỏ.

#### V8 — Series Registration + Tera Syntax: conflict-free PR vẫn vỡ `zola build`

- **Symptom:** PR shows **no merge conflicts** (mergeable) but `zola build` fails
  unexpectedly. Error originates in the `/posting/` pager or the SERIES block, e.g.
  `Failed to render 'section.html'` → `Filter call 'replace' failed` →
  ``Filter `replace` expected an arg called `from` ``. Builds fine on `main` until a
  new series' content lands.
- **Root causes:** (1) A new series manifest (`data/<id>-series.json`) was added in
  content but **not registered** in the `manifests` array of
  `templates/macros/series-listing.html` → the series falls into the **orphan
  fallback** branch. (2) That orphan branch used **Python-style filter kwargs** in
  Tera. Tera's `replace` filter uses `from=`/`to=`, NOT Python's `old=`/`new=`:
  - Wrong: `replace(old="-", new=" ")`
  - Correct: `replace(from="-", to=" ")`
  The orphan branch was dormant while every series was registered, so the bad syntax
  only triggered once an unregistered series existed.
- **FIXER:** (a) Register every new series manifest in **both** `series-listing.html`
  (`manifests` array) and the `elif` chains in `page.html` + `macros/series-nav.html`
  (one `elif` per series — multi-series pattern). (b) Use `replace(from=…, to=…)`;
  never use Python keyword names (`old`/`new`) in Tera filters.
- **Prevention:**
  - After adding any series, verify it is registered in `series-listing.html`.
  - Audit orphan-series fallback paths for valid Tera syntax.
  - Never use Python keyword names in Tera filters; prefer explicit `from=`/`to=`.
  - **Conflict-free PR ≠ build-safe PR** — always inspect templates after a merge
    (auto-resolved series `elif` unions can still leave an unregistered manifest).
- **Validation:** `python3 qa_check.py` → `python3 scripts/paywall_prepare_build.py
  --strip` → `zola build` → `python3 scripts/paywall_prepare_build.py --restore` →
  `python3 scripts/check_internal_links.py`; confirm the SERIES block and `/posting/`
  pagination render correctly. (Applied 18/06/2026 in PR #451 merge.)

#### V9 — Docs-only PR Can Fail Due to Stale Base

- **Symptom:** A PR changes **only docs** (`CLAUDE.md`, `README`, etc.) but `qa-check`
  or `zola build` **fails**. The failure looks unrelated to the modified files.
- **Root cause:** The branch was created from an **outdated `main`**. CI validates the
  **entire repository**, not only the changed files — so an old base **resurrects
  already-fixed site bugs** that no longer exist on current `main`.
- **Example:** PR #452 modified only `CLAUDE.md`, but its base `653e4f3` still
  contained the pre-#451 `series-listing.html` bug (see V8). qa-check's `zola build`
  step failed. **Rebasing onto `9221a39` (post-#451) fixed the build immediately** —
  no content change needed.
- **FIXER / Procedure:**
  1. `git fetch origin main`.
  2. Rebase (or merge) the branch onto the latest `main`.
  3. Regenerate generated files if needed (`build_references.py`, etc.).
  4. Validate: `python3 qa_check.py` → `python3 scripts/paywall_prepare_build.py
     --strip` → `zola build` → `python3 scripts/paywall_prepare_build.py --restore` →
     `python3 scripts/check_internal_links.py`.
  5. Push only when the working tree is clean and the build is green.
- **Prevention / Rules:**
  - **Even docs-only PRs must be rebased** onto current `main` before relying on CI.
  - CI tests the **whole repo, not the diff** — a green local doc edit is not enough.
  - A build failure right after an **unrelated** edit usually means a **stale branch**,
    not bad content — rebase first, debug second.
- **Validation:** working tree clean · QA green · no resurrected bugs · PR mergeable.
#### V10 — Dirty PR / merge race: PR turns `dirty` after QA already passed (stale branch base)

> Process vaccine (not a workflow-run failure). Match the signature → run the
> FIXER, do not re-diagnose.

- **Symptom:** PR reports `mergeable_state: dirty` (or fresh conflicts) AFTER
  `qa-check` already passed; another PR merged into `main` first and left this
  PR's base stale. Conflicts cluster in auto-generated files
  (`data/references.json`, `data/seo-qa-scores.json`) and in shared registries
  that multiple PRs append to (series `elif` blocks in
  `templates/macros/series-nav.html`, `templates/page.html`, `templates/base.html`;
  `categories.json`). The real content (`content/**/*.md`) does NOT conflict.
- **Root cause:** the branch was cut from an older `main`, and generated data
  drifted while the PR waited for auto-merge. `dirty` here is a **merge race, not
  a code bug**. QA-green only proves the branch is internally consistent — never
  that it is merge-safe against the current `main`.
- **FIXER (mandatory before opening AND on every PR update):**
  1. `git fetch origin main`.
  2. Merge/rebase the branch onto the latest `main`.
  3. Resolve conflicts locally — for shared registries keep **BOTH** sides
     (append every series `elif` / category entry; never pick one side). For
     generated data, take `main` then **regenerate**: `python3 scripts/build_references.py`,
     `python3 scripts/seo_qa_checker.py --all`, plus any category/tag/series
     manifest generators.
  4. Run the local gate: `python3 qa_check.py` + `python3 scripts/check_internal_links.py`.
  5. Push ONLY when the tree is clean and free of conflict markers.
- **After the PR is open — watch until merged:** poll BOTH the PR and `main`.
  If another PR lands first (`main` advances without your content), immediately
  re-sync: merge latest `main`, re-resolve, regenerate, re-run QA, push the new
  head. Repeat until YOUR commit is the one on `main`. Never assume the first
  green is the final state.
- **Rules:** never trust an old branch base; never treat QA-green as merge-safe;
  a `dirty` PR is a merge race, not a code bug; auto-merge must always operate on
  the latest `main`.
- **Validation:** no conflict markers; QA passes; working tree clean; PR
  mergeable; keep watching until the production deploy completes.
- **Evidence (PR #451, 18/06/2026):** PR #451 went `dirty` twice because the
  VietinBank series PRs (#449/#450) merged first. Each time the FIXER applied
  cleanly: merge `main`, keep all three series `elif`s (korean-30day +
  google-analytics + vietinbank), take `main` for `data/*.json` then regenerate
  (references → 156 posts), QA PASS, push → auto-merge landed #451 with no further
  conflicts.

#### V11 — Daily Vaccine Autofixer (manual shortcut `vacxin11` + cron 06:00 ICT)

> Process/tooling vaccine — KHÔNG phải lỗi build. Đây là engine tự chạy CHÍNH bộ
> vaccine này hằng ngày, và shortcut chạy ngay theo yêu cầu.

- **Mục đích:** chạy ngay bộ "Daily Vaccine Autofixer" mà không chờ lịch 06:00
  (Asia/Ho_Chi_Minh). Đọc thư viện vaccine trong `CLAUDE.md` → quét repo → auto-fix
  các issue AN TOÀN → chạy QA/build → lưu log → cập nhật report cho trang Insights.
- **Trigger:** lệnh `vacxin11` (xem `shortcuts.md`) **hoặc** nút *Run Daily Vaccine
  Autofixer* trên trang Insights → GitHub Actions `workflow_dispatch`. Cùng engine
  với run theo lịch.
- **Engine:** `scripts/vaccine_autofixer.py` (`load_vaccines` parse các block
  `#### V<N> — …`; các step fixer AN TOÀN reuse tool sẵn có: V1 HF model id,
  internal-link 404 `--fix`, references; rule-checker report-only). Report:
  `data/vaccine-autofixer-report.json` (trigger → matched vaccines → fixes → QA →
  production status). Lock `data/vaccine-autofixer-state.json` (stale sau 30').
- **Rules (BẮT BUỘC):** (1) **Không chạy đồng thời** — lock + `concurrency` group
  trong workflow; run mới khi đang chạy → skip (exit 3). (2) **Code change đi qua
  PR flow** — workflow `vaccine-autofixer.yml` mở PR `chore/vaccine-autofixer-*`,
  KHÔNG push thẳng `main`; auto-merge khi QA xanh → deploy. (3) **Theo dõi PR tới
  khi MERGED + deploy production xong.**
- **File map:** `scripts/vaccine_autofixer.py` · `scripts/test_vaccine_autofixer.py`
  · `.github/workflows/vaccine-autofixer.yml` · UI `templates/insights.html`
  (`.vaccine-panel`) + `sass/_vaccine-autofixer.scss` · data
  `data/vaccine-autofixer-report.json` / `-state.json` / `.log`.

#### V12 — Semantic Conflict Auto-Fix: shared infra files (`templates/base.html` + `sass/_footer.scss`)

> Process vaccine (not a workflow-run failure). These two files are the repo's
> highest-conflict zone. Match the signature → run the FIXER **by intent**, NEVER
> blind `ours`/`theirs`.

- **Symptom:** A PR touching the global layout turns `mergeable_state: dirty` with
  conflicts clustered in **`templates/base.html`** and/or **`sass/_footer.scss`**
  (siblings `sass/_footer-tags.scss`, `_sidebar.scss`, `_theme-overrides.scss`,
  `site.scss` usually auto-merge). Multiple parallel PRs each relocate a sidebar/
  footer module (categories → footer, tags → footer, add a sidebar widget) so they
  edit the SAME footer/sidebar regions. The PR's real feature is fine; only the
  shared scaffolding collides.
- **Root cause:** `base.html` + `_footer.scss` are **shared infrastructure / high-
  conflict zones**. Parallel PRs branched from different bases each move a block into
  the footer or add a widget. A blind `--ours` re-introduces the module the other PR
  already moved (→ duplicate render); a blind `--theirs` deletes a feature that
  already landed on `main`. It is a **merge race over shared layout**, not a logic
  bug — QA-green on a branch never proves it is merge-safe against latest `main`.
- **FIXER (semantic, by intent — never blind ours/theirs):**
  1. `git fetch origin main` → merge latest `main` into the branch.
  2. **Classify each conflict hunk** as `additive` · `overlapping` · `replacement`.
  3. **Additive (the common case):** preserve BOTH sides. A module moved to the
     footer must exist in the footer **exactly once** and be **absent** from the
     sidebar — so drop the stale sidebar copy on *both* sides and keep every footer
     block (`.footer-categories` from one PR + `.footer-tags` from another both live).
  4. **`templates/base.html` — merge by BLOCK.** Protect & dedupe: SEO `<meta>`/
     schema metadata, analytics, `<script>`/asset-version includes, macro imports,
     `{% block %}` partials, nav + `[[extra.main_menu]]`-driven links (e.g. S-DNA),
     the `<footer>` blocks, sidebar widgets (`google_rank`, `seo_reality`). **No
     duplicate JS/CSS imports, no duplicate footer/sidebar blocks, no broken Tera tags.**
  5. **`sass/_footer.scss` — merge by COMPONENT.** Protect: `.footer-categories`,
     `.footer-tags`, footer cards, spacing, theme tokens, typography hierarchy, every
     `@media` breakpoint. **Each selector defined exactly once** (grep the opener
     count to confirm); never delete an unrelated footer module; keep responsive
     behavior intact (desktop / tablet / mobile).
  6. **Validate before commit:** `python3 scripts/build_references.py` →
     `python3 scripts/paywall_prepare_build.py --strip` → `zola build` → `--restore`
     → `python3 qa_check.py` → `python3 scripts/check_internal_links.py` →
     `python3 qa-404-checker.py`. Confirm in built HTML: footer categories render,
     footer tags render, SEO Reality Check renders, S-DNA route/menu works, **no
     duplicate footer/sidebar blocks**.
  7. **If build + QA pass → commit immediately** (zero conflict markers left).
- **Prevention / Rules:** never `--ours`/`--theirs` blindly on these files; classify
  every hunk (additive / overlapping / replacement); for additive keep both; for a
  moved module keep it in the footer once + remove it from the sidebar; rebase onto
  latest `main` before trusting CI; a `dirty` PR after QA-green = merge race, not a
  code bug.
- **Lesson (root cause, permanent):** parallel PRs modified shared infrastructure
  files (`templates/base.html`, `sass/_footer.scss`). **Infrastructure files are
  high-conflict zones — always perform a SEMANTIC merge, not a text merge. Truth >
  speed. Structure > line numbers. Intent > ours/theirs.**
- **Evidence (PR #469, 19/06/2026):** #469 (Tags → footer) went `dirty` after #467
  (SEO Reality Check sidebar), #468 (Categories → footer) and #470 (S-DNA tools menu)
  landed on `main` first. Conflicts only in `templates/base.html` + `sass/_footer.scss`.
  Semantic FIXER kept `.footer-categories` (#468) **and** `.footer-tags` (#469) both
  in the footer; removed both stale sidebar blocks; preserved `seo_reality` (#467) +
  S-DNA menu (#470). `zola build` PASS (173 pages) · `qa_check.py` PASS (558 files) ·
  `check_internal_links.py` PASS · `qa-404-checker.py` 0 internal broken. All four
  features survived.

#### V13 — Scheduled Forward-Reference: future-dated drafts wrongly flagged as broken links

> Process + tooling vaccine (not a workflow-run failure). Match the signature →
> trust the FIXER below; the checker already handles it automatically.

- **Symptom:** `qa-404-checker.py` reports `N internal broken` and **exit 2** (→
  `qa-check` red → auto-merge blocked → deploy blocked) for links that point to a
  post which **does not yet exist in `public/`**. The target turns out to be a post
  that is `draft = true` with `[extra] publish_at = "<future ISO>"` (scheduled via
  `scheduled-publish.yml`). The failure is **unrelated** to the PR under review —
  often a content/news post links *forward* to a sibling that publishes in a day or
  two. Example (19/06/2026): 3 `content/baochi/*` posts linked to
  `bidv-smartbanking-khong-vao-duoc` (publish 21/06) and `bi-kip-xin-visa-han-quoc-5-nam-de`
  (publish 20/06) → 3 false "broken" links blocking an unrelated paywall PR.
- **Root cause:** Zola does not build drafts (`build_drafts` off), so a link to a
  scheduled-but-unpublished post 404s in `public/`. These are **scheduled
  forward-references**, NOT broken links — they resolve automatically the moment
  `scheduled-publish.yml` flips `draft=false` on the publish date. The checker
  previously had no draft/`publish_at` awareness, so it treated them as hard 404s.
- **FIXER (already implemented in `qa-404-checker.py`):** before flagging an
  internal 404, the checker builds a map of **scheduled forward-targets** —
  `_scheduled_forward_targets(now)` scans `content/**/*.md`, and for any post with
  `draft = true` **and** `[extra].publish_at` (top-level accepted too) parsing to a
  datetime **in the future**, records its canonical URL + aliases. A 404 whose
  target is in that map is reclassified `status: "scheduled-forward-ref"`
  (`error_type: scheduled_forward_ref`, with `publish_at`) → counted as a
  **warning**, NOT in `internal_broken`, so **exit stays 0**. Summary gains
  `scheduled_forward_refs`. Once `publish_at` has **passed** (or there is no
  `publish_at`, or the post is not a draft) the link is checked with **strict 404**
  again — no permanent allow-list. Parsing is crash-proof (any error → treated as a
  normal/strict link, so a genuine broken link is never silenced).
- **Rules:** (1) Keep genuine 404 detection STRICT for everything else — only
  `draft=true` + FUTURE `publish_at` is exempt. (2) Never hard-code slugs into an
  allow-list; the exemption is computed from frontmatter and self-expires. (3) A
  scheduled forward-ref is a warning to surface, not a failure to gate on. (4) Do
  NOT "fix" such links by repointing/removing them — they are intentional; let them
  resolve on publish.
- **Tests:** `python3 -m unittest scripts.test_qa_404_scheduled -v` (future=skip ·
  past=strict · no-publish_at=strict · published=n/a · aliases included · bad
  frontmatter degrades to strict).
- **Validation (19/06/2026):** with V13, `qa-404-checker.py` → `0 internal broken ·
  3 scheduled forward-refs · status warn · exit 0`; genuine broken links elsewhere
  still exit 2.

#### V14 — Fabricated topic-cluster cross-links: `/zola/bai-N-<title-slug>/` 404s block the QA gate

> Content vaccine (not a workflow-run bug — the gate is RIGHT, the content is wrong).
> Match the signature → run the FIXER **by intent**; do NOT re-diagnose, do NOT blanket
> slug-remap, do NOT rely on `--fix` alone.

- **Symptom:** `QA Gatekeeper` (`qa.yml`) red at the last step — `qa-404-checker.py`
  prints `… N internal broken … status: fail` and **exit 2** → auto-merge + deploy
  blocked. `zola build` itself **PASSES** (Zola ignores dangling internal markdown
  links). The broken hrefs are **root-level** `/zola/bai-<part>-<slugified-title>/`
  (hub gets a `-pillar` suffix), **NOT** under `/posting/`. The same broken target is
  referenced from several sibling articles, so the count multiplies (e.g. **40 broken =
  20 distinct targets × 2–4 refs**). The failure looks **unrelated** to the PR under
  review and reproduces on **every** branch cut from the same `main` (identical count
  on independent branches = systemic, from `main` content).
- **Why the scheduled checker can show 0/pass (false calm):** the scheduled
  `qa-404-checker.yml` runs with `--fix` and **without** `build_feed_pagination.py`; if
  it last ran on an **older base** (before the offending articles landed) its committed
  `data/qa-404-report.json` reads `pass`. The breakage surfaces only in the QA
  Gatekeeper build. (Same "stale base" family as V9 — confirm the report's `updated_at`
  vs the offending commit.)
- **Root cause:** a batch of auto/agent-generated **"topic authority cluster"** articles
  (e.g. commit *"add 19 topic authority cluster articles"*) embed cross-cluster nav
  lines — `**Cluster:**`, `**SEO Cluster:**`, `## Liên kết … Cluster` bullet lists —
  whose URLs were **fabricated** from the series part number + a slugified title:
  `/{base}/bai-{part}-{slugify(title)}/` instead of the post's **real built URL**
  `/{base}/posting/{real-slug}/`. The fabricated stub is also **mangled** (truncated,
  language/section suffix dropped) — real `derado-va-neunda-haedo-tieng-han` → link
  `bai-2-derado-va-neunda-haedo`. No page **nor `aliases`** builds at `/bai-N-…/` → hard
  404. (Root-level links that *happen* to match a declared alias — e.g.
  `/zola/review-lpbank-so-2026/` — resolve; only the `bai-N-` fabrications 404.)
- **Why `--fix` is INSUFFICIENT:** `qa-404-checker.py --fix` only repoints a 404 when its
  nearest candidate scores **≥ 0.6** similarity. The mangled `bai-N` stubs fall below
  that for ~half (Korean/abbreviated slugs → `suggestion: None`), so `--fix` repairs only
  ~**20 of 40** and resolves to root-alias URLs, not canonical `/posting/`. **Running
  `--fix` alone does NOT clear the gate.**
- **FIXER (by intent — never blanket slug-remap):**
  1. List offenders: `grep -rlE "\(/(zola/)?bai-[a-z0-9-]+/?\)" content/`.
  2. For **each** link, read its **anchor text + host article** to find the **intended**
     sibling, then repoint to that post's **real** URL `/zola/posting/<real-slug>/`
     (verify `content/posting/<real-slug>.md` exists and is **not** `draft = true`).
  3. If the intended target is a **planned/unwritten** post (e.g. link text *"FAQ điểm
     thi lớp 10"* with no such article) → **REMOVE** the link; never invent a target.
  4. **Intent > slug:** do NOT trust stub auto-mapping — `bai-5-faq` *looked* like the
     banking FAQ post but its text meant a different (grade-10 exam) post.
  5. Gate locally: `python3 scripts/build_feed_pagination.py` → `build_references.py` →
     `python3 scripts/paywall_prepare_build.py --strip` → `zola build` → `--restore` →
     `python3 qa-404-checker.py` must print `0 internal broken … exit 0` (zero
     `/bai-` links left).
- **Prevention / Rules:**
  - Cross-cluster / series / pillar nav links MUST use the target post's **real built
    URL** (`/zola/posting/<slug>/`) or a **real declared `aliases`** entry — **NEVER** a
    fabricated `/bai-N-<title>/` scheme. The `/posting/` section prefix is required;
    root-level only works if the post declares that exact alias.
  - Any generator emitting cluster/pillar cross-links must derive the URL from the target
    post's **actual slug/section/aliases**, not from `bai-{part}-{slugify(title)}`.
  - A clean `zola build` does **not** prove links resolve — only `qa-404-checker.py` (the
    `qa.yml` gate) catches dangling internal links. Run it locally before trusting CI.
  - QA-green / conflict-free ≠ **link-safe**: a fresh batch of generated articles can
    pass build yet inject dozens of 404s. The scheduled `--fix` is a *partial* net only.
- **Validation / Evidence (19/06/2026):** QA Gatekeeper runs **#1760**
  (`claude/awesome-gauss-edm7ve`) & **#1761** (`claude/sleepy-carson-13c9yp`) both red —
  `qa-404-checker.py: 40 internal broken · status fail · exit 2`, while `zola build`
  passed (396 pages). 19 articles from *"add 19 topic authority cluster articles"*; 40
  broken = 20 distinct fabricated `/bai-N-…/` targets, each referenced 1–4×. The 07:15
  scheduled report read `0/pass` because it ran on the pre-batch base. `--fix` dry-run:
  only **20/40** reached a ≥0.6 suggestion → manual intent-based repoint/removal required.

#### V16 — Static-site ↔ backend split-brain: CI green but VIP premium still locked (Render not redeployed)

> Deploy/infra vaccine. Match the signature → run `backend8` (do NOT re-diagnose),
> then suggest a Render Manual Sync. **Never report success while the backend lags `main`.**

- **Symptom:** QA Gatekeeper green, `auto-merge.yml` merged, **`deploy.yml` (GitHub Pages)
  succeeds**, yet a VIP/supervip on a premium article (`data-vipzone-premium="true"`) still
  cannot read the body — `GET {vipzone_api}/api/vipzone/content/{post_id}` returns
  **404 `premium_content_unavailable`** (or 503). The "Premium gộp gói" promise looks broken
  even though the code is on `main`. Often co-occurs with GitHub API **rate-limit** noise
  during `theodoi8` polling, masking the real cause.
- **Root cause:** GitHub Pages always ships the latest `main`, but the FastAPI backends on
  Render (`blog-vipzone-api`) only redeploy on a **manual** Blueprint sync. So the **static
  site is ahead of the backend** — endpoints/content that exist in the repo 404 in
  production. This is a **split-brain**, NOT a code bug and NOT a `zola build` failure. A
  green static deploy is **not** proof the backend serves the new code.
- **Detector / FIXER (`backend8`):** `python3 scripts/backend_sha_check.py` compares
  **`git rev-parse origin/main`** against the backend's **`/health.deployed_sha`** (Render
  injects `RENDER_GIT_COMMIT`; exposed by `services/vipzone/main.py`). Outcomes:
  `in_sync` (no action) · `outdated` → **BACKEND_OUTDATED** (Render → Blueprints → **Manual
  Sync `blog-vipzone-api`**) · `unknown` (dyno asleep / `RENDER_GIT_COMMIT` unset → retry,
  never a false success). Report cached to `data/backend-status.json`. **Report-only** (exit 0)
  unless `--strict` (exit 2 on outdated) — it must never gate CI offline.
- **Auto-heal (frontend, already wired):** `static/js/vipzone.js` `initPremiumUnlock()` — for a
  VIP/supervip on a premium article it fetches the content endpoint and **reveals it inside the
  per-post paywall DOM** (`#paywall-premium [data-paywall-body]`); on 404/503/auth-fail it
  prepends a calm **"backend pending"** notice (`.vipzone__backend-pending`) to `#paywall-box`
  **without** overlaying/blurring (that was the #507 regression) so the per-post unlock stays
  usable. Diagnoses the mismatch instead of showing a dead lock.
- **Rate-limit-safe monitoring (reuse, no new daemon):** prefer authenticated MCP/`gh` +
  `try_auto_merge.py` (`auto-merge.yml` `concurrency` queues merges FIFO → no API storm);
  `backend8` uses **one** `/health` GET with **exponential backoff** + cached
  `data/backend-status.json`; dispatch workflows **one-shot** only. `theodoi8` surfaces
  `BACKEND_OUTDATED` after a green deploy — **never silently succeed**.
- **Prevention:** after any backend change merges (`services/**`), run `backend8`
  (`deploysafe8`) before calling a deploy "done"; treat a green Pages deploy + outdated
  backend SHA as **incomplete**; the only human action is a Render Manual Sync (Claude cannot
  deploy Render).
- **Tests:** `python3 -m unittest scripts.test_backend_sha_check -v` (in_sync · outdated ·
  unreachable=unknown · no-backend-sha=unknown · no-main=unknown · prefix-match).

#### V17 — VIPZone admin OAuth loop + Content Picker hidden on Edge/Safari

> Auth/UI vaccine. Match signature → apply FIXER; details: `docs/memory/vaccine-v17-vipzone-edge-safari-auth.md`.

- **Symptom:** `/tools/vipzone-admin/` login loop (`/auth/login` → `missing_token` → retry); Content Picker blank/hidden; superadmin button missing after OAuth on Edge/Safari.
- **Root cause:** Session only in `sessionStorage` + Bearer header (`credentials:omit`); callback blocked non-super users; no `SameSite=None` HttpOnly cookie for cross-site static↔Render API.
- **FIXER:** `cms_auth.py` Set-Cookie `zola_cms_sid` (Secure+HttpOnly+SameSite=None) + allow all OAuth users; `roles.py` `tamsudev.com@gmail.com` → superadmin; `vip-admin.js` localStorage sid mirror + `credentials:include` + always render picker (disable actions by role); `vipzone.js` admin button stays visible for superadmin.
- **Detector:** `scripts/qa_vaccines.py` → `check_v17_vipzone_edge_safari_auth`.
- **Tests:** `python3 -m unittest services.vipzone.test_main scripts.test_vipzone_roles -v`.

#### V18 — Runtime Artifact Conflict: volatile state/log/report files committed to hotfix PRs

> Process + tooling vaccine (not a workflow-run failure). Match signature → apply FIXER.
> Root class: same as V6 (bot data refresh conflict) but specific to **vaccine/QA engine runtime files**.
> Evidence: PR #548 (`vaccine-hotfix/deploy_fail-27866069932`) and #547/#549 — all blocked
> `dirty` because concurrent hotfix runs each committed volatile state/log/report artifacts
> to the same paths (timestamps, PIDs, run IDs) with no real code change.

- **Symptom:** `vaccine-hotfix/*` or `qa/*` PR shows `mergeable_state: dirty` with conflicts
  **only** in these files:
  - `data/vaccine-hotfix-state.json` (lock — PID + timestamps)
  - `data/vaccine-hotfix.log` (append-only log)
  - `data/vaccine-hotfix-report.json` (run metadata — trigger, run_id, branch, timestamps)
  - `data/vaccine-autofixer-state.json` (lock — same pattern)
  - `data/vaccine-autofixer.log` (append-only log)
  - `data/qa-rule-checker-state.json` (state append entries with timestamps)
  - `data/autofix-conflicts-state.json` (state file)
  - `reports/rule-conflict-report.json` (only `updated_at` changed)
  - `reports/rule-conflict-report.md` (only `Updated:` line changed)
  The PR's actual code fix (templates, scripts, content) does **NOT** conflict.
- **Root cause:** `vaccine-hotfix.yml` used `git add -A` which staged volatile runtime
  artifacts alongside the real fix. Every concurrent hotfix run writes the same state/log/report
  paths with different timestamps/PIDs/run_ids → merge conflict. The conflict is NOT a logic
  bug and carries zero fixable code. `qa-auto-rule-checker.py` unconditionally updated
  `updated_at` in `reports/rule-conflict-report.*` on every run even when conflict count was
  unchanged → timestamp-only conflict.
- **FIXER (applied 20/06/2026):**
  1. `.gitignore` — added pure lock/log/state files (they are never needed on the deployed site):
     `data/vaccine-hotfix-state.json`, `data/vaccine-hotfix.log`,
     `data/vaccine-autofixer-state.json`, `data/vaccine-autofixer.log`,
     `data/qa-rule-checker-state.json`, `data/autofix-conflicts-state.json`.
  2. `git rm --cached` those 6 files to untrack them from the index.
  3. `.github/workflows/vaccine-hotfix.yml` — after `git add -A`, explicitly unstage all
     volatile runtime artifacts (including `data/vaccine-hotfix-report.json` and
     `reports/rule-conflict-report.*`) via `git restore --staged`. Hotfix PRs now commit
     ONLY the actual code delta; run metadata is committed by scheduled workflows.
  4. `scripts/qa-auto-rule-checker.py` `write_reports()` — idempotent: only write
     `reports/rule-conflict-report.*` when conflict count or conflict list actually changes;
     a timestamp-only run leaves the files unmodified → no git dirty state → no conflict.
- **Rules (permanent):**
  - **Never `git add -A` in a multi-PR automation** without explicitly unstaging runtime artifacts.
  - **State/lock/PID files → gitignore** — they change on every run and never contribute code.
  - **Report files → idempotent writes** — only update when the semantic content changes.
  - **Hotfix PRs → minimal delta only**: commit the fix files, not run bookkeeping.
  - `dirty` PR with conflicts ONLY in `data/*state*.json`, `data/*.log`, or `reports/*report.*`
    = V18 signature → apply FIXER (below), never hand-merge these files.
  - **V18 self-conflict (PR #551, 2026-06-20):** the V18 fix PR itself was blocked by the
    same 3 files it was gitignoring (`data/qa-rule-checker-state.json`,
    `data/vaccine-hotfix-state.json`, `data/vaccine-hotfix.log`). Resolution: `git merge
    origin/main` → for each `DU` (deleted-by-us, modified-by-them) conflict file → `git rm
    --cached <file>` (keep untracked). Never commit stale runtime state/log. Never hand-merge.
    This is always safe because these files carry zero fixable code.
- **Detector:** `scripts/qa_vaccines.py` → `check_v18_runtime_artifact_conflict` (code `V18-RUNTIME`).
  FAIL if any of the 6 state/log files are still tracked (`git ls-files`).
  WARN if `vaccine-hotfix.yml` lacks the `git restore --staged` filter.
  WARN if `write_reports` in `qa-auto-rule-checker.py` is not idempotent.
- **Regression test list (exact #548 files):** `data/qa-rule-checker-state.json`,
  `data/vaccine-hotfix-report.json`, `data/vaccine-hotfix-state.json`,
  `data/vaccine-hotfix.log`, `reports/rule-conflict-report.json`, `reports/rule-conflict-report.md`.
- **Regression test list (exact #551 self-conflict files):** `data/qa-rule-checker-state.json`,
  `data/vaccine-hotfix-state.json`, `data/vaccine-hotfix.log`.
- **Regression test list (exact #555 files — vaccine-autofixer):** `data/qa-rule-checker-state.json`,
  `reports/rule-conflict-report.json`, `reports/rule-conflict-report.md`.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines -v -k V18` (includes `RuntimeArtifactV18Test` and `RuntimeArtifactVaccineTest`).
- **Evidence (PR #555, 2026-06-20):** `chore/vaccine-autofixer-20260620-102216` went dirty because
  `main` ran `qa-rule-checker` at `10:22:42Z` while the PR had entries at `10:15:47Z`. Zero real
  code in conflict. Resolved by taking main's versions + applying FIXER above.

#### V19 — GSC Domain Property: must use sc-domain:seomoney.org (not URL-prefix)

> Migration + config vaccine. Domain `seomoney.org` verified via Cloudflare DNS TXT (2026-06-20).
> Match the signature → run the FIXER immediately; do NOT re-diagnose.

- **Symptom:** GSC data shows low coverage or property mismatch; `fetch_gsc_metrics.py` connects
  but returns 0 indexed pages / wrong sitemap; dashboard shows old `https://seomoney.org/` property
  instead of `sc-domain:seomoney.org`; CI workflow `gsc-stats.yml` secret `GSC_PROPERTY_URL` still
  set to the URL-prefix form; or QA Vaccine Gate reports **V19 FAIL**.
- **Root cause:** Google Search Console has two property types: (a) **URL-prefix** (`https://seomoney.org/`
  — verifies only that exact URL protocol+path) and (b) **Domain property** (`sc-domain:seomoney.org`
  — covers `http://`, `https://`, all subdomains, after DNS TXT verification). After Cloudflare setup
  the domain property was verified and the sitemap submitted → 1,634 discovered pages. The old
  URL-prefix property misses `http://` and subdomains; the domain property is the authoritative one.
  Code/config left pointing at `https://seomoney.org/` fetches from the WRONG property.
- **Signature (match all):**
  - `services/visitor-counter/gsc_client.py`: `DEFAULT_GSC_PROPERTY_URL = "https://seomoney.org/"` (old)
  - `scripts/fetch_gsc_metrics.py` docstring: example still shows URL-prefix
  - `config.toml` comment: "URL prefix trong GSC"
  - `data/gsc-metrics.json`: property field is null or `https://seomoney.org/`
  - QA V19 FAIL reported by `scripts/qa_vaccines.py`
- **FIXER:**
  1. `services/visitor-counter/gsc_client.py` → `DEFAULT_GSC_PROPERTY_URL = "sc-domain:seomoney.org"`
  2. Update GitHub secret `GSC_PROPERTY_URL` → `sc-domain:seomoney.org` (Settings → Secrets).
  3. Update Render env var `GSC_PROPERTY_URL` → `sc-domain:seomoney.org` on blog-vipzone-api.
  4. After OAuth reconnect, verify backend's `GET /gsc/status` returns `property: sc-domain:seomoney.org`.
  5. Run `python3 scripts/fetch_gsc_metrics.py` locally (with secrets) to confirm data flows.
  6. Check `static/robots.txt` has `Sitemap: https://seomoney.org/sitemap.xml`.
  7. Run `python3 scripts/qa_vaccines.py` → V19 must PASS.
- **Public JSON safety rules (BẮT BUỘC):**
  - `data/gsc-metrics.json` MUST NOT contain: `refresh_token`, `access_token`, `client_secret`, `client_id`.
  - Only aggregate metrics (clicks, impressions, top pages, etc.) allowed in the public file.
  - Credentials stay in GitHub secrets + Render env vars only — NEVER in repo or `data/*.json`.
- **Sitemap canonical:** `https://seomoney.org/sitemap.xml` (submit in GSC → Sitemaps → Add).
  Zola generates `sitemap.xml` automatically; `static/robots.txt` must declare it.
- **Validation:** `python3 scripts/qa_vaccines.py` → V19 PASS · `python3 scripts/test_gsc_client.py` →
  `test_default_property` + `test_normalize_sc_domain_passthrough` + `test_pick_preferred_sc_domain` PASS.
- **Evidence (2026-06-20):** domain property `sc-domain:seomoney.org` verified via Cloudflare;
  sitemap `https://seomoney.org/sitemap.xml` submitted; 1,634 discovered pages confirmed. Code
  migrated from `DEFAULT_GSC_PROPERTY_URL = "https://seomoney.org/"` to `"sc-domain:seomoney.org"`.

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

### Quy tắc (BẮT BUỘC)

1. **Không** duplicate scan — tắt mấy vaccine nếu có bot khác đang fix cùng issue.
2. **Không** break CI/deploy — auto-fix chỉ **safe issues** (confidence ≥90%, không sửa content).
3. **Luôn** chạy QA sau fix — `qa_check.py`, `zola build` trước khi mở PR.
4. **PR flow cho MỌI thay đổi** — workflow mở PR `chore/vaccine-autofixer-*` → auto-merge khi QA xanh. **KHÔNG** push thẳng `main`.
5. **Không chạy đồng thời** — lock `data/vaccine-autofixer-state.json` (stale 30') + `concurrency` group; run trùng → skip (exit 3).
6. **Log lịch sử** — append `history[]`, giữ 30 mốc gần nhất.
7. **Error handling** — bọc mọi đọc file/network trong try/except, exit 0 nếu non-critical (không sập CI); CI-log diagnosis (`gh`) best-effort, thiếu `gh`/token → skip.

### Insights UI

Trang `/zola/insights/` có block mới **🔬 Vaccine Autofixer**:

- **Header**: tiêu đề + nút **Run Daily Vaccine Autofixer** (mở GitHub Actions →
  Run workflow) + chip "Đang chạy…" khi lock active.
- **Meta**: Last run · Next scheduled run (06:00 GMT+7 kế tiếp) · Trigger ·
  Vaccine library count · Fixed count.
- **Status chips**: status tổng (ok/dry-run/fail) · QA pass/fail · Build pass/fail ·
  Prod (up-to-date/pending-pr).
- **Matched vaccines**: mỗi vaccine khớp lần chạy = 1 chip (✓ nếu đã fix; tooltip = detail).
- Khi chưa có report → hướng dẫn chạy `vacxin11` / đợi lịch 06:00.

### Chạy thủ công (local/dev)

```bash
# Shortcut: vacxin11 (CI: GitHub Actions → Daily Vaccine Autofixer → Run workflow)
python3 scripts/vaccine_autofixer.py --trigger manual     # quét + auto-fix an toàn
python3 scripts/vaccine_autofixer.py --dry-run --no-build  # chỉ quét, không sửa
# Kết quả: data/vaccine-autofixer-report.json được sinh/update
```

**Mở Insights** → scroll xuống → thấy block **🧪 Daily Vaccine Autofixer** với data mới nhất.

### Mở rộng (future)

- Thêm vaccine mới → chỉ cần thêm block `#### V<N> — …` vào CLAUDE.md (engine tự
  parse qua `load_vaccines`); thêm safe fixer step nếu auto-fix được.
- Nối `DOMAIN_CHECK_API`/provider thật cho các bước cần network.
- Webhook notification khi detect risky issue (Slack).
- Auto-rerun nếu first attempt fail.

#### V10 — Compliance Heading Focus: pages with 0 `<h1>` (feed-anchor + homepage pagination)

- **Symptom:** `compliance_audit.py` warns **Heading focus** — e.g. `635/749 single H1`.
  Built HTML scan shows `h1_count=0` on `/feed-anchor-*` routes and homepage `/page/N/`
  (including `/`). Article pages are fine (`page.html` already renders one `<h1>`).
- **Root cause:** `templates/feed-anchor.html` had empty `{% block main %}`; `index.html`
  used only `<h2>` for listing sections. Zola pagination routes inherit `index.html`.
- **FIXER:** (a) Add `<h1 class="visually-hidden">` in `feed-anchor.html` (uses
  `page.title`). (b) Add one visually-hidden `<h1>` at top of `index.html` main block
  (matches SERP title). Reuse `.visually-hidden` from `_reset.scss` (same pattern as
  `editor.html`, `insights.html`). **Do not** add visible duplicate titles.
- **Validation:** `zola build` → `python3 scripts/compliance_audit.py --stdout` →
  Heading focus = `N/N single H1` (100%).

#### V11 — Compliance Taxonomies: `feed-anchor-*.md` stubs untagged

- **Symptom:** **Taxonomies** warn — e.g. `156/176 tagged`; all failures are
  `posting/feed-anchor-*.md` (no `[taxonomies]` block).
- **Root cause:** `scripts/build_feed_pagination.py` generated minimal front matter
  (`feed_anchor = true` only). Anchors in `content/` root do not count as posts, but
  `posting/feed-anchor-*.md` are scanned as articles by `compliance_audit.py`.
- **FIXER:** (a) Extend `ANCHOR_TEMPLATE` in `build_feed_pagination.py` with
  `categories = ["Tất cả", "Công nghệ"]` and
  `tags = ["feed-pagination", "site-infrastructure", "zola"]`. (b) Run
  `python3 scripts/compliance_content_vaccine.py --apply` to upgrade existing anchors.
  Auto-tag rule: infrastructure anchors share fixed taxonomy; real posts keep manual tags.
- **Validation:** Taxonomies = `176/176 tagged` (or `posts/posts` after anchor count).

#### V12 — Compliance Article Depth: thin `feed-anchor` bodies (0 chars)

- **Symptom:** **Article depth** warn — e.g. `156/176 substantive`; same 20 posting
  anchors with empty body (`CONTENT_MIN_CHARS = 300` in `compliance_audit.py`).
- **Root cause:** Anchors intentionally had no markdown body; audit treats all
  `posting/*.md` as articles regardless of `feed_anchor`.
- **FIXER:** (a) Append meaningful stub in `ANCHOR_TEMPLATE`: purpose, noindex note,
  link to homepage, small markdown table (not filler lorem). (b)
  `compliance_content_vaccine.py --apply` backfills all `feed-anchor-*.md`. For real thin
  posts (&lt;300 chars): expand with context H2, FAQ `[[extra.faq]]`, internal links from
  `related.json` — **never** pad with nonsense words.
- **Validation:** Article depth = `176/176 substantive`; `zola build` still green;
  homepage feed still excludes anchors (`feed_anchor` filter in `index.html`).

**Content vaccine runner (V10–V12):**

```bash
python3 scripts/compliance_content_vaccine.py --dry-run   # preview
python3 scripts/compliance_content_vaccine.py --apply     # fix anchors + body H1
zola build && python3 scripts/compliance_audit.py --stdout
python3 -m unittest scripts.test_compliance_content_vaccine -v
```

**Last run (19/06/2026):** `compliance_content_vaccine.py --apply` + template H1 →
Heading focus **801/801** · Taxonomies **176/176** · Article depth **176/176** ·
score **97.8/100 (A+)**. Root cause: 104 `feed-anchor` + 10 homepage `/page/N/` had
0 `<h1>`; 20 `posting/feed-anchor-*.md` lacked taxonomy/body. Reverted mistaken
code-fence demotion in `sentence-transformers-sbert-deep-dive.md` — demoter skips
fenced blocks.

#### V19 — Domain Migration Drift: stale `github.io/zola` refs in operational files after apex-domain migration

> Process + tooling vaccine. Match the signature → run `scripts/domain_migration_audit.py`; fix per FIXER below.

- **Symptom:** After migrating `banhang-chogao.github.io/zola` → `https://seomoney.org`, stale
  `github.io/zola` references survive in operational code (NOT test fixtures or migration-tool
  docstrings). Typical locations: (a) script variable comments (`# banhang-chogao.github.io` in
  qa-404-checker.py), (b) `data/performance-audit-snapshot.json` `url` field holding the old
  origin, (c) docs TODO items still open (`- [ ] custom domain`), (d) CLAUDE.md rule examples
  using the old domain in watermark/branding strings. Detector: `check_v19_domain_migration_drift`
  in `scripts/qa_vaccines.py`.
- **Root cause:** Migration tools (`scripts/rewrite_cdn_urls.py`, `scripts/fix_site_prefix_links.py`)
  correctly rewrote content/templates, but human-authored comments, cached data snapshots, and
  documentation examples were not in scope. These drift silently until audited.
- **Detector (WARN — does not break build):** `check_v19_domain_migration_drift`:
  1. Reads `config.toml` `base_url`; extract expected apex host (`seomoney.org`).
  2. Reads `data/performance-audit-snapshot.json`; WARN if `.url` ≠ base_url (stale snapshot).
  3. Scans operational files (`.py`, `.yml`, `.html`, `.js`, `.scss`, `.toml`, `.md` outside
     `scripts/test_*`, `data/`, `scripts/rewrite_cdn_urls.py`, `scripts/fix_site_prefix_links.py`,
     `scripts/dns_vaccine.py`, `CLAUDE.md`) for pattern `banhang-chogao\.github\.io/zola` →
     WARN per file found.
  4. Severity: WARN (drift, not build-breaking); escalate to FAIL only if `config.toml`
     `base_url` or `static/CNAME` still holds `github.io` (already gated by V15/dns_vaccine,
     but V19 re-checks for defence-in-depth).
- **FIXER (minimal delta — run after any domain rename):**
  1. `python3 scripts/domain_migration_audit.py` — full scan + table report.
  2. Fix stale comments: update `# github.io` / `# /zola` variable comments to reflect new host.
  3. Regenerate `data/performance-audit-snapshot.json`: trigger `perf-audit.yml` workflow or
     run `python3 scripts/fetch_pagespeed.py` locally (TARGET_URL already = seomoney.org).
  4. Mark done any open `- [ ]` doc TODOs about custom domain.
  5. Update CLAUDE.md examples that use old domain strings (watermark, branding examples).
  6. Content tutorial articles (`content/posting/*.md`) that *explain* GitHub Pages using
     `github.io` example URLs are **legitimate content** — do NOT rewrite them.
- **Exclusion list (never flag as V19 issues):**
  - `scripts/dns_vaccine.py` (PAGES_ORIGIN_HOST = `banhang-chogao.github.io` is correct DNS www-CNAME target)
  - `scripts/rewrite_cdn_urls.py`, `scripts/fix_site_prefix_links.py` (migration-tool docstrings)
  - `scripts/test_*.py`, `data/merge-report.json`, `data/dns-vaccine-report.json` (test fixtures / history)
  - `content/posting/tao-blog-voi-zola.md`, `content/posting/tu-dong-deploy-zola-github-actions.md`,
    `content/posting/ung-ho-du-an-ai-ten-mien-ai.md` (tutorial content explaining GitHub Pages)
- **Validation (20/06/2026):** Applied: stale comment in `qa-404-checker.py` (lines 79–82); done
  marker on `docs/seo-strategy.md` custom-domain TODO; watermark example in `CLAUDE.md` updated
  to `seomoney.org`. `scripts/domain_migration_audit.py` created. `dns_vaccine --offline --gate`
  PASS; `zola build` PASS; `qa_check.py` PASS.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.DomainMigrationDriftTest -v`

#### V20 — Search UI raw/unstyled: BEM markup with no structural CSS (only colour tints)

> UI vaccine (not a workflow-run bug — the page builds, it just looks broken).
> Match the signature → ship the scoped partial; do NOT rewrite the search engine.

- **Symptom:** the internal search dialog ("Tìm trong blog", opened from the navbar
  search button) renders **raw/default**: plain browser form, bad spacing, ugly close
  button, input + button not aligned, panel floating with no card. **Search logic works
  fine** — only the UI is broken. `zola build` PASSES (it is purely missing CSS).
- **Root cause:** the markup in `templates/base.html` uses BEM `.site-search__*` classes
  and the engine `static/js/site-search.js` injects `.site-search__summary` /
  `__results` / `__result*` nodes, but the **structural/layout CSS was never written**.
  Only **colour-tint** overrides existed in `sass/_theme-overrides.scss`
  (`:root[data-theme="hilda"] .site-search__*` — background/border/colour). Tints alone
  cannot lay out a modal: with no `position`, `max-width`, flex, padding or radius the
  panel collapses into document flow → looks unstyled. A colour override is **not** a
  component.
- **FIXER (already applied):** scoped partial **`sass/_site-search.scss`** supplies ALL
  structure — fixed overlay above the navbar (`z-index: 10050`) with a calm backdrop,
  a centred command-palette **panel card** (`max-width: 640px`, rounded, soft shadow),
  kicker + `Tìm trong blog` title, circular **close** button, search **field with icon**
  + focus ring, **primary submit**, summary chips, and a **result list styled like blog
  cards**. Imported in `site.scss` **before** `theme-overrides` so the Ericsson/Hilda
  tints still refine it. All colours use semantic `--c-*` tokens (B-DNA: tokens are the
  source of truth) → adapts to light/dark. Mobile (`≤720px`) stacks the input/button
  full-width; `.site-search[hidden]` keeps the overlay off until opened. **Search engine
  + markup unchanged** (minimal delta, no logic rewrite).
- **Prevention / Rules:** never ship BEM markup whose only CSS is a theme tint — a
  component needs its own scoped structural partial; reference the design system first
  (see the **UI/UX Reference Rule** below: `/branding-guideline/`, `/tools/s-dna/`,
  `/tools/b-dna/`, `/font/`); dialogs MAY float above content (B-DNA), but a clean,
  not raw, surface. **A green `zola build` does NOT prove the UI is styled** — only a
  render/visual check (or this detector) catches a raw component.
- **Detector:** `scripts/qa_vaccines.py` → `check_search_ui_vaccine` (code `SEARCH-UI`):
  FAIL if `_site-search.scss` is missing / unimported / lacks the overlay+panel+field+
  submit+result structure, or if base.html lost the dialog/input/submit/close/search-data
  markup, or `site-search.js` is gone; WARN if the mobile media query or
  `.site-search[hidden]` guard is absent.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.SearchUiVaccineTest -v`
- **Validation:** `zola build` PASS · `qa_check.py` PASS (search_ui_vaccine PASS) ·
  `check_internal_links.py` PASS · `qa-404-checker.py` 0 internal broken · search dialog
  renders a styled panel on desktop + mobile with the input/button aligned and visible.

#### V22 — Editor S-DNA visual layer: keep `/editor/` emoji-free + KPI cards, logic intact

> UI vaccine (not a workflow-run bug — the editor builds, the guard protects its look
> and its handlers). Match the signature → keep the scoped partial + outline SVGs;
> never re-introduce emoji icons or strip publish/SEO logic.

- **Symptom (regression it guards):** the `/editor/` CMS dashboard reverts to the old
  loud look — rainbow CMS pill, emoji action icons (🔐 🔍 🗑 📝 💾 📌 ✎ ⇄ 👁 📥 🚀 🧠 ⚠ ↻ ⏻ ✦ ＋),
  default form chrome — instead of the calm S-DNA surface (soft pastel KPI cards, coloured
  left accents, thin outline icons in circle rings). A green `zola build` does NOT prove the
  editor still looks/works right.
- **Root cause it prevents:** the S-DNA repaint lives in the scoped partial
  `sass/_editor-sdna.scss` (imported LAST in `site.scss`, after `editor` + `cms`) plus inline
  Lucide-style outline SVGs in `templates/editor.html` + `templates/partials/editor-seo-rail.html`.
  If that partial is dropped/unimported, or someone re-adds emoji glyphs, or removes the
  publish/edit handlers / SEO rail, the editor degrades. The repaint is **scoped to
  `.editor-app`** — it must never leak into navbar/footer/blog article surfaces (S-DNA's own
  "borrow selectively, never global redesign" rule).
- **FIXER:** keep `sass/_editor-sdna.scss` + `@import "editor-sdna"` in `site.scss`; map every
  visible action to an outline SVG (new/edit/save/publish/delete/back/search/refresh/logout/
  check/link/seo/sticky/image/tag/calendar) — never an emoji; render the SEO assistant as S-DNA
  KPI cards (pastel fill · left accent · circle ring · small label · big value); preserve
  `data-action="publish"`, `data-form="post"`, the `editor.js` include and the SEO rail
  (`data-seo-rail`). Mobile: two-column → single-column, sticky action bar anchored inside the
  editor panel (no floating/drifting). Logic (publish/edit GitHub commit, old-post SEO
  hydration, single-active sticky overwrite) stays in `editor.js` — untouched.
- **Detector:** `scripts/qa_vaccines.py` → `check_editor_sdna_vaccine` (code `EDITOR-SDNA`):
  FAIL if `_editor-sdna.scss` missing/unimported, if the editor templates carry emoji icons in
  visible UI (Tera/HTML comments stripped first; plain `↑↓←→` keycaps in `<kbd>` allowed), if
  `data-action="publish"` / `data-form="post"` / the `editor.js` include is gone, or if the SEO
  assistant (`editor-seo-rail` / `data-seo-rail`) is removed; WARN if the partial lacks the
  KPI-card (`.esr-kpi`) / circle-icon (`.ed-ico`) structure or the `≤720px` media query.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.EditorSdnaVaccineTest -v`
- **Validation (2026-06-20):** `zola build` PASS (245 pages) · `qa_check.py` PASS (EDITOR-SDNA
  PASS, 0 FAIL) · editor templates emoji-free · publish/edit handlers + SEO rail intact ·
  rail renders as KPI cards; redesign scoped to `.editor-app` only. The editor's
  bottom action bar is **in-flow on desktop** (honours V21 No-Floating-Nav) and only
  becomes sticky inside the panel under the mobile `≤720px` breakpoint.

#### V21 — No Floating Bar / Stable Nav Vaccine: desktop nav must stay in normal flow

> **No floating/sticky navigation on SEOMONEY desktop. Stable nav only.** The blog
> owner dislikes floating bars; they are visually tiring (eye strain). Desktop nav
> rails, sidebars and action bars MUST stay anchored in normal document flow and
> scroll naturally with the page — they may never detach and drift on scroll.

- **Symptom:** the desktop primary nav / sidebar nav card / action bar detaches from
  the layout and floats/drifts/jitters while scrolling past it. Caused by
  `position: sticky` / `position: fixed`, scroll-driven CSS animation/parallax
  (`animation-timeline: scroll()/view()`), or a JS scroll listener that mutates the
  nav's `transform`/`top`. `zola build` still PASSES — it is purely a UX regression.
- **Root cause / canonical fix (PR #585):** the desktop primary nav `.side-nav` used
  `position: sticky; top: 1rem`, which made it drift on scroll. The fix is
  `.side-nav { position: static }` — anchored in the right column's normal flow, with
  Search / Clear-cache actions kept inside the panel (`.side-nav__actions`). This
  vaccine permanently protects that behavior.
- **Rules (permanent):**
  - Protected desktop selectors — `.side-nav`, `.side-nav__actions`, `.primary-nav`,
    `.site-sidebar`, `.nav-rail`, `.desktop-nav` — must NOT use `position: sticky`/`fixed`,
    scroll-driven animation/parallax, or scroll-linked JS transform mutation in desktop scope.
  - **Exceptions (allowed):** true overlays / modals / search dialogs and the mobile
    hamburger drawer — `.nav-drawer*`, `.nav-toggle`, `.site-search*`, `[role="dialog"]` —
    and ANYTHING scoped under a mobile `@media (max-width: …)` breakpoint. Mobile is
    handled separately; do **not** break mobile to satisfy this rule.
- **Detector:** `scripts/qa_vaccines.py` → `check_no_floating_nav_vaccine` (code `V21`):
  FAIL if a protected desktop nav/sidebar/action selector floats (sticky/fixed/
  scroll-animation) outside a mobile media query, or a nav-referencing JS file wires a
  scroll listener that mutates `transform`/`top`/`position`. Comment-stripped + mobile-
  media-exempt so the mobile drawer and explanatory notes never false-trip.
- **Source guard:** `sass/_side-nav.scss` carries an inline comment on
  `.side-nav { position: static }` marking it intentional and protected by V21.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.NoFloatingNavVaccineTest -v`
  (sticky/fixed side-nav, translate-on-scroll JS, floating bottom action bar → FAIL;
  `position: static`, normal flow, mobile-drawer exception, search-modal exception → PASS).
- **Validation:** `python3 scripts/qa_vaccines.py` (V21 PASS) · `qa_check.py` PASS ·
  `zola build` PASS · desktop nav no longer floats/drifts on scroll.

#### V22 — Editor save→GitHub: CMS save must commit (not draft-only download), edit needs SHA, SEO rail hydrates, sticky single-active

> CMS/editor vaccine. Match the signature → run the FIXER **by intent**; the static
> detector `check_editor_publish_vaccine` (code `EDITOR-PUBLISH`) already guards it.
> Canonical fix: PR #588.

- **Symptom:** in `/editor/` (the GitHub-OAuth CMS) clicking **Save** / **Publish**
  never actually commits — the post silently goes nowhere or surfaces a vague
  **"Not Found"** with no real status. Editing an existing post can overwrite/conflict.
  Opening an old post shows an **all-zero SEO checklist** in the right rail. Pinning a
  post leaves the **previous sticky still pinned** (multiple sticky posts), or the save
  is **hard-blocked** with "unpin the other post first". `zola build` PASSES — the bug
  is in the editor save flow, not the site build.
- **Root cause:** `static/js/editor.js` shipped a **DRAFT-ONLY** `putPost` that merely
  triggered a `.md` blob **download** (`URL.createObjectURL` / `a.download = filename`)
  instead of **PUT-ing to GitHub** — so "saving" never committed. Edits sent **no SHA**,
  so updating an existing file was overwrite-unsafe. The SEO rail
  (`static/js/cms/editor-seo-rail.js`) only re-analyzed on the `input` event, but the
  editor populates fields with `.value = …` (which does **not** fire `input`) → loaded
  posts stayed on a zero checklist. Sticky was enforced by a client-side **hard block**
  (`ensureStickyAllowed`) rather than the backend auto-unsticking the previous post.
- **FIXER (canonical, PR #588):**
  1. **Commit, never download.** `editor.js` saves via a single
     `commitPostToGithub(payload)` → `POST {AUTH_API}/cms/save-post` (Bearer sid). Delete
     the draft-only `putPost` / blob-download save path entirely. Surface backend error
     `detail`/`status` clearly — **no silent "Not Found"**.
  2. **Edit forwards a SHA.** Send `sha: payload.sha` from `state.editing.sha` when
     updating an existing file (overwrite-safe). Backend re-reads the live sha
     (authoritative) but accepts `client_sha` as fallback.
  3. **SEO rail hydrates old posts.** After populating the form by `.value`, `editor.js`
     fires `document.dispatchEvent(new CustomEvent('cms:hydrated'))` (on post-load AND
     draft-recovery); `editor-seo-rail.js` listens for `cms:hydrated` → re-analyzes with
     the loaded values.
  4. **Sticky is single-active via auto-demote (no hard block).** Backend
     `services/visitor-counter/main.py` route `@app.post("/cms/save-post")` calls
     `_demote_other_sticky_posts(...)` in the SAME save op when the saved post is
     `sticky=true` → clears `sticky = true` from every other CMS `.md` (mirrors the
     `featured` auto-demote semantics). The client no longer hard-blocks save; UI mirrors
     via `applySavedPostState`.
- **Rules (permanent):** the CMS editor MUST commit to GitHub (never a draft-only file
  download); edits MUST send a SHA; field population by `.value` MUST emit `cms:hydrated`
  so the SEO rail re-scores loaded posts; sticky MUST be single-active by **auto-demoting**
  the previous sticky, never by hard-blocking the save; backend errors MUST be surfaced
  with `detail`/`status` (never a vague "Not Found"). A green `zola build` does NOT prove
  the editor commits — only this detector / a real save check does.
- **Detector:** `scripts/qa_vaccines.py` → `check_editor_publish_vaccine` (code
  `EDITOR-PUBLISH`): FAIL if `editor.js` doesn't call `/cms/save-post`, still ships a
  draft-only download (`putPost` / `a.download = filename`), sends no `sha` /
  `state.editing.sha`, or never emits `cms:hydrated`; if the rail doesn't listen for
  `cms:hydrated`; or if backend lacks the `/cms/save-post` route or
  `_demote_other_sticky_posts` wired into the save route. WARN if `editor.js` still
  hard-blocks save via `ensureStickyAllowed` (should auto-unstick) or backend is unreadable.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.EditorPublishVaccineTest -v`
  (missing save endpoint · draft-only download · edit without SHA · rail no hydrate ·
  backend no sticky-demote → FAIL; hard-block sticky → WARN; real repo → PASS) ·
  `python3 -m unittest scripts.test_editor_frontmatter.StickySingleActiveTests -v`.
- **Validation:** `python3 scripts/qa_vaccines.py` (EDITOR-PUBLISH PASS) · `qa_check.py`
  PASS · `zola build` PASS · saving in `/editor/` commits to GitHub, edits carry a SHA,
  old posts hydrate the SEO rail, sticky stays single-active.
- **V22b — Deployment split-brain (production smoke fail after #588, 2026-06-21):** the
  V22 backend routes in #588 were added to `services/visitor-counter/main.py`, but that
  Redis service is NOT deployed — `render.yaml` deploys `blog-vipzone-api` from
  `services/vipzone`, and `editor.js`'s `AUTH_API` points there. So in production every
  `POST {AUTH_API}/cms/save-post` (create new post, edit-with-SHA, sticky auto-demote) hit
  a non-existent route → **`404 {"detail":"Not Found"}`** (SEO-rail hydration is frontend-
  only and was unaffected). Same class as V16/#594 (GSC routes 404'd until served on the
  deployed vipzone app). **FIXER:** serve the CMS write surface on the DEPLOYED backend —
  `services/vipzone/cms_repo.py` (router: `/cms/save-post`, `/cms/posts/bulk-delete`,
  `/api/categories/{list,add}`, faithful port of the GitHub Contents + featured/sticky
  single-active demote logic), mounted in `services/vipzone/main.py` via `configure()` with
  the GitHub token sourced from the vipzone CMS session. `cms_auth.py` now persists the
  OAuth `access_token` in the session payload (whitelisted out of `/auth/me`, never leaked)
  and exposes `github_token_from_session()`. **Rule:** any route the frontend calls on
  `blog-vipzone-api` MUST exist on `services/vipzone` — a route living only in
  `visitor-counter` is dead in production. Tests: `services/vipzone/test_main.py`
  (`CmsRepoRoutesTests`, `CmsStickyFeaturedHelpersTests`).

#### V23 — SEO Identity / Homepage Migration: brand + canonical root must stay `https://seomoney.org/`

> SEO-identity vaccine (built from the 20/06/2026 apex-domain migration hotfix). Match the
> signature → restore the canonical identity; do NOT re-introduce the old domain/brand.

- **Symptom:** After moving to the apex domain `https://seomoney.org/`, a later edit silently
  regresses the **site identity** — any of: (a) `config.toml` `base_url` drifts back to a
  `github.io` host or a `/zola` subpath / `http://` scheme; (b) the homepage `<title>` / `<h1>`
  loses the **SEOMONEY** brand (e.g. reverts to the old "Blog công nghệ, du lịch & ẩm thực"
  wording) so SERP shows a stale identity; (c) article JSON-LD `@type` reverts from
  `BlogPosting` to a non-blog type, weakening rich-result eligibility. Canonical / OG / Twitter /
  RSS / sitemap / robots all derive from `config.base_url`, so a wrong `base_url` poisons every
  canonical signal at once.
- **Root cause:** the canonical identity lives in a few high-leverage spots
  (`config.toml base_url`, `templates/index.html` title/H1, `templates/base.html` article schema,
  `content/_index.md` meta). These are easy to overwrite during unrelated template/content work,
  and the regression is invisible until a crawler re-indexes the wrong canonical/brand.
- **FIXER:** (a) `config.toml` `base_url = "https://seomoney.org"` — apex, `https`, **no** `/zola`
  subpath, **no** `github.io`. (b) Homepage `templates/index.html` `{% block title %}` and the
  visually-hidden `<h1>` keep the brand string **`SEOMONEY`** (current: `SEOMONEY – SEO, AI WebOps
  & Tài chính cá nhân`); `content/_index.md` title/description stay on-brand. (c)
  `templates/base.html` page JSON-LD uses `"@type": "BlogPosting"` with `BreadcrumbList` present.
  Rebuild and verify the built `public/` has **0** old-domain site URLs, sitemap all-`seomoney.org`,
  robots Sitemap → `https://seomoney.org/sitemap.xml`.
- **GSC note:** runtime GSC property = `sc-domain:seomoney.org` (aggregates http/https + www/apex
  post-migration; `services/visitor-counter/gsc_client.py`), with `https://seomoney.org/`
  URL-prefix kept as fallback. **Canonical/sitemap stay `https://seomoney.org/`** — the sc-domain
  form is for the Search Console API only, never for on-page canonical tags.
- **Detector:** `scripts/qa_vaccines.py` → `check_v20_seo_identity_homepage` (result code `V20`).
  FAIL if `base_url` is non-apex/`github.io`/`/zola`/`http://`, or the homepage lost the SEOMONEY
  brand. WARN if article schema is not `BlogPosting`. Calibrated so current `main` = PASS.
  (Documented as **V23** because `#### V20`–`#### V22` were already taken on `main` when this
  landed — the registry guard below requires unique `#### V<N>` numbers, so the new vaccine takes
  the next free number; the detector's *result code* stays `V20` for continuity.)
- **Registry guard:** `scripts/qa_vaccines.py` → `check_vaccine_registry_integrity` (code
  `VACCINE-REGISTRY`) FAILs on (1) an **unexpected duplicate `#### V<N>` number** in CLAUDE.md
  beyond the documented legacy/multi-entry set `{V10, V11, V12, V19, V22}`, or (2) a **duplicate
  detector registration** (same callable or detector name listed twice in `DETECTORS`). New
  vaccines must use the next free number from `next_free_vaccine_number()` — never hardcode a taken one.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.SeoIdentityV20Test scripts.test_qa_vaccines.VaccineRegistryGuardTest -v`

#### V25 — Split-backend 404: frontend route on `blog-vipzone-api` exists only in undeployed `services/visitor-counter`

> Deploy/infra vaccine — generalises V16/V22b into a permanent rule + static gate +
> post-deploy checker. Match the signature → mount the route on the DEPLOYED service;
> NEVER report success while a frontend-called route 404s.

- **Symptom:** the static site calls `${vipzone_api_url}/…` (= `https://blog-vipzone-api.onrender.com/…`,
  the `AUTH_API` in `static/js/*`) and gets **`404 {"detail":"Not Found"}`** for a route
  that clearly exists in the repo — typically a `/cms/*`, `/gsc/*`, `/auth/*` or
  `/api/vipzone/*` endpoint. `zola build` and the GitHub Pages deploy are both green;
  the bug is purely backend route absence. Editor save, SEO Reality Check (GSC), author
  profile, footer countdown, content-creator, giscus setup, etc. silently fail.
- **Root cause (the permanent trap):** Render deploys **ONLY** `services/vipzone`
  (`render.yaml` → `rootDir: services/vipzone`, `name: blog-vipzone-api`). The route was
  added to `services/visitor-counter/` (the old Redis service, **not deployed**), so it
  lives in the repo but is **dead in production**. A route that exists only in
  `visitor-counter` is never served to the production frontend. Same class as V16
  (static↔backend split-brain) and V22b (#588 CMS routes 404'd until ported to vipzone).
- **RULE (BẮT BUỘC):** **Any** frontend API path that uses `vipzone_api_url` /
  `blog-vipzone-api.onrender.com` (i.e. `AUTH_API + "/…"` in `static/js/**`) MUST have a
  matching route mounted on the **deployed** `services/vipzone` app — either directly in
  `services/vipzone/main.py` (`@app.*`) or on a router mounted there via `include_router`
  (`cms_auth.py`, `cms_repo.py`, or `gsc_routes.py` imported from visitor-counter with
  prefix `/gsc`). Keep `services/visitor-counter` for compatibility, but **never rely on
  it** for any route the production frontend calls.
- **FIXER:** port/mount the missing route onto `services/vipzone` (faithful minimal port,
  source the GitHub token from the vipzone CMS session as `cms_repo.py` does); add it to
  the appropriate mounted router; re-run the static parity detector + the post-deploy
  checker; after merge, run `backend_route_check.py` against production before calling it
  done (a green Pages deploy + a 404 critical route = **incomplete**).
- **Static detector:** `scripts/qa_vaccines.py` → `check_v24_backend_route_parity`
  (code `V24`). **FAIL** if a critical route (`/health`, `/gsc/status`, `/cms/save-post`)
  is not mounted on `services/vipzone` (directly or via a mounted router). **WARN** per
  frontend `/cms/*` or `/gsc/*` family that has no matching deployed route (drift to fix).
  Calibrated so current `main` = 0 FAIL.
- **Post-deploy checker:** `python3 scripts/backend_route_check.py` hits the live backend
  and asserts the critical routes never return 404 — `/health` 200, `/gsc/status` not-404,
  `/cms/save-post` (POST, no auth) **401/403/405 but NEVER 404**. Report-only by default
  (exit 0), `--strict` exits 2 on any 404. Reads `/health` `critical_routes`/`cms_mounted`/
  `gsc_mounted`/`backend_sha` when present.
- **`/health` fields (optional, additive):** `services/vipzone/main.py` `_health_payload()`
  now also returns `backend_sha` (alias of `deployed_sha`), `cms_mounted`, `gsc_mounted`,
  and `critical_routes` (`{route: mounted}` from the live `app.routes`).
- **Smoke URLs (exact):**
  - `https://blog-vipzone-api.onrender.com/health` → 200, `critical_routes` all `true`
  - `https://blog-vipzone-api.onrender.com/gsc/status` → not 404 (401/200)
  - `curl -X POST https://blog-vipzone-api.onrender.com/cms/save-post` → 401/403/405, never 404
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.BackendRouteParityV25Test scripts.test_backend_route_check -v`

#### V24 — GSC OAuth refresh token acquired but not persistable after redeploy (operator export path)

> Deploy/operator vaccine. The OAuth flow can mint a refresh token into the VIPZone
> SQLite KV, but on Render free tier `/tmp` is wiped on redeploy → the token vanishes
> and the SEO Reality Check widget goes back to "not connected" after every deploy.
> The durable home is the **`GSC_REFRESH_TOKEN` env var**, but the operator had **no
> safe way to extract** the acquired token to copy it there. Match the signature →
> use the export endpoint; never widen `/gsc/status`.

- **Symptom:** after a Render redeploy of `blog-vipzone-api`, `/gsc/status` shows
  `connected:false` / `token_source:none` again even though the operator completed the
  GSC OAuth flow before. The KV-stored refresh token did not survive the redeploy
  (`/tmp` SQLite reset, same class as V16/V22b split-brain) and there is no env token.
  Or: operator wants to persist the token but cannot read it anywhere (status is
  public-safe and never exposes it).
- **Root cause:** the OAuth callback persisted the refresh token **only** to the volatile
  SQLite KV (`gsc:refresh_token`). `GSC_REFRESH_TOKEN` was a *fallback*, and there was no
  endpoint/CLI to export the minted token, so the operator could not copy it into the
  durable env var. Result: re-OAuth on every redeploy.
- **FIXER (already implemented in `services/visitor-counter/gsc_routes.py`):**
  1. **Env priority** — `_load_refresh_token` / `_token_source` prefer the durable
     `GSC_REFRESH_TOKEN` env over the volatile KV copy (once persisted, env wins even
     over a stale KV token).
  2. **`/gsc/status` stays public-safe** — never returns the token; only `configured`,
     `connected`, `has_refresh_token`, `token_source` (`env|kv|none`).
  3. **Supervip-only export** — `GET /gsc/refresh-token` (Bearer sid or `?sid=`):
     denied 401/403 without a valid superadmin; **masked by default**; full secret only
     with explicit `?reveal=1`; 404 with a clear `no_refresh_token` message when none;
     the token is **never logged**. Payload carries `instructions` (the operator runbook).
  4. **OAuth start forces a refresh token** — `access_type=offline` + `prompt=consent`
     + `include_granted_scopes=true` so Google always returns `refresh_token`.
  5. **Operator runbook after callback** — success redirect carries `gsc_persist=1` when
     the token is not yet in env, signalling the UI to surface: copy refresh_token → set
     Render env `GSC_REFRESH_TOKEN` → Manual Sync `blog-vipzone-api` → verify
     `/gsc/status` shows `token_source=env`.
- **Rules (permanent):** `/gsc/status` is public — NEVER add the raw token to it; the
  token is exported ONLY through the supervip-gated `/gsc/refresh-token` (masked unless
  `?reveal=1`); the env token ALWAYS wins over the KV token; never write the token to a
  log line; the only durable persistence is the Render env var + Manual Sync (Claude
  cannot set Render env).
- **Tests:** `python3 -m unittest services.vipzone.test_main.GscRefreshTokenExportTests -v`
  (no token leak in status · supervip-only export · invalid sid denied · masked default /
  reveal full · env preferred over KV · missing token → clear 404).

#### V26 — "On This Page" TOC rail: blog posts need the sticky scroll-spy right rail (B-DNA pattern)

> UI vaccine (not a workflow-run bug — the post builds, the guard protects the rail).
> Match the signature → keep the scoped partial + scroll-spy JS; never ship a raw rail
> or break mobile. Detector `check_toc_rail_vaccine` (code `TOC-RAIL`) gates it.

- **Symptom (regression it guards):** a long article loses its sticky **"Trong bài này"**
  right rail — the desktop scroll-spy TOC inspired by the B-DNA rail (`.bdna__rail`,
  `templates/b-dna.html`). Either the rail stops rendering, the active-heading highlight
  dies (no `IntersectionObserver`), or the rail leaks onto narrow/mobile widths and
  overflows. A green `zola build` does NOT prove the rail still works — only this detector
  or a render check does.
- **Root cause it prevents:** the rail lives in three coupled places — the scoped partial
  `sass/_toc-rail.scss` (`@import "toc-rail"` in `site.scss`, after `toc`), the server-side
  markup in `templates/page.html` (`<aside class="toc-rail" data-toc-rail>` generated from
  `page.toc`, gated by `show_rail = show_toc and not paywall_active`), and the scroll-spy
  engine `static/js/toc-rail.js`. Drop any one → the rail breaks. The rail is **additive**:
  it sits in a `.post-layout--rail` grid (`minmax(0,1fr) 248px`) beside the article, sticky
  on desktop **≥1300px only**; below that it is `display:none` and the existing inline
  `.toc` (top of content) serves instead — never two TOCs at once, no overflow, no layout
  shift (rail is server-rendered; JS only toggles `.is-active`).
- **FIXER:** keep `sass/_toc-rail.scss` (`.toc-rail` `position:sticky`, `.post-layout`
  `grid-template-columns`, `.is-active` accent highlight, `display:none` default + a
  `@media (min-width: …)` desktop gate) + `@import "toc-rail"`; keep the `data-toc-rail` /
  `data-toc-link` / `page.toc` markup + the `toc-rail.js` include in `page.html`; keep
  `IntersectionObserver` in `toc-rail.js`. Smooth scroll on click is CSS-native
  (`html { scroll-behavior: smooth; scroll-padding-top }`, `_reset.scss`) — do not add a
  scroll handler. Heading IDs come from Zola (stable slugs) → `#{{ h.id }}` anchors.
- **Rules (permanent):** the rail is a **reader-facing TOC, not site navigation** — it uses
  `.toc-rail*` selectors (never `.side-nav`/`.nav-rail`), so it is sticky by design and is
  **not** subject to V21 (No Floating Nav). Never render the rail on mobile (keep the inline
  `.toc` there); never duplicate the inline TOC and the rail at the same width; tokens only
  (`var(--c-*)`), no hardcoded colors; the rail must no-op safely with few/no headings
  (template `toc_total >= 3` guard + JS early-returns).
- **Detector:** `scripts/qa_vaccines.py` → `check_toc_rail_vaccine` (code `TOC-RAIL`): FAIL if
  the partial is missing/unimported, lacks sticky/`.post-layout` grid/`.is-active`, if
  `page.html` lost `data-toc-rail`/`data-toc-link`/`page.toc`/`toc-rail.js`, or if
  `toc-rail.js` is gone / has no `IntersectionObserver`; WARN if the rail is not hidden by
  default or has no desktop `min-width` media (overflow risk).
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.TocRailVaccineTest -v`
- **Validation:** `python3 scripts/qa_vaccines.py` (TOC-RAIL PASS) · `qa_check.py` PASS ·
  `zola build` PASS · rail renders sticky on desktop ≥1300px with the active section
  highlighted on scroll, hidden (inline `.toc` only) on tablet/mobile.
#### V27 — GA stats module: build-time analytics, never fake numbers, pending when not configured

> Analytics/identity vaccine. After the seomoney.org domain move the footer GA module must
> read the NEW GA4 property only. GA data is generated at **CI build-time** (not Render env).
> If `GA_SERVICE_ACCOUNT_KEY` is missing or property access not granted, the UI shows a calm
> **pending** state — never fake/demo numbers. Match the signature → apply the FIXER;
> detector `check_ga_stats_vaccine` (code `V27`) guards it statically.

- **Symptom:** the footer GA stats module shows stale numbers from the OLD github.io property
  (e.g. top country `United States` / `desktop`), or shows nothing with no explanation, after
  the site moved to `seomoney.org`. Root cause: (a) `scripts/fetch_ga_stats.py` still fetching
  property `541698865`; (b) `config.toml` still on measurement `G-REFBXH86Z5`; (c)
  `data/ga-stats.json` cached with the old property leaking even after the code is fixed;
  (d) no health signal, so a disconnected GA looks identical to "zero traffic". A green
  `zola build` does NOT prove the GA module reads the right property.
- **Canonical identity (single source = `config.toml [extra]`):** property **`542421812`** ·
  measurement **`G-SMTFZVC0XN`** · site `seomoney.org`. Deep links `ga_dashboard_url` /
  `ga_fix_url` use the account-agnostic `#/p542421812/` form. **`config.toml` carries public
  identity only — NEVER the service-account key, NEVER a credential.**
- **Cache isolation (the key rule):** every GA data file is **stamped** with `property_id` +
  `measurement_id` + `site`. `templates/base.html` renders numbers ONLY when
  `ga_stats.property_id == config.extra.ga_property_id` AND `ga-health.json` status is `ok`;
  otherwise every KPI cell shows `—` and an inline warning banner + a link button to GA
  appears. A stale/foreign-property file can never leak old numbers.
- **GA Vacxin (hourly bot):** `scripts/ga_vacxin.py` + `.github/workflows/ga-vacxin.yml`
  (cron `30 * * * *`, offset from Fetch GA Stats at `:00`). Checks: GA API auth · property
  access (542421812 only) · recent data (7d) · site tag connectivity (live gtag for
  `G-SMTFZVC0XN`) · cache isolation. Writes a **public-safe** `data/ga-health.json`
  (+`static/data/ga-health.json` for `ga-health.js` live refresh). Crash-safe (never raises,
  exit 0; `--offline` skips network → status `pending`); NEVER writes a credential field.
  Status ∈ {ok, pending, disconnected, error}: `ok` → subtle healthy chip + last-checked time;
  otherwise → warning banner + fix link.
- **Build-time analytics rules (PERMANENT):**
  1. Analytics public UI on static site MUST read CI/build-time generated JSON (`data/ga-stats.json`,
     `data/ga-health.json`). NO Render env required for this module.
  2. If `GA_SERVICE_ACCOUNT_KEY` is missing or GA4 property Viewer permission is not granted,
     the UI MUST show a calm **pending** state — NEVER fake, hardcoded, or demo numbers.
  3. `GA_SERVICE_ACCOUNT_KEY` lives ONLY in **GitHub Actions Secrets**. NEVER commit it,
     NEVER put it in `config.toml`, NEVER require it on Render.
  4. `config.toml` may contain ONLY public identity: `ga_property_id`, `ga_measurement_id`,
     `ga_dashboard_url`, `ga_fix_url` — NO credentials.
  5. The GA fetch workflow (`ga-stats.yml`) MUST be fail-safe: if it errors → exit 0,
     write a `status: pending` health file, NEVER break the production build.
  6. Only report "live with real numbers" AFTER a successful `ga-stats.yml` run generates
     valid JSON stamped with `property_id: "542421812"` AND `ga-health.json` status is `ok`.
- **FIXER:** (1) `fetch_ga_stats.py` `PROPERTY_ID` default `542421812` + stamp identity in
  output. (2) `config.toml` `ga_measurement_id = "G-SMTFZVC0XN"`, `ga_property_id = "542421812"`,
  add `ga_dashboard_url` / `ga_fix_url`. (3) Reset `data/ga-stats.json` to the new property
  with null metrics (no old-property leak; **no fake/demo numbers**). (4) `base.html` gtag
  stays templated (`config.extra.ga_measurement_id`, never a hardcoded `G-\u2026`). (5) Remove
  `541698865` / `G-REFBXH86Z5` from all active GA config/code (only `ga_vacxin.py` +
  `qa_vaccines.py` may reference them — to DETECT them).
- **Operator action (external — Claude cannot do this):**
  - GitHub Actions Secret: `GA_SERVICE_ACCOUNT_KEY` (service account JSON key)
  - GA4 Property `542421812`: grant the service-account email **Viewer** role in GA console
  - Existing `WORKFLOW_BOT_PAT` pushes the refreshed data JSON
- **UI-healthy ≠ data/auth-healthy (BẮT BUỘC):** the GA card MUST distinguish *UI styled* from
  *data/auth healthy* — **never show the "Khoẻ mạnh" pulse when the GA data source is pending**
  (offline / no key / disconnected / error / no fresh `updated_at`). The template gates the pulse
  with `hidden` whenever `stats_ok` is false (`property_match AND ga_stats.updated_at AND
  health_status == "ok"`), so any healthy badge styling MUST honour `[hidden]`. A bare
  `.ga-stats__pulse { display: inline-flex }` (author CSS) overrides the UA `[hidden]{display:none}`
  → a **false healthy chip while GA is pending** (the 2026-06-21 regression). FIXER: add
  `&[hidden] { display: none; }` to `.ga-stats__pulse` (and `.ga-stats__health`) in
  `sass/_ga-stats.scss`. A green `zola build` does NOT prove the badge hides — only a render check
  or the detector catches it.
- **Detector (`scripts/qa_vaccines.py` → `check_ga_stats_vaccine`, code `V27`):** FAIL on
  wrong property/measurement in config, wrong `fetch_ga_stats.py` default, old id drift in
  active GA files, hardcoded gtag id, a credential/old-property leak in `ga-stats.json`
  / `ga-health.json`, **the pulse not gated by `hidden` in base.html, or `.ga-stats__pulse`
  missing its `&[hidden]` guard in `_ga-stats.scss`** (false-healthy badge). WARN if the hourly
  workflow, the inline banner, `ga-health.js`, the deep-link config, or the health schema is missing.
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.GaStatsVaccineTest -v` ·
  `python3 -m unittest scripts.test_ga_vacxin -v`.
- **Validation (2026-06-21):** `qa_vaccines.py` V27 PASS · `fetch_ga_stats.py` stamps
  property 542421812 · `ga_vacxin.py --offline` → status `pending`, config + cache checks
  PASS · `ga-stats.json` reset (null metrics, new property) · no old id in active files.

#### V28 — Conflict-safe vaccine registry merge: keep ALL main detectors/rules, append only the PR delta

> Process + tooling vaccine (not a workflow-run bug — it guards how the vaccine
> registry itself is merged). The vaccine library is now the repo's most-edited
> shared registry (CLAUDE.md §4 + `scripts/qa_vaccines.py` `DETECTORS[]` +
> `scripts/test_qa_vaccines.py` + generated `data/*.json`). Parallel PRs each append
> a new `#### V<N>` block + detector, so they collide on the SAME registry files —
> a blind `--ours`/`--theirs` silently **renumbers or deletes** a vaccine/detector
> that already landed on `main`. Match the signature → resolve **by intent**.

- **Symptom:** a PR that adds/edits a vaccine turns `mergeable_state: dirty` with
  conflicts clustered in `CLAUDE.md` (§4 vaccine blocks), `scripts/qa_vaccines.py`
  (the `DETECTORS[]` list + new detector fn), `scripts/test_qa_vaccines.py` (new test
  class), and generated `data/*.json` (e.g. `data/seo-qa-scores.json`,
  `data/vaccine-autofixer-report.json`). The real feature is fine; only the shared
  registry collides. A green `zola build` does NOT prove the merge kept every vaccine —
  a botched resolve can drop a detector or duplicate a `V<N>` number and still build.
- **Root cause:** the vaccine registry is **append-mostly shared infrastructure** (same
  class as V12 `base.html`/`_footer.scss`). QA-green on a branch never proves it is
  merge-safe against the current `main`. Picking one side blindly re-introduces a
  removed vaccine (`--ours`) or deletes a vaccine that already merged (`--theirs`);
  hand-merging stale `data/*.json` resurrects old timestamps/entries (V6/V18 family).
- **FIXER (by intent — never blind ours/theirs on registry files):**
  1. `git fetch origin main` → merge latest `main` into the branch.
  2. **Registry SOURCE (`CLAUDE.md`, `scripts/qa_vaccines.py`,
     `scripts/test_qa_vaccines.py`) → `manual`, keep BOTH sides:** append the PR's new
     `#### V<N>` block, new detector fn, `DETECTORS[]` entry and test class **on top of**
     every vaccine/detector already on `main`. Never drop a `#### V<N>` block, never
     unregister a detector, never renumber an existing vaccine.
  3. **New vaccine number = `next_free_vaccine_number()`** — never hardcode a taken
     number; if `main` advanced past your number while the PR waited, **renumber YOUR
     new block to the next free one** (never an existing one).
  4. **Generated `data/*.json` → take `main` then REGENERATE** (never hand-merge stale
     JSON): `git checkout --theirs data/<file>.json` then re-run the generator
     (`build_references.py`, `seo_qa_checker.py --all`, autofixer report, etc.).
  5. Gate locally: `python3 scripts/qa_vaccines.py` (V28 + VACCINE-REGISTRY PASS) →
     `python3 -m unittest scripts.test_qa_vaccines -v` → `python3 qa_check.py`. Confirm
     zero conflict markers left and `next_free_vaccine_number()` advanced by exactly the
     number of new vaccines.
- **Rules (permanent):** registry source is `manual` (append delta, preserve every main
  detector/rule); generated data JSON is `main`+regenerate; never renumber or delete an
  existing vaccine (only `[DEPRECATED — xem V<N>]`, per Vaccine Governance); each detector
  registered exactly once (guarded by `_assert_no_duplicate_registration` +
  `check_vaccine_registry_integrity`).
- **Detector:** `scripts/qa_vaccines.py` → `check_v28_vaccine_registry_merge` (code `V28`):
  live-imports `autofix_conflicts.classify()` and FAILs if a registry source file is not
  `manual` or a generated data JSON is not `main`, or if a conflict marker leaked into
  `CLAUDE.md` / `qa_vaccines.py` / `test_qa_vaccines.py` / `autofix_conflicts.py`; WARN if
  `autofix_conflicts.py` or the test layer is missing. Pairs with `VACCINE-REGISTRY`
  (duplicate-number / duplicate-detector guard).
- **Tests:** `python3 -m unittest scripts.test_qa_vaccines.VaccineRegistryMergeV28Test -v`

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
- **KHÔNG** force-push / push thẳng `main` — engine chỉ ghi branch `vaccine-hotfix/*`.
- **KHÔNG** xoá content/data người dùng — `content/**`, `private_content/**`,
  `*-series.json`, `categories.json` được bảo vệ (conflict giữ phía PR/content; data
  CI tự sinh mới lấy `main`).
- Conflict (vd manual-approval) **không** chặn việc *sửa* — chỉ giới hạn *merge* về đúng
  cổng đã gate. `vaccine-hotfix/` đã nằm trong `auto_eligible_branch_prefixes`
  (`data/auto-merge-policy.json`) → PR auto-merge qua **cùng** cổng `qa-check`, không phải bypass.

### Triggers (5)

`build_fail` · `deploy_fail` · `auto_merge_blocked` · `merge_conflict` ·
`required_checks_fail`. Workflow nhận qua `workflow_run` (QA Gatekeeper / deploy /
Auto-merge **completed=failure**) + `workflow_dispatch`.

### Behavior

1. Activate + **conflict-safe precheck** (`--precheck`).
2. Diagnose root cause — reuse `scripts/ai_diagnose.py` (heuristic miễn phí).
3. Create/update branch `vaccine-hotfix/<issue-id>` (issue-id bám branch lỗi → retry
   tăng cùng counter anti-loop; lỗi sẵn trên hotfix branch thì tái dùng, không lồng).
4. Fix **delta tối thiểu** — `merge_conflict` → `scripts/autofix_conflicts.py`; build
   breaker đã biết → SAFE fixer của `vaccine_autofixer.py` (V1 model id, internal-link
   `--fix`, references…). KHÔNG refactor lớn.
5. Re-run QA/build/test, **lặp tới khi xanh** (bounded `MAX_FIX_ATTEMPTS`; anti-loop
   `LOOP_THRESHOLD` → escalate, dừng).
6. Update PR; **auto-merge chỉ khi mọi required check xanh** (giao `try_auto_merge.py`).
7. Log → `data/vaccine-hotfix-report.json` ("Autofixer_report_by Vacxin") + `history[]`.

### Output (mỗi lần chạy)

PR link · Root cause · Files changed · Checks result (qa/build/tests) · Deploy status.

### Lệnh

```bash
python3 scripts/vaccine_hotfix.py --precheck                       # audit rule, không sửa
python3 scripts/vaccine_hotfix.py --trigger required_checks_fail --issue-id qa-123
python3 scripts/vaccine_hotfix.py --trigger merge_conflict --issue-id pr-87 --branch feature/x
python3 scripts/vaccine_hotfix.py --trigger build_fail --issue-id qa-9 --dry-run --no-build
python3 -m unittest scripts.test_vaccine_hotfix -v
```

### File map

| Thành phần | Path |
|------------|------|
| Engine | `scripts/vaccine_hotfix.py` |
| Tests | `scripts/test_vaccine_hotfix.py` |
| Workflow | `.github/workflows/vaccine-hotfix.yml` (`workflow_run` + dispatch; concurrency `vaccine-hotfix-<branch>`, KHÔNG dùng chung lock `auto-merge-main`/`production-deploy`) |
| Report | `data/vaccine-hotfix-report.json` ("Autofixer_report_by Vacxin") |
| Reuse | `ai_diagnose.py` (root cause) · `autofix_conflicts.py` (conflict) · `vaccine_autofixer.py` (safe fixers) · `try_auto_merge.py` (gated merge) |

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
- Responsive matrix: kiểm tra **360, 390, 768, 1024, desktop** trước merge.

### 6. Responsive UX Standards — Momo-inspired (18/06/2026)

> Chuẩn tái sử dụng học từ [momo.vn/blog](https://www.momo.vn/blog). Bổ sung §1–§5,
> KHÔNG thay thế. Áp dụng khi tối ưu feed/card/article mobile.

| ID | Pattern | Symptom nếu thiếu | Fix / Prevention |
|----|---------|-------------------|------------------|
| **R1** | **Surface card feed** | Card list ngang chật trên tablet; ảnh bé | ≤768px: stack 1 cột; ảnh top `aspect-ratio: 16/9–16/10`; body `padding: 1–1.25rem`; `border-radius: 14–18px` + shadow nhẹ. Ref: `_post.scss`, `_home-momo.scss`. |
| **R2** | **Readable prose scale** | Tường chữ / chữ quá nhỏ mobile | Body mobile `15–16px`, `line-height: 1.65–1.75`; H1 bài `1.35–1.75rem`; tablet 769–1024 có thể `1.02rem` body. Ref: `_reset.scss`, `_single.scss`. |
| **R3** | **Summary line-clamp** | Excerpt dài đẩy fold | Card summary `-webkit-line-clamp: 2` (mobile), `3` (desktop). Class đúng: `post-card__summary` (KHÔNG `__excerpt`). |
| **R4** | **Category nav scroll** | Menu kẹt / wrap xấu mobile | Navbar ≤720px: horizontal scroll tabs, `scroll-snap`, ẩn scrollbar; active = underline accent. Ref: `_navbar.scss`. |
| **R5** | **Pill category chip** | Tag category khó quét | Mobile: pill `border-radius: 999px`, nền `var(--c-accent-soft)`. Ref: `_home-momo.scss`. |
| **R6** | **Touch target scope** | Link trong đoạn văn bị padding → gãy dòng | `min-height: 44px` CHỈ chrome (nav, CTA, card image, pagination) — **KHÔNG** `a[href]` global. Prose links `padding: 0`. Ref: `_reset.scss`. |
| **R7** | **Safe horizontal inset** | Nội dung sát mép notch | `.container` dùng `max(12–16px, env(safe-area-inset-*))`. Không `overflow-x: hidden` trên `html`. |
| **R8** | **Scrollable embeds** | Code/table kéo ngang cả page | `pre`, `table` trong `.post-single__content`: `overflow-x: auto; -webkit-overflow-scrolling: touch` — scope mobile only. |

**Selector hygiene (R3):** trước khi thêm mobile override, grep class trong `templates/` — selector CSS phải khớp HTML thật.

## Design Language (Branding — BẮT BUỘC cho mọi UI mới)

> Ngôn ngữ thiết kế chuẩn của blog: **calm enterprise**, lấy cảm hứng từ *premium
> annual report*. Áp dụng khi tạo MỚI bất kỳ page, dashboard, tool, widget, report,
> article block. **Không clone pixel-by-pixel** UI tham chiếu — học design language rồi
> tái sử dụng. Mọi giá trị màu dùng **semantic token** `var(--c-*)` (xem
> `_themes.scss`/`_brand-vars.scss`) để tự đúng light/dark; mọi component mới = **scoped
> SCSS partial** (như `_post-nav.scss`, `_vaccine-autofixer.scss`).

### Design Style Anchor (hỏi TRƯỚC khi thiết kế)

Trước khi thiết kế bất kỳ page / dashboard / tool / widget / article layout / component, **căn theo anchor**:

> **Think Apple Annual Report × Bloomberg × Stripe Docs × Notion.**

**KHÔNG** theo: AdminLTE · Crypto Dashboard · Bootstrap Admin Template · Material Design overload ·
Gaming UI · Neon UI · thiết kế nặng glassmorphism.

**Cảm giác mong muốn:** như một *premium annual report* / ấn phẩm tài chính chất lượng cao / nền tảng
tri thức thanh lịch — calm, professional, dễ đọc, **information-dense nhưng không chật chội**.

**🔑 Design Consistency Rule (BẮT BUỘC):** mỗi khi sinh UI, hỏi:
*"Cái này có trông tự nhiên bên trong một Apple annual report, Bloomberg dashboard, Stripe Docs page,
hay Notion workspace không?"* — **Nếu KHÔNG → thiết kế lại.**

### Calm > flashy
Sang trọng hơn hiệu ứng. **Tránh:** shadow nặng, gradient mạnh, lạm dụng glassmorphism, màu neon,
animation thừa, hiệu ứng "đòi chú ý". **Ưu tiên:** whitespace · typography · hierarchy · màu dịu.

### Cards First (cards before tables)
**Card là primitive UI mặc định.** Trước khi nghĩ tới bảng/đống div, gói nội dung vào card. Tránh bảng to khi có thể.
- `border-radius`: **14–20px** (component nhỏ ~12–14px, panel lớn ~16–20px).
- Border mảnh (`1px solid var(--c-border)`), nền mềm (`var(--c-bg-surface)` / `var(--c-bg-soft)`), KHÔNG viền đậm.
- `padding`: **18–28px**. Đủ khoảng thở, tránh layout chật.

### Typography Hierarchy
- **Level 1 — section title:** lớn, đậm. **Level 2 — content title:** vừa. **Level 3 — secondary label:** nhỏ, màu nhạt (`var(--c-text-muted)`).
- **Số liệu quan trọng (KPI):** *lớn hơn + weight nặng hơn*. Nội dung chính phải nổi bật tự nhiên **mà không cần màu chói**.
- **Metadata** (ngày, nguồn, ghi chú): nhỏ + màu nhạt.

### White Space Is A Feature
Khoảng trắng là tính năng, không phải chỗ trống cần lấp. **Không nén thông tin.**
Khi phân vân → **thêm spacing, đừng thêm element.**

### Dashboard Style
Dashboard phải trông như **Bloomberg terminal × premium annual report**: calm · structured · informative · low-noise.
**Ưu tiên:** cards + sections + timelines + metrics + progress indicators. **Tránh:** bảng "developer-style" xấu
khắp nơi, hay "20 widget tranh nhau sự chú ý". (Khớp pattern Insights hiện có: `.vaccine-panel`, build/merge cards.)

### Article Style (magazine-style)
Bài viết gần với **Apple Newsroom / Financial Times / Stripe Docs / Notion** hơn là blog truyền thống — **không** tường chữ.
Cấu trúc: Hero → Content → Related articles → External references → Copyright/nguồn → Insights box → Series box →
Reading progress → soft cards. (Hạ tầng template đã lo phần lớn — xem rule TOC, References, Series, Related.)

### Color System
Dịu, chuyên nghiệp — **tránh màu bão hoà**, **tránh đen tuyền (`#000`)**, **tránh tương phản gắt**.
Palette ưu tiên: slate · blue-gray · light teal · muted purple · nền pale.

| Vai trò | Màu | Token gợi ý |
|---------|-----|-------------|
| Primary | slate blue | `--c-accent` (+ `--c-accent-soft`) |
| Secondary | teal | teal token (thêm mới nếu cần) |
| Highlight | amber | highlight/warning token |
| Success | green | success token |
| Warning | orange | warning token |
| Danger | red | danger token |
| Background | very light gray (KHÔNG `#000`/`#fff` tuyệt đối) | `--c-bg-page` / `--c-bg-surface` / `--c-bg-soft` |

> Token thật trong `_themes.scss`: `--c-bg-page` · `--c-bg-surface` · `--c-bg-soft` ·
> `--c-text-heading` · `--c-text-body` · `--c-text-muted` · `--c-accent` ·
> `--c-accent-hover` · `--c-accent-soft` · `--c-border` · `--c-border-strong`. Dùng đúng
> tên này (KHÔNG bịa token). Nguồn ưu tiên cao nhất: trang **`/branding-guideline/`**.

### Animation / Motion Philosophy
Animation hỗ trợ đọc, không cướp chú ý. **Duration 150–250ms**, transition tinh tế.
**Tránh** bounce, scale transform lớn, motion gây xao nhãng.

### Information Density
**Mật độ trung bình.** Chuẩn: *premium annual report · Bloomberg terminal × Apple*.
**KHÔNG:** crypto dashboard · gaming UI · Material Design overload.

### Component Library (reuse trước khi tạo mới)
Trang/feature mới ưu tiên tái dùng: **KPI card · timeline card · metric card · section card · expandable card ·
comparison card · progress card · insight card.** Trước khi phát minh component mới → tìm component sẵn có
(Insights, dashboards, `.vaccine-panel`, `.post-nav`…) và mở rộng nó.

### Supplemental Card Theme — Annual-report KPI cards (OPTIONAL, áp dụng CÓ CHỌN LỌC)

> Một **card skin / visual flavor** bổ sung (cảm hứng annual report: card pastel mềm, icon viền tròn,
> KPI số lớn). Đây **KHÔNG phải** hướng thiết kế mới hay redesign — chỉ là "một kiểu card nữa **trong
> cùng** design system". **Tuyệt đối không** redesign cả site theo screenshot này.

**Thứ tự ưu tiên (cao → thấp):** 1) Global Branding Guideline (`/branding-guideline/`) → 2) Existing Design
DNA (mục này) → 3) Existing component library → 4) **Card theme này (tuỳ chọn)**.

**Phạm vi áp dụng (chỉ những chỗ hợp):** KPI card · stats card · metric card · fact box · highlight box ·
comparison card · insights block · dashboard summary. Ví dụ: company profile, bài tài chính/ngành,
trang kiểu annual report, section thống kê. **KHÔNG** ép đổi: layout tổng thể · navigation · hệ typography ·
cấu trúc bài · color system · spacing rules · component hierarchy · design language hiện có.

**Chỉ mượn 4 thứ:**
1. **Soft background cards** — nền pastel rất nhạt: pale blue / pale teal / pale purple / light gray.
2. **Circular outline icons** — icon viền mảnh (thin outline) đặt trong vòng tròn, bên trái.
3. **Spacious KPI cards** — padding thoải mái; **số quan trọng lớn + đậm**, label trên nhỏ, đơn vị/hỗ trợ nhỏ.
4. **Calm annual-report feeling** — low visual noise, không hiệu ứng loè loẹt.

**KHÔNG copy:** thay toàn bộ card site-wide · đổi layout sẵn có · thêm nhiều màu · biến mọi trang thành
infographic doanh nghiệp · bỏ article style hiện tại · redesign trang đã theo branding guideline.

**🔑 Compatibility Rule:** trước khi dùng theme, hỏi *"Cái này có như một mở rộng TỰ NHIÊN của branding
guideline hiện tại không?"* — **CÓ →** áp dụng có chọn lọc; **KHÔNG →** giữ thiết kế hiện tại. Theme phải
**bổ trợ**, không cạnh tranh. *Preserve consistency above novelty.*

**Triển khai:** *guidelines first, components later* — **CHƯA** tạo component nào cho theme này.
Đây chỉ là **hướng thị giác tái sử dụng** để mượn SAU, khi có **trang thật** cần section KPI-heavy
(vd company profile, bài tài chính/ngành, trang annual-report). Khi đó mới dựng component (scoped SCSS +
shortcode, opt-in, additive), tái dùng component sẵn có trước khi tạo mới. **Evolution, not proliferation.**

## UI/UX Reference Rule (BẮT BUỘC — mọi lần làm/sửa UI/UX)

> Quy tắc vĩnh viễn. Áp dụng cho **MỌI** lần implement hoặc fix UI/UX (page, component,
> dashboard, widget, tool, modal, article block, dialog…). Bổ sung "Design Language" +
> "Design Style Anchor" + "Global UI/UX Design DNA" — KHÔNG thay thế.

**Rule:** When implementing or fixing UI/UX, Claude must **always reference** the existing
design system **before** writing any markup or CSS:

- **Branding guideline** → `/branding-guideline/` — source of truth (`--c-*` tokens, palette, spacing).
- **S-DNA** → `/tools/s-dna/` — Sembcorp design DNA (soft surfaces, whitespace, calm hierarchy).
- **B-DNA** → `/tools/b-dna/` — Brand design DNA (cards-first, kicker+title+purpose, tokens are truth, dialogs may float above content).
- **Font guideline** → `/font/` — typography (`$font-heading` / `$font-body`, hierarchy).

**Goal:** user-first usability, visual harmony, and consistency with the existing blog UI.

- **Never ship raw/default-looking UI** when the blog already has a polished design system —
  no default browser form controls/buttons, no unstyled panels, no misaligned inputs.
- Every new visual component = **scoped SCSS partial** using semantic `var(--c-*)` tokens
  (auto light/dark), imported in `site.scss`; **reuse** an existing component before inventing one.
- Respect the responsive scope rules (mobile ≤720px vs desktop — see "Quy tắc tối ưu hoá giao diện").
- **A green `zola build` does NOT prove the UI is styled** — always do a render/visual check
  (desktop + mobile) before calling a UI task done. BEM markup whose only CSS is a theme tint
  is **not** a finished component (see vaccine **V20 — Search UI**).
- Ask the Design Consistency question first: *"Does this look natural inside an Apple annual
  report × Bloomberg × Stripe Docs × Notion?"* — if **no → redesign** before shipping.

## Global UI/UX Design DNA

> Repo này theo một **calm enterprise design language** lấy cảm hứng từ *premium annual report*
> (Apple Annual Report × Bloomberg × Stripe Docs × Notion). Đây là **kiến thức thiết kế vĩnh viễn** —
> coi như **cộng dồn**, KHÔNG ghi đè; chỉ **mở rộng / tinh chỉnh** theo thời gian.

Core principles:

1. **Calm > flashy.**
2. **Cards before tables.**
3. **Whitespace is a feature.**
4. **Typography creates hierarchy.**
5. **Large numbers deserve emphasis.**
6. **Soft colors over saturated colors.**
7. **Premium annual report aesthetic.**
8. **Magazine-style articles.**
9. **Dashboard sections over giant tables.**
10. **Reuse components before creating new ones.**

Áp dụng cho: blog pages · dashboards · tools · widgets · reports · insights pages · category pages ·
series pages · mọi feature tương lai.

**Khi sinh UI bất kỳ, Claude PHẢI tham chiếu các nguyên tắc này TRƯỚC khi tự bịa layout** (đọc cả
"Design Language" + "Design Style Anchor" + "Quy tắc tối ưu hoá giao diện (CSS / Responsive)"). Token màu →
`var(--c-*)`; component mới → scoped SCSS partial; tuân thủ scope mobile/desktop (R1–R8). Tự hỏi Design
Consistency Rule trước khi commit UI mới.

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

### Mỗi thay đổi = 1 đơn vị ship riêng, tự lên `main` (2026-06-19 — user request)

> ⛔ **KHÔNG GỘP** nhiều thay đổi độc lập vào cùng 1 lần ship — mỗi thứ tự lên `main`
> độc lập, không bắt user chờ cả lô.

- Mỗi thay đổi logic riêng (1 bài viết · 1 fix workflow · 1 sửa CSS · 1 update rule)
  = **1 đơn vị ship riêng**, **tự lên `main` ngay khi QA xanh**.
  - ✅ Đúng: bài A và fix deploy lên `main` độc lập, auto-merge riêng.
  - ❌ Sai: gộp bài A + fix deploy + update rule vào 1 lần.
- Mỗi thay đổi **tự lên `main`** qua `auto-merge.yml` (QA xanh → squash). **KHÔNG cần
  agent mở/merge PR thủ công**; KHÔNG hỏi user.
- Session giới hạn 1 branch dev → làm xong 1 thay đổi: push (automation tự đưa lên
  `main`) → reset branch về `origin/main` → làm thay đổi kế tiếp. KHÔNG tích nhiều
  thay đổi không liên quan trên cùng branch.

### Quy tắc hoàn thành task (MANDATORY — 2026-06-20)

> **KHÔNG được dừng ở bước push branch.** Mỗi task hoàn chỉnh PHẢI đi qua đầy đủ
> vòng PR → CI → auto-merge. Branch mà không có PR là **loose finished work** — vi phạm.

**Checklist bắt buộc sau mỗi task:**

1. **PR tồn tại** — `mcp__github__list_pull_requests` kiểm tra branch. Chưa có → tạo PR
   với tiêu đề rõ ràng + body mô tả thay đổi + test plan. PR title cũ/tự động
   (vd "Claude/branch-name") → cập nhật bằng `mcp__github__update_pull_request`.
2. **Không có conflict markers** — `grep tìm conflict markers trong content/, templates/, scripts/`
   → không được có kết quả (ngoài example text trong comment). Nếu có → giải quyết
   semantically (V10/V12 CLAUDE.md) trước khi push.
3. **Rebase lên latest `main`** — nếu branch stale (V9/V10 vaccine), merge `origin/main`
   trước khi tạo PR; conflict ở data `*.json` → lấy `main` + regenerate (V10 FIXER).
4. **Kích hoạt auto-merge** — `mcp__github__enable_pr_auto_merge mergeMethod=SQUASH`.
   Nếu fail (CI in_progress) → ghi chú trạng thái; không retry loop.
5. **Report trạng thái** — dù merge thành công hay blocked, output bảng tóm tắt:

   ```
   Branch audit: <branch-name>
   PR: #<N> — <URL>
   Conflicts: ✅ none | ❌ <file>
   CI: ✅ green | 🟡 in_progress | ❌ <error>
   Auto-merge: ✅ enabled | ⏳ CI running | ❌ blocked (<reason>)
   ```

**Branch stale (content đã trên main):** kiểm tra với `git show origin/main:<file>`. Nếu
content đã merge → branch là redundant; đóng/xóa thay vì tạo PR thừa.

**KHÔNG áp dụng "KHÔNG canh PR" để bỏ qua bước tạo PR** — hai quy tắc khác nhau:
- Tạo PR + enable auto-merge = **bắt buộc khi hoàn thành task** (mục này).
- Theo dõi PR tới trạng thái cuối = **bắt buộc** (mục dưới — GHI ĐÈ luật "cấm babysit" cũ).

### Theo dõi PR tới trạng thái cuối (MANDATORY — 2026-06-20 — user request, GHI ĐÈ "HẾT NHIỆM VỤ — KHÔNG canh PR")

> **Sau khi mở PR, bot PHẢI theo dõi PR tới trạng thái cuối.** Push branch / mở PR **KHÔNG**
> còn là "hết nhiệm vụ". Quy tắc này **GHI ĐÈ** rule 2026-06-19 ("Đẩy thay đổi xong = HẾT
> NHIỆM VỤ — KHÔNG canh PR") cho mọi task. Nhiệm vụ chỉ **Done** khi PR đã **MERGED** hoặc
> bot báo lại **đúng blocker cụ thể** đang chặn.

Sau khi mở PR, bám theo CI/PR và xử lý theo trạng thái:

1. **CI đang chạy (`in_progress`/`pending`):** report **pending** — KHÔNG kết thúc với trạng
   thái "done". Chờ/poll tới khi CI đạt terminal rồi xử tiếp theo nhánh dưới.
2. **QA xanh (`success`):** xác nhận **auto-merge + deploy** đã/đang chạy; báo PR merged.
3. **QA đỏ (`failure`):** **chẩn đoán** (đối chiếu §4 Vaccine library) → tạo **fix delta
   tối thiểu** trên cùng branch → push → quay lại bước 1.
4. **Conflict / `dirty`:** chạy **vaccine/preflight conflict checker** (`scripts/autofix_conflicts.py`,
   `vaccine_hotfix.py --precheck`, V10/V12 FIXER) → resolve semantic → push → quay lại bước 1.

**Done = PR merged HOẶC báo lại đúng blocker** (CI error cụ thể, conflict file cụ thể, hoặc
việc cần user quyết). KHÔNG bao giờ kết thúc turn ở trạng thái "đã push, để pipeline tự lo"
khi PR chưa tới trạng thái cuối.

### Definition of Done — "branch pushed + PR opened + QA green + auto-merge attempted"

> **Done KHÔNG bao giờ chỉ là "đã push branch".** Push branch mà KHÔNG có PR =
> **incomplete work** — QA → auto-merge → deploy không thể tiếp tục. Bot tuyệt đối
> không được dừng ở "I pushed the branch" trừ khi bị chặn quyền (permissions).

**Done = đủ 4 điều kiện:**
1. **Branch pushed** — code đã lên feature branch (`claude/**`, `codex/**`,
   `vaccine-hotfix/**`, `fix/**`, `feature/**`, …).
2. **PR opened/updated** — branch có đúng **1** PR mở vào `main` (reuse nếu đã có,
   KHÔNG tạo trùng). Title rõ ràng kèm branch/task name; body gồm **summary ·
   changed files · QA/build status · rollback note**.
3. **QA green** — chỉ merge khi `qa-check` (QA Gatekeeper) **xanh**. QA đỏ → KHÔNG
   merge; để lại comment failed checks + next fix action. QA đang chạy → chờ.
4. **Auto-merge attempted** — đã delegate cho pipeline gated (`try_auto_merge.py` /
   `auto-merge.yml`), KHÔNG bypass QA.

**Tự động hoá (không cần agent thao tác tay):**

| Thành phần | Path | Vai trò |
|------------|------|---------|
| Engine | `scripts/ensure_pr_after_push.py` | Sau push → ensure PR (create/reuse) + body chuẩn + preflight conflict + delegate gated auto-merge |
| Workflow | `.github/workflows/ensure-pr-after-push.yml` | Trigger `push` tới `claude/**` · `codex/**` · `vaccine-hotfix/**` + `workflow_dispatch` |
| Tests | `scripts/test_ensure_pr_after_push.py` | Pure-helper tests (eligibility, title/body, summary) |
| Merge | `scripts/try_auto_merge.py` (reuse) | Gated squash-merge khi `qa-check` xanh — KHÔNG bypass |

- **Preflight conflict:** branch `mergeable_state=dirty` → comment cảnh báo (V10/V12 +
  `autofix_conflicts.py`/`ff9`), KHÔNG merge cho tới khi resolve.
- **Không tạo PR trùng:** đã có PR mở cho branch → reuse + cập nhật title/body.
- **Không force-push, không merge PR đỏ.** Nếu bị chặn quyền (`pull-requests:write`
  thiếu) → output đúng lý do + lệnh tay: `gh pr create --base main --head <branch>`.
- Chạy tay: `GITHUB_TOKEN=… GH_REPO=Banhang-Chogao/zola BRANCH=<branch>
  python3 scripts/ensure_pr_after_push.py --enable-auto-merge`.

### Quy tắc chung

- Làm xong BẤT KỲ việc gì → **push để automation tự đưa lên `main`** → prod. KHÔNG cần
  agent mở PR thủ công, KHÔNG hỏi user "có mở PR không". Không để thay đổi nằm im trên
  feature branch. (Branch protection chặn push thẳng `main` — xem §5/§5a/§5b — nên bước
  đưa lên main do **máy tự làm** qua PR + `auto-merge.yml`, không phải việc agent ngồi canh.)
- Commit phải có tiêu đề rõ ràng + tóm tắt thay đổi và cách verify (để Merge Report đọc được).
- Đang dở 1 thay đổi trên branch → push thêm commit vào cùng branch; KHÔNG nhét thay
  đổi MỚI không liên quan vào.
- **⚠️ SUPERSEDED (2026-06-19 "HẾT NHIỆM VỤ — KHÔNG canh PR") → xem "Theo dõi PR tới
  trạng thái cuối (MANDATORY — 2026-06-20)" bên trên.** Luật cũ coi push là kết thúc
  nhiệm vụ và cấm canh PR; user đã GHI ĐÈ: nay bot PHẢI theo dõi PR tới khi MERGED hoặc
  báo đúng blocker. Pipeline ZERO_BARRIER (`qa-check` → `auto-merge.yml` → `deploy.yml`)
  vẫn chạy như cơ chế nền, nhưng bot **không** dừng ở "đã push, để máy lo": có quyền/
  nghĩa vụ poll CI, fix QA đỏ (§4 Vaccine / `ff`), resolve conflict (vaccine/preflight)
  trên cùng branch tới trạng thái cuối.

### Báo cáo PR sau merge (BẮT BUỘC — 2026-06-19)

> Ghi đè format báo cáo cũ (markdown table đơn giản). 3 quy tắc BẮT BUỘC:
> 1. **Theo dõi PR tới trạng thái cuối** (MANDATORY 2026-06-20 — GHI ĐÈ luật "KHÔNG canh PR" cũ): poll CI tới terminal, xử QA đỏ/conflict trên cùng branch; Done = MERGED hoặc báo đúng blocker. Vẫn tránh poll-loop vô hạn lãng phí — ưu tiên cơ chế event/`auto-merge.yml`.
> 2. **Luôn output summary cuối sau merge** (khi gọi `merge`/`gg`/`prm` hoặc merge xong cùng turn) — một lần, rồi dừng.
> 3. **Status = fail/error → đọc §4 Vaccine library** trong `CLAUDE.md` → đề xuất đúng `Vaccine match` + `Suggested fix tool`.

**Mobile-safe MD output (BẮT BUỘC):** output shortcut đọc chủ yếu trên điện thoại → mọi
bảng do shortcut sinh ra phải mobile-safe: (1) **tối đa 3 cột/bảng** (field thừa → bullet
`• key: value` ngoài bảng, KHÔNG thêm cột 4); (2) **truncate branch/title dài ≤ 28 ký tự
+ `…`** (giữ phần đầu để nhận diện); (3) **notes/diễn giải dài ra ngoài bảng** (merged sha,
deploy, error, vaccine match, next action = bullet `•`); (4) **dùng markdown table gọn**
(`| … |`), KHÔNG vẽ box-drawing rộng cố định (`┌─┐`) — fixed-width tràn mép màn hình mobile.
Canonical: `shortcuts.md` §5.

**Thành công** — copy đúng khung (markdown table mobile-safe, GMT+7 `HH:mm dd/mm/yyyy`):

```text
Tổng kết 1 PR vừa merged

| PR   | Title (≤28, … nếu dài)     | Status |
|------|----------------------------|--------|
| #487 | feat(flight-db): time pic… | ✅     |

• Merged: <commit_sha> lúc <HH:mm dd/mm/yyyy> (GMT+7)
• Deploy: deploy.yml tự chạy trên main → production
• Track: https://github.com/Banhang-Chogao/zola/pulls
```

Nhiều PR merged cùng turn → thêm dòng trong bảng; header `Tổng kết N PR vừa merged`.

**Thất bại** (merge fail / CI error / PR không merge được) — đọc log ngắn, đối chiếu
§4 Vaccine library trong `CLAUDE.md`, output:

```text
Tổng kết PR lỗi

| PR   | Title (≤28, … nếu dài) | Status |
|------|------------------------|--------|
| #487 | <title cắt ≤28>…       | ❌     |

• Error: <short error>
• Vaccine match: <V1–V13 tên vaccine khớp dấu hiệu>
• Suggested fix tool: <ff | ff9 | vacxin11 | fix_site_prefix_links.py | …>
• Next action: <một dòng kế hoạch fix>
• Track: https://github.com/Banhang-Chogao/zola/pulls
```

Quy tắc vaccine mapping (không chẩn đoán lại từ đầu nếu đã khớp):
- Internal link thiếu `/zola/` → `fix_site_prefix_links.py` hoặc `check_internal_links.py --fix`
- `configure-pages` rate limit / deploy cancelled → V5 (đợi, không panic)
- `mergeable_state: dirty` / data `*.json` conflict → V10 + `ff9`
- Tera `replace(old=` → V8 · HF 401 → V1 · qa-failed unknown → V7

Canonical copy: `shortcuts.md` §5.

## Quy tắc SEO QA cho mỗi bài blog (BẮT BUỘC)

Áp dụng cho MỌI lần viết hoặc sửa bài viết trong `content/` (đuôi `.md`,
không tính trang `_index`).

### 1. Luôn tối ưu SEO khi viết bài

Mỗi bài mới PHẢI có đủ tín hiệu SEO on-page trong front matter + nội dung:

- `title` (20–65 ký tự, chứa từ khoá chính ở nửa đầu).
- `description` (50–160 ký tự) — KHÔNG để Zola tự cắt summary.
- `[extra] seo_keyword = "..."` — khai báo từ khoá chính để chấm điểm chính xác.
- `[extra] thumbnail` (og:image), slug chữ-thường-nối-gạch-ngang không dấu.
- Từ khoá chính xuất hiện ở: title, đoạn mở đầu (≤150 từ đầu), ít nhất 1 heading H2 **và** đoạn kết.
- ≥ 2 heading H2, ≥ 3 tag, **≥ 5 internal link** + ≥ 1 external link uy tín
  (xem chuẩn mới "SEO CONTENT SYSTEM RULE" bên dưới; tin ngắn được hạ xuống ≥ 3
  nhưng phải gồm link tới **hub chuyên mục** + bài cùng cluster).
- Độ dài: tin ngắn ≥ 800 từ · bài chuẩn ≥ 1500 từ · bài pillar 2500–5000 từ.
  Đoạn văn ngắn, không tường chữ (readability, mobile-first).
- Mỗi bài PHẢI có block FAQ (`[[extra.faq]]`, 3–8 câu) + CTA/next-step cuối bài,
  KHÔNG để trang cụt (dead-end).

### 2. Hệ thống tự chấm điểm + lưu DB

Mỗi lần viết/sửa bài, hệ thống TỰ chấm SEO qua `scripts/seo_qa_checker.py`
(thang 100 điểm bám tiêu chí on-page của Google) và lưu điểm + lịch sử vào
**DB `data/seo-qa-scores.json`**. Việc này chạy tự động qua PostToolUse hook
(`scripts/seo_qa_hook.py`, cấu hình ở `.claude/settings.json`).

- Chấm thủ công 1 bài: `python3 scripts/seo_qa_checker.py content/<đường-dẫn>.md`
- Chấm lại toàn bộ: `python3 scripts/seo_qa_checker.py --all`
- Bài < 70 điểm → script exit code 2 (CI có thể dùng để chặn).
- **Mỗi entry có field `published`** (`false` khi frontmatter `draft = true`).
  Trang SEO board (`/seo-bang-vang/`) dùng field này để hiển thị bài nháp dạng
  `(nháp)` KHÔNG link → tránh link tới trang Zola không build (draft) làm hỏng
  internal link (bị `qa-404-checker.py` gate bắt). Khi thêm consumer mới đọc DB:
  PHẢI skip entry `published == false`.

### 3. Trang Insights điểm SEO (về sau)

DB `data/seo-qa-scores.json` là nguồn dữ liệu để dựng trang Insights "điểm SEO
của blog" sau này. KHÔNG xoá file này; mỗi lần chấm chỉ append thêm mốc lịch sử
(`history`, giữ tối đa 20 mốc/bài).

## SEO CONTENT SYSTEM RULE (GLOBAL — BẮT BUỘC, có hiệu lực 18/06/2026)

> Áp dụng cho **MỌI** bài viết, trang chuyên mục (category), landing page và nội
> dung auto-generate. Mục tiêu: tối đa **organic search**, giảm **bounce rate**,
> tăng **engagement time**, internal linking chặt, Lighthouse SEO ~100.
> Đây là chuẩn nâng cấp của "Quy tắc SEO QA" ở trên — khi xung đột, **lấy mục này**.

### Trạng thái hạ tầng repo (đừng làm lại thủ công cái đã auto)

| Yêu cầu | Trạng thái Zola | Ghi chú |
|---------|-----------------|---------|
| TOC tự động | ✅ auto `page.html` (≥ 3 heading) | KHÔNG viết `## Mục lục` tay |
| Related Articles block | ✅ auto `page.html` (semantic `data/related.json` + fallback tag/category) | Hiện 3–5 bài; KHÔNG tự thêm "## Bài viết liên quan" tay |
| FAQPage schema | ✅ auto `base.html` từ `[[extra.faq]]` | Chỉ cần khai báo FAQ ở frontmatter |
| Article schema | ✅ auto `base.html` | — |
| BreadcrumbList schema | ✅ auto `base.html` (Trang chủ → Section → Bài) | — |
| References cuối bài | ✅ auto macro `references::section` | Chạy `build_references.py` trước build |
| Internal link validation | ✅ `check_internal_links.py` + `qa-404-checker.py` (gate cứng trong `qa.yml`) | Còn link nội bộ hỏng → exit 2 → CI đỏ → chặn auto-merge |
| **Prev/Next + "Đọc tiếp"** | ✅ auto `page.html` (`page.lower`/`page.higher`) | Block `.post-nav` cuối bài, chống orphan; KHÔNG để trang cụt |
| Taxonomy pagination | ✅ `taxonomy_single.html` + `paginate_by = 10` (categories/tags) | `section.html` cũng hỗ trợ `paginator` |

### 15 rule nội dung BẮT BUỘC

1. **Search intent** — xác định trước khi viết: *Informational · Commercial ·
   Navigational · Transactional*. Nội dung phải **thoả intent trong 150 từ đầu**.
2. **Cấu trúc bài** theo thứ tự: H1 → Intro (50–150 từ) → TOC → các H2/H3 → FAQ →
   Related Articles → CTA. (TOC + Related auto ở template.)
3. **Internal linking** — **≥ 5 internal link/bài** (tin ngắn ≥ 3). Ưu tiên: cùng
   topic cluster · **trang hub chuyên mục** · tool liên quan · evergreen content.
4. **Related content** — block "Bài viết liên quan" hiện 3–8 bài (template lo). Bài
   viết tự link chéo thêm trong thân bài, không ỷ lại block auto.
5. **Content depth** — tin ≥ 800 từ · bài chuẩn ≥ 1500 từ · pillar 2500–5000 từ.
   **Cấm thin content.** (`bb`/`bb9` tối thiểu ~1000 từ vẫn áp dụng, ưu tiên 1500+.)
6. **SEO on-page** — title < 60 ký tự · meta description < 155 ký tự · slug ·
   `seo_keyword` (focus) · keyword variations. Đặt focus keyword ở: **title · đoạn
   đầu · 1 H2 · kết bài**.
7. **FAQ schema** — mọi bài có 3–8 FAQ + JSON-LD `FAQPage` (qua `[[extra.faq]]`).
   Tin ngắn/quan điểm thuần thì miễn (theo rule `bb`).
8. **E-E-A-T** — nguồn dẫn thật, ví dụ thực tế, hướng dẫn từng bước, ngữ cảnh đời
   thực. **Cấm AI fluff** chung chung.
9. **Engagement** — dùng bullet list · bảng khi hữu ích · mục so sánh · checklist
   hành động. Tránh tường chữ lớn.
10. **Giảm bounce** — mỗi bài có TOC + Related + internal link + **next-step gợi ý**.
    **KHÔNG bao giờ để trang cụt.**
11. **Category hub** — mọi bài PHẢI link về trang chuyên mục cha (vd `/categories/ngan-hang/`,
    `/categories/du-lich/`…). Map theo `categories.json`.
12. **Mobile-first** — đoạn ngắn, section nhỏ, dễ scan.
13. **Featured snippet** — trả lời câu hỏi chính ngay lập tức, định nghĩa súc tích,
    dùng bước đánh số khi hợp.
14. **Content clustering** — liên kết Article ↔ Hub ↔ supporting articles (hub-spoke,
    cross-link 2 chiều). Khớp pattern series `data/*-series.json` đã có.
15. **Quality gate trước khi lưu** — REJECT nếu: < 5 internal link (tin < 3) · thiếu
    TOC · thiếu FAQ (bài cần) · thiếu CTA/next-step · thiếu Related · thiếu focus
    keyword · thin content. **AUTO-FIX**: thiếu gì thì sinh + chèn trước khi build.

### Checklist nhanh khi viết bài mới (dán vào đầu việc)

- [ ] Xác định search intent → thoả trong 150 từ đầu
- [ ] `title` < 60 ký tự chứa focus keyword (nửa đầu)
- [ ] `description` < 155 ký tự chứa keyword
- [ ] `seo_keyword` + keyword ở title/đoạn đầu/1 H2/kết bài
- [ ] ≥ 1500 từ (bài chuẩn) / ≥ 800 (tin) — không thin
- [ ] ≥ 5 internal link gồm **1 link hub chuyên mục** + bài cùng cluster
- [ ] ≥ 1 external link uy tín, có thật
- [ ] 3–8 FAQ (`[[extra.faq]]`) cho bài cần snippet
- [ ] CTA / next-step cuối bài (không dead-end)
- [ ] `categories` đúng rule ("Tất cả" đầu mảng) → hub tồn tại
- [ ] Chạy `build_references.py` → `seo_qa_checker.py` ≥ 90 (A) → `check_internal_links.py` PASS

### Hạ tầng crawl-depth / SEO (✅ đã làm — giữ nguyên, đừng làm lại)

- **Prev/Next + "Đọc tiếp"** — ✅ block `.post-nav` cuối `page.html` (trước footer tags),
  dùng `page.lower` (bài cũ hơn → "← Bài trước") / `page.higher` (bài mới hơn →
  "Bài kế tiếp →"). **Lưu ý Zola 0.22:** dùng `page.lower`/`page.higher` (KHÔNG phải
  `page.earlier`/`page.later` — bị `None` khi section có `paginate_by`). Guard
  `{% if page.lower or page.higher %}` → bài lẻ/section không date-sort render rỗng.
  Style scoped: `sass/_post-nav.scss` (import sau `donate-card` trong `site.scss`),
  có block mobile `@media (max-width: 720px)`. **KHÔNG đụng content** khi sửa.
- **Taxonomy pagination** — ✅ `paginate_by = 10` (categories + tags trong `config.toml`)
  + `taxonomy_single.html` dùng `paginator`; `section.html` cũng hỗ trợ `paginator`.
  Đừng thêm `paginate_by` cho section `posting` (đổi route/SEO không cần thiết).
- **Fail build khi internal link hỏng** — ✅ `qa.yml` chạy `qa-404-checker.py` ở step
  cuối (sau `zola build`). Script exit 2 khi có link **nội bộ** hỏng → step đỏ →
  job đỏ → **chặn auto-merge**. External link KHÔNG gate (offline-safe, không treo CI).

## GLOBAL WRITING RULES (Áp dụng cho MỌI bài viết — BẮT BUỘC)

> Chuẩn văn phong cho mọi nội dung viết/sửa trong `content/`. Mục tiêu: bài đọc
> như **blogger thật** viết, KHÔNG giống AI-generated. Khi xung đột về giọng văn,
> lấy mục này. (Bổ sung cho "SEO CONTENT SYSTEM RULE" — SEO lo cấu trúc, mục này lo giọng.)

### 1. Human-first
- Viết như chính chủ blog là người trải nghiệm / nghiên cứu / tổng hợp rồi chia sẻ lại.
- Giọng tự nhiên, có cảm xúc, có góc nhìn cá nhân. Tránh văn phong AI, sáo rỗng, máy móc, lặp cấu trúc.
- KHÔNG mở đầu kiểu "Trong thời đại số hiện nay…", "Ngày nay…", "Trong bối cảnh…" nếu không thực sự cần.

### 2. Vietnamese Grammar
- Chính tả tiếng Việt chuẩn. KHÔNG viết hoa tùy tiện.
- Chỉ viết hoa: tên riêng · tên thương hiệu · đầu câu · thuật ngữ bắt buộc theo quy chuẩn.
- KHÔNG viết hoa toàn bộ tiêu đề phụ. Hạn chế lạm dụng dấu chấm than.

### 3. Authentic Blogger Voice
- Dùng ngôi "mình" / "tôi" / góc nhìn chủ blog khi phù hợp.
- Được thêm: nhận xét cá nhân, kinh nghiệm thực tế, lưu ý, mẹo dùng, quan điểm riêng.
- KHÔNG tự nhận đã trải nghiệm điều chưa có bằng chứng. Khi chưa trải nghiệm thật → diễn đạt
  "theo tìm hiểu của mình", "theo tài liệu công bố", "qua quá trình nghiên cứu".

### 4. E-E-A-T Friendly
- Ưu tiên trải nghiệm thật, dữ liệu, nguồn chính thức. KHÔNG bịa số liệu/khuyến mãi/chính sách/nhận định.
- Có nguồn chính thức → dẫn nguồn.

### 5. Readability
- Câu ngắn, dễ đọc. Đoạn 2–4 câu. Dùng bullet list khi cần.
- Ưu tiên ngôn ngữ đời thường thay vì học thuật.

### 6. SEO
- Chèn từ khóa tự nhiên, KHÔNG nhồi nhét. Nội dung phải đọc như người thật viết.
- Ưu tiên trải nghiệm người đọc hơn tối ưu máy tìm kiếm.

### 7. Anti-AI Pattern — tránh các cụm AI hay dùng (chỉ dùng khi thực sự cần)
- "không chỉ… mà còn…" · "đóng vai trò quan trọng" · "trong bối cảnh hiện nay"
- "có thể nói rằng" · "một trong những" · "ngày càng trở nên phổ biến"

### 8. Final Check Before Publish
Trước khi xuất bản: kiểm tra chính tả tiếng Việt · loại câu mang dấu hiệu AI · loại viết hoa sai
quy tắc · đảm bảo bài đọc giống blogger thật viết. **Nếu vẫn giống AI-generated → tiếp tục rewrite
cho tới khi đạt.**

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

### Nguồn ảnh & Alt text (BẮT BUỘC — mọi bài/ảnh)

> Quy tắc nguồn ảnh thống nhất cho MỌI nơi chèn ảnh (bài viết, thumbnail, ảnh thân
> bài, OG). Mục tiêu: ảnh luôn liên quan nội dung + accessible + SEO.

- **CHỈ dùng ảnh do user cung cấp** — file đính kèm (attachment) hoặc URL user
  đưa trực tiếp. **KHÔNG tự fetch/tải ảnh ngoài** (picsum, Unsplash, CDN bên thứ
  ba, kết quả search ảnh…) để chèn vào bài. Ảnh ngoài = không kiểm soát nội dung +
  bản quyền + có thể chết link.
- **Không có ảnh user → dùng placeholder hệ thống** (`img/placeholder/*.svg` — xem
  mục dưới). KHÔNG bịa ảnh, KHÔNG random ảnh ngoài thay thế.
- **Alt text bắt buộc cho MỌI ảnh**, sinh theo NGỮ CẢNH, thân thiện SEO: mô tả
  đúng nội dung ảnh + chứa từ khoá bài khi tự nhiên (KHÔNG nhồi keyword). Thumbnail
  mặc định lấy alt từ tiêu đề bài; ảnh thân bài tự viết alt mô tả riêng. Tránh alt
  rỗng / chung chung ("image", "ảnh").

### Ảnh Placeholder mặc định (bài KHÔNG có ảnh)

- KHÔNG dùng ảnh random ngoài (vd `picsum.photos`) làm thumbnail — nội dung
  không liên quan bài viết. KHÔNG nhúng chữ baked cứng lên ảnh minh hoạ.
- Bài/section nào thiếu `[extra] thumbnail` → template TỰ chèn placeholder
  thương hiệu (gradient xanh `#38bdf8 → #1d4ed8`, KHÔNG chữ) qua macro
  `img::thumb_src` (`templates/macros/img.html`). Alt text lấy từ tiêu đề bài.
- Bộ placeholder cố định ở `static/img/placeholder/` (sinh bằng
  `python3 scripts/make_placeholder.py`): `placeholder.svg` (3:2, thumbnail),
  `placeholder-wide.svg` (16:9, ảnh trong bài), `placeholder-square.svg` (1:1).
- SVG là vector → ảnh dùng `object-fit: cover` tự crop mọi kích thước.
- **OG/social cho cover SVG (twin `.og.webp`):** mạng xã hội (FB/Threads/X/Zalo)
  KHÔNG render SVG. `scripts/build_og_images.py` rasterize mỗi `static/img/**/*.svg`
  → twin `*.og.webp` (1200×630, cairosvg+Pillow). `base.html` khi `thumbnail` là
  `.svg` thì og:image dùng twin (`.svg` → `.og.webp`) → social hiện đúng ảnh COVER
  của bài thay vì banner chung. `img/og-default.webp` giờ CHỈ là fallback cho bài
  **không khai báo thumbnail**. Script idempotent, không vỡ build khi thiếu dep
  (dùng `.og.webp` đã commit); chạy trong `deploy.yml` trước `zola build`; thêm cover
  SVG mới → chạy `python3 scripts/build_og_images.py` (hoặc CI tự sinh) + commit twin.
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

### 💉 VACCINE — Conflict ở DATA FILE CI/HOOK TỰ SINH (PR #428, 2026-06-18)

> **Đây là loại conflict PHỔ BIẾN NHẤT. Khớp dấu hiệu → resolve NGAY theo FIXER, không chẩn lại.**

| Field | Detail |
|-------|--------|
| **Dấu hiệu** | PR conflict CHỈ ở file `data/*.json` do script/hook/cron sinh — điển hình `data/seo-qa-scores.json` (PostToolUse hook chấm SEO), `data/references.json`, `data/related.json`, `data/compliance-score.json`, dashboards, `*-report.json`, `*-state.json`, `*-scores.json`, `*-dashboard.json`. Diff chỉ đổi `updated_at`/`scored_at`/timestamp + vài entry. Thay đổi NỘI DUNG thật của PR (`.md`) KHÔNG conflict. |
| **Nguyên nhân** | Base PR cũ → `main` đã chạy lại hook/cron sinh data mới (timestamp khác) → cùng dòng đầu file đụng nhau. KHÔNG phải xung đột logic. |
| **FIXER** | **Lấy bản `main`** cho mọi data CI tự sinh (KHÔNG giữ data stale của PR): merge `origin/main` vào branch → `git checkout --theirs data/<file>.json` → `git add`. Giữ nguyên thay đổi `.md` của PR. Sau đó (tùy chọn) chạy lại script sinh data để khớp state mới (vd `build_references.py`). Commit merge → push → CI auto-merge. **TỰ ĐỘNG:** `python3 scripts/autofix_conflicts.py --branch <branch>` làm đúng việc này (classify `data/*.json` regen → strategy `main`). |
| **KHÔNG áp dụng cho** | `data/*-series.json` (curate tay), `data/categories.json`, `data/auto-merge-policy.json` → strategy `manual`. Template/SCSS/code/`CLAUDE.md` → `manual` (append cả hai bên, đừng đoán). |
| **Tool** | `scripts/autofix_conflicts.py` (resolver + bảng classify), `scripts/test_autofix_conflicts.py` (26 case), workflow `.github/workflows/autofix-conflicts.yml` (cron 30' + dispatch). |
| **Verify (#428)** | Conflict chỉ ở `data/seo-qa-scores.json`; lấy main → `zola build` PASS, bài premium `draft=true` ẩn đúng, PR `unstable`→mergeable. |

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
| `cms_auth_url` | `config.toml` → **`[extra]`** (không nest trong `[extra.giscus]`) | Render meta `vipzone-auth-api` |
| Backend | `services/visitor-counter` (`blog-vipzone-api.onrender.com`) | `/auth/login`, `/auth/callback`, `/auth/me` |
| Session key | `sessionStorage` → `zola-cms-session-id` | Chung CMS + F-Dashboard |
| `return_to` | Client gửi `location.pathname` (vd `/zola/tools/f-dashboard/`) | Backend strip `/zola` prefix → redirect `#sid=...` |
| Whitelist | `ADMIN_EMAILS` + `ADMIN_USERNAMES` (Render env) | Email verified **hoặc** GitHub login `banhang-chogao` |
| OAuth callback | GitHub App → `{BACKEND_URL}/auth/callback` | **Không** cần thêm callback riêng cho F-Dashboard (cùng app CMS) |
| Lỗi auth | `?auth_error=...` trên **đúng** `return_to` | Không ép về `/editor/` |

**F-Dashboard flow:** `auth-gate.js` → `GET {cms_auth_url}/auth/login?return_to=/tools/f-dashboard/` → GitHub → callback → redirect `https://seomoney.org/tools/f-dashboard/#sid=...` → `fetchMe()` → hiện dashboard.
- **Ephemeral:** `exportAndWipe()` — download → `clearAll()` ngay; no persistent online storage.
- **PDF watermark (trace):** `SHA256-style 16 hex lowercase` + `_` + `seomoney.org` (no `https://`).

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
python3 qa_check.py                      # QA cũ + Vaccine Gate (in summary cuối) — gate chính
python3 scripts/qa_vaccines.py           # chỉ Vaccine Gate (report + summary), exit 1 nếu FAIL
python3 scripts/qa_vaccines.py --json     # JSON cho dashboard/automation
python3 scripts/qa_vaccines.py --strict-warn   # coi WARN như FAIL
python3 qa_check.py --no-vaccines         # tắt gate (debug); --strict-vaccines = chặn cả WARN
python3 -m unittest scripts.test_qa_vaccines -v
```

### File map

| Thành phần | Path |
|------------|------|
| Engine + detectors | `scripts/qa_vaccines.py` |
| Tích hợp gate | `qa_check.py` (`run_vaccine_gate()` → in summary cuối, fold vào exit code) |
| Tests | `scripts/test_qa_vaccines.py` (negative: bắt bug synthetic; calibration: `main` = 0 FAIL) |
| CI | `.github/workflows/qa.yml` (step "Run QA Gatekeeper + Vaccine Gate" + unittest) |

> **Thêm vaccine mới có thể auto-check:** thêm block `#### V<N> — …` vào §4 (engine tự đếm),
> rồi viết 1 detector trong `DETECTORS[]` (FAIL nếu vỡ build/prod, WARN nếu chỉ consistency) +
> 1 negative test. Giữ nguyên tắc: detector lỗi nội bộ KHÔNG bao giờ crash gate (bọc try/except).

## V10 — Shared Link-Utils + Test Layer (link-safety; NOT a §4 vaccine number)

> ⚠️ **Đây KHÔNG phải vaccine số trong §4.** "V10" ở đây là nhãn cho **lớp hạ tầng
> link-safety dùng chung** (shared link-utils + test + detector), **không** đụng/đổi
> tên `#### V9` (Docs-only stale base) hay các `#### V10` đã có trong §4. Header dùng
> `##`/`###` (không phải `#### V<N> —`) nên `load_vaccines()` KHÔNG đếm nó là vaccine.

**Bug nó chặn (migration + regex 404):** code xử lý link tái phát 2 lỗi —
(1) **HOST guard** (`if HOST not in url` / `SITE_HOST in url`) để phân loại internal
vs external → **drop link `/zola/*`** (không mang host) → 404 sau migration;
(2) chạy regex link trên **raw markdown** → parse/rewrite link nằm **trong code span**
(```` ``` ```` block + inline `` `code` ``).

### Invariant (BẮT BUỘC — giữ vĩnh viễn)

- **`/zola/*` (và mọi `/…`, `@/…`, `./…`) LUÔN là internal — KHÔNG bao giờ cần host.**
  External chỉ là `http(s)://` / `//`. `#`, `mailto:`, `tel:`, `javascript:`, `data:` → skip.
- **KHÔNG parse/rewrite link trong code span.** Mask code span (fenced + inline) TRƯỚC
  khi extract/replace. Migration tool (`fix_site_prefix_links.py`) phải dùng
  `code_span_ranges()` để chừa code.
- Regex chịu được markdown wrapper (`<url>`, `"title"`) + trailing punctuation (`clean_url`).

### Reuse (đừng tự viết lại regex link)

Mọi script cần phân loại/đếm/extract link PHẢI dùng `scripts/link_utils.py` thay vì tự
viết regex riêng: `classify`/`is_internal`/`is_external`/`validate`/`clean_url`/
`code_span_ranges`/`mask_code_spans`/`extract_urls`/`extract_link_pairs`/`extract_bare_urls`/
`process`. Stdlib-only, crash-safe (input lỗi → trả rỗng, không raise).

### File map

| Thành phần | Path |
|------------|------|
| Lib dùng chung | `scripts/link_utils.py` |
| Test lib | `scripts/test_link_utils.py` (`python3 -m unittest scripts.test_link_utils -v`) |
| Consumer (migration) | `scripts/fix_site_prefix_links.py` (code-span-safe `/zola/` prefixer) |
| Consumer (báo cáo) | `scripts/content_direction.py` (`count_links` dùng pipeline an toàn) |
| Detector gate | `scripts/qa_vaccines.py` → `check_v10_link_utils_layer` (code `V10-LINKS`) |
| Test detector | `scripts/test_qa_vaccines.py` → `LinkUtilsLayerTest` |

Detector `V10-LINKS` **FAIL** nếu `link_utils.py` vắng hoặc bất biến bị phá (live-check:
`classify("/zola/x")=="internal"`, code-span không leak); **WARN** nếu thiếu test file /
migration tool không dùng `code_span_ranges`. Calibrate: `main` hiện tại = PASS (0 FAIL).

## QA Auto Rule Checker

Bot phát hiện rule/policy/workflow/automation xung đột — schedule mỗi **48 giờ** (`qa-rule-checker.yml`, cron `0 3 */2 * *` UTC).

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

**Prevention:** Chạy `qa-auto-rule-checker.py` mỗi 48h (schedule); đồng bộ CLAUDE.md khi đổi policy.

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

- Payment link mặc định (premium paywall **và** donate): `https://me.momo.vn/G5T1CDFRuJFWfBCDiK/y5eVvzz2nlXXeEP`
  - Cấu hình: `config.toml` → `momo_payment_link` (paywall) + `donate_momo_link` (donate, key riêng để đổi độc lập). Hiện cùng tài khoản nhận tiền.
  - Đồng bộ ở: `config.toml`, `templates/macros/paywall.html` (fallback), `backend/paywall_app.py` (`MOMO_LINK` default), `render.yaml` (`MOMO_PAYMENT_LINK`), `docs/paywall.md`. Khi đổi link → cập nhật TẤT CẢ chỗ này.
- Override qua env `MOMO_PAYMENT_LINK` trên backend.
- Flow: đọc teaser → thanh toán Momo → gửi yêu cầu (email) → admin xác nhận → generate approve code → gửi email.
- Không có webhook Momo — xác nhận thanh toán thủ công qua admin panel.

## Watermark Rules

- Dynamic watermark overlay khi đọc online: `blogName • emailHash • postId • traceCode`.
- Print/PDF: `@media print` chèn watermark `{traceCode16}_{blogDomain}` + bản quyền.
- Ví dụ in: `A9F328BC71D06E2A_seomoney.org` + «Bản quyền thuộc blog. Không được sao chép hoặc phân phối lại.»
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

## H-Dashboard (Hóa đơn mua hàng — invoice PDF + OCR)

Trang `/tools/h-dashboard/` — thống kê chi tiêu từ **hóa đơn mua hàng / biên lai** (vd Highlands Coffee, siêu thị) dạng **PDF**. Clone kiến trúc **O/L-Dashboard**, chỉ khác **source dữ liệu (invoice, không phải sao kê) + parser + OCR**. UI/UX, charts, health, export PDF/CSV/JSON, OAuth gate **y chang** L/O-Dashboard.

- **Đọc PDF (2 tầng):** `static/js/h-dashboard/invoice-parser.js` thử pdf.js text layer trước (hóa đơn điện tử có text); nếu text quá ít → **OCR fallback** `ocr-loader.js` (Tesseract.js `vie+eng`, render page→canvas, 100% client-side). Hàm `looksLikeText()` quyết định có cần OCR.
- **Parser invoice:** mỗi **mặt hàng = 1 transaction expense**. Số tiền VN (`15.000`=15000), loại token leading-zero (id hóa đơn `0099`). Bắt metadata: merchant (dòng đầu), `Check#`/`Số HĐ`, ShopID, POS, Pager, Thu ngân, ngày `DD-MM-YYYY HH:MM` / `DD/MM/YYYY`, hình thức TT. Items nằm giữa header và dòng tổng (`Tổng tiền`/`Tổng cộng`/`Thành tiền`/`Total`); **"thanh toan" KHÔNG là total marker** (trùng tiêu đề "Hóa Đơn Thanh Toán"). Dòng nối tiếp (vd `510ml`) gộp vào tên mặt hàng.
- **Schema giao dịch** (khớp L/O): `{transaction_id, date, value_date, merchant, description, txn_no, qty, unit_price, debit, credit:0, fee:0, balance, amount:-debit, type:"expense"}`. `balance` = lũy kế chi trong hóa đơn. `transaction_id = SHA256(merchant|date|invoice_no|idx|name|amount)` → re-upload cùng hóa đơn dedupe.
- **Tách biệt F/L/O:** namespace `HDashboard*`, id `hd-`, IndexedDB riêng `h-dashboard-db`. Dữ liệu chỉ local (AES-GCM), không upload server.
- **CSP (base.html):** OCR cần `worker-src 'self' blob: https://cdn.jsdelivr.net` + `connect-src` thêm `https://cdn.jsdelivr.net https://tessdata.projectnaptha.com` (tesseract core/wasm + traineddata). Đây là thay đổi global tối thiểu, additive.
- **Bảng 7 cột:** STT · Ngày · Mặt hàng · SL · Đơn giá · Thành tiền · Lũy kế. Meta panel: Cửa hàng · Mã HĐ · Ngày xuất · Thu ngân · Tổng HĐ · Hình thức TT.

| Thành phần | Path |
|------------|------|
| Trang | `content/tools/h-dashboard.md`, `templates/h-dashboard.html` |
| Styles | `sass/_h-dashboard.scss` (import sau `o-dashboard` trong `site.scss`) |
| JS | `static/js/h-dashboard/*.js` (`invoice-parser.js`, `ocr-loader.js`, `app.js`, `export.js`…) |
| Menu | `config.toml` `[[extra.main_menu]]` sau O-Dashboard |
