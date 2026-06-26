+++
title = "Push, pull, fetch: đồng bộ code với GitHub"
description = "Phân biệt git push, pull, fetch và cách đồng bộ code với GitHub an toàn, tránh ghi đè. Series Git & GitHub — Bài 8/15 cho người mới."
date = 2026-06-18
aliases = ["/push-pull-fetch-dong-bo-voi-github/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "git github series", "git push", "github", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "git push"
featured = false
series = "git-github"
series_part = 8
series_total = 15

[[extra.faq]]
q = "git fetch và git pull khác nhau thế nào?"
a = "git fetch chỉ tải dữ liệu mới từ remote về nhưng không thay đổi nhánh làm việc của bạn, để bạn xem trước. git pull = git fetch + git merge: vừa tải vừa gộp ngay vào nhánh hiện tại."

[[extra.faq]]
q = "Lệnh git push dùng để làm gì?"
a = "git push đẩy các commit từ máy bạn lên repository remote (GitHub). Lần đầu nên dùng git push -u origin main để thiết lập nhánh theo dõi; các lần sau chỉ cần git push."

[[extra.faq]]
q = "Vì sao push bị từ chối (rejected)?"
a = "Thường vì remote có commit mới hơn mà máy bạn chưa có. Hãy git pull để gộp thay đổi từ remote về, xử lý conflict nếu có, rồi git push lại. Tránh dùng --force trừ khi thật sự hiểu hậu quả."
+++

> 📚 **Git & GitHub Series (Bài 8/15)** — Đã có repository GitHub ở [Bài 7](/zola/posting/github-la-gi-tao-repository-dau-tien/), giờ ta học bộ ba đồng bộ, bắt đầu bằng **git push**.

**Git push**, `pull` và `fetch` là ba lệnh bạn dùng mỗi ngày để đồng bộ code giữa máy cá nhân và GitHub. Hiểu rõ sự khác biệt giữa chúng giúp bạn tránh hai nỗi sợ lớn nhất của người mới: ghi đè mất việc của người khác, và "kẹt" không push được. Bài này giải thích từng lệnh kèm luồng làm việc an toàn.

<!-- more -->

## Bức tranh tổng thể

Sau khi đã kết nối remote ở [Bài 6](/zola/posting/git-remote-lam-viec-voi-repository-tu-xa/), việc đồng bộ diễn ra theo hai chiều:

- **Lên remote**: `git push` — đẩy commit của bạn lên GitHub.
- **Về máy**: `git fetch` và `git pull` — lấy thay đổi của người khác về.

Hãy hình dung remote là "bảng tin chung", còn máy bạn là "bản nháp riêng". Bạn push để đăng lên bảng tin, pull để cập nhật những gì người khác đã đăng.

## git push — đẩy commit lên GitHub

```bash
git push -u origin main
```

Lần đầu, tham số `-u` (viết tắt của `--set-upstream`) thiết lập nhánh `main` local theo dõi `origin/main`. Từ lần sau, bạn chỉ cần:

```bash
git push
```

Theo [tài liệu git push](https://git-scm.com/docs/git-push), lệnh này chỉ đẩy các commit đã có trên máy — nên nhớ luôn `git commit` trước khi push.

## git fetch — xem trước, chưa gộp

`git fetch` tải về mọi commit, nhánh mới từ remote, nhưng **không** đụng vào nhánh làm việc của bạn:

```bash
git fetch origin
git log origin/main --oneline
```

Sau fetch, bạn có thể xem `origin/main` đã đi tới đâu trước khi quyết định gộp. Đây là cách an toàn nhất để biết người khác đã làm gì.

## git pull — fetch rồi merge

`git pull` là tổ hợp của hai bước: fetch về rồi merge ngay vào nhánh hiện tại:

```bash
git pull origin main
```

Tiện lợi, nhưng vì gộp ngay nên có thể phát sinh conflict cần xử lý (kỹ năng đã học ở [Bài 5](/zola/posting/git-merge-va-xu-ly-conflict/)). Một số người thích `git pull --rebase` để giữ lịch sử thẳng — chủ đề của [Bài 10 về rebase](/zola/posting/git-rebase-lam-sach-lich-su-commit/).

## So sánh nhanh ba lệnh

| Lệnh | Tải về remote? | Thay đổi nhánh local? |
|---|---|---|
| `git fetch` | Có | Không |
| `git pull` | Có | Có (merge ngay) |
| `git push` | Ngược lại (đẩy lên) | Không (đổi remote) |

## Luồng làm việc an toàn hằng ngày

Để tránh xung đột và ghi đè, hãy theo nhịp này:

1. `git pull` đầu buổi để cập nhật mới nhất.
2. Tạo nhánh tính năng, làm việc, commit.
3. `git pull` (hoặc fetch) lần nữa trước khi push nếu làm lâu.
4. `git push` để đẩy lên.
5. Mở Pull Request (Bài 9) thay vì push thẳng `main`.

Đây cũng đúng nguyên tắc của blog này: mọi thay đổi đi qua nhánh và Pull Request, không push trực tiếp lên `main`.

## Xử lý khi push bị từ chối

Thông báo `! [rejected] ... (fetch first)` nghĩa là remote có commit mới hơn. Cách xử lý đúng:

```bash
git pull --no-rebase origin main
git push
```

> ⚠️ **Tránh `git push --force`** trừ khi bạn thật sự hiểu — nó ghi đè lịch sử remote và có thể xóa việc của người khác. Nếu buộc phải force, hãy ưu tiên `--force-with-lease` an toàn hơn.

## Theo dõi nhánh (tracking branch) là gì?

Khi bạn chạy `git push -u origin main`, Git ghi nhớ rằng nhánh `main` local "theo dõi" `origin/main`. Nhờ vậy:

- `git status` cho biết bạn đang **đi trước** (ahead) hay **đi sau** (behind) remote bao nhiêu commit.
- `git push` và `git pull` không cần nêu lại tên remote và nhánh.

Bạn có thể xem quan hệ theo dõi bằng `git branch -vv`. Mỗi nhánh local có thể theo dõi một nhánh remote tương ứng, giúp Git biết đẩy đi đâu và kéo từ đâu — bớt gõ và bớt nhầm.

## Tóm lại

Bộ ba **git push** / `pull` / `fetch` là nhịp tim của làm việc với GitHub: push đẩy việc của bạn lên, fetch xem trước thay đổi của người khác, pull tải và gộp. Quy tắc vàng cho người mới: pull trước khi push, và đừng force khi chưa hiểu.

Ở **Bài 9**, chúng ta học quy trình cộng tác chuẩn của GitHub: [Pull Request và cách review code](/zola/posting/pull-request-quy-trinh-cong-tac-github/) — trái tim của làm việc nhóm hiện đại.
