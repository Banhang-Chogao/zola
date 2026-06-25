# Root Cause: GitHub Actions "Action required" on bot maintenance PRs

**Date:** 2026-06-18  
**Repo:** Banhang-Chogao/zola  
**Symptom:** PRs opened by `github-actions[bot]` (Build Dashboard, Compliance, Merge Report, …) show **Action required** — 0 check runs, auto-merge never fires.

## Root causes (verified)

### 1. GITHUB_TOKEN PR gate (GitHub platform)

When a workflow uses `GITHUB_TOKEN` to open/update a PR, GitHub **does not** run workflows triggered by `pull_request` on that PR. The UI shows **Approve and run workflows** / **Action required**.

This is documented GitHub behavior (privilege escalation prevention), not a misconfigured workflow file.

**Evidence:** PR #355 `chore/build-dashboard-data` — `total_count: 0` check runs; author `github-actions[bot]`.

### 2. Broken `workflow_run` relay condition

`qa.yml` relay (historical — `pr-policy.yml` removed 2026-06-18) required:

```yaml
github.event.workflow_run.head_branch != 'main'
```

Maintenance workflows (`Fetch Build Dashboard`, `Fetch Merge Report`, `Compliance Score Audit`, …) run on **`main`** via `schedule` / `push` / `workflow_run`. Relay was **always skipped** → no QA/Policy checks.

### 3. Wrong commit SHA in relay

`workflow_run.head_sha` is the commit the **source workflow** ran on (usually `main`), not the new commit on `chore/*` created by `push_via_pr.sh`. `commits/{sha}/pulls` API returns nothing → relay exited silently.

## Permanent fix (2026-06-18 — no approval gate)

| Layer | Change |
|-------|--------|
| **Primary** | **Xóa `pull_request` trigger** khỏi `qa.yml`, `auto-merge.yml`, `changelog-update.yml` |
| **CI path** | `push` feature branch → QA Gatekeeper (không approval) → `workflow_run` → Auto Merge |
| **Backup** | `trigger_bot_pr_ci.sh` dispatch QA + Auto Merge via `workflow_dispatch` |
| **Relay** | `resolve_open_bot_pr.sh` + `workflow_run` cho maintenance workflows trên `main` |
| **Removed** | `pr-policy.yml` — không còn PR Policy gate |
| **Optional** | `WORKFLOW_BOT_PAT` — PAT mở PR (native CI) |

## Repository settings (admin — not in git)

| Setting | Required value |
|---------|----------------|
| Actions → Workflow permissions | **Read and write** |
| Branches → `main` → Required approvals | **0** |
| Branches → `main` → Required checks | `qa-check` only (PR Policy removed) |
| General → Allow auto-merge | **On** |
| Environments → `github-pages` | Only `deploy.yml` — not QA/chore |

## Validation plan

1. Merge this PR to `main`
2. Wait for next scheduled `Fetch Build Dashboard` or manual `workflow_dispatch`
3. Confirm new bot PR gets `qa-check` without owner approval
4. Confirm `Auto Merge PRs` merges when checks green
5. Stuck PRs #355–#361: re-run source workflow or close/reopen after merge

## Residual risk

- Without `WORKFLOW_BOT_PAT`, CI depends on `workflow_dispatch` chain — monitor `trigger_bot_pr_ci.sh` warnings in workflow logs
- Fork PRs still require maintainer approval (GitHub platform — outside repo config)
- **Admin:** remove `PR Policy` / `policy` from branch protection required checks if still listed in GitHub Settings