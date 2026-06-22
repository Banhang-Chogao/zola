+++
title = "GitHub PR Conflict Pending Merge Checks UNSTABLE UNKNOWN"
description = "PR conflict hay pending checks UNSTABLE/UNKNOWN? Xử lý GitHub, hiểu merge states, QA delays, kỹ thuật merge an toàn."
date = 2026-06-21
aliases = ["/github-pr-conflict-pending-checks/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "github", "github actions", "merge conflict", "pull request"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "GitHub PR conflict pending merge checks UNSTABLE UNKNOWN"
series = "github-workflow"
series_part = 16
series_total = 18

[[extra.faq]]
q = "Nếu PR hiển thị 'No conflicts with base branch' nhưng vẫn không merge được thì sao?"
a = "'No conflicts with base branch' chỉ có nghĩa là Git có thể merge (không xung đột file). Nó KHÔNG nói gì về CI checks hoặc QA Gatekeeper. PR có thể zero conflict nhưng failed build, failed tests, hoặc pending reviews — tất cả đều chặn merge."

[[extra.faq]]
q = "mergeStateStatus = 'UNSTABLE' có nghĩa là gì?"
a = "UNSTABLE có nghĩa là PR có thể merge (không conflict) nhưng có checks vẫn đang chạy hoặc failed. Merge ngay lúc này là nguy hiểm vì code chưa được validate đủ. Nên chờ mọi checks xanh (BEHIND = PR cần rebase, BLOCKED = cần fix checks, CLEAN = sẵn sàng merge)."

[[extra.faq]]
q = "UNKNOWN after force-push là bình thường không?"
a = "Bình thường hoàn toàn. Sau force-push, GitHub cần vài giây để tính toán lại mergeability. Trong lúc đó nó hiển thị UNKNOWN. Đợi 10–30 giây rồi refresh, lúc đó status sẽ rõ ràng (CLEAN, UNSTABLE, BLOCKED)."

[[extra.faq]]
q = "QA Gatekeeper chạy lâu (10–15 phút) là vấn đề gì?"
a = "Không phải vấn đề nếu đó là lần đầu hoặc đây là runner cold start. QA Gatekeeper chạy: dependency install (2–3 phút), build (2–3 phút), tests (3–5 phút), link check (2–3 phút). Cộng lại 10–15 phút là bình thường. Nếu force-push, CI chạy lại từ đầu."

[[extra.faq]]
q = "Squash and merge có thể revert được không?"
a = "Có. Dù squash merge gộp tất cả commit, commit merge vẫn có SHA riêng. Dùng `git revert <merge_commit_sha>` để tạo revert commit, hoặc revert trực tiếp trên GitHub UI (PR merged tab → Revert button)."
+++

Một buổi chiều, một PR bị stuck: **"No conflicts with base branch"** — nhưng vẫn không merge được. CI status hiển thị `UNSTABLE`, sau force-push nó thành `UNKNOWN`. Đợi 15 phút rồi checks mới xanh.

Đó là câu chuyện thực tế từ trường hợp PR #652 của tôi. Bài này chia sẻ kinh nghiệm xử lý **GitHub PR conflict pending merge checks UNSTABLE UNKNOWN** — hiểu đúng merge states, tại sao QA Gatekeeper chạy lâu, và **khi nào an toàn merge PR**.

Nếu bạn đang gặp tình huống "pending checks" hay mergeStateStatus đang ở trạng thái UNSTABLE, UNKNOWN, hoặc BLOCKED, bài này sẽ giúp bạn tìm nguyên nhân và giải pháp.

<!-- more -->

## Khi PR Bị "No Conflicts" Nhưng Vẫn Pending Merge

Phổ biến nhất là hiểu lầm này: **PR không conflict với main = sẵn sàng merge ngay**.

Sự thật là: "No conflicts with base branch" chỉ nói Git có thể tự động merge (không xung đột). Nó KHÔNG nói gì về:

- CI checks (build pass/fail)
- Tests (pass/fail)
- Required reviews (approved chưa)
- QA Gatekeeper (pass/fail)
- Link validity
- SEO compliance

Một PR có thể **zero conflict nhưng failed QA** — Git merge được, nhưng production sẽ vỡ.

Quy tắc an toàn:
> **Chỉ merge khi:** 0 failing checks + 0 pending checks + Gatekeeper pass + code review approved

## GitHub PR Conflict Pending Merge Checks UNSTABLE UNKNOWN Là Gì?

Khi xử lý trên [GitHub Actions](/github-actions-ci-cd-cho-nguoi-moi/), bạn cần hiểu rõ từng trạng thái merge. Đây là key để biết khi nào an toàn merge, khi nào cần chờ hoặc fix.

Sau khi force-push, GitHub status bar hiển thị: `UNSTABLE`. Tôi đợi vài phút rồi check lại thành `UNKNOWN`. Khi đó tôi hoang mang.

Thực ra đó là hành vi bình thường theo [GitHub merge state documentation](https://docs.github.com/en/repositories/configuring-branches-and-merging-for-your-repository/managing-protected-branches/about-protected-branches):

| Status | Ý nghĩa | Nên làm gì |
|--------|---------|-----------|
| **CLEAN** | Không conflict, mọi checks xanh | Sẵn sàng merge |
| **UNSTABLE** | Có thể merge nhưng checks đang chạy / có lỗi | Chờ checks finish, rồi fix errors |
| **BLOCKED** | Không thể merge (required reviewer, branch protection) | Fix điều kiện block, hoặc request review |
| **UNKNOWN** | GitHub chưa tính xong mergeability (thường sau force-push) | Đợi 10–30 giây, refresh lại |
| **BEHIND** | PR base branch cũ hơn main | Rebase: `git rebase main` + force-push |

**Sau force-push, UNKNOWN là bình thường.** GitHub cần vài giây để recalculate base, checks status, và conflicts. Đợi và refresh — không cần hoang mang.

## Tại Sao QA Gatekeeper Chạy 10–15 Phút?

PR #652 case: push → CI chạy → 5 phút: "pending checks" → 10 phút: "QA Gate running" → 15 phút: xanh.

Đó là thời gian:

1. **Runner cold start** (1–2 phút): GitHub allocate runner, start VM, install tools
2. **Dependency install** (2–3 phút): `pip install`, `npm install`, clone dependencies
3. **Build** (2–3 phút): `zola build` hoặc build tool of choice
4. **Tests & Lint** (2–4 phút): run unit tests, format check, linter
5. **Link validation** (2–3 phút): check internal links, 404s
6. **Report generation** (1 phút): generate report, push logs

Tổng: **10–15 phút là bình thường** lần đầu hoặc cold start.

**Nếu force-push (khi conflict/pending):** CI chạy lại từ đầu = +10–15 phút nữa. Đó là lý do tại sao:
- Force-push nhiều lần = chờ lâu
- Nên rebase cẩn thận trước force-push (xem lại [lệnh Git cơ bản](/lenh-git-co-ban-init-add-commit-status/) nếu cần)
- Hoặc dùng `git push --force-with-lease` (safer) — xem [best practices Git](/bao-mat-best-practices-git-github/)

## Khi Nào An Toàn Merge? Checklist

Đừng merge chỉ vì "không conflict" hay "1 check xanh". Dùng checklist này:

**Trước khi merge (bắt buộc):**

- ☑️ Tất cả required checks xanh (không pending, không failed)
- ☑️ QA Gatekeeper / CI xanh
- ☑️ Não conflict (Git có thể auto-merge)
- ☑️ Code review approved (nếu có required reviewers)
- ☑️ Branch up-to-date với base (hoặc GitHub auto-sync)

**Tránh merge khi:**

- ❌ Còn pending checks (test chạy dở)
- ❌ mergeStateStatus = UNSTABLE (chờ thêm)
- ❌ Có failed check (fix trước)
- ❌ Required reviewer chưa approve
- ❌ Có unresolved conversations

**Terminal check:**

```bash
# Xem PR merge status
gh pr view <PR_NUMBER> --json mergeStateStatus,mergeable,statusCheckRollup

# Output mong đợi (SAFE để merge):
# mergeStateStatus: CLEAN
# mergeable: true
# statusCheckRollup: [{ state: SUCCESS }, ...]

# Xem tất cả checks
gh pr checks <PR_NUMBER>

# Merge an toàn (squash recommended)
gh pr merge <PR_NUMBER> --squash --auto
```

## Squash Merge vs. Normal Merge

**Squash merge** (gộp tất cả commits thành 1):
- ✅ History sạch
- ✅ Dễ revert (1 commit duy nhất)
- ✅ Tránh "merge commits" spam

**Normal merge** (giữ commit history):
- ✅ History rõ ràng từng step
- ✅ Trace được ai commit gì khi
- ❌ History nhiều "merge commit"

**Khuyến cáo:** Dùng **squash merge** cho feature branch. Nếu lỡ cần revert:

```bash
# Tìm merge commit SHA
git log --oneline | head -20

# Revert
git revert -m 1 <merge_commit_sha>
git push
```

## Force-Push: Cẩn Trọng + Rebase Đúng Cách

Force-push làm GitHub recalculate mergeability → UNKNOWN status. Nó bình thường, nhưng:

**Nên làm:**

```bash
# Rebase trước force-push (an toàn hơn)
git fetch origin main
git rebase origin/main
git push --force-with-lease  # Safer than --force

# Check local trước khi push
git log --oneline <local> ^origin/main  # View commits that will push
```

**Không nên:**

```bash
# ❌ Force-push khi chưa rebase = lose history
# ❌ Force-push với --force (rủi ro cao)
# ❌ Force-push vào main trực tiếp (dangerous)
```

## Khi QA Gate Fail: Tôi Làm Gì?

Nếu QA xanh nhưng PR vẫn pending → check:

1. **Pending checks?** Refresh (`gh pr checks`) — có thể vẫn chạy
2. **Required reviewers?** Request review hoặc get approval
3. **Branch stale?** Rebase: `git pull origin main && git push --force-with-lease`
4. **Merge conflict?** Resolve conflicts, commit, push
5. **mergeStateStatus = BLOCKED?** Check PR settings — có thể GitHub Pages bảo vệ branch

**Nếu tất cả xanh nhưng GH UI vẫn nói "pending":**

```bash
gh pr merge <PR> --squash --force
```

(Hoặc đợi 2–3 phút GitHub update status.)

## Terminal Command Cheat Sheet

```bash
# Check PR merge readiness (mong đợi: CLEAN, mergeable=true, checks=all SUCCESS)
gh pr view <PR> --json mergeStateStatus,mergeable,statusCheckRollup

# Xem tất cả checks + status
gh pr checks <PR> --watch  # Watch live

# Merge an toàn (squash)
gh pr merge <PR> --squash

# Merge và auto-delete branch
gh pr merge <PR> --squash --delete-branch

# Force rebase + push (nếu lỡ force-push)
git fetch origin main && git rebase -i origin/main && git push --force-with-lease

# Revert merge (nếu lỡ merge sai)
git revert -m 1 <merge_commit_sha>

# Check UNKNOWN status (refresh sau 10–30 giây)
for i in {1..5}; do echo "Check $i:"; gh pr view <PR> --json mergeStateStatus; sleep 10; done
```

## Bài Học Từ PR #652

1. **"No conflicts" không = "ready to merge"** — kiểm tra tất cả checks, không chỉ conflict status
2. **UNKNOWN sau force-push là bình thường** — đợi, không panic
3. **QA Gatekeeper 10–15 phút là bình thường** — runner cold start + build + tests = lâu
4. **Merge chỉ khi checklist tất cả xanh** — dùng `gh pr view --json` check trước
5. **Squash merge an toàn để revert** — nếu cần rollback, 1 commit dễ handle hơn 20 commits

GitHub PR workflow có vẻ đơn giản ("không conflict = merge đi") nhưng thực tế phức tạp hơn — phần lớn delays không phải từ conflict mà từ CI/QA chạy lâu. Hiểu workflow + sử dụng `gh` CLI check trước merge = tránh ngạc nhiên.

## FAQ

**Q: Lỡ merge PR sai rồi (hoặc buggy PR lên production) — có cách nào để rollback không?**

A: Có. Nếu dùng squash merge, rollback bằng `git revert <commit_sha>`. Nếu dùng normal merge, dùng `git revert -m 1 <merge_commit_sha>`. Revert tạo 1 commit mới undo changes — an toàn hơn reset --hard. Có thể revert trực tiếp trên GitHub UI (merged PR tab → Revert button).

**Q: Branching strategy nào tốt nhất cho team?**

A: Phổ biến nhất là **Git Flow** (main + develop + feature branches) hoặc **GitHub Flow** (main + feature branches, merge bằng PR). Chọn cái phù hợp quy mô team. Quan trọng nhất: **tất cả merges bắt buộc qua PR + checks pass** — tránh hotfix trực tiếp lên main.

**Q: Có nên dùng `--force` hay `--force-with-lease`?**

A: Dùng `--force-with-lease`. Nó an toàn hơn — chỉ force-push nếu remote không thay đổi sau lần fetch của bạn. `--force` bình tĩnh overwrite bất kỳ thay đổi remote nào — rủi ro mất code người khác.

+++
