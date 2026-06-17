# Branch protection — `main`

Áp dụng trên GitHub: **Settings → Branches → Branch protection rules** cho `main`.

## Cấu hình — DIRECT PUSH (2026-06-18)

| Setting | Giá trị |
|---------|---------|
| Branch name pattern | `main` |
| Require a pull request before merging | **❌ TẮT** |
| Require status checks to pass before merging | (tùy chọn) `qa-check` |
| Allow force pushes | ❌ |
| Allow deletions | ❌ |

## Quy trình

```
git commit → git push origin main → QA + Deploy tự chạy → Xong
```

Không branch feature, không PR, không auto-merge.

## Kiểm tra

```bash
git push origin main   # phải thành công ngay
```