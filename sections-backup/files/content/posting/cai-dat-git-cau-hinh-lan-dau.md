+++
title = "Cài đặt Git và cấu hình lần đầu (Windows, macOS, Linux)"
description = "Hướng dẫn cài đặt Git trên Windows, macOS, Linux và cấu hình lần đầu: user.name, user.email, SSH. Series Git & GitHub — Bài 2/15."
date = 2026-06-18
aliases = ["/cai-dat-git-cau-hinh-lan-dau/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["cài đặt git", "git", "git github series", "github", "lập trình"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "cài đặt git"
featured = false
series = "git-github"
series_part = 2
series_total = 15

[[extra.faq]]
q = "Cài đặt Git trên Windows như thế nào?"
a = "Tải bộ cài tại git-scm.com, chạy file .exe và giữ phần lớn tùy chọn mặc định (Git Bash, dùng main làm nhánh mặc định). Sau khi cài, mở Git Bash và gõ git --version để kiểm tra."

[[extra.faq]]
q = "Lệnh cấu hình Git lần đầu là gì?"
a = "Hai lệnh bắt buộc: git config --global user.name \"Tên của bạn\" và git config --global user.email \"email@cua-ban.com\". Đây là thông tin gắn vào mỗi commit."

[[extra.faq]]
q = "Có cần cấu hình SSH cho GitHub không?"
a = "Không bắt buộc khi mới học, nhưng nên có. SSH giúp push/pull lên GitHub mà không phải nhập mật khẩu/token mỗi lần. Bạn tạo khóa bằng ssh-keygen rồi thêm khóa công khai vào GitHub."
+++

> 📚 **Git & GitHub Series (Bài 2/15)** — Sau khi đã hiểu [Git là gì ở Bài 1](/posting/git-la-gi-version-control-cho-nguoi-moi/), bài này hướng dẫn **cài đặt Git** và cấu hình lần đầu để sẵn sàng commit.

**Cài đặt Git** chỉ mất vài phút trên mọi hệ điều hành, nhưng bước **cấu hình lần đầu** mới là phần nhiều người bỏ sót — dẫn đến commit bị ghi sai tên, sai email, hoặc gặp lỗi xuống dòng (line ending) trên Windows. Bài này đi qua đầy đủ: cài Git trên Windows, macOS, Linux, thiết lập danh tính, và chuẩn bị khóa SSH để kết nối GitHub về sau.

<!-- more -->

## Cài đặt Git trên từng hệ điều hành

### Windows

Cách phổ biến nhất là tải bộ cài chính thức tại [git-scm.com](https://git-scm.com/download/win):

1. Tải file `.exe` và chạy.
2. Giữ các tùy chọn mặc định, đặc biệt là cài kèm **Git Bash** — một terminal giống Linux rất tiện trên Windows.
3. Ở bước chọn nhánh mặc định, nên chọn **main** thay vì `master`.
4. Hoàn tất, mở **Git Bash** từ menu Start.

Ngoài ra bạn có thể dùng `winget install --id Git.Git` nếu thích dòng lệnh.

### macOS

Cách nhanh nhất là qua [Homebrew](https://brew.sh):

```bash
brew install git
```

Hoặc gõ `git --version` — nếu chưa có, macOS sẽ gợi ý cài Command Line Tools của Xcode kèm Git.

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install git
```

Với Fedora dùng `sudo dnf install git`, với Arch dùng `sudo pacman -S git`.

## Kiểm tra cài đặt thành công

Mở terminal (hoặc Git Bash trên Windows) và gõ:

```bash
git --version
```

Nếu thấy dòng kiểu `git version 2.45.0`, bạn đã cài đặt Git thành công. Phiên bản cụ thể không quan trọng, miễn là từ 2.x trở lên.

## Cấu hình Git lần đầu — bước không thể bỏ qua

Mỗi commit trong Git đều gắn **tên** và **email** của người tạo. Bạn cần khai báo một lần (dùng `--global` để áp dụng cho mọi repo trên máy):

```bash
git config --global user.name "Nguyen Van A"
git config --global user.email "vana@example.com"
```

> ⚠️ Email này nên trùng với email tài khoản GitHub để commit được liên kết đúng với hồ sơ của bạn về sau (sẽ dùng ở [Bài 7](/posting/github-la-gi-tao-repository-dau-tien/)).

### Các cấu hình nên thiết lập thêm

| Lệnh | Tác dụng |
|---|---|
| `git config --global init.defaultBranch main` | Đặt `main` làm nhánh mặc định khi `git init` |
| `git config --global core.editor "code --wait"` | Dùng VS Code làm trình soạn thông điệp commit |
| `git config --global pull.rebase false` | Mặc định merge khi `git pull` (an toàn cho người mới) |

### Xử lý line ending (rất quan trọng trên Windows)

Windows dùng ký tự xuống dòng khác Linux/macOS, dễ gây "toàn bộ file bị đánh dấu thay đổi". Cấu hình:

- Windows: `git config --global core.autocrlf true`
- macOS/Linux: `git config --global core.autocrlf input`

## Xem lại toàn bộ cấu hình

Để kiểm tra những gì đã thiết lập:

```bash
git config --list
```

Bạn sẽ thấy `user.name`, `user.email` và các giá trị khác. File cấu hình toàn cục nằm ở `~/.gitconfig` — bạn có thể mở và sửa trực tiếp nếu muốn.

## Chuẩn bị khóa SSH cho GitHub

Khi push code lên GitHub, bạn cần xác thực. Có hai cách: HTTPS (nhập token) hoặc **SSH** (dùng cặp khóa, không cần nhập gì sau khi thiết lập). SSH tiện hơn về lâu dài:

```bash
# 1. Tạo cặp khóa mới (nhấn Enter qua các bước)
ssh-keygen -t ed25519 -C "vana@example.com"

# 2. In khóa công khai ra để copy
cat ~/.ssh/id_ed25519.pub
```

Sau đó vào GitHub → **Settings → SSH and GPG keys → New SSH key**, dán nội dung khóa công khai vào. Kiểm tra kết nối:

```bash
ssh -T git@github.com
```

Nếu thấy lời chào `Hi <username>!` nghĩa là thành công. Chúng ta sẽ dùng SSH thật sự khi [làm việc với remote ở Bài 6](/posting/git-remote-lam-viec-voi-repository-tu-xa/).

## Những lỗi cấu hình thường gặp

- **Commit hiện sai tên/email**: do quên chạy `git config user.name/email`, hoặc đặt nhầm ở cấp local thay vì global.
- **`Permission denied (publickey)`** khi push: chưa thêm khóa SSH vào GitHub, hoặc thêm nhầm khóa riêng thay vì khóa `.pub`.
- **Toàn bộ file báo thay đổi trên Windows**: chưa cấu hình `core.autocrlf`.

## Tóm lại

Sau **cài đặt Git** và cấu hình lần đầu, máy bạn đã sẵn sàng quản lý phiên bản: Git đã được cài, danh tính (`user.name`, `user.email`) đã khai báo, line ending đã xử lý, và khóa SSH đã chuẩn bị cho GitHub. Đây là nền móng cho mọi bài thực hành tiếp theo.

Ở **Bài 3**, chúng ta sẽ tạo repository đầu tiên và thực hành [các lệnh Git cơ bản: init, add, commit, status, log](/posting/lenh-git-co-ban-init-add-commit-status/) — bắt đầu ghi lại lịch sử dự án thật sự. Nếu chưa đọc nền tảng, hãy quay lại [Bài 1: Git là gì](/posting/git-la-gi-version-control-cho-nguoi-moi/).
