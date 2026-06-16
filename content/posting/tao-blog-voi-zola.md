+++
title = "Tạo blog với Zola từ A–Z: deploy GitHub Pages"
description = "Hướng dẫn tạo blog cá nhân với Zola từ con số 0: cài đặt trên Windows/Mac/Linux, cấu trúc thư mục, viết bài Markdown, theme và deploy miễn phí lên GitHub Pages."
date = 2026-06-16

[taxonomies]
categories = ["Công nghệ"]
tags = ["zola", "static site generator", "github pages", "github actions", "blog", "rust", "markdown", "tutorial"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/covers/tao-blog-voi-zola.svg"
featured = true

[[extra.faq]]
q = "Zola là gì?"
a = "Zola là một static site generator (công cụ tạo trang tĩnh) viết bằng Rust, đóng gói thành một file thực thi duy nhất, không cần cài runtime. Nó biến file Markdown cùng template Tera thành các trang HTML tĩnh, build cực nhanh và host được miễn phí."

[[extra.faq]]
q = "Tạo blog với Zola có miễn phí không?"
a = "Có. Bản thân Zola là mã nguồn mở miễn phí; host trên GitHub Pages miễn phí; build tự động bằng GitHub Actions cũng miễn phí cho repo cá nhân. Bạn chỉ tốn tiền nếu muốn mua tên miền riêng, khoảng vài trăm nghìn đồng một năm."

[[extra.faq]]
q = "Zola và Hugo nên chọn cái nào?"
a = "Cả hai đều nhanh và là một file thực thi duy nhất. Zola dùng template Tera (cú pháp giống Jinja2, dễ đọc) và có sẵn Sass, tìm kiếm, syntax highlight tích hợp. Hugo nhiều theme và cộng đồng lớn hơn nhưng template Go khó hơn. Người mới thường thấy Zola gọn và dễ bắt đầu hơn."

[[extra.faq]]
q = "Cần biết lập trình để dùng Zola không?"
a = "Không cần biết lập trình sâu, nhưng bạn nên quen Markdown để viết bài và biết vài lệnh Git cơ bản để đẩy code lên GitHub. Nếu muốn tùy biến giao diện thì cần đọc thêm về template Tera và HTML/CSS."
+++

Bạn muốn có một blog **nhanh, miễn phí, gọn nhẹ** và toàn quyền kiểm soát — không phải lo cập nhật bảo mật WordPress, không phí hosting hằng tháng? Bài này hướng dẫn bạn **tạo blog với Zola từ con số 0**: từ cài đặt, viết bài, đến deploy lên GitHub Pages. Chính blog bạn đang đọc cũng chạy bằng Zola, nên đây là kinh nghiệm thực tế chứ không phải lý thuyết.

## Zola là gì?

**Zola là một static site generator (SSG) viết bằng Rust**, đóng gói thành **một file thực thi duy nhất** — tải về là chạy, không cần cài Node, Python hay Ruby. Nó nhận file **Markdown** + template **Tera** rồi sinh ra các trang **HTML tĩnh** sẵn sàng phục vụ.

Vì là trang tĩnh (không cần database hay server động), blog Zola:

- **Tải rất nhanh** — chỉ là HTML/CSS thuần.
- **Bảo mật cao** — không có database để bị tấn công.
- **Host miễn phí** — chạy được trên GitHub Pages, Netlify, Cloudflare Pages.
- **Tích hợp sẵn** Sass, tìm kiếm, syntax highlight, sitemap, RSS — không cần plugin.

> Muốn hiểu sâu hơn về stack vận hành một blog tĩnh thực tế (CMS mini, CI/CD, tự động hoá), đọc thêm bài [Tự xây blog cá nhân $0/tháng với Zola + GitHub Pages](/zola/posting/cong-nghe-blog-duy-nguyen/).

## Chuẩn bị

- Một tài khoản **GitHub** (miễn phí).
- **Git** cài sẵn trên máy.
- Một trình soạn thảo (VS Code khuyến nghị).

## Bước 1 — Cài đặt Zola

Zola chỉ là một file binary. Chọn theo hệ điều hành:

**macOS** (qua Homebrew):

```bash
brew install zola
```

**Windows** (qua Scoop hoặc Chocolatey):

```powershell
scoop install zola
# hoặc
choco install zola
```

**Linux** (tải binary từ GitHub Releases):

```bash
curl -sL https://github.com/getzola/zola/releases/download/v0.19.2/zola-v0.19.2-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv zola /usr/local/bin/
```

Kiểm tra cài đặt thành công:

```bash
zola --version
```

## Bước 2 — Khởi tạo site mới

```bash
zola init my-blog
```

Zola sẽ hỏi vài câu (URL site, có dùng Sass không, có compile search index không) — cứ Enter để dùng mặc định, sửa sau cũng được. Sau đó:

```bash
cd my-blog
```

## Bước 3 — Hiểu cấu trúc thư mục

```
my-blog/
├── config.toml      # cấu hình chính (URL, tiêu đề, taxonomies…)
├── content/         # bài viết & trang (file .md)
├── templates/       # template Tera (.html)
├── sass/            # file .scss (tự compile sang CSS)
├── static/          # ảnh, font, file tĩnh — copy nguyên si
└── themes/          # theme cài thêm (tùy chọn)
```

Mở `config.toml` và sửa dòng quan trọng nhất:

```toml
base_url = "https://<tên-github>.github.io/my-blog"
title = "Blog của tôi"
default_language = "vi"
compile_sass = true

[markdown]
highlight_code = true

[taxonomies]
categories = [{ name = "categories", feed = true }]
tags = [{ name = "tags", feed = true }]
```

> Lưu ý: nếu deploy lên GitHub Pages dạng *project page* (`username.github.io/my-blog`), `base_url` **phải** có đuôi `/my-blog`, nếu không link và CSS sẽ gãy.

## Bước 4 — Thêm theme (hoặc tự làm template)

Cách nhanh nhất cho người mới là dùng theme có sẵn ở [getzola.org/themes](https://www.getzola.org/themes/). Thêm theme dưới dạng git submodule:

```bash
git init
git submodule add https://github.com/<tác-giả>/<theme>.git themes/<theme>
```

Rồi khai báo trong `config.toml`:

```toml
theme = "<theme>"
```

Nếu thích tự kiểm soát, tạo `templates/index.html` tối giản:

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>{{ config.title }}</title>
</head>
<body>
  <h1>{{ config.title }}</h1>
  {% for page in section.pages %}
    <article>
      <h2><a href="{{ page.permalink }}">{{ page.title }}</a></h2>
      <p>{{ page.description }}</p>
    </article>
  {% endfor %}
</body>
</html>
```

## Bước 5 — Viết bài đầu tiên

Tạo file `content/bai-viet-dau-tien.md`:

```markdown
+++
title = "Bài viết đầu tiên của tôi"
description = "Mô tả ngắn cho SEO và mạng xã hội."
date = 2026-06-16

[taxonomies]
categories = ["Linh tinh"]
tags = ["zola", "blog"]
+++

Xin chào! Đây là bài viết **đầu tiên** viết bằng Markdown.
```

Phần giữa hai dấu `+++` gọi là **frontmatter** (định dạng TOML) — chứa metadata. Phần dưới là nội dung Markdown.

## Bước 6 — Chạy thử ở máy local

```bash
zola serve
```

Mở `http://127.0.0.1:1111` — Zola tự động **live reload**: bạn sửa file, lưu lại, trình duyệt cập nhật ngay. Khi ưng ý, build bản production:

```bash
zola build
```

Toàn bộ trang tĩnh được sinh ra trong thư mục `public/`.

## Bước 7 — Deploy miễn phí lên GitHub Pages

Đẩy code lên một repo GitHub, rồi tạo file `.github/workflows/deploy.yml`:

```yaml
name: Deploy
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
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
      - run: zola build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
    steps:
      - uses: actions/deploy-pages@v4
```

Vào **Settings → Pages** của repo, ở mục *Build and deployment* chọn **Source = GitHub Actions**. Từ giờ mỗi lần `git push` lên nhánh `main`, blog tự build và lên sóng. Đây cũng là nền tảng để [tự động hoá QA và self-healing CI](/zola/posting/qa-gatekeeper-tu-fix-loi-blog/) sau này.

## Bước 8 — Tối ưu SEO cơ bản

Zola lo phần khó giúp bạn, chỉ cần bật:

- **Sitemap**: tự sinh ở `/sitemap.xml` (không cần làm gì).
- **RSS/Atom**: thêm `generate_feeds = true` trong `config.toml`.
- **Mô tả & tiêu đề**: điền `description` cho mỗi bài, đặt từ khoá ở đầu `title`.
- **Ngôn ngữ**: `default_language = "vi"` để thẻ `<html lang>` đúng.

## Lỗi thường gặp

- **CSS/ảnh không hiện sau khi deploy** → sai `base_url` (thiếu đuôi `/repo`). Sửa lại cho khớp URL GitHub Pages.
- **Theme trống trơn** → quên `submodules: true` khi checkout trong workflow.
- **Link nội bộ gãy** → dùng `@/đường-dẫn.md` cho internal link trong Markdown để Zola tự kiểm tra.

## Kết

Chỉ với một file binary và một repo GitHub, bạn đã có blog **miễn phí, nhanh, an toàn** và tự động deploy. Bước tiếp theo nên làm: tùy biến template Tera cho ra chất riêng, thêm bình luận (giscus), và dựng pipeline tự động hoá nội dung.

Nếu bạn tò mò một blog Zola "đời thực" được vận hành thế nào — từ CMS mini viết bằng vanilla JS đến hệ thống tự fix lỗi — hãy đọc tiếp [Tự xây blog cá nhân $0/tháng](/zola/posting/cong-nghe-blog-duy-nguyen/) và [QA Gatekeeper: blog tự fix lỗi 24/7](/zola/posting/qa-gatekeeper-tu-fix-loi-blog/).
