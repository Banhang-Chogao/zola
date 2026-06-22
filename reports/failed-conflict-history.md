# Failed Checks, Conflicts & Hotfix History — Debugging Memory Map

> **Purpose:** A single, reusable map of recent CI failures, deploy failures, merge
> conflicts, hotfix events, and PR-hygiene issues — each mapped to a repo rule,
> CLAUDE.md doctrine, vaccine pattern, or hotfix decision. This is a **debugging
> memory map, not a blame log**: list the failure, point to the fix, make the next
> agent faster and safer.
>
> - **Generated:** 2026-06-22
> - **Scope:** Banhang-Chogao/zola — `main` + recent open/merged PRs, deploy runs
>   #933–#944, vaccine-hotfix history, autofix-conflicts state, QA/404 reports.
> - **Sources:** `data/deploy-monitor.json`, `data/vaccine-hotfix-report.json`,
>   `data/autofix-conflicts-report.json`, `data/merge-report.json`,
>   `data/qa-404-report.json`, `data/compliance-link-report.json`, git log,
>   GitHub PR/Actions API, `CLAUDE.md`, `docs/vaccine-archive.md`,
>   `docs/image-watermark.md`.
> - **Constraints honored:** no secrets/tokens/local paths, no CLAUDE.md vaccine
>   registry edits, no vaccine renumbering, no production-code changes, no `public/`
>   or volatile data committed.

---

## 0. Snapshot — current health

| Signal | Value | Source |
|--------|-------|--------|
| Last successful deploy | run **#943** (`01f9023`) — `feat(images): watermark rule (#699)` | `deploy-monitor.json` |
| Deploy in-flight at snapshot | run **#944** (`3097767`) — running, not failed | `deploy-monitor.json` |
| Recent deploy failures (rolling) | **19** failed / **2** cancelled — most **superseded** | `deploy-monitor.json` |
| Storm flag | `false` (no active rate-limit burst) | `deploy-monitor.json` |
| Internal broken links | **0** of 1084 checked (pass) | `qa-404-report.json` |
| Compliance links | **0** broken of 934 (pass) | `compliance-link-report.json` |
| QA Vaccine gate | PASS · 33 vaccines loaded · 0 fail | `vaccine-autofixer-report.json` |
| Open vaccine-hotfix PRs | #727, #721, #719, #718, #695, #686, #676, #672 | GitHub PRs |
| Open PRs total (sampled) | ~18 open, many `⏳ qa-check chưa chạy` (Checks 0) | GitHub PRs |

**Read:** Production is healthy on `main`. The noise is in the **PR layer** — stale
"Checks 0" states, an accumulation of unmerged vaccine-hotfix PRs, and superseded
(not real) deploy failures from the concurrency queue.

---

## 1. Incident Log

> Unverifiable fields are marked **`unknown`**. Nothing here asserts "production done"
> without deploy + smoke evidence.

### INC-01 — Superseded deploy "failures" (#934–#937)

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-21 (~21:0x UTC) |
| PR/branch/commit | runs #934–#937; titles incl. `vaccine-hotfix/claude-amazing-goldberg-9hwo4`, `SEO11`, `SEO+AdSense Strategy Hotfix` |
| Symptom | `deploy.yml` runs marked `failure`; `superseded: true` |
| Root cause | Production-deploy concurrency queue (`group: production-deploy, cancel-in-progress: false`) — newer commit pushed before older deploy finished; older runs reported failure/superseded, **not a real build break** |
| Impact | Dashboard noise (`failed_recent: 19`); no production regression — #943 succeeded after |
| Fix | None required — `last_success #943` confirms healthy. Do **not** re-run superseded jobs |
| Rule / vaccine | **V5** (configure-pages rate-limit), Deploy Queue Policy (FIFO, retry-not-restart), Failure Priority Policy (drop stale/report-only) |
| Prevention | Treat `superseded: true` as non-actionable; only diagnose the **latest HEAD** deploy run; never burst parallel deploys |

### INC-02 — Cancelled deploy #933

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-21 |
| Commit/title | `feat(shortcut): add dantri inspired blog writing s…` |
| Symptom | run `cancelled` |
| Root cause | Concurrency cancel of an in-queue run superseded by a newer push (expected with queued deploys) |
| Impact | None — cosmetic in feed |
| Fix | None — cancelled ≠ failed |
| Rule / vaccine | **V5**, Deploy Queue Policy |
| Prevention | Map `cancelled` → "superseded", exclude from failure triage |

### INC-03 — Vaccine-hotfix PR backlog (required_checks_fail)

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-20 → 2026-06-22 |
| PRs/branches | #727, #721, #719, #718, #695, #686, #676, #672 (`vaccine-hotfix/*`); history: `claude/friendly-dijkstra`, `claude/uptime-me`, `claude/deploy-monitor` |
| Symptom | Auto-opened hotfix PRs accumulate open; latest report `trigger: required_checks_fail`, `confidence 77`, `pattern_id JS_ERROR` |
| Root cause | `vaccine_hotfix.py` fires on a required-check failure, opens a minimal-delta branch; PRs stay open because `qa-check` hasn't run on head (Checks 0) or auto-merge gate not yet satisfied |
| Impact | PR-list bloat; risk of stale base → `dirty` later (V10) |
| Fix (suggested) | For each: confirm `qa-check` green on latest head → let `try_auto_merge.py` merge; if `Checks 0`, **rebase/refresh** to re-trigger CI; close duplicates that target the same issue |
| Rule / vaccine | Vaccine Hotfix doctrine, **V10** (dirty/merge-race), **V28** (conflict-safe registry merge) |
| Prevention | Hotfix engine should refresh/rebase before assuming deploy failure; periodically drain merged-eligible hotfix PRs FIFO |

### INC-04 — "Checks 0 / qa-check chưa chạy cho head sha"

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-22 |
| PRs | #727, #724, #683 (`⏳ chưa chạy`); #723/#722/#717/#716/#680 (`🟡 đang chạy`) |
| Symptom | PR shows no checks / qa-check not started for the head SHA |
| Root cause | GITHUB_TOKEN PR-trigger gate ("workflows awaiting approval") — CI runs via `push` + `workflow_dispatch` + `workflow_run`, so a freshly pushed head may have **zero checks** until relayed |
| Impact | Auto-merge cannot evaluate; PR looks "stuck" but is **not** a deploy failure |
| Fix | Refresh/rebase/clean-commit to re-emit a `push` event so `qa.yml` runs; verify via Actions, not the PR badge |
| Rule / vaccine | CLAUDE.md §"GITHUB_TOKEN PR gate", `.github/ACTIONS-PERMISSIONS.md`, `docs/ROOT-CAUSE-ACTION-REQUIRED.md` |
| Prevention | **Checks 0 ≠ deploy failed.** Always confirm head SHA has a run before declaring failure; `ensure_pr_after_push.py` / `push_via_pr.sh` re-arm CI |

### INC-05 — Merge conflict auto-resolved on `qa.yml`

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-21T10:45:50Z |
| File | `.github/workflows/qa.yml` |
| Symptom | Open PR conflicted with `main` |
| Root cause | Dirty / generated-data conflict; shared-infra file diverged |
| Impact | Blocked merge until resolved; QA re-run `pass` after autofix |
| Fix | `autofix_conflicts.py` auto-resolved → opened `autofix/conflict-pr-<N>` → QA pass |
| Rule / vaccine | Autofixer Conflict Resolver, **V12** (semantic conflict on shared infra), **V10** |
| Prevention | Never force-push others' branches; resolve via dedicated autofix PR; rebase stale bases early |

### INC-06 — Paywall/premium merge-conflict resolution (#683)

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-21 |
| PR/branch | #683 `claude/vibrant-hawking-dhzptd` |
| Symptom | Conflicts across `config.toml`, `paywall.html/js`, `base.html`, `premium.html` (14 files) |
| Root cause | Long-running branch diverged from `main` on shared paywall surface |
| Impact | Manual merge of `origin/main`; AdSense-safe wording had to be preserved |
| Fix | Resolved conflicts, preserved reader-supported wording; `⏳ qa-check chưa chạy` at snapshot |
| Rule / vaccine | Premium Paywall Rules, AdSense-safe doctrine, **V12** |
| Prevention | Rebase shared-surface branches frequently; keep paywall copy AdSense-safe on every resolution |

### INC-07 — PR #712 conflict-resolution merge

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-22 |
| Commit | `d843b2d Merge origin/main into PR #712 branch (resolve conflicts)` |
| Symptom | PR went `dirty` after base advanced |
| Root cause | Stale base / merge race after QA already passed |
| Impact | Required explicit merge-from-main + re-run |
| Fix | Merged `origin/main`, resolved, re-pushed |
| Rule / vaccine | **V10** (dirty PR / merge race) |
| Prevention | Merge promptly after green; for high-churn periods, rebase before final QA |

### INC-08 — Broken internal link blocking QA (#720)

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-22 |
| PR/commit | #720 / `032e984`, `c8c490a` `fix(links): bỏ placeholder ![alt](url)` |
| Symptom | Placeholder `![alt](url)` produced a broken internal link → 404 gate fail |
| Root cause | Markdown placeholder image syntax left in content |
| Impact | `qa-404-checker` hard gate blocks merge/deploy |
| Fix | Removed placeholder; current `qa-404-report` = 0 broken |
| Rule / vaccine | **V14** (fabricated cross-links), Failure Priority tier 5 (links) |
| Prevention | No `![alt](url)` placeholders; run `qa-404-checker.py` before push |

### INC-09 — Dead internal routes blocking the gate (#693 / #680)

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-21 → 2026-06-22 |
| PRs | #693 "remove dead internal links blocking the QA gate"; #680 "whitelist dynamic app routes + fix broken internal link" |
| Symptom | Static links to removed routes (F-dashboard/H-dashboard) 404; dynamic app routes (`/cms`,`/gsc`) false-flagged |
| Root cause | Section/route removal not reflected in content links; checker lacked dynamic-route whitelist |
| Impact | Unrelated PRs blocked by site-wide link failures |
| Fix | Minimal cleanup PR to `main` removing dead links; whitelist dynamic routes in `qa-404-checker.py` |
| Rule / vaccine | **V14**, **V25** (split-backend 404), **V30** (preserve public `/tools/*` routes) |
| Prevention | Site-wide broken links → fix via **minimal cleanup PR to main**, not inside the blocked feature PR |

### INC-10 — Empty/frontmatter-less Trello posts

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-22 |
| Commits | `c0fbb8c`/`7c4cde0` add missing frontmatter; `e87d152`/`8c4a669` remove empty Trello posts |
| Symptom | Content files without frontmatter / empty bodies risk `zola build` break + thin-content compliance fail |
| Root cause | Imported posts missing required frontmatter / body |
| Impact | Potential build break (tier 3) + compliance thin-body flag |
| Fix | Added frontmatter, then removed the empty stubs |
| Rule / vaccine | **V8** (build break), compliance article-depth vaccines (thin body) |
| Prevention | Validate frontmatter + non-empty body before commit; `zola build` locally |

### INC-11 — Volatile runtime artifacts in commits

| Field | Detail |
|-------|--------|
| Date/time | ongoing |
| Examples | `data/vaccine-hotfix-state.json`, `data/vaccine-hotfix.log`, `data/qa-rule-checker-state.json`, `reports/rule-conflict-report.json`, plus `data/qa-404-report.json`, `data/seo-qa-scores.json` churn (and a malformed `ata/qa-rule-checker-state.json` path in one report) |
| Symptom | State/log/report files appear in hotfix `files_changed`; high-churn JSON in PR diffs |
| Root cause | Generated/volatile artifacts committed alongside fixes |
| Impact | Conflict magnets (V6/V18), noisy diffs, merge races |
| Fix | Keep volatile state/logs out of feature/hotfix PRs; regenerate via workflow, not by hand |
| Rule / vaccine | **V18** (runtime artifact conflict), **V6** (regenerated data conflict) |
| Prevention | Do **not** commit `public/`, `*-state.json`, `*.log`, ad-hoc report JSON unless policy explicitly allows; let scheduled jobs regenerate `data/*.json` |

### INC-12 — Duplicate slug (QA rule checker)

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-21T14:12:50Z |
| Slug | `auto-fixer-github-actions-he-mien-dich-tu-chua-loi-blog` in both `content/baochi/` and `content/posting/` |
| Symptom | Duplicate slug flagged MEDIUM by `qa-auto-rule-checker.py` |
| Root cause | Same slug published in two sections |
| Impact | Slug-uniqueness violation; potential canonical/SEO ambiguity |
| Fix | Rename slug or merge the duplicate post |
| Rule / vaccine | QA Rule Checker Learning (CLAUDE.md tail), **V23** (SEO identity/canonical) |
| Prevention | Run `qa-auto-rule-checker.py` on schedule; enforce unique slug per site |

### INC-13 — OG / social image integrity (risk pattern)

| Field | Detail |
|-------|--------|
| Date/time | standing risk (no live failure in snapshot) |
| Where | `templates/macros/img.html`, `templates/base.html` (`og:image`) |
| Symptom (potential) | `og:image` pointing at deleted `jpg/png/svg` placeholder → broken social preview |
| Root cause | OG meta referencing non-built or removed asset paths |
| Impact | Broken social cards; weak SEO/social CTR |
| Fix (suggested) | Ensure `og:image` resolves to a **real built `.webp`** (or `*.og.webp`); avoid deleted placeholder paths |
| Rule / vaccine | OG-image integrity (see Reusable Patterns §RP-6); image macro convention |
| Prevention | After deleting an image, grep templates/content for stale OG refs; verify built asset exists |

### INC-14 — Image watermark / compliance (owned-only)

| Field | Detail |
|-------|--------|
| Date/time | 2026-06-21 (feature #699) → 2026-06-22 (#722 manifest update) |
| Where | `docs/image-watermark.md`, `data/image-watermark-manifest.json`, `static/img/posting/**` |
| Symptom (risk) | Watermarking third-party/app/bank/card/logo images = legal risk |
| Root cause | Watermark must apply **only** to owned/cleared assets |
| Impact | Brand/legal exposure if mis-stamped |
| Fix | Folder-based conservative rule: auto-watermark `static/img/posting/**` & `static/img/owned/**`; **skip** `covers/`, `brand/`, `og/`, `placeholder/`, `icons/`, remote/unknown |
| Rule / vaccine | Image watermark policy (owned-only), AdSense-safe doctrine |
| Prevention | Unclear/risky image → use existing safe placeholder; never guess legal safety; never watermark stock/brand/app/bank assets |

### INC-15 — External egress blocked (sandbox)

| Field | Detail |
|-------|--------|
| Date/time | ongoing (sandbox) |
| Evidence | `qa-404-report.json` → `external_enabled: false`, `external_checked: 0` of 1063 unique; PR #702 notes "egress sandbox chặn external → skip + đối chiếu bằng 404 checker" |
| Symptom | External link verification cannot run in sandbox |
| Root cause | Network egress blocked by environment policy |
| Impact | External links unverified — must **not** be claimed as passing |
| Fix | Use `zola check --skip-external-links` + internal `qa-404-checker.py`; report egress block clearly |
| Rule / vaccine | Egress-honesty pattern (RP-7) |
| Prevention | Never pretend external verification passed; state egress block explicitly |

---

## 2. Reusable Vaccine Patterns

| ID | Pattern | Signal | Action | Linked rule |
|----|---------|--------|--------|-------------|
| RP-1 | **Merge ≠ production done** | PR merged but no deploy/smoke evidence | Require deploy **success + public smoke check** before claiming done | Deploy Queue Policy, "Định nghĩa DONE" |
| RP-2 | **Superseded ≠ failed** | `superseded: true` / `cancelled` on `deploy.yml` | Ignore; diagnose only latest-HEAD run | V5, Failure Priority |
| RP-3 | **Checks 0 ≠ deploy failed** | "no checks for this commit" / `qa-check chưa chạy` | Refresh/rebase/clean-commit to re-emit CI; verify in Actions | GITHUB_TOKEN PR gate |
| RP-4 | **Stale conflict comment** | Old "conflict" comment after force-push/rebase | Latest green preflight wins; don't act on stale comment | Preflight conflict, V10 |
| RP-5 | **Site-wide broken link blocks unrelated PRs** | 404 gate red on a content PR that didn't touch the link | Fix via **minimal cleanup PR to `main`** | V14, V30 |
| RP-6 | **OG image must be a real built `.webp`** | `og:image` → deleted jpg/png/svg | Point to built `.webp`/`*.og.webp`; verify asset exists | OG-image integrity |
| RP-7 | **Egress honesty** | Sandbox blocks external links | `--skip-external-links` + internal check; report block, never fake-pass | Egress policy |
| RP-8 | **Owned-only watermark** | Risky/unclear image | Use safe placeholder; never watermark third-party/brand/app/bank/card/logo | Watermark policy |
| RP-9 | **No volatile artifacts in PRs** | `*-state.json`, `*.log`, `public/`, report JSON in diff | Exclude; regenerate via workflow | V18, V6 |
| RP-10 | **Auto-fix green ≠ editorial approval** | CI passes on a public-content change | Public content still needs editorial review before publish | Post-Bugfix Blog policy, approval gate |
| RP-11 | **Dirty PR / merge race** | PR turns `dirty` after QA passed | Merge promptly after green, or rebase before final QA | V10 |
| RP-12 | **Hotfix backlog drain** | Many open `vaccine-hotfix/*` PRs | Confirm green head → auto-merge FIFO; close duplicates | Vaccine Hotfix, V28 |

---

## 3. Hotfix Decision Tree

```text
CI/PR/deploy looks red — what is it really?
│
├─ Merge CONFLICT (dirty / non-fast-forward)
│   └─ Is it shared-infra (templates/base.html, sass, qa.yml, paywall)?
│       ├─ yes → autofix_conflicts.py → dedicated autofix/conflict-pr-<N> → QA  [V12]
│       └─ no  → merge origin/main into branch, resolve, re-push              [V10]
│       (NEVER force-push someone else's branch)
│
├─ REQUIRED checks FAILED on latest HEAD
│   └─ Triage by Failure Priority ladder (security→merge→build→QA→links→route→SEO→UI)
│       └─ Match a Vaccine signature? → run that FIXER (don't re-diagnose)
│          else → ff/ff9 diagnose, minimal delta, re-run qa_check.py          [§4]
│
├─ Checks NOT running (Checks 0 / "no checks for this commit")
│   └─ NOT a deploy failure → refresh / rebase / clean-commit to re-emit push
│       → confirm run exists in Actions before any other action               [RP-3]
│
├─ DEPLOY failed
│   ├─ superseded:true / cancelled → ignore (queue), check last_success       [V5/RP-2]
│   ├─ configure-pages "API rate limit" → V5 FIXER: retry/backoff, don't restart
│   └─ real build break on latest HEAD → fix build (tier 3) first
│
├─ BROKEN LINK / 404 gate
│   ├─ placeholder ![alt](url) → remove it                                    [V14]
│   ├─ dead static route → minimal cleanup PR to main                         [RP-5]
│   └─ dynamic app route false-flag → whitelist in qa-404-checker.py          [V25]
│
├─ OG IMAGE broken
│   └─ point og:image to real built .webp; verify asset; drop deleted paths   [RP-6]
│
├─ IMAGE COMPLIANCE risk
│   └─ unclear/third-party/app/bank/logo → safe placeholder, NO watermark     [RP-8]
│
├─ VOLATILE files committed
│   └─ drop *-state.json / *.log / public/ / report JSON; regenerate via job  [V18/RP-9]
│
└─ SANDBOX egress blocked
    └─ zola check --skip-external-links + internal 404 check; report honestly  [RP-7]
```

---

## 4. Do / No — for future agents

### ✅ Do

- **Diagnose only the latest HEAD** required failure; drop stale & report-only.
- **Confirm a run exists** in Actions before declaring "deploy failed".
- Treat `superseded`/`cancelled` deploys as **non-actionable queue noise**.
- Match the log to a **Vaccine signature first**; run its FIXER, don't re-diagnose.
- Fix site-wide broken links via a **minimal cleanup PR to `main`**.
- Keep `og:image` on **real built `.webp`** assets; verify after any image delete.
- Watermark **owned/cleared assets only**; risky image → safe placeholder.
- Use `--skip-external-links` + internal checker when **egress is blocked**, and say so.
- Require **deploy success + public smoke** before claiming production done.
- Rebase/refresh stale branches before final QA to avoid `dirty`/merge race.
- Drain the **vaccine-hotfix PR backlog FIFO** once each head is green.

### ⛔ No

- **No** "production done" without deploy + smoke evidence.
- **No** acting on stale conflict comments after a newer green preflight.
- **No** assuming deploy failure from `Checks 0` — refresh/rebase instead.
- **No** committing `public/`, `*-state.json`, `*.log`, or volatile report JSON.
- **No** force-pushing someone else's branch.
- **No** watermarking third-party/stock/brand/app/bank/card/logo images.
- **No** pretending external verification passed when egress was blocked.
- **No** guessing legal safety of an image — use the safe placeholder.
- **No** treating auto-fix green as editorial approval for public content.
- **No** bypassing required checks / vaccine gates to force a merge.
- **No** CLAUDE.md vaccine registry edits or vaccine renumbering.

---

*Memory map, not a blame log. Every failure above maps to a rule, vaccine, or hotfix
decision so the next agent moves faster and safer.*
