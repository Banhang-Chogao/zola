# Branch protection — `main`

Áp dụng thủ công trên GitHub (repo owner): **Settings → Branches → Branch protection rules → Add rule** cho `main`.

## Cấu hình khuyến nghị

| Setting | Giá trị |
|---------|---------|
| Branch name pattern | `main` |
| Require a pull request before merging | ✅ |
| Required approvals | **1** |
| Dismiss stale pull request approvals when new commits are pushed | ✅ |
| Require review from Code Owners | (tùy chọn) |
| Require status checks to pass before merging | ✅ |
| Status checks | `QA Gatekeeper`, `PR Policy`, `Build and deploy` (nếu required) |
| Require conversation resolution before merging | ✅ |
| Require signed commits | (tùy chọn) |
| Require linear history | (tùy chọn — squash merge OK) |
| Include administrators | ✅ (admin cũng phải qua PR) |
| Allow force pushes | ❌ |
| Allow deletions | ❌ |
| Restrict who can push to matching branches | ✅ — **không ai** push trực tiếp |

## Không cho bot bypass

- Tắt **"Allow specified actors to bypass required pull requests"**
- Workflow `GITHUB_TOKEN` không được quyền bypass (mặc định GitHub)

## Kiểm tra sau khi bật

```bash
# Phải FAIL (bị chặn bởi branch protection):
git checkout main && git commit --allow-empty -m "test direct" && git push origin main

# Phải PASS:
# feature branch → PR → approve → Merge pull request
```

## CLI (nếu có `gh` + quyền admin)

```bash
gh api repos/Banhang-Chogao/zola/branches/main/protection -X PUT \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  -f enforce_admins=true \
  -f required_status_checks='{"strict":true,"contexts":["QA Gatekeeper","PR Policy"]}' \
  -f restrictions=null \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```

Điều chỉnh `contexts` theo danh sách status check thực tế trong repo.