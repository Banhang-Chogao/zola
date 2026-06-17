# Branch protection — `main`

Áp dụng trên GitHub: **Settings → Branches → Branch protection rules** cho `main`.

## Cấu hình — FULLY AUTOMATED OPERATIONS (2026-06-18)

| Setting | Giá trị |
|---------|---------|
| Branch name pattern | `main` |
| Require a pull request before merging | ✅ |
| Required approvals | **0** |
| Dismiss stale pull request approvals when new commits are pushed | (tùy chọn) |
| Require status checks to pass before merging | ✅ |
| Status checks | `qa-check`, `policy` (hoặc tên workflow `QA Gatekeeper`, `PR Policy`) |
| Allow auto-merge | ✅ (Settings → General → Allow auto-merge) |
| Require conversation resolution before merging | (tùy chọn) |
| Include administrators | ✅ |
| Allow force pushes | ❌ |
| Allow deletions | ❌ |

## Auto-merge workflow

- File: `.github/workflows/auto-merge.yml`
- Policy: `data/auto-merge-policy.json`, `scripts/auto_merge_policy.py`
- Script: `scripts/try_auto_merge.py`
- Merge method: squash
- Label sau merge: `auto-merged`
- Protected domain → skip auto-merge, comment lý do trên PR

## Bypass cho GitHub Actions (nếu cần)

Nếu merge vẫn bị chặn dù approvals = 0:

1. Settings → Actions → General → **Workflow permissions** → Read and write
2. Hoặc thêm rule: allow `github-actions[bot]` bypass required pull requests (chỉ khi cần)

## Kiểm tra

```bash
# Phải FAIL — push trực tiếp:
git checkout main && git commit --allow-empty -m "test" && git push origin main

# Phải PASS — PR + CI xanh → auto-merge.yml merge
```

## Merge Report

Sau mỗi merge: `merge-report.yml` cập nhật `data/merge-report.json`.

```bash
GITHUB_TOKEN=... python3 scripts/fetch_merge_report.py
```