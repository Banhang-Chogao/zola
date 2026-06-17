# GitHub Actions — permissions & workflow approval

## Root cause: "Action required" on bot PRs

| # | Cause | Effect |
|---|-------|--------|
| 1 | **GITHUB_TOKEN PR gate** | `pull_request` workflows blocked on PRs opened by `github-actions[bot]` |
| 2 | **Relay `head_branch != main`** | `workflow_run` relay skipped for scheduled maintenance on `main` |
| 3 | **Wrong relay SHA** | `workflow_run.head_sha` = `main`, not PR head → no PR found |

Full report: `docs/ROOT-CAUSE-ACTION-REQUIRED.md`

## Permanent fix (in repo)

1. **`push_via_pr.sh`** → **`trigger_bot_pr_ci.sh`** dispatches `QA Gatekeeper` + `PR Policy` on branch (`workflow_dispatch`)
2. **`qa.yml` / `pr-policy.yml` / `auto-merge.yml`** — skip `pull_request` when actor is `github-actions[bot]` (no ghost Action required)
3. **`resolve_open_bot_pr.sh`** — fallback PR resolution for `workflow_run` relay
4. **`actions: write`** on maintenance workflows that dispatch CI

## GitHub repo Settings (admin)

**Settings → Actions → General**

| Setting | Value |
|---------|-------|
| Workflow permissions | **Read and write** |
| Fork PR workflows | Require approval for **outside collaborators** only |

**Settings → Branches → `main`**

- Required checks: `qa-check`, `policy`
- Required approvals: **0**
- Allow auto-merge: **On**

**Settings → Environments → `github-pages`**

- Only `deploy.yml` job `deploy` — not QA/chore

## Optional: `WORKFLOW_BOT_PAT` secret

Fine-grained PAT (scope: `contents`, `pull_requests`, `actions`).

When set, `push_via_pr.sh` uses PAT → `pull_request` CI runs natively; `trigger_bot_pr_ci.sh` skips dispatch.

## Manual review exceptions

Protected domain / paths → `scripts/auto_merge_policy.py` blocks auto-merge. Labels: `no-auto-merge`, `manual-review`.

## Rule

- Never re-add `pr-approval.yml` / `manual-approval` check
- Never push `main` directly (`main-guard.yml`)
- Bot maintenance PRs: CI via dispatch or PAT — not owner "Approve workflows"