+++
title = "Git remote: làm việc với repository từ xa"
description = "Git remote là gì, cách thêm origin, clone, xem và đổi remote, HTTPS vs SSH. Series Git & GitHub — Bài 6/15 cho người mới."
date = 2026-06-18
aliases = ["/git-remote-lam-viec-voi-repository-tu-xa/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "github", "git remote", "git github series", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "git remote"
featured = false
series = "git-github"
series_part = 6
series_total = 15

[[extra.faq]]
q = "Git remote là gì?"
a = "Git remote là một bản sao của repository nằm ở nơi khác — thường trên server như GitHub. Bạn dùng remote để đồng bộ code giữa máy cá nhân và đám mây, hoặc chia sẻ với cộng tác viên. Remote mặc định khi clone thường tên 'origin'."

[[extra.faq]]
q = "origin trong Git là gì?"
a = "origin là tên mặc định Git đặt cho remote mà bạn clone về. Đó chỉ là một cái tên gợi nhớ trỏ tới URL của repository từ xa; bạn có thể đổi tên hoặc thêm nhiều remote khác như upstream."
+++

> 📚 **Git & GitHub Series (Bài 6/15)** — Sau khi đã merge thành thạo ở [Bài 5](/zola/posting/git-merge-va-xu-ly-conflict/), bài này đưa Git ra khỏi máy cá nhân với **git remote**.

**Git remote** là cầu nối giữa repository trên máy bạn và một bản sao đặt ở nơi khác — thường là trên GitHub. Hiểu remote là bước bắt buộc trước khi đẩy code lên đám mây, cộng tác với người khác, hay deploy tự động. Bài này giải thích remote là gì, cách thêm và quản lý nó, cùng sự khác biệt giữa HTTPS và SSH.

<!-- more -->

## Vì sao cần git remote?

Cho tới giờ, mọi commit của bạn chỉ nằm trên máy cá nhân. Điều đó tốt cho việc lưu lịch sử, nhưng:

- Nếu máy hỏng, toàn bộ dự án mất theo.
- Không thể cộng tác với người khác.
- Không thể kích hoạt deploy tự động như [GitHub Actions deploy Zola](/zola/posting/tu-dong-deploy-zola-github-actions/).

**Remote** giải quyết tất cả: nó là một bản sao repository đặt trên server, để bạn đẩy (push) và kéo (pull) thay đổi qua lại.

## Clone một repository có sẵn

Cách nhanh nhất để bắt đầu với remote là **clone** một repo từ GitHub về:

```bash
git clone https://github.com/ten-user/ten-repo.git
```

Khi clone, Git tự động:

- Tải toàn bộ lịch sử về máy.
- Tạo một remote tên `origin` trỏ tới URL bạn vừa clone.
- Checkout nhánh mặc định (thường là `main`).

Theo [tài liệu Git về remote](https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes), `origin` chỉ là tên quy ước, không có gì đặc biệt — bạn hoàn toàn có thể đổi.

## Thêm git remote vào repo đã có sẵn

Nếu bạn đã `git init` một dự án trên máy và muốn kết nối nó với GitHub:

```bash
git remote add origin git@github.com:ten-user/ten-repo.git
git remote -v
```

Lệnh `git remote -v` liệt kê mọi remote kèm URL (fetch và push). Đây là cách kiểm tra repo đang trỏ đi đâu.

## Quản lý remote

| Lệnh | Tác dụng |
|---|---|
| `git remote -v` | Xem danh sách remote và URL |
| `git remote add <tên> <url>` | Thêm remote mới |
| `git remote rename origin upstream` | Đổi tên remote |
| `git remote remove <tên>` | Xóa remote |
| `git remote set-url origin <url-mới>` | Đổi URL (ví dụ chuyển HTTPS sang SSH) |

Trong các dự án mã nguồn mở, bạn thường có hai remote: `origin` (bản fork của bạn) và `upstream` (repo gốc) — kỹ thuật dùng nhiều khi đóng góp open source, bàn ở [Bài 9 về Pull Request](/zola/posting/pull-request-quy-trinh-cong-tac-github/).

## HTTPS hay SSH — chọn cách nào?

Có hai dạng URL remote tới GitHub:

- **HTTPS**: `https://github.com/user/repo.git` — dễ bắt đầu, nhưng cần nhập Personal Access Token khi push.
- **SSH**: `git@github.com:user/repo.git` — cần thiết lập khóa một lần (đã hướng dẫn ở [Bài 2](/zola/posting/cai-dat-git-cau-hinh-lan-dau/)), sau đó push/pull không cần nhập gì.

Với người dùng thường xuyên, SSH tiện hơn. Bạn có thể chuyển bất cứ lúc nào bằng `git remote set-url`.

## Đồng bộ với remote (xem trước Bài 8)

Sau khi có remote, ba thao tác đồng bộ cốt lõi là:

- `git fetch` — tải dữ liệu mới từ remote về nhưng **chưa** gộp.
- `git pull` — fetch rồi merge vào nhánh hiện tại.
- `git push` — đẩy commit của bạn lên remote.

Ba lệnh này sẽ được mổ xẻ chi tiết ở [Bài 8: push, pull, fetch](/zola/posting/push-pull-fetch-dong-bo-voi-github/). Ở bài này, bạn chỉ cần hiểu remote là "đích đến" mà chúng hướng tới.

## Lỗi remote thường gặp

- **`remote origin already exists`**: bạn đã có `origin`, hãy dùng `git remote set-url origin <url>` để đổi thay vì add lại.
- **`Permission denied (publickey)`**: dùng URL SSH nhưng chưa thêm khóa vào GitHub.
- **`Repository not found`**: sai URL, hoặc repo private mà bạn chưa có quyền truy cập.
- **`failed to push some refs`**: remote có commit mới hơn máy bạn — hãy `git pull` trước rồi push lại (xem Bài 8).

Khi nghi ngờ, luôn chạy `git remote -v` để xác nhận URL, và `git fetch` để xem remote có gì mới trước khi thao tác sâu hơn.

## Tóm lại

**Git remote** là bản sao repository ở nơi khác, kết nối máy bạn với đám mây. Bạn clone để lấy repo có sẵn (kèm `origin` tự tạo), hoặc `git remote add` để gắn dự án cũ với GitHub, và chọn HTTPS hay SSH tùy nhu cầu. Đây là nền tảng cho mọi thao tác cộng tác.

Ở **Bài 7**, chúng ta chính thức bước vào thế giới [GitHub: tạo tài khoản và repository đầu tiên](/zola/posting/github-la-gi-tao-repository-dau-tien/) — nơi remote của bạn sẽ "sống".
