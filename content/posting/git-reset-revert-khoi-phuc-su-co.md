+++
title = "Git reset, revert và khôi phục sự cố (nâng cao)"
description = "Phân biệt git reset soft/mixed/hard, git revert, git restore và cách khôi phục an toàn khi lỡ tay. Series Git & GitHub — Bài 12/15."
date = 2026-06-18
aliases = ["/git-reset-revert-khoi-phuc-su-co/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "github", "git reset", "git github series", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "git reset"
featured = false
series = "git-github"
series_part = 12
series_total = 15

[[extra.faq]]
q = "git reset và git revert khác nhau thế nào?"
a = "git reset di chuyển con trỏ nhánh về commit cũ, viết lại lịch sử — phù hợp cho nhánh riêng. git revert tạo một commit mới đảo ngược thay đổi của commit cũ, giữ nguyên lịch sử — an toàn cho nhánh chung."

[[extra.faq]]
q = "git reset --soft, --mixed, --hard khác gì nhau?"
a = "--soft: lùi commit nhưng giữ thay đổi ở staging. --mixed (mặc định): lùi commit, giữ thay đổi ở working directory nhưng bỏ staging. --hard: lùi commit và XÓA mọi thay đổi — nguy hiểm, dùng cẩn thận."

[[extra.faq]]
q = "Lỡ git reset --hard thì khôi phục được không?"
a = "Thường là được, nếu các commit đã từng được tạo. Dùng git reflog để tìm mã băm trước khi reset rồi git reset --hard tới mã đó. Nhưng thay đổi chưa từng commit thì không cứu được."
+++

> 📚 **Git & GitHub Series (Bài 12/15)** — Sau bộ phao cứu sinh [stash, cherry-pick, reflog ở Bài 11](/zola/posting/git-stash-cherry-pick-reflog-nang-cao/), bài này dạy cách quay ngược thời gian có chủ đích với **git reset** và revert.

**Git reset**, `revert` và `restore` là ba cách "hoàn tác" trong Git, nhưng chúng hoạt động rất khác nhau — và nhầm lẫn giữa chúng có thể khiến bạn mất việc hoặc làm rối nhánh chung. Bài này phân biệt rõ từng lệnh, kèm quy tắc chọn lệnh nào trong từng tình huống, để bạn xử lý sự cố một cách an toàn.

<!-- more -->

## Ba cấp độ của git reset

`git reset` di chuyển con trỏ nhánh về một commit trước đó. Điểm khác biệt nằm ở việc nó xử lý staging và working directory ra sao. Theo [tài liệu git reset](https://git-scm.com/docs/git-reset), có ba chế độ:

| Chế độ | Lùi commit? | Giữ ở staging? | Giữ ở working dir? |
|---|---|---|---|
| `--soft` | Có | Có | Có |
| `--mixed` (mặc định) | Có | Không | Có |
| `--hard` | Có | Không | **Không (xóa hết)** |

Ví dụ gộp 3 commit cuối thành một cách thủ công:

```bash
git reset --soft HEAD~3
git commit -m "Gộp 3 commit thành một"
```

`--soft` lùi con trỏ nhưng giữ mọi thay đổi ở staging, sẵn sàng commit lại.

## ⚠️ Cẩn thận với git reset --hard

```bash
git reset --hard HEAD~1
```

Lệnh này lùi một commit **và xóa sạch** mọi thay đổi chưa commit. Nó cực mạnh nhưng nguy hiểm. Trước khi `--hard`, hãy chắc chắn bạn không cần các thay đổi hiện tại — hoặc đã `git stash` chúng. Nếu lỡ tay, nhớ tới [git reflog ở Bài 11](/zola/posting/git-stash-cherry-pick-reflog-nang-cao/) để cứu hộ.

## git revert — hoàn tác an toàn cho nhánh chung

Khác với reset (viết lại lịch sử), `git revert` tạo một **commit mới** đảo ngược thay đổi của một commit cũ:

```bash
git revert a1b2c3d
```

Vì không xóa lịch sử, revert an toàn cho nhánh đã chia sẻ như `main`. Đây là cách đúng để hoàn tác một thay đổi đã được push và người khác đã pull. Quy tắc:

- **Nhánh riêng, chưa chia sẻ** → có thể `reset`.
- **Nhánh chung, đã push** → dùng `revert`.

## git restore — khôi phục file cụ thể

Từ Git 2.23, `git restore` chuyên dùng để khôi phục file (tách khỏi `checkout` cho rõ nghĩa):

```bash
git restore ten-file.txt          # bỏ thay đổi chưa staging
git restore --staged ten-file.txt # bỏ staging, giữ thay đổi
```

Đây là cách an toàn để "vứt" thay đổi một file về trạng thái commit gần nhất mà không đụng các file khác.

## Bảng chọn lệnh theo tình huống

| Tình huống | Lệnh nên dùng |
|---|---|
| Sửa thông điệp commit cuối | `git commit --amend` |
| Bỏ staging một file | `git restore --staged <file>` |
| Vứt thay đổi chưa commit của file | `git restore <file>` |
| Lùi commit nhưng giữ thay đổi | `git reset --soft/--mixed` |
| Hoàn tác commit đã push lên main | `git revert` |
| Quay về điểm cũ, chấp nhận mất | `git reset --hard` (cẩn thận) |

## git commit --amend — sửa commit vừa tạo

Lỡ commit thiếu file hoặc sai chính tả thông điệp? Không cần tạo commit mới:

```bash
git add file-quen.txt
git commit --amend
```

Lưu ý `--amend` cũng viết lại lịch sử, nên đừng amend commit đã push lên nhánh chung.

## Quy trình khôi phục an toàn khi gặp sự cố

Khi có chuyện không mong muốn, đừng vội gõ lệnh "mạnh tay". Hãy theo trình tự bình tĩnh sau:

1. **Dừng lại và `git status`** — hiểu rõ Git đang ở trạng thái nào trước khi hành động.
2. **`git log --oneline` và `git reflog`** — xác định commit bạn muốn quay về.
3. **Ưu tiên thao tác không phá hủy**: thử `git restore` hoặc `git revert` trước khi nghĩ tới `reset --hard`.
4. **Sao lưu nhánh hiện tại** bằng `git switch -c backup-truoc-khi-sua` để có đường lùi.
5. Chỉ khi đã chắc chắn mới dùng lệnh viết lại lịch sử.

Thói quen "tạo nhánh sao lưu trước khi làm điều nguy hiểm" là dấu hiệu của người dùng Git cẩn trọng — nó biến mọi thao tác rủi ro thành có thể đảo ngược.

## Tóm lại

**Git reset** lùi con trỏ và (tùy chế độ) xử lý thay đổi; `revert` hoàn tác an toàn bằng commit mới cho nhánh chung; `restore` khôi phục từng file. Quy tắc cốt lõi: viết lại lịch sử (`reset`, `amend`) chỉ cho nhánh riêng; nhánh chung thì `revert`. Nắm điều này, bạn xử lý sự cố mà không gây họa cho cả nhóm.

Ở **Bài 13**, chúng ta nâng tầm lên quy trình tổ chức công việc: [Git workflow chuyên nghiệp với Git Flow và GitHub Flow](/zola/posting/git-workflow-chuyen-nghiep-gitflow-github-flow/).
