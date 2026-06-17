# GitHub Actions — permissions & workflow approval

## "Workflows awaiting approval" — nguyên nhân & fix

GitHub **không cho phép** tắt hoàn toàn approval gate cho PR do `github-actions[bot]` tạo bằng `GITHUB_TOKEN` khi workflow dùng trigger `pull_request`. UI hiện **"3 workflows awaiting approval"** dù job đã skip.

| Nguyên nhân | Fix trong repo |
|-------------|----------------|
| `pull_request` trigger trên bot PR | **Đã xóa** — dùng `push` + `workflow_dispatch` + `workflow_run` |
| `pr-policy.yml` | **Đã xóa** |
| Fork PR từ outside collaborator | Cấu hình Settings (bên dưới) |

Chi tiết: `docs/ROOT-CAUSE-ACTION-REQUIRED.md`

## Luồng CI tự động (ZERO_BARRIER)

```
push_via_pr.sh → push feature branch
    → QA Gatekeeper (push event, không approval)
    → Auto Merge PRs (workflow_run sau QA)
    → merge main → deploy.yml → production
```

Backup: `trigger_bot_pr_ci.sh` dispatch `QA Gatekeeper` + `Auto Merge PRs` trên branch.

## GitHub repo Settings — BẮT BUỘC cấu hình thủ công

Vào: **https://github.com/Banhang-Chogao/zola/settings/actions**

### Actions → General

| Setting | Giá trị đúng |
|---------|----------------|
| **Actions permissions** | Allow all actions and reusable workflows |
| **Workflow permissions** | **Read and write permissions** |
| **Allow GitHub Actions to create and approve pull requests** | ✅ **Bật (checked)** |
| **Fork pull request workflows** | Require approval for **outside collaborators** only (không chọn "all") |

### Actions → General → Approval for running fork pull request workflows

- ❌ Không chọn "Require approval for first-time contributors" (nếu có tùy chọn riêng)
- Chỉ giữ bảo vệ cho fork từ **outside collaborators**

### Settings → Branches → `main` → Edit

| Setting | Giá trị |
|---------|---------|
| Required approvals | **0** |
| Required status checks | Chỉ `qa-check` — **gỡ** `policy` / `PR Policy` nếu còn |
| Allow auto-merge | ✅ On (Settings → General → Allow auto-merge) |

### Settings → Environments → `github-pages`

- Chỉ `deploy.yml` — không gate QA/chore

## Optional: `WORKFLOW_BOT_PAT` secret

Fine-grained PAT (scope: `contents`, `pull_requests`, `actions`).

Khi set, `push_via_pr.sh` mở PR bằng PAT → `pull_request` CI chạy native (không cần push relay). Không bắt buộc sau fix push-based CI.

## Unstick bot PRs đang kẹt "awaiting approval"

Sau merge fix này, với PR bot đang mở:

1. Re-run workflow **QA Gatekeeper** (`workflow_dispatch` trên head branch), hoặc
2. Push empty commit: `git commit --allow-empty && git push`, hoặc
3. Close + để maintenance workflow tạo PR mới

## Rule

- Không thêm lại `pull_request` trigger trên QA / auto-merge / changelog
- Không thêm lại `pr-approval.yml` / `pr-policy.yml`
- Không push `main` trực tiếp (`main-guard.yml`)