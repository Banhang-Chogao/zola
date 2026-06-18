+++
title = "Git workflow chuyên nghiệp: Git Flow và GitHub Flow"
description = "So sánh Git Flow, GitHub Flow và Trunk-Based Development, quy ước đặt tên nhánh và commit. Series Git & GitHub — Bài 13/15."
date = 2026-06-18
aliases = ["/git-workflow-chuyen-nghiep-gitflow-github-flow/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "github", "git workflow", "git github series", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "git workflow"
featured = false
series = "git-github"
series_part = 13
series_total = 15

[[extra.faq]]
q = "Git workflow là gì?"
a = "Git workflow là quy ước về cách một nhóm dùng nhánh, commit và merge để phối hợp công việc. Các mô hình phổ biến gồm Git Flow, GitHub Flow và Trunk-Based Development, mỗi loại phù hợp quy mô và nhịp phát hành khác nhau."

[[extra.faq]]
q = "GitHub Flow khác Git Flow thế nào?"
a = "GitHub Flow đơn giản: chỉ có main và các nhánh tính năng ngắn hạn, merge qua Pull Request rồi deploy ngay — hợp triển khai liên tục. Git Flow phức tạp hơn với các nhánh develop, release, hotfix — hợp sản phẩm có chu kỳ phát hành rõ ràng."

[[extra.faq]]
q = "Conventional Commits là gì?"
a = "Conventional Commits là quy ước viết thông điệp commit có cấu trúc, dạng 'type(scope): mô tả', ví dụ feat(auth): thêm đăng nhập. Nó giúp tự động sinh changelog và đọc lịch sử dễ hơn."
+++

> 📚 **Git & GitHub Series (Bài 13/15)** — Đã thành thạo công cụ qua các bài trước, giờ ta học cách tổ chức chúng thành một **git workflow** chuyên nghiệp.

**Git workflow** là tập quy ước về cách cả nhóm dùng nhánh, commit và Pull Request để phối hợp mà không giẫm chân nhau. Cùng một bộ lệnh Git, nhưng cách tổ chức khác nhau sẽ quyết định dự án trơn tru hay hỗn loạn. Bài này so sánh ba mô hình phổ biến nhất — Git Flow, GitHub Flow, Trunk-Based — và quy ước đặt tên nhánh, commit chuẩn.

<!-- more -->

## Vì sao cần một git workflow rõ ràng?

Khi làm một mình, bạn có thể tùy hứng. Nhưng khi nhiều người cùng làm, thiếu quy ước dẫn tới: nhánh tên lung tung, commit khó đọc, merge rối, không biết bản nào đang chạy production. Một workflow tốt trả lời rõ:

- Nhánh nào là "nguồn chân lý" (thường là `main`)?
- Tính năng mới phát triển ở đâu, gộp về thế nào?
- Lỗi khẩn (hotfix) xử lý ra sao?
- Khi nào và làm sao để phát hành?

## GitHub Flow — đơn giản và phổ biến

[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow) là mô hình nhẹ, hợp với triển khai liên tục:

1. `main` luôn ở trạng thái phát hành được.
2. Tạo nhánh tính năng ngắn hạn từ `main`.
3. Commit, push, mở Pull Request (Bài 9).
4. Review + CI xanh → merge vào `main`.
5. Deploy ngay.

Đây chính là mô hình blog này áp dụng: mỗi thay đổi một nhánh, qua PR, CI xanh thì merge và [tự động deploy](/zola/posting/tu-dong-deploy-zola-github-actions/). Đơn giản, nhanh, ít nhánh dài hạn.

## Git Flow — bài bản cho sản phẩm có chu kỳ phát hành

Git Flow phức tạp hơn, dùng nhiều nhánh dài hạn và tạm thời:

| Nhánh | Vai trò |
|---|---|
| `main` | Code production đã phát hành |
| `develop` | Tích hợp tính năng đang phát triển |
| `feature/*` | Mỗi tính năng một nhánh, gộp vào `develop` |
| `release/*` | Chuẩn bị phát hành, sửa lỗi nhỏ |
| `hotfix/*` | Sửa khẩn trên production, gộp cả `main` và `develop` |

Git Flow phù hợp phần mềm đóng gói, có phiên bản rõ ràng (ví dụ ứng dụng desktop, mobile). Với web triển khai liên tục, nó thường quá nặng.

## Trunk-Based Development — cho tốc độ cao

Mô hình thứ ba được nhiều công ty lớn dùng: mọi người commit thường xuyên vào `main` (trunk), nhánh sống cực ngắn (vài giờ), dựa mạnh vào CI tự động và **feature flag** để giấu tính năng chưa xong. Nó tối ưu tốc độ tích hợp nhưng đòi hỏi kỷ luật test cao.

## So sánh nhanh ba mô hình

| Tiêu chí | GitHub Flow | Git Flow | Trunk-Based |
|---|---|---|---|
| Độ phức tạp | Thấp | Cao | Thấp–trung bình |
| Số nhánh dài hạn | 1 (`main`) | 2+ | 1 |
| Hợp với | Web, CI/CD | Sản phẩm có version | Đội lớn, tốc độ cao |
| Tần suất phát hành | Liên tục | Theo chu kỳ | Rất liên tục |

## Quy ước đặt tên nhánh và commit

Dù chọn workflow nào, quy ước nhất quán giúp lịch sử dễ đọc:

- **Tên nhánh**: `feature/ten-tinh-nang`, `fix/loi-gi-do`, `chore/cong-viec-vat`.
- **Conventional Commits**: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`. Quy ước này còn giúp tự sinh changelog.

Một thông điệp commit kiểu `feat(auth): thêm đăng nhập Google` ngay lập tức cho biết loại thay đổi, phạm vi và nội dung. Sự nhất quán nhỏ này tích lũy thành một lịch sử dự án sạch sẽ và dễ truy vết về sau.

## Tóm lại

**Git workflow** biến những lệnh rời rạc thành quy trình nhóm mạch lạc. GitHub Flow đơn giản hợp web và CI/CD; Git Flow bài bản cho sản phẩm có phiên bản; Trunk-Based cho tốc độ cao. Quan trọng nhất là cả nhóm **thống nhất một quy ước** và tuân thủ nó.

Ở **Bài 14**, chúng ta tự động hóa toàn bộ quy trình kiểm thử và phát hành với [GitHub Actions — CI/CD cho người mới](/zola/posting/github-actions-ci-cd-cho-nguoi-moi/).
