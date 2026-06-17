# Branch protection — `main`

## Trạng thái hiện tại

**Không có branch protection rule** trên `main` — direct push được phép.

Đã xác minh qua GitHub API (`/repos/Banhang-Chogao/zola/branches/main` → `protected: false`).

## Không bật lại các rule sau

| Setting | Giá trị |
|---------|---------|
| Require a pull request before merging | ❌ Tắt |
| Required status checks before merging | ❌ Tắt (QA chạy song song, không chặn push) |
| Restrict who can push | ❌ Tắt |
| Lock branch | ❌ Tắt |

## Quy trình

```
git commit → git push origin main → QA + Deploy tự chạy → Xong
```

## Kiểm tra

```bash
curl -s https://api.github.com/repos/Banhang-Chogao/zola/branches/main \
  | python3 -c "import sys,json; print('protected:', json.load(sys.stdin)['protected'])"
# Kỳ vọng: protected: False

git push origin main   # phải thành công ngay
```

## Nếu ai đó bật lại protection

Repo admin gỡ rule tại: **Settings → Branches → `main` → Delete rule**

Hoặc CLI (cần `gh auth login`):

```bash
gh api -X DELETE repos/Banhang-Chogao/zola/branches/main/protection
```