+++
title = "GitHub Actions: CI/CD tự động hóa cho người mới"
description = "GitHub Actions là gì, workflow, job, step, trigger và ví dụ CI/CD đầu tiên để build, test, deploy tự động. Series Git & GitHub — Bài 14/15."
date = 2026-06-18
aliases = ["/github-actions-ci-cd-cho-nguoi-moi/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "git", "git github series", "github", "github actions"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "github actions"
featured = false
series = "git-github"
series_part = 14
series_total = 15

[[extra.faq]]
q = "GitHub Actions là gì?"
a = "GitHub Actions là nền tảng tự động hóa CI/CD tích hợp sẵn trong GitHub. Nó cho phép bạn chạy các quy trình tự động (build, test, deploy) khi có sự kiện như push hay pull request, định nghĩa bằng file YAML trong thư mục .github/workflows."

[[extra.faq]]
q = "CI/CD nghĩa là gì?"
a = "CI (Continuous Integration) là tích hợp liên tục: tự động build và test mỗi khi có thay đổi. CD (Continuous Delivery/Deployment) là phát hành liên tục: tự động đưa code đã qua kiểm tra lên môi trường chạy thật."

[[extra.faq]]
q = "GitHub Actions có miễn phí không?"
a = "Có hạn mức miễn phí rộng rãi: repository công khai dùng Actions gần như không giới hạn, repository riêng tư có hạn mức phút chạy hằng tháng tùy gói. Đủ dùng thoải mái cho cá nhân và dự án nhỏ."
+++

> 📚 **Git & GitHub Series (Bài 14/15)** — Sau khi chọn được [git workflow ở Bài 13](/posting/git-workflow-chuyen-nghiep-gitflow-github-flow/), giờ ta tự động hóa nó bằng **GitHub Actions**.

**GitHub Actions** là công cụ CI/CD tích hợp sẵn trong GitHub, giúp bạn tự động build, test và deploy mỗi khi có thay đổi — không cần dịch vụ bên ngoài. Chính blog này được build và phát hành lên GitHub Pages hoàn toàn tự động nhờ Actions. Bài này giải thích các khái niệm cốt lõi và dựng workflow CI/CD đầu tiên của bạn, từng dòng.

<!-- more -->

## GitHub Actions là gì và CI/CD để làm gì?

[GitHub Actions](https://docs.github.com/en/actions) cho phép định nghĩa các quy trình tự động chạy trên máy chủ của GitHub khi xảy ra sự kiện (push, pull request, theo lịch…). Lợi ích:

- **CI (tích hợp liên tục)**: mỗi push tự động chạy test/build, phát hiện lỗi sớm.
- **CD (phát hành liên tục)**: code qua kiểm tra được tự động deploy.
- Bớt thao tác thủ công, giảm sai sót con người, tăng tốc độ giao hàng.

## Các khái niệm cốt lõi

Một quy trình GitHub Actions gồm các tầng:

| Khái niệm | Ý nghĩa |
|---|---|
| **Workflow** | Một quy trình tự động, định nghĩa trong file `.yml` |
| **Event (trigger)** | Sự kiện kích hoạt: `push`, `pull_request`, `schedule`… |
| **Job** | Một nhóm bước chạy trên cùng một máy ảo (runner) |
| **Step** | Một bước trong job: chạy lệnh hoặc dùng action có sẵn |
| **Action** | Khối tái sử dụng, ví dụ `actions/checkout` để lấy code |

## Workflow đầu tiên: chạy test khi push

File workflow nằm trong `.github/workflows/`. Ví dụ một CI đơn giản cho dự án Node.js:

```yaml
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm install
      - run: npm test
```

Giải thích nhanh: workflow tên `CI`, kích hoạt khi push lên `main` hoặc khi có pull request. Nó chạy trên Ubuntu, checkout code, cài Node 20, cài dependency rồi chạy test. Commit file này vào repo là Actions tự chạy ngay.

## Thêm bước deploy (CD)

Sau khi test xanh, bạn có thể nối thêm job deploy. Đây cũng là mô hình blog này dùng: build site tĩnh rồi đẩy lên GitHub Pages. Bạn có thể đọc chi tiết thực tế ở bài [tự động deploy Zola bằng GitHub Actions](/posting/tu-dong-deploy-zola-github-actions/), nơi mỗi PR merge vào `main` sẽ kích hoạt build và phát hành sản xuất.

## Secrets — đừng bao giờ hardcode

Khi workflow cần token hay mật khẩu (ví dụ key deploy), **không** viết thẳng vào file YAML. Hãy lưu trong **Settings → Secrets and variables → Actions**, rồi dùng:

```yaml
      - run: ./deploy.sh
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
```

Đây là nguyên tắc bảo mật quan trọng, sẽ được nhấn mạnh ở [Bài 15](/posting/bao-mat-best-practices-git-github/).

## Ma trận (matrix) — test trên nhiều phiên bản

Một sức mạnh nữa của GitHub Actions là chạy cùng một job trên nhiều cấu hình song song bằng `strategy.matrix`. Ví dụ test trên ba phiên bản Node cùng lúc:

```yaml
    strategy:
      matrix:
        node-version: [ 18, 20, 22 ]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm test
```

Thay vì viết ba job riêng, matrix tự nhân bản job cho từng giá trị. Cách này giúp bạn phát hiện sớm lỗi chỉ xuất hiện trên một phiên bản cụ thể, mà vẫn giữ file workflow gọn gàng.

## Mẹo cho người mới

- Xem kết quả ở tab **Actions** của repo; mỗi lần chạy có log chi tiết từng step.
- Bắt đầu nhỏ: chỉ một job test, rồi mở rộng dần.
- Tận dụng Marketplace: hàng nghìn action dựng sẵn cho mọi nhu cầu.
- Dùng `workflow_dispatch` để có thể bấm chạy thủ công khi cần.

## Tóm lại

**GitHub Actions** đưa CI/CD vào ngay trong repository: định nghĩa workflow bằng YAML, kích hoạt theo sự kiện, chạy job gồm các step để build, test, deploy tự động. Chỉ với một file nhỏ, bạn biến mỗi commit thành một quy trình kiểm tra và phát hành đáng tin cậy.

Bài cuối — **Bài 15** — khép lại series với những điều quan trọng nhất về [bảo mật và best practices với Git/GitHub](/posting/bao-mat-best-practices-git-github/).
