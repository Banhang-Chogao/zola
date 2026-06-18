+++
title = "Git rebase: làm sạch lịch sử commit (nâng cao)"
description = "Git rebase là gì, khác merge ra sao, interactive rebase để squash và sửa commit, và quy tắc vàng không rebase nhánh chung. Series Git & GitHub — Bài 10/15."
date = 2026-06-18
aliases = ["/git-rebase-lam-sach-lich-su-commit/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "git github series", "git rebase", "github", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "git rebase"
featured = false
series = "git-github"
series_part = 10
series_total = 15

[[extra.faq]]
q = "Git rebase là gì?"
a = "Git rebase là thao tác di chuyển hoặc viết lại chuỗi commit của một nhánh lên trên một commit cơ sở mới, tạo ra lịch sử thẳng (linear). Khác với merge vốn tạo merge commit, rebase 'phát lại' các commit như thể chúng được tạo từ điểm mới."

[[extra.faq]]
q = "Khi nào nên dùng rebase thay vì merge?"
a = "Dùng rebase để giữ lịch sử nhánh tính năng sạch và thẳng trước khi gộp, hoặc cập nhật nhánh với main mới nhất. Dùng merge khi muốn giữ nguyên dấu vết lịch sử thật và điểm hợp nhất."

[[extra.faq]]
q = "Quy tắc vàng của rebase là gì?"
a = "Không bao giờ rebase các commit đã được đẩy lên nhánh dùng chung mà người khác đang dựa vào. Rebase viết lại lịch sử, làm thay đổi mã băm commit, gây rối loạn cho cộng tác viên đã pull nhánh đó."
+++

> 📚 **Git & GitHub Series (Bài 10/15)** — Bắt đầu phần nâng cao. Sau khi thành thạo [Pull Request ở Bài 9](/zola/posting/pull-request-quy-trinh-cong-tac-github/), ta học **git rebase** để làm sạch lịch sử.

**Git rebase** là một trong những công cụ mạnh và dễ gây sợ nhất của Git. Nó cho phép bạn viết lại lịch sử commit — gộp nhiều commit lộn xộn thành một chuỗi gọn gàng, hoặc cập nhật nhánh với `main` mới nhất mà không tạo merge commit rối mắt. Nhưng sức mạnh đi kèm trách nhiệm: dùng sai có thể gây rối cho cả nhóm. Bài này giải thích rebase an toàn.

<!-- more -->

## Git rebase khác merge thế nào?

Cả `merge` và `rebase` đều tích hợp thay đổi từ nhánh này sang nhánh khác, nhưng theo cách khác nhau:

- **Merge** (Bài 5): tạo một merge commit mới nối hai dòng lịch sử. Lịch sử giữ nguyên, có nhánh rẽ.
- **Rebase**: "nhấc" các commit của nhánh tính năng và phát lại chúng lên trên đỉnh `main` mới nhất, tạo lịch sử **thẳng** như thể bạn vừa tách nhánh.

Theo [tài liệu Git về rebase](https://git-scm.com/book/en/v2/Git-Branching-Rebasing), kết quả cuối cùng về nội dung thường giống nhau, nhưng **lịch sử trông khác**: merge giữ vết rẽ nhánh, rebase cho đường thẳng dễ đọc.

## Rebase cơ bản: cập nhật nhánh với main

Tình huống phổ biến: bạn làm nhánh tính năng vài ngày, `main` đã có commit mới. Để đưa nhánh lên ngang `main`:

```bash
git switch feature/trang-moi
git rebase main
```

Git phát lại từng commit của bạn lên đỉnh `main`. Nếu gặp conflict, xử lý như Bài 5 rồi chạy `git rebase --continue`. Muốn hủy giữa chừng: `git rebase --abort`.

## Interactive rebase — sửa lịch sử commit

Đây là tính năng mạnh nhất: `git rebase -i` cho phép bạn chỉnh sửa một chuỗi commit gần đây.

```bash
git rebase -i HEAD~4
```

Git mở trình soạn thảo liệt kê 4 commit gần nhất kèm các lệnh bạn có thể áp dụng:

| Lệnh | Tác dụng |
|---|---|
| `pick` | Giữ commit nguyên trạng |
| `reword` | Giữ commit nhưng sửa thông điệp |
| `squash` | Gộp commit này vào commit phía trên |
| `fixup` | Như squash nhưng bỏ thông điệp |
| `drop` | Xóa hẳn commit |

Ví dụ thực tế: bạn có 4 commit "wip", "wip2", "sửa typo", "xong" → dùng `squash`/`fixup` để gộp thành một commit sạch trước khi mở Pull Request.

## Squash trước khi mở PR

Một thói quen chuyên nghiệp là dọn nhánh trước khi đẩy lên:

1. `git rebase -i HEAD~n` với `n` là số commit cần dọn.
2. Đổi các dòng phụ thành `fixup`.
3. Lưu, đóng trình soạn thảo.
4. `git push --force-with-lease` (vì lịch sử đã đổi).

Lưu ý `--force-with-lease` an toàn hơn `--force` vì nó từ chối ghi đè nếu remote có thay đổi bạn chưa thấy.

## Quy tắc vàng của git rebase

> ⚠️ **Không bao giờ rebase commit đã chia sẻ trên nhánh dùng chung.**

Vì rebase viết lại lịch sử (đổi mã băm commit), nếu bạn rebase một nhánh mà người khác đã pull, họ sẽ gặp lịch sử "phân kỳ" và rối loạn khi đồng bộ. An toàn nhất:

- Chỉ rebase nhánh **riêng của bạn**, chưa ai dựa vào.
- Với nhánh chung (`main`, `develop`): dùng `merge`.

## Rebase hay merge — chọn khi nào?

| Tình huống | Nên dùng |
|---|---|
| Dọn nhánh tính năng riêng trước PR | `rebase -i` |
| Cập nhật nhánh riêng với main mới | `rebase main` |
| Gộp PR vào nhánh chung | `merge` (hoặc squash-merge) |
| Lịch sử cần phản ánh đúng sự thật | `merge` |

## git pull --rebase — đồng bộ mà không tạo merge commit

Nhắc lại từ [Bài 8](/zola/posting/push-pull-fetch-dong-bo-voi-github/): khi `git pull`, mặc định Git sẽ merge. Nếu muốn giữ lịch sử thẳng, bạn có thể dùng:

```bash
git pull --rebase origin main
```

Lệnh này fetch về rồi rebase commit của bạn lên trên thay vì tạo merge commit. Rất hợp khi bạn chỉ đang cập nhật nhánh riêng. Có thể đặt mặc định bằng `git config --global pull.rebase true` nếu bạn thích phong cách lịch sử tuyến tính.

## Tóm lại

**Git rebase** giúp lịch sử commit thẳng và sạch: cập nhật nhánh với `rebase main`, dọn commit lộn xộn với `rebase -i`. Sức mạnh này đi kèm quy tắc vàng — đừng rebase những gì đã chia sẻ. Dùng đúng chỗ, rebase khiến lịch sử dự án dễ đọc và chuyên nghiệp hơn hẳn.

Ở **Bài 11**, chúng ta khám phá ba công cụ cứu cánh nâng cao: [git stash, cherry-pick và reflog](/zola/posting/git-stash-cherry-pick-reflog-nang-cao/).
