+++
title = "Xử lý PR revert sai base: case study 3135 commits và 1112 files"
description = "Case study xử lý PR revert sai base với 3135 commits, 1112 files. Cách dùng git revert -m 1, tìm merge commit, và quy trình QA/build trước khi merge."
date = 2026-06-28
aliases = ["/xu-ly-pr-revert-sai-base/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["case-study", "ci-cd", "devops", "git", "github", "kinh-nghiem", "opencode", "xử lý pr revert sai base"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "xử lý PR revert sai base"
featured = false
toc = true

[[extra.faq]]
q = "Tại sao PR #1171 có tới 3135 commits?"
a = "Vì branch được tạo từ base cũ (commit cách main rất xa), không phải từ origin/main. Khi mở PR, GitHub so sánh toàn bộ lịch sử khác biệt giữa hai branch — dẫn tới diff gồm gần như toàn bộ lịch sử repo, không chỉ thay đổi thực sự."

[[extra.faq]]
q = "Làm sao để tìm đúng merge commit cần revert?"
a = "Dùng lệnh gh pr view <số-PR> --json mergeCommit để lấy SHA. Trên web GitHub, vào PR đã merged → copy commit SHA từ dòng merged commit. Với squash merge, dùng git log --oneline --merges origin/main -5, tìm dòng Squashed."

[[extra.faq]]
q = "git revert -m 1 có tác dụng gì?"
a = "Khi revert một merge commit (có hai parents), -m 1 chỉ định mainline là parent đầu tiên (branch chính, thường là main). Git sẽ rollback changes từ nhánh feature nhưng giữ nguyên lịch sử của main. Thiếu -m 1 sẽ báo lỗi fatal: commit is a merge but no -m option."

[[extra.faq]]
q = "Có thể resolve thủ công 1112 files conflict không?"
a = "Không nên. Với 1112 files, resolve thủ công mất nhiều giờ, dễ sai sót, và khó review. Conflict markers còn sót lại sẽ vỡ build. Chỉ resolve tay khi dưới 10 files và bạn hiểu rõ nội dung từng file."

[[extra.faq]]
q = "Vai trò của OpenCode trong quy trình này là gì?"
a = "OpenCode giúp audit branch hiện tại, tìm commit gây lỗi, chạy git revert đúng cách, resolve conflict theo rule repo, chạy QA/build, fix P0 blocker, và mở PR mới — tất cả tự động theo ZERO_BARRIER policy."

[[extra.faq]]
q = "Làm thế nào để tránh PR revert sai trong tương lai?"
a = "Checklist: (1) git fetch origin main → (2) git checkout -b <branch> origin/main → (3) gh pr view <PR> --json mergeCommit → (4) git revert -m 1 <sha> → (5) git diff origin/main...HEAD --stat → (6) QA → (7) build → (8) PR."

[[extra.faq]]
q = "Merge commit và squash merge khác nhau thế nào khi revert?"
a = "Merge commit có hai parents → cần git revert -m 1. Squash merge tạo commit thường (một parent) → git revert <sha> là đủ. Dùng git cat-file -p <sha> | head -5 để xem số lượng parents."

[[extra.faq]]
q = "Sau khi revert, cần kiểm tra những gì trước khi merge?"
a = "Chạy QA gate (qa_check.py, check_base_url_hygiene.py), zola build, kiểm tra internal links. Nếu có P0 blocker phải fix. Rồi mới push và rely vào auto-merge khi CI xanh."
+++

Tôi vừa phải **xử lý PR revert sai base** — một Pull Request hiện ra **3.135 commits và 1.112 files conflict**. Con số nghe như bug GitHub, nhưng không — đó là lỗi của chính quy trình tạo PR.

Câu chuyện diễn ra trên blog SEOMONEY tối ngày 28/06/2026. Tôi chia sẻ lại với hy vọng bạn khỏi mắc sai lầm tương tự khi vội vàng revert production.

<!-- more -->

## Bối cảnh: merge PR gây lỗi UI production — cần revert gấp

Mọi chuyện bắt đầu từ PR #1169 — một bản nâng cấp hệ thống Open Graph (OG) cho blog. Mục tiêu: bổ sung `og:image:secure_url`, `twitter:image:alt`, auto-detect image type, và script sinh ảnh OG branded. Merge xong, production bắt đầu hiển thị lỗi.

Chuyện gì cũng có thể xảy ra — template không tương thích, metadata mới làm vỡ layout hiện tại, hoặc đơn giản là chưa test kỹ trên staging. Dù lý do gì, lúc UI sập thì ai cũng chỉ muốn một thứ: **revert nhanh nhất có thể**.

Và đó là lúc sai lầm đầu tiên xảy ra.

## Sai lầm số 1: tạo branch revert từ base cũ

PR #1171 được tạo với ý đồ tốt — revert PR #1169, đưa production về trạng thái ổn định. Nhưng **branch được tạo từ một base cũ**, không phải từ `origin/main`.

Cụ thể: AI agent đang hoạt động trên một branch đã checkout từ commit cách `main` rất xa. Nó chạy lệnh `git revert <sha>` rồi tạo PR ngay từ branch đó.

```bash
# ❌ Sai: tạo branch từ base KHÔNG phải origin/main
# Branch hiện tại đang ở commit cách main rất xa
git checkout -b revert-pr-1169
# đang ở branch cũ, base cũ!
git revert 58992d18
# (thiếu -m 1 — nhưng đó lại là chuyện khác)
git push origin revert-pr-1169
# → GitHub PR compare với main → 3.135 commits
```

Lúc mở PR lên GitHub, kết quả hiện ra:

<div class="highlight">

**PR #1171** — `revert-pr-1169` → `main`
- Commits: **3.135**
- Files changed: **1.112**
- Conflicts: **có, khắp nơi**

</div>

Con số này hoàn toàn có thể giải thích được.

## Phân tích: tại sao lại ra 3.135 commits?

### Base branch sai là nguyên nhân gốc

Pull Request trên GitHub so sánh `head` (branch của bạn) với `base` (thường là `main`). Nếu branch của bạn rẽ nhánh từ một commit cũ, GitHub tính **tất cả** commits từ điểm rẽ đó tới HEAD của `main` vào diff — chứ không chỉ commits bạn vừa tạo.

```text
diff = commits(origin/main..<your-branch>)     # thay đổi của bạn
     + commits(<common-ancestor>..origin/main) # lịch sử từ điểm rẽ tới main
     # = toàn bộ lịch sử từ điểm rẽ tới nay
```

Có nghĩa là nếu branch của bạn cắt từ 500 commits trước, PR sẽ hiện 500 commits cộng với thay đổi của bạn — dù bạn chỉ muốn thay đổi 2 files.

**Bài học:** trước khi tạo bất kỳ branch nào, luôn kiểm tra:

```bash
git log --oneline origin/main..HEAD | wc -l
# Nếu ra số > 10-20, bạn đang ở base cũ
git fetch origin main
git checkout -b <branch> origin/main  # base mới, sạch
```

### Merge commit vs squash merge

PR #1169 là một **merge commit** — Git merge thường, giữ nguyên lịch sử feature branch. Nó có hai parents:

```text
commit 58992d18 fix(social-share): upgrade SEOMONEY OG image (#1169)
parent 4814367f  ← mainline (parent 1 — branch chính)
parent a1b2c3d4  ← feature branch (parent 2)
```

Khi revert một merge commit, Git không biết bạn muốn revert về phía nào — vì có hai nhánh con. Bạn phải chỉ định **mainline** bằng flag `-m 1`:

```bash
# ✅ Đúng: revert nhưng giữ nguyên main
git revert -m 1 58992d18

# ❌ Sai: thiếu -m 1
git revert 58992d18
# → fatal: commit 58992d18 is a merge but no -m option was given.

# ❌ Sai: nhầm parent
git revert -m 2 58992d18
# → rollback nhầm nhánh, hỏng main
```

Còn với **squash merge** — Git gộp tất cả commits trong PR thành một commit duy nhất (một parent) — thì revert đơn giản hơn:

```bash
git revert <squash-commit-sha>
```

Cách kiểm tra loại commit:

```bash
git cat-file -p 58992d18 | head -5
# Nếu có 2 dòng "parent" → merge commit, cần -m 1
# Nếu có 1 dòng "parent" → squash hoặc commit thường
```

### Vì sao không resolve thủ công 1.112 files?

Tôi từng thấy đồng nghiệp nói: "1.112 files thì resolve từ từ, làm tới sáng là xong." Tôi không khuyên bạn làm vậy vì ba lý do:

1. **Thời gian — quá lớn.** Resolve 1.112 files conflict thủ công cần nhiều giờ, nếu không muốn nói là nhiều ngày. Chưa kể mỗi lần merge main vào để resolve lại phát sinh conflict mới.

2. **Rủi ro — quá cao.** Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) còn sót lại là chuyện thường. Một marker sót trong template HTML là build vỡ toàn bộ. Một marker sót trong workflow YAML là CI không chạy được.

3. **Không review được.** Reviewer mở PR lên thấy 1.112 files — họ sẽ làm gì? Click "close".

Giải pháp đúng rất đơn giản: **bỏ PR đó, tạo branch mới từ `origin/main`.**

## Quy trình đúng: xử lý PR revert sai base

Đây là các bước tôi đã làm và bạn nên làm khi gặp tình huống tương tự.

### Bước 1: Đóng PR sai, đừng lãng phí thời gian

PR #1171 bị đóng ngay. Không resolve, không debug, không cố gắng cứu. Nếu base đã sai, mọi thứ phía sau đều sai.

```bash
gh pr close 1171 --comment "Base sai, tạo lại từ origin/main"
```

### Bước 2: Tạo branch mới từ origin/main

```bash
git fetch origin main
git checkout -b revert-pr-1169-clean origin/main
```

Branch này sạch — không dính lịch sử cũ, không lỗi thời. Lịch sử của nó bằng đúng lịch sử `origin/main` tại thời điểm fetch.

### Bước 3: Tìm đúng merge commit

Có hai cách để tìm commit cần revert:

```bash
# Cách 1: GitHub CLI — nhanh và chính xác
gh pr view 1169 --json mergeCommit
# → {"mergeCommit":{"oid":"58992d184320f..."}}

# Cách 2: git log — lọc merge commits
git log --oneline --merges origin/main -5
# 58992d18 fix(social-share): upgrade SEOMONEY OG image (#1169)
```

### Bước 4: git revert -m 1

```bash
git revert -m 1 58992d184320f0621dfa1c5658b10e0289f85e27 --no-edit
```

Kết quả: **zero conflict.** Git revert đúng cách, chỉ thay đổi 2 files:

- `scripts/create_og_image.py` — xoá file (được thêm trong #1169, 210 dòng)
- `templates/base.html` — rollback OG metadata (54 dòng)

### Bước 5: Kiểm tra diff trước khi push

```bash
git diff origin/main...HEAD --stat
# 3 files changed, 7 insertions(+), 261 deletions(-)
# 3 files, không phải 1.112
```

Con số này đúng với kỳ vọng: 2 files từ revert + 1 file fix P0 QA (sẽ nói ở bước sau).

### Bước 6: QA và build

Đây là bước nhiều người bỏ qua khi vội — nhưng là bước quan trọng nhất.

```bash
python3 qa_check.py
# → PASS (0 P0, 2 warnings pre-existing)
zola build
# → 417 pages, 21 sections
```

QA phát hiện một **P0 blocker**: `scripts/check_base_url_hygiene.py` báo lỗi `/zola/` reference trong 2 file test. Nguyên nhân: file test chứa `/zola/` URL để kiểm tra normalization logic — legitimate code, không phải production. Fix đơn giản: thêm vào whitelist.

```bash
git add scripts/check_base_url_hygiene.py
git commit -m "fix(qa): whitelist test files with legacy /zola/ URLs"
git diff origin/main...HEAD --stat
# scripts/check_base_url_hygiene.py | 4 +-
# scripts/create_og_image.py        | 210 -----------------
# templates/base.html               | 54 +---------
```

### Bước 7: Push và mở PR

```bash
git push origin revert-pr-1169-clean

gh pr create \
  --base main \
  --head revert-pr-1169-clean \
  --title 'Revert "fix(social-share): upgrade SEOMONEY OG (#1169)"' \
  --body 'Clean revert, replaces PR #1171...'
```

### Bước 8: Auto-merge khi CI xanh

Với chính sách ZERO_BARRIER, PR xanh sẽ tự động merge và deploy — không cần human approval.

```bash
gh pr merge 1172 --auto --squash
```

## So sánh PR sai vs PR đúng

| Tiêu chí | PR #1171 (sai) | PR #1172 (đúng) |
|----------|---------------|-----------------|
| Base branch | Branch cũ (cách main ~500 commits) | `origin/main` |
| Commits hiển thị | 3.135 | 2 |
| Files thay đổi | 1.112 | 3 |
| Conflict | Có (khắp nơi) | Không (ngay từ đầu) |
| Thời gian tạo PR | ~1 giây | ~1 phút |
| Thời gian resolve | Nhiều giờ → bỏ cuộc | 0 (không cần) |
| Có thể QA được | Không (quá nhiều) | Có (3 files) |
| Kết quả | PR closed, làm lại | Merged, production ổn định |

## Vai trò của OpenCode trong quy trình **xử lý PR revert sai base**

Toàn bộ case study này được xử lý bởi **OpenCode** (dùng Claude làm engine). Các bước tự động:

1. **Audit PR #1171:** Xác định diff bất thường (3.135 commits, 1.112 files), kết luận: revert sai base, không thể resolve thủ công.
2. **Đóng PR cũ:** `gh pr close 1171` — dừng ngay, không lãng phí.
3. **Tra cứu merge commit:** `gh pr view 1169 --json mergeCommit` — lấy SHA chính xác.
4. **Revert sạch:** Tạo branch từ `origin/main` → `git revert -m 1 <sha>` → **zero conflict**.
5. **QA toàn diện:** `qa_check.py` + `zola build` + `check_base_url_hygiene.py`. Phát hiện P0 blocker.
6. **Fix P0 blocker:** Phân biệt legitimate test code vs production code → whitelist an toàn.
7. **Push + PR:** Tạo PR #1172, update title/body, enable auto-merge.

Tất cả tuân thủ **ZERO_BARRIER policy** — CI xanh là merge được. Không cần chờ approval. Không cần review thủ công.

## Bài học và checklist

### Bài học số 1: Luôn kiểm tra base branch

Lỗi cơ bản nhất nhưng dễ mắc nhất khi vội.

```
git log --oneline origin/main..HEAD | wc -l
# 0-5: ok
# >20: bạn đang ở base cũ → rebase hoặc tạo branch mới
```

### Bài học số 2: Diff stat trước PR

Trước khi push và mở PR, kiểm tra diff:

```bash
git diff origin/main...HEAD --stat
# ≤10 files: khả quan
# >20 files: kiểm tra lại
# >100 files: chắc chắn sai
```

### Bài học số 3: Biết loại commit để revert đúng

| Loại merge | Dấu hiệu | Cách revert |
|-----------|---------|------------|
| Merge commit | `git cat-file -p <sha>` có 2 dòng `parent` | `git revert -m 1 <sha>` |
| Squash merge | 1 dòng `parent` | `git revert <sha>` |
| Regular commit | 1 dòng `parent` | `git revert <sha>` |

### Bài học số 4: Đừng resolve conflict mù quáng

Nếu PR có > 100 files conflict → **dừng lại**. Tạo branch mới từ `origin/main` luôn an toàn hơn.

Conflict resolve thủ công chỉ nên làm khi:
- Dưới 10 files
- Bạn hiểu rõ nội dung từng file
- File trùng là do thay đổi thực sự (không phải drift lịch sử)

### Bài học số 5: Kiểm tra diff stat trước khi push

Câu này xứng đáng nhắc lại. `git diff origin/main...HEAD --stat` trước khi push sẽ cho bạn biết chính xác PR sắp tới trông như thế nào.

### Checklist cho lần sau

```text
□ git fetch origin main
□ git checkout -b <branch> origin/main
□ gh pr view <PR> --json mergeCommit    # tìm SHA
□ git cat-file -p <sha> | head -5       # kiểm tra loại commit
□ git revert -m 1 <sha>                 # nếu merge commit
□ git diff origin/main...HEAD --stat    # verify ≤5 files
□ python3 qa_check.py                   # QA pass
□ zola build                            # build pass
□ git push origin <branch>
□ gh pr create ...
□ gh pr merge --auto --squash
```

## Kết luận

PR #1171 với 3.135 commits là một sai lầm — nhưng là sai lầm có thể tránh được. Chỉ cần nhớ một nguyên tắc: **tạo branch từ `origin/main`, không từ branch cũ.**

Công cụ như OpenCode giúp tự động hoá quy trình này, nhưng bản thân người dùng cũng cần hiểu bản chất để kiểm tra lại kết quả. Git không tha thứ cho sự vội vàng. Cái giá của 5 phút vội vàng là hàng giờ resolve conflict vô ích.

Tôi khuyến khích bạn dành 10 phút tìm hiểu thêm về các lệnh Git cơ bản để xử lý tình huống khẩn cấp:

- Đọc thêm về [Git revert và reset](/posting/git-reset-revert-khoi-phuc-su-co/) — bài chi tiết về phục hồi sự cố với Git.
- Khám phá chuyên mục [Công nghệ](/categories/cong-nghe/) — nơi tổng hợp các case study kỹ thuật thực tế.
- Tài liệu chính thức về [`git revert`](https://git-scm.com/docs/git-revert) trên git-scm.com — nên đọc ít nhất một lần.

Revert đúng cách mất 5 phút. Revert sai cách mất nhiều giờ, rồi cuối cùng vẫn phải làm lại từ đầu. Nhưng ít nhất, sau bài này, bạn đã biết cách làm đúng.
