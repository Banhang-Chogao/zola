+++
title = "Pull Request và quy trình cộng tác trên GitHub"
description = "Pull Request là gì, cách tạo PR, review code, fork và đóng góp mã nguồn mở trên GitHub. Series Git & GitHub — Bài 9/15."
date = 2026-06-18
aliases = ["/pull-request-quy-trinh-cong-tac-github/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "github", "pull request", "git github series", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "pull request"
featured = false
series = "git-github"
series_part = 9
series_total = 15

[[extra.faq]]
q = "Pull Request là gì?"
a = "Pull Request (PR) là đề xuất gộp các thay đổi từ một nhánh vào nhánh khác trên GitHub. Nó là nơi đồng đội xem diff, thảo luận, review code và chạy CI trước khi merge — trái tim của quy trình cộng tác hiện đại."

[[extra.faq]]
q = "Fork khác clone thế nào?"
a = "Clone tạo bản sao repo về máy bạn. Fork tạo một bản sao repo trên tài khoản GitHub của bạn từ repo của người khác — dùng khi bạn muốn đóng góp cho dự án mà không có quyền ghi trực tiếp."

[[extra.faq]]
q = "Nên dùng squash, merge hay rebase khi gộp PR?"
a = "Squash gộp mọi commit của PR thành một, cho lịch sử gọn. Merge commit giữ nguyên lịch sử và thêm điểm gộp. Rebase đưa commit lên thẳng main không tạo merge commit. Tùy quy ước nhóm; squash phổ biến cho blog/cá nhân."
+++

> 📚 **Git & GitHub Series (Bài 9/15)** — Đã biết đồng bộ ở [Bài 8](/zola/posting/push-pull-fetch-dong-bo-voi-github/), giờ ta học trái tim của cộng tác GitHub: **Pull Request**.

**Pull Request** (thường gọi tắt là PR) là tính năng làm nên tên tuổi GitHub. Thay vì đẩy thẳng code vào nhánh chính, bạn mở một PR để đề xuất thay đổi, để người khác xem diff, góp ý, và để hệ thống tự động kiểm tra (CI) chạy — rồi mới gộp. Bài này hướng dẫn tạo PR, review code, và quy trình fork để đóng góp mã nguồn mở.

<!-- more -->

## Pull Request là gì và vì sao quan trọng?

Theo [tài liệu GitHub về Pull Request](https://docs.github.com/en/pull-requests), PR là yêu cầu gộp commit từ một nhánh (nhánh nguồn) vào một nhánh khác (thường là `main`). Giá trị của nó không chỉ là "gộp", mà là cả một không gian cộng tác:

- Hiển thị **diff** rõ ràng giữa hai nhánh.
- Cho phép **review từng dòng** và để lại bình luận.
- Tự động chạy **CI/CD** (kiểm thử, build) trước khi merge — chủ đề [Bài 14](/zola/posting/github-actions-ci-cd-cho-nguoi-moi/).
- Lưu lại lý do và lịch sử thảo luận của mỗi thay đổi.

Blog này áp dụng đúng nguyên tắc đó: mọi thay đổi đều qua PR, không push thẳng `main`.

## Quy trình tạo Pull Request cơ bản

Giả sử bạn đã làm việc trên một nhánh tính năng (từ [Bài 4](/zola/posting/git-branch-lam-viec-voi-nhanh/)):

```bash
git switch -c feature/them-trang-gioi-thieu
git add .
git commit -m "Thêm trang giới thiệu"
git push -u origin feature/them-trang-gioi-thieu
```

Sau khi push, GitHub hiện nút **Compare & pull request**. Bấm vào, viết tiêu đề và mô tả rõ ràng (làm gì, vì sao, cách kiểm tra), rồi bấm **Create pull request**.

## Viết mô tả PR tốt

| Phần | Nội dung nên có |
|---|---|
| Tiêu đề | Ngắn gọn, kiểu `feat: thêm trang giới thiệu` |
| Mô tả | Thay đổi gì và vì sao |
| Cách test | Các bước để người review kiểm chứng |
| Ảnh chụp | Với thay đổi giao diện (nếu có) |

Mô tả tốt giúp người review hiểu nhanh và duyệt sớm hơn.

## Review code — văn hóa cộng tác

Khi review một PR, bạn có thể:

- Bình luận trên từng dòng cụ thể.
- Đề xuất chỉnh sửa trực tiếp (suggestion).
- Chọn **Approve**, **Request changes**, hoặc **Comment**.

Review tốt nên cụ thể, tôn trọng, tập trung vào code chứ không vào người. Đây là kỹ năng mềm quan trọng ngang với kỹ năng kỹ thuật.

## Ba cách gộp Pull Request

Khi PR được duyệt, GitHub cho ba lựa chọn merge:

- **Create a merge commit** — giữ nguyên mọi commit và thêm một merge commit.
- **Squash and merge** — gộp tất cả commit của PR thành một, lịch sử `main` gọn gàng.
- **Rebase and merge** — đưa từng commit lên thẳng `main`, không tạo merge commit.

Với blog cá nhân hoặc dự án nhỏ, **squash** thường gọn nhất. Khái niệm rebase sẽ được làm rõ ở [Bài 10](/zola/posting/git-rebase-lam-sach-lich-su-commit/).

## Fork và đóng góp mã nguồn mở

Khi muốn đóng góp cho dự án bạn không có quyền ghi:

1. **Fork** repo về tài khoản của bạn (nút Fork trên GitHub).
2. Clone bản fork về máy, thêm remote `upstream` trỏ repo gốc (nhắc lại [Bài 6](/zola/posting/git-remote-lam-viec-voi-repository-tu-xa/)).
3. Tạo nhánh, commit, push lên fork.
4. Mở PR từ fork của bạn tới repo gốc.

Đây chính là cách hàng triệu người đóng góp cho mã nguồn mở mỗi ngày.

## Tóm lại

**Pull Request** biến Git từ công cụ cá nhân thành nền tảng cộng tác: bạn đề xuất thay đổi qua nhánh, người khác review diff, CI kiểm tra tự động, rồi mới merge. Nắm PR và quy trình fork là bạn đã sẵn sàng làm việc nhóm và đóng góp mã nguồn mở chuyên nghiệp.

Từ bài sau, series bước sang phần **nâng cao**. **Bài 10** mở đầu với [git rebase — làm sạch lịch sử commit](/zola/posting/git-rebase-lam-sach-lich-su-commit/), một công cụ mạnh nhưng cần dùng đúng cách.
