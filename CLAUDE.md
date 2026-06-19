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

### 1. Không cần qua PR thủ công — code xong → tự lên `main` → prod

> **Cập nhật (2026-06-19 — user request):** Bỏ rào PR thủ công. Code xong là **tự động**
> lên `main` → deploy production. KHÔNG mở/duyệt/babysit PR bằng tay, KHÔNG hỏi user.

- Agent làm xong thay đổi → để automation đưa lên `main` → `deploy.yml` → prod. Không
  tự tay quản lý PR, không chờ human review.
- **Lỗi để máy bắt & sửa, không phải human gate:** `qa-check` (QA Gatekeeper) chặn build
  hỏng trước khi lên `main`; có lỗi thì **vaccine autofixer** (§4 V1–V12) + `ff`/`ff9` +
  autofix-conflicts tự chẩn & sửa. KHÔNG chờ người review.
- **Hạ tầng (agent không cần bận tâm):** bước "đưa lên `main`" do `auto-merge.yml` tự thực
  hiện (squash khi `qa-check` xanh) — GITHUB_TOKEN/branch protection KHÔNG cho push thẳng
  `main` (§5/§5a/§5b), nên auto-merge là **bước máy tự làm**, không phải rào thủ công.

### 2. Auto-merge khi CI xanh (máy tự làm hết)

1. Code xong → push lên branch (`feature/`, `fix/`, `chore/`, …)
2. **`auto-merge.yml`** tự đưa lên `main` khi **qa-check** pass (QA Gatekeeper — không PR Policy)
3. `deploy.yml` chạy sau merge → GitHub Pages → prod

**Không hỏi user** trước khi merge, **không** cần agent mở/duyệt PR thủ công, không dùng label chặn auto-merge.

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

### Quy tắc chung

- Làm xong BẤT KỲ việc gì → **push để automation tự đưa lên `main`** → prod. KHÔNG cần
  agent mở PR thủ công, KHÔNG hỏi user "có mở PR không". Không để thay đổi nằm im trên
  feature branch. (Branch protection chặn push thẳng `main` — xem §5/§5a/§5b — nên bước
  đưa lên main do **máy tự làm** qua PR + `auto-merge.yml`, không phải việc agent ngồi canh.)
- Commit phải có tiêu đề rõ ràng + tóm tắt thay đổi và cách verify (để Merge Report đọc được).
- Đang dở 1 thay đổi trên branch → push thêm commit vào cùng branch; KHÔNG nhét thay
  đổi MỚI không liên quan vào.
- **Đẩy thay đổi xong = HẾT NHIỆM VỤ — KHÔNG canh PR (2026-06-19 — user request, GHI ĐÈ
  luật cũ "Theo dõi tới khi xong (BẮT BUỘC)"):** push để kích hoạt pipeline auto-merge là
  **kết thúc nhiệm vụ**. Pipeline ZERO_BARRIER tự lo phần còn lại: `qa-check` xanh →
  `auto-merge.yml` (squash) → `deploy.yml` production. **Lỗi để máy lo:** `qa-check` đỏ →
  vaccine autofixer (§4) + `ff`/`ff9` tự chẩn & sửa, push lại cùng branch tới khi xanh.
  - **KHÔNG** `subscribe_pr_activity`, **KHÔNG** canh CI tới khi merge, **KHÔNG** hẹn
    `send_later` self check-in, **KHÔNG** babysit/poll PR. Push xong là kết thúc turn.
  - **Ngoại lệ — chỉ khi user CHỦ ĐỘNG yêu cầu** ("canh PR", "babysit", "autofix CI",
    "theo dõi tới khi merge"): lúc đó mới `subscribe_pr_activity`, fix CI đỏ trên cùng
    branch (Vaccine §4 / `ff`), và dừng (`unsubscribe_pr_activity`) khi user bảo dừng
    hoặc PR đã MERGED/CLOSED.
  - Nếu CI đỏ mà user KHÔNG yêu cầu canh: pipeline tự xử theo cấu hình repo; không tự
    spawn monitor/subscribe trừ khi được yêu cầu.

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
