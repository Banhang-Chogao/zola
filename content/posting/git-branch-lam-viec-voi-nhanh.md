+++
title = "Git branch: làm việc với nhánh trong Git"
description = "Git branch là gì, cách tạo, chuyển, đổi tên và xóa nhánh, switch vs checkout. Series Git & GitHub — Bài 4/15 cho người mới và nâng cao."
date = 2026-06-18
aliases = ["/git-branch-lam-viec-voi-nhanh/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "github", "git branch", "git github series", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "git branch"
featured = false
series = "git-github"
series_part = 4
series_total = 15

[[extra.faq]]
q = "Git branch là gì?"
a = "Git branch (nhánh) là một con trỏ trỏ tới một commit, tạo ra một dòng phát triển song song. Bạn dùng nhánh để phát triển tính năng mới mà không ảnh hưởng nhánh chính (main), rồi gộp lại khi xong."

[[extra.faq]]
q = "git switch và git checkout khác nhau thế nào?"
a = "git checkout là lệnh cũ làm nhiều việc (chuyển nhánh, khôi phục file). Từ Git 2.23, git switch chuyên dùng để chuyển nhánh và git restore để khôi phục file — rõ ràng và ít nhầm lẫn hơn. Cả hai vẫn dùng được."

[[extra.faq]]
q = "Tạo nhánh mới trong Git bằng lệnh gì?"
a = "Dùng git branch ten-nhanh để tạo, rồi git switch ten-nhanh để chuyển sang. Hoặc gộp một bước: git switch -c ten-nhanh (hoặc git checkout -b ten-nhanh)."
+++

> 📚 **Git & GitHub Series (Bài 4/15)** — Sau khi thành thạo [lệnh Git cơ bản ở Bài 3](/zola/posting/lenh-git-co-ban-init-add-commit-status/), bài này mở khóa sức mạnh lớn nhất của Git: **branch (nhánh)**.

**Git branch** là tính năng khiến Git trở nên mạnh mẽ và linh hoạt hơn hẳn các công cụ cũ. Nhánh cho phép bạn tạo một "dòng thời gian song song" để thử tính năng mới, sửa lỗi, hay viết bài blog mới — mà không hề đụng tới bản chính đang ổn định. Khi xong, bạn gộp (merge) lại. Bài này hướng dẫn tạo, chuyển, đổi tên và xóa nhánh một cách an toàn.

<!-- more -->

## Vì sao git branch lại quan trọng?

Hãy hình dung bạn đang có một blog chạy ổn định trên nhánh `main`. Bạn muốn thử một giao diện mới, nhưng nếu sửa trực tiếp `main` mà hỏng thì site sập. Giải pháp: tạo nhánh `giao-dien-moi`, làm thoải mái ở đó, khi ưng ý mới gộp về `main`.

Nhờ tạo nhánh **cực nhanh và nhẹ** (chỉ là một con trỏ tới commit), Git khuyến khích bạn tạo nhánh cho mọi việc. Đây là nền tảng của mọi quy trình cộng tác hiện đại — sẽ bàn ở [Bài 13 về workflow](/zola/posting/git-workflow-chuyen-nghiep-gitflow-github-flow/).

## Xem và tạo nhánh

```bash
git branch              # liệt kê các nhánh, dấu * là nhánh hiện tại
git branch tinh-nang-a  # tạo nhánh mới tên tinh-nang-a
```

Lưu ý: `git branch tinh-nang-a` chỉ **tạo** nhánh chứ chưa chuyển sang. Theo [tài liệu chính thức của Git](https://git-scm.com/docs/git-branch), nhánh thực chất chỉ là một tham chiếu tới commit.

## Chuyển nhánh với git switch

Từ Git 2.23, lệnh `git switch` được khuyến nghị để chuyển nhánh:

```bash
git switch tinh-nang-a       # chuyển sang nhánh đã có
git switch -c tinh-nang-b    # tạo VÀ chuyển sang nhánh mới (gộp 2 bước)
```

Lệnh cũ tương đương là `git checkout tinh-nang-a` và `git checkout -b tinh-nang-b`. Cả hai vẫn hoạt động, nhưng `switch` rõ nghĩa hơn cho người mới.

## switch và checkout — nên dùng cái nào?

| Việc cần làm | Lệnh mới (khuyến nghị) | Lệnh cũ |
|---|---|---|
| Chuyển nhánh | `git switch <nhánh>` | `git checkout <nhánh>` |
| Tạo + chuyển nhánh | `git switch -c <nhánh>` | `git checkout -b <nhánh>` |
| Khôi phục file đã sửa | `git restore <file>` | `git checkout -- <file>` |

`checkout` làm quá nhiều việc nên dễ gây nhầm. Tách thành `switch` (đổi nhánh) và `restore` (khôi phục file) giúp ý định của bạn rõ ràng hơn.

## Quy trình thực hành với một nhánh tính năng

```bash
git switch -c them-trang-lien-he
git add .
git commit -m "Thêm trang liên hệ"
git switch main
```

Lúc này nhánh `main` vẫn nguyên vẹn, còn công việc của bạn nằm an toàn trên `them-trang-lien-he`. Khi muốn đưa vào `main`, bạn sẽ dùng `git merge` — chủ đề của [Bài 5](/zola/posting/git-merge-va-xu-ly-conflict/).

## HEAD và con trỏ nhánh hoạt động ra sao

Để hiểu sâu **git branch**, cần biết khái niệm `HEAD` — con trỏ đặc biệt chỉ tới nhánh (và commit) bạn đang đứng. Khi bạn `git switch` sang nhánh khác, `HEAD` di chuyển theo, và thư mục làm việc được cập nhật về trạng thái của nhánh đó.

- Mỗi nhánh chỉ là một con trỏ nhẹ tới một commit cụ thể.
- Khi bạn commit, con trỏ nhánh hiện tại tự động tiến lên commit mới.
- Vì nhánh nhẹ như vậy, tạo và xóa nhánh gần như tức thì — khác hẳn việc copy cả thư mục.

Nếu bạn `git switch` tới một commit cụ thể (không phải nhánh), Git báo trạng thái **detached HEAD**: bạn đang xem lịch sử nhưng không đứng trên nhánh nào. Muốn giữ thay đổi ở đó, hãy tạo nhánh mới bằng `git switch -c ten-nhanh-moi`.

## So sánh các nhánh

Khi làm nhiều nhánh, bạn thường cần biết chúng khác nhau ra sao:

```bash
git log --oneline --graph --all
git diff main..tinh-nang-a
```

Lệnh đầu vẽ cây toàn bộ nhánh; lệnh sau so sánh khác biệt giữa hai nhánh. Đây là công cụ trực quan giúp bạn quyết định khi nào nên merge.

## Đổi tên và xóa nhánh

```bash
git branch -m ten-cu ten-moi   # đổi tên nhánh
git branch -d tinh-nang-a      # xóa nhánh đã merge (an toàn)
git branch -D tinh-nang-a      # xóa cưỡng bức, kể cả chưa merge
```

`-d` (chữ thường) chỉ xóa khi nhánh đã được gộp, tránh mất việc. Dùng `-D` (chữ hoa) khi bạn chắc chắn muốn bỏ nhánh dù chưa merge.

## Mẹo làm việc với nhiều nhánh

- Luôn `git status` trước khi chuyển nhánh — nếu còn thay đổi chưa commit, hãy commit hoặc dùng `git stash` (xem [Bài 11](/zola/posting/git-stash-cherry-pick-reflog-nang-cao/)).
- Đặt tên nhánh rõ ràng: `feature/`, `fix/`, `chore/` — đúng quy ước blog này đang dùng.
- `git switch -` quay lại nhánh vừa rời, giống `cd -` trong terminal.

## Tóm lại

**Git branch** cho bạn quyền tự do thử nghiệm mà không sợ phá bản chính: tạo nhánh bằng `git branch` hoặc `git switch -c`, chuyển bằng `git switch`, dọn dẹp bằng `git branch -d`. Tư duy "mỗi việc một nhánh" là thói quen của lập trình viên chuyên nghiệp.

Ở **Bài 5**, chúng ta học cách hợp nhất công sức trên nhánh trở lại `main` qua [git merge và cách xử lý conflict](/zola/posting/git-merge-va-xu-ly-conflict/) — kỹ năng không thể thiếu khi làm việc nhóm. Nếu bỏ lỡ nền tảng, hãy đọc lại [Bài 1: Git là gì](/zola/posting/git-la-gi-version-control-cho-nguoi-moi/).
