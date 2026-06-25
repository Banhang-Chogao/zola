+++
title = "GitHub là gì? Tạo tài khoản và repository đầu tiên"
description = "GitHub là gì, vì sao phổ biến nhất thế giới, cách tạo tài khoản và repository đầu tiên từng bước. Series Git & GitHub — Bài 7/15."
date = 2026-06-18
aliases = ["/github-la-gi-tao-repository-dau-tien/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "git github series", "github", "github là gì", "lập trình"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "github là gì"
featured = false
series = "git-github"
series_part = 7
series_total = 15

[[extra.faq]]
q = "GitHub là gì?"
a = "GitHub là nền tảng lưu trữ mã nguồn trực tuyến dựa trên Git, do Microsoft sở hữu. Ngoài việc host repository, GitHub cung cấp Pull Request, Issues, review code, Actions (CI/CD) và là mạng xã hội lập trình viên lớn nhất thế giới."

[[extra.faq]]
q = "GitHub có miễn phí không?"
a = "Có. GitHub cho phép tạo không giới hạn repository công khai và riêng tư miễn phí, kèm CI/CD qua GitHub Actions với hạn mức rộng rãi. Các gói trả phí thêm tính năng cho doanh nghiệp và bảo mật nâng cao."

[[extra.faq]]
q = "README.md trong repository GitHub để làm gì?"
a = "README.md là file giới thiệu hiển thị ngay trên trang chủ repository. Nó mô tả dự án là gì, cách cài đặt và sử dụng. Một README tốt là ấn tượng đầu tiên với người ghé thăm dự án của bạn."
+++

> 📚 **Git & GitHub Series (Bài 7/15)** — Đã nắm [git remote ở Bài 6](/git-remote-lam-viec-voi-repository-tu-xa/), giờ ta chính thức bước vào **GitHub** — nơi remote của bạn sẽ sống.

**GitHub là gì?** Đó là nền tảng lưu trữ và cộng tác mã nguồn phổ biến nhất thế giới, với hàng trăm triệu repository và lập trình viên. Nếu Git là động cơ quản lý phiên bản chạy trên máy bạn, thì GitHub là "ngôi nhà chung" trên đám mây để lưu trữ, chia sẻ và làm việc nhóm. Bài này giải thích GitHub là gì, vì sao nó thống trị, rồi hướng dẫn tạo tài khoản và repository đầu tiên.

<!-- more -->

## GitHub là gì và vì sao phổ biến nhất thế giới

[GitHub](https://github.com) ra đời năm 2008, được Microsoft mua lại năm 2018. Nó xây trên nền Git nhưng bổ sung cả một hệ sinh thái:

- **Lưu trữ repository** công khai và riêng tư trên đám mây.
- **Pull Request** — quy trình đề xuất và review thay đổi (Bài 9).
- **Issues** — theo dõi lỗi và nhiệm vụ.
- **GitHub Actions** — tự động hóa CI/CD (Bài 14).
- **GitHub Pages** — host website tĩnh miễn phí, chính là cách blog này được xuất bản.

Sự phổ biến của GitHub đến từ hiệu ứng mạng: hầu hết dự án mã nguồn mở lớn (Linux, React, VS Code…) đều ở đây, nên đây cũng là nơi lập trình viên xây dựng hồ sơ cá nhân.

## Git và GitHub — đừng nhầm lẫn

Nhắc lại từ [Bài 1](/git-la-gi-version-control-cho-nguoi-moi/) vì đây là điểm gây nhầm nhất:

| | Git | GitHub |
|---|---|---|
| Bản chất | Phần mềm trên máy bạn | Dịch vụ trực tuyến |
| Hoạt động offline | Có | Không (cần mạng) |
| Sở hữu | Mã nguồn mở | Microsoft |
| Thay thế bằng | Mercurial… | GitLab, Bitbucket… |

Bạn dùng Git để tạo commit; dùng GitHub để lưu trữ và cộng tác trên các commit đó.

## Tạo tài khoản GitHub

1. Vào [github.com](https://github.com) và bấm **Sign up**.
2. Nhập email, đặt mật khẩu mạnh và chọn **username** — nên chuyên nghiệp vì nó xuất hiện trong mọi URL dự án.
3. Xác minh email.
4. **Bật xác thực hai lớp (2FA)** ngay trong Settings → đây là yêu cầu bảo mật quan trọng, sẽ bàn kỹ ở [Bài 15](/bao-mat-best-practices-git-github/).

## Tạo repository đầu tiên

Sau khi đăng nhập:

1. Bấm dấu **+** góc trên phải → **New repository**.
2. Đặt **Repository name** (ví dụ `du-an-dau-tien`).
3. Chọn **Public** (ai cũng xem được) hoặc **Private** (chỉ bạn và người được mời).
4. Tick **Add a README file** để repo có nội dung ban đầu.
5. Bấm **Create repository**.

Vậy là bạn đã có một repository trên GitHub — chính là **remote** mà Bài 6 nói tới.

## Kết nối repo trên máy với GitHub

Nếu bạn đã có dự án local từ [Bài 3](/lenh-git-co-ban-init-add-commit-status/), hãy kết nối nó:

```bash
git remote add origin git@github.com:ten-user/du-an-dau-tien.git
git branch -M main
git push -u origin main
```

Lệnh `push -u` đẩy code lên và thiết lập nhánh theo dõi, để lần sau chỉ cần `git push`. Chi tiết về push sẽ ở [Bài 8](/push-pull-fetch-dong-bo-voi-github/).

## Viết README.md ấn tượng

`README.md` là file đầu tiên người ta thấy. Một README tốt nên có:

- Tên và mô tả ngắn dự án làm gì.
- Hướng dẫn cài đặt và chạy.
- Ví dụ sử dụng.
- Giấy phép (license) nếu là mã nguồn mở.

README dùng cú pháp **Markdown** — cùng ngôn ngữ định dạng mà bài blog này đang dùng, nên rất dễ học.

## Tóm lại

**GitHub là gì?** — Là nền tảng lưu trữ và cộng tác mã nguồn dựa trên Git, phổ biến nhất thế giới, miễn phí cho phần lớn nhu cầu. Bạn vừa tạo tài khoản, bật 2FA, tạo repository đầu tiên và kết nối nó với máy của mình. Đây là bệ phóng cho mọi tính năng cộng tác phía sau.

Ở **Bài 8**, chúng ta đi sâu vào ba thao tác đồng bộ cốt lõi: [push, pull và fetch để đồng bộ code với GitHub](/push-pull-fetch-dong-bo-voi-github/).
