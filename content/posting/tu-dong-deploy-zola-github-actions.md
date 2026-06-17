+++
title = "Deploy blog Zola lên GitHub Pages tự động"
description = "Cách viết deploy.yml để tự động build và deploy blog Zola lên GitHub Pages mỗi khi push: giải thích từng dòng workflow, phân quyền và xử lý lỗi."
date = 2026-06-16
aliases = ["/tu-dong-deploy-zola-github-actions/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci/cd", "deploy", "devops", "github actions", "github pages", "tutorial", "tự động hoá", "zola"]
[extra]
seo_keyword = "deploy Zola GitHub Pages"
thumbnail = "https://banhang-chogao.github.io/zola/img/covers/tu-dong-deploy-zola-github-actions.svg"
featured = false

[[extra.faq]]
q = "GitHub Actions có miễn phí không?"
a = "Có. Với repo công khai (public), GitHub Actions miễn phí không giới hạn phút chạy. Repo riêng tư cũng có hạn mức phút miễn phí hằng tháng, đủ thừa cho việc build một blog tĩnh."

[[extra.faq]]
q = "Deploy một blog Zola mất bao lâu?"
a = "Thường chỉ 30 giây đến hơn một phút: phần lớn thời gian là tải Zola và build, còn bước deploy lên GitHub Pages rất nhanh. Sau khi push, đợi một lát là trang cập nhật."

[[extra.faq]]
q = "Vì sao deploy xong mà CSS và ảnh bị lỗi (404)?"
a = "Gần như luôn do sai base_url trong config.toml. Với GitHub Pages dạng project page, base_url phải có đuôi /tên-repo. Sai đường dẫn này thì CSS, ảnh và link nội bộ đều gãy dù build thành công."

[[extra.faq]]
q = "Có cần nhánh gh-pages riêng không?"
a = "Không, nếu dùng cách deploy bằng GitHub Pages Actions (actions/deploy-pages). Cách này deploy thẳng artifact, không cần tạo và đẩy vào nhánh gh-pages như phương pháp cũ."
+++

Sau khi đã [tạo blog với Zola](/posting/tao-blog-voi-zola/), việc bạn muốn tiếp theo chắc chắn là: **mỗi lần viết bài xong, push lên là blog tự cập nhật** — không phải build tay, không phải kéo thả file. Bài này hướng dẫn viết file **`deploy.yml`** để **deploy Zola lên GitHub Pages** bằng GitHub Actions, **giải thích từng phần** để bạn hiểu chứ không chỉ copy.

## Cơ chế deploy Zola lên GitHub Pages

GitHub Actions là dịch vụ CI/CD tích hợp sẵn trong mọi repo GitHub. Ý tưởng:

1. Bạn `git push` lên nhánh `main`.
2. Một **workflow** tự kích hoạt: cài Zola → `zola build` → đẩy thư mục `public/` lên GitHub Pages.
3. Blog cập nhật sau khoảng một phút. Hoàn toàn tự động và miễn phí.

## File deploy.yml hoàn chỉnh

Tạo file `.github/workflows/deploy.yml` trong repo:

```yaml
name: Deploy
on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
      - name: Cài Zola
        run: |
          curl -sL https://github.com/getzola/zola/releases/download/v0.19.2/zola-v0.19.2-x86_64-unknown-linux-gnu.tar.gz | tar xz
          sudo mv zola /usr/local/bin/
      - name: Build
        run: zola build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

## Giải thích từng phần

### `on: push: branches: [main]`
Workflow chỉ chạy khi có commit đẩy lên nhánh `main`. Bạn có thể thêm `workflow_dispatch:` để bật nút "Run workflow" chạy tay khi cần.

### `permissions`
GitHub Pages dạng mới cần 3 quyền: `pages: write` (ghi lên Pages) và `id-token: write` (xác thực OIDC khi deploy). Thiếu các quyền này, bước deploy sẽ báo lỗi từ chối.

### `concurrency`
Nếu bạn push liên tiếp, nhóm `pages` đảm bảo chỉ một lần deploy chạy; `cancel-in-progress: true` hủy lần cũ để luôn deploy bản mới nhất, tránh "giẫm chân nhau".

### `submodules: true`
Quan trọng nếu theme của bạn được thêm dưới dạng git submodule. Quên dòng này, theme sẽ trống và trang vỡ giao diện.

### Bước cài Zola
Tải đúng phiên bản Zola (nên ghim số version để build ổn định, tránh bản mới đổi hành vi) rồi đưa vào `PATH`. Sau đó `zola build` sinh ra thư mục `public/`.

### `upload-pages-artifact` và `deploy-pages`
Hai action chính thức của GitHub: một cái đóng gói `public/` thành artifact, một cái deploy artifact đó lên Pages. **Không cần** nhánh `gh-pages` thủ công như cách cũ.

## Bật GitHub Pages

Vào **Settings → Pages** của repo, mục *Build and deployment* chọn **Source = GitHub Actions**. Từ đây mỗi lần push, blog tự lên sóng tại `https://<tên-github>.github.io/<repo>`.

## Mẹo tối ưu

- **Ghim version Zola** thay vì `latest` để build không gãy khi có bản mới.
- **Cache** thư mục tải Zola nếu muốn nhanh hơn (với blog nhỏ thì không cần).
- **Tách kiểm thử**: thêm một workflow QA chạy `zola check` hoặc script kiểm tra link/HTML trước khi deploy — đây chính là nền tảng của [QA Gatekeeper giúp blog tự fix lỗi 24/7](/posting/qa-gatekeeper-tu-fix-loi-blog/).

## Lỗi thường gặp

- **403 ở bước deploy** → thiếu `permissions` (pages/id-token).
- **Theme trống** → quên `submodules: true`.
- **CSS/ảnh 404** → sai `base_url` (thiếu đuôi `/repo`).
- **Trang không đổi** → Pages chưa chọn Source = GitHub Actions, hoặc workflow lỗi (xem tab Actions).

## Tên miền riêng và HTTPS

Khi pipeline đã chạy, bạn có thể gắn **tên miền riêng** thay cho đường `github.io`. Vào **Settings → Pages → Custom domain**, nhập domain của bạn rồi thêm bản ghi DNS trỏ về GitHub (CNAME tới `<tên-github>.github.io` cho subdomain, hoặc các A record cho apex domain). GitHub tự cấp **chứng chỉ HTTPS miễn phí** qua Let's Encrypt sau khi DNS xác thực — nhớ bật *Enforce HTTPS*. Một lưu ý nhỏ: khi đổi sang domain riêng, hãy cập nhật lại `base_url` trong `config.toml` cho khớp, nếu không CSS và link nội bộ sẽ trỏ sai.

Quy trình deploy bằng GitHub Actions ở trên bám sát [tài liệu GitHub Pages chính thức](https://docs.github.com/en/pages) và [hướng dẫn deploy Zola](https://www.getzola.org/documentation/deployment/github-pages/) — nếu workflow đổi hành vi sau này, hai nguồn đó luôn là chỗ kiểm chứng đầu tiên.

## Kết

Chỉ với một file YAML, bạn có pipeline **build và deploy tự động, miễn phí**. Đây là viên gạch đầu tiên để tiến tới tự động hoá toàn diện: kiểm thử tự động, tự sửa lỗi, thậm chí tự đăng bài.

Xem thêm: [tạo blog với Zola từ A–Z](/posting/tao-blog-voi-zola/) và [công nghệ vận hành một blog cá nhân $0/tháng](/posting/cong-nghe-blog-duy-nguyen/).
