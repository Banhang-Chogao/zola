# GitHub Actions — permissions (direct push)

## Quy trình

```
git commit → git push origin main → QA Gatekeeper → deploy.yml → production
```

Bot workflows dùng `.github/scripts/push_to_main.sh` — **không** tạo branch/PR.

## GitHub repo Settings

**https://github.com/Banhang-Chogao/zola/settings/actions**

### Actions → General

| Setting | Giá trị |
|---------|---------|
| Actions permissions | Allow all actions and reusable workflows |
| Workflow permissions | **Read and write permissions** |

### Settings → Branches → `main`

| Setting | Giá trị |
|---------|---------|
| Require a pull request before merging | **❌ TẮT** |
| Required status checks | (tùy chọn) `qa-check` |
| Allow force pushes | ❌ |

### Settings → Environments → `github-pages`

- Chỉ `deploy.yml` — không gate QA/chore

## Optional: `WORKFLOW_BOT_PAT` secret

Fine-grained PAT (`contents` write). Dùng khi `GITHUB_TOKEN` bị giới hạn push main.

## Đã gỡ (không dùng lại)

- `main-guard.yml`, `auto-merge.yml`, `batch-merge.yml`, `autofix-conflicts.yml`
- `push_via_pr.sh`, `trigger_bot_pr_ci.sh`, `resolve_open_bot_pr.sh`
- Trigger `pull_request` trên QA / changelog