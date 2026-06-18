+++
title = "Lệnh Git cơ bản: init, add, commit, status, log"
description = "Học các lệnh Git cơ bản qua thực hành: git init, add, commit, status, log, diff. Series Git & GitHub — Bài 3/15 cho người mới."
date = 2026-06-18
aliases = ["/lenh-git-co-ban-init-add-commit-status/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "github", "lệnh git", "git github series", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "lệnh git cơ bản"
featured = false
series = "git-github"
series_part = 3
series_total = 15

[[extra.faq]]
q = "Các lệnh Git cơ bản nhất cần nhớ là gì?"
a = "Năm lệnh nền tảng: git init (khởi tạo repo), git add (đưa thay đổi vào staging), git commit (lưu snapshot), git status (xem trạng thái), git log (xem lịch sử). Nắm năm lệnh này là đủ làm việc hằng ngày."

[[extra.faq]]
q = "git add . và git add -A khác nhau thế nào?"
a = "git add . thêm các thay đổi trong thư mục hiện tại trở xuống. git add -A thêm mọi thay đổi trong toàn repo, kể cả file bị xóa ở thư mục khác. Với Git 2.x, hai lệnh gần như tương đương khi chạy ở thư mục gốc."

[[extra.faq]]
q = "Làm sao viết commit message tốt?"
a = "Dòng đầu ngắn gọn (dưới 50 ký tự), dùng động từ mệnh lệnh như 'Thêm', 'Sửa', 'Xóa', mô tả 'làm gì'. Nếu cần chi tiết, để trống một dòng rồi viết phần thân giải thích 'vì sao'."
+++

> 📚 **Git & GitHub Series (Bài 3/15)** — Đã [cài đặt Git ở Bài 2](/zola/posting/cai-dat-git-cau-hinh-lan-dau/), giờ là lúc thực hành **các lệnh Git cơ bản** để ghi lại lịch sử dự án thật sự.

Nắm vững **lệnh Git cơ bản** là bước biến lý thuyết ở [Bài 1 về version control](/zola/posting/git-la-gi-version-control-cho-nguoi-moi/) thành kỹ năng thực tế. Chỉ với năm lệnh — `init`, `add`, `commit`, `status`, `log` — bạn đã có thể quản lý phiên bản cho bất kỳ dự án nào. Bài này hướng dẫn từng bước qua một ví dụ chạy thật, kèm `diff` và cách viết commit message chuẩn.

<!-- more -->

## Tạo repository với git init

Mở terminal, tạo một thư mục dự án và khởi tạo Git:

```bash
mkdir du-an-dau-tien
cd du-an-dau-tien
git init
```

Lệnh [`git init`](https://git-scm.com/docs/git-init) tạo một thư mục ẩn `.git` chứa toàn bộ cơ sở dữ liệu phiên bản. Từ giờ Git sẽ theo dõi mọi thay đổi trong thư mục này. Bạn chỉ chạy `git init` **một lần** cho mỗi dự án.

## Kiểm tra trạng thái với git status

Tạo một file rồi xem Git nói gì:

```bash
echo "# Dự án đầu tiên" > README.md
git status
```

Git báo `README.md` đang là **Untracked** (chưa được theo dõi). Lệnh `git status` là lệnh bạn sẽ gõ nhiều nhất — nó cho biết file nào đã sửa, file nào đang ở staging, nhánh hiện tại. Khi bối rối, cứ `git status`.

## Đưa thay đổi vào staging với git add

Nhớ lại mô hình ba khu vực ở Bài 1: để commit, trước hết phải đưa thay đổi vào **staging area**:

```bash
git add README.md
```

Một vài biến thể hữu ích:

- `git add .` — thêm mọi thay đổi từ thư mục hiện tại.
- `git add -A` — thêm mọi thay đổi trong toàn repo.
- `git add -p` — thêm **từng phần** của file (xét duyệt từng đoạn), rất hữu ích khi muốn tách commit gọn gàng.

## Lưu snapshot với git commit

Khi đã staging xong, lưu lại thành một mốc lịch sử:

```bash
git commit -m "Thêm README cho dự án"
```

Tham số `-m` truyền thông điệp commit trực tiếp. Mỗi commit được Git gán một mã băm SHA duy nhất (ví dụ `a1b2c3d`), gắn tên/email bạn đã cấu hình ở Bài 2, và thời gian.

### Cách viết commit message tốt

| Nên | Không nên |
|---|---|
| `Sửa lỗi tính tổng giỏ hàng` | `fix` |
| `Thêm trang liên hệ` | `update code` |
| `Xóa file cấu hình thừa` | `asdfgh` |

Quy ước phổ biến: dòng đầu dưới 50 ký tự, dùng động từ mệnh lệnh, mô tả "làm gì". Một lịch sử commit rõ ràng là tài sản quý khi cần truy vết lỗi.

## Xem thay đổi với git diff

Trước khi commit, bạn thường muốn xem mình đã sửa gì:

```bash
git diff            # thay đổi chưa staging
git diff --staged   # thay đổi đã staging, chuẩn bị commit
```

Dòng bắt đầu bằng `+` là nội dung thêm vào, `-` là nội dung bị xóa. Đọc `diff` thành thạo giúp bạn không commit nhầm.

## Xem lịch sử với git log

Để xem toàn bộ các commit đã tạo:

```bash
git log
git log --oneline          # gọn, mỗi commit một dòng
git log --oneline --graph  # hiển thị dạng cây nhánh
```

`git log --oneline` là dạng tôi dùng nhiều nhất — nó cho cái nhìn nhanh về lịch sử. Mỗi dòng gồm mã SHA rút gọn và thông điệp commit.

## Luồng làm việc với lệnh Git cơ bản hằng ngày

Gộp lại, vòng lặp công việc điển hình với Git là:

1. Sửa file trong dự án.
2. `git status` — xem mình đã đụng vào gì.
3. `git diff` — xem chi tiết thay đổi.
4. `git add <file>` — chọn thay đổi đưa vào commit.
5. `git commit -m "..."` — lưu lại.
6. Lặp lại.

Đây chính là nhịp điệu bạn lặp đi lặp lại mỗi ngày khi lập trình — kể cả khi viết một bài blog tĩnh như [blog tạo bằng Zola](/zola/posting/tao-blog-voi-zola/).

## File .gitignore — bỏ qua những thứ không cần

Không phải file nào cũng nên đưa vào Git (ví dụ thư mục `node_modules`, file bí mật, file build). Tạo file `.gitignore` ở gốc dự án:

```
node_modules/
.env
*.log
dist/
```

Git sẽ tự động bỏ qua các đường dẫn này. Đây là thói quen quan trọng để không vô tình commit dữ liệu nhạy cảm — chủ đề chúng ta sẽ đào sâu ở [Bài 15 về bảo mật](/zola/posting/bao-mat-best-practices-git-github/).

## Tóm lại

Bạn vừa nắm trọn vòng đời cơ bản của **lệnh Git cơ bản**: `init` để khởi tạo, `status`/`diff` để quan sát, `add` để chuẩn bị, `commit` để lưu, và `log` để xem lại. Đây là 80% công việc Git hằng ngày.

Ở **Bài 4**, chúng ta bước sang một sức mạnh thật sự của Git: [làm việc với branch (nhánh)](/zola/posting/git-branch-lam-viec-voi-nhanh/) — cách phát triển nhiều tính năng song song mà không giẫm chân nhau.
