# Duy Nguyen Blog

**Blog cá nhân tĩnh về công nghệ, du lịch và ẩm thực — xây dựng trên Zola, deploy GitHub Pages, không backend runtime.**

[![Live site](https://img.shields.io/badge/Live-banhang--chogao.github.io%2Fzola-003784?style=flat-square)](https://banhang-chogao.github.io/zola/)
[![Zola](https://img.shields.io/badge/Zola-0.22.1-FF4900?style=flat-square&logo=rust&logoColor=white)](https://www.getzola.org/)
[![Deploy](https://img.shields.io/github/actions/workflow/status/Banhang-Chogao/zola/deploy.yml?branch=main&style=flat-square&label=deploy)](https://github.com/Banhang-Chogao/zola/actions/workflows/deploy.yml)
[![QA](https://img.shields.io/github/actions/workflow/status/Banhang-Chogao/zola/qa.yml?branch=main&style=flat-square&label=qa)](https://github.com/Banhang-Chogao/zola/actions/workflows/qa.yml)

[Trang chủ](https://banhang-chogao.github.io/zola/) · [Viết bài (CMS)](https://banhang-chogao.github.io/zola/editor/) · [Web Vitals](https://banhang-chogao.github.io/zola/stats/) · [Insights](https://banhang-chogao.github.io/zola/insights/) · [Bảng Vàng SEO](https://banhang-chogao.github.io/zola/seo-bang-vang/)

---

## Tổng quan

Đây là blog tĩnh (SSG) của **Duy Nguyen**, viết chủ yếu bằng tiếng Việt. Toàn bộ HTML được sinh tại build time; trình duyệt chỉ tải thêm JavaScript thuần cho các tính năng nâng cao (CMS, sidebar cá nhân hoá, dashboard QA, v.v.).

Repo không dùng `npm`/`package.json` cho frontend blog — không Webpack, không React runtime. Pipeline CI kết hợp **Zola** (build site) và **Python** (sinh dữ liệu, QA, related posts).

Mọi thay đổi vào production đi qua **Pull Request** → CI xanh → auto-merge → `deploy.yml` publish lên GitHub Pages. Chi tiết vận hành: [docs/OPERATIONS.md](docs/OPERATIONS.md).

---

## Tính năng nổi bật

| Nhóm | Mô tả |
|------|--------|
| **Nội dung** | ~150+ bài viết (`posting/`, `baochi/`), taxonomy categories/tags, series đa phần, TOC tự động, FAQ + JSON-LD |
| **Mini CMS** | `/editor/` — Markdown live preview, publish qua GitHub REST API (PAT), không cần clone repo |
| **SEO & QA** | Canonical, Open Graph, Twitter Card, JSON-LD Article/FAQ/Breadcrumb, sitemap, Atom/RSS, compliance audit |
| **Related posts** | Embedding `sentence-transformers` (build-time) → `data/related.json` |
| **Bình luận** | [Giscus](https://giscus.app) (GitHub Discussions) |
| **Analytics** | Google Analytics 4, Search Console verification, Web Vitals client-side (`/stats/`) |
| **Premium / Paywall** | Teaser + thanh toán MoMo; nội dung premium strip trước `zola build` |
| **Công cụ nội bộ** | Content Creator, SEO board, dashboards (F/L/O/H), Korean converter, Insights GitHub |
| **CI tự phục hồi** | QA gatekeeper, compliance score, autofix conflicts, build-failure handler, 28 workflows |

---

## Tech stack

| Lớp | Công nghệ | Ghi chú |
|-----|-----------|---------|
| **SSG** | [Zola](https://www.getzola.org/) **0.22.1** | Rust binary, `compile_sass = true` |
| **Template** | Tera | 32 template HTML trong `templates/` |
| **Style** | SCSS (45 partial) | Design system Hilda (Ericsson Blue), `sass/site.scss` |
| **Font** | Ericsson Hilda (self-host) + Google Fonts (Manrope, Inter, Be Vietnam Pro) | `static/fonts/`, preconnect trong `base.html` |
| **Syntax highlight** | Catppuccin Mocha | `highlight_themes/`, bật trong `config.toml` |
| **Client JS** | Vanilla JS (35 module) | IIFE/defer, không framework UI |
| **Build scripts** | Python 3.11 (70+ script) | Sinh OG image, references, related, trends, compliance… |
| **CI** | GitHub Actions + Node 24 (actions only) | `deploy.yml`, `qa.yml`, … |
| **Hosting** | GitHub Pages | `base_url = https://banhang-chogao.github.io/zola` |
| **Search** | Local JSON index + Google CSE (tuỳ cấu hình) | `site-search-data` inline trong `base.html` |
| **Optional services** | FastAPI paywall (`backend/`, `services/`) | Không bắt buộc để đọc blog tĩnh |

---

## Cấu trúc thư mục

```
zola/
├── config.toml              # Site config, menu, GA4, GSC, taxonomies
├── content/                 # Markdown — posting, baochi, pages, tools, …
├── templates/               # Tera layouts (base, page, index, editor, …)
├── sass/                    # SCSS modules → site.css
├── static/                  # JS, fonts, img, vendor, data snapshot
├── data/                    # JSON build-time (SEO scores, related, compliance, …)
├── scripts/                 # Python: build, audit, autofix, tests
├── highlight_themes/        # Zola syntax themes
├── .github/workflows/       # CI/CD (deploy, qa, related, pagespeed, …)
├── qa_check.py              # QA gatekeeper (conflicts, SEO, SCSS, …)
├── docs/OPERATIONS.md       # Quy trình PR / auto-merge / deploy
└── CLAUDE.md                # Runbook + vaccine library cho agent/CI
```

---

## Phát triển local

### Yêu cầu

- [Zola](https://www.getzola.org/documentation/getting-started/installation/) **≥ 0.22.1**
- Git
- Python **3.11+** (khi chạy script build/QA giống CI)

### Chạy dev server (nhanh)

```bash
git clone https://github.com/Banhang-Chogao/zola.git
cd zola
zola serve
# → http://127.0.0.1:1111 (live reload)
```

### Build giống CI (đầy đủ)

```bash
# Bước tối thiểu trước zola build
python3 scripts/build_feed_pagination.py
python3 scripts/build_references.py

# Tuỳ chọn — cần pip install theo từng script
pip install -r scripts/requirements-og-images.txt
python3 scripts/build_og_images.py
python3 scripts/build_google_rank.py
python3 scripts/build_github_activity.py   # cần GITHUB_TOKEN

python3 scripts/paywall_prepare_build.py --strip
zola build
# Output: public/
```

### Kiểm tra chất lượng

```bash
python3 qa_check.py
python3 scripts/check_internal_links.py
zola build && python3 scripts/compliance_audit.py --stdout
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

---

## Build & deploy

| Bước | Lệnh / Workflow |
|------|-----------------|
| **PR** | `git checkout -b feature/ten-nhanh origin/main` → commit → push → mở PR |
| **CI** | `qa.yml` (gatekeeper), các workflow audit/domain tùy nhánh |
| **Merge** | Auto-merge khi `qa-check` pass ([docs/OPERATIONS.md](docs/OPERATIONS.md)) |
| **Deploy** | `deploy.yml` trên `main` — build artifact → GitHub Pages |
| **Lịch** | Deploy định kỳ 6h/lần để publish data bot refresh |

Production URL: **https://banhang-chogao.github.io/zola/**

---

## Quy trình nội dung

1. **Local** — sửa `content/**/*.md`, chạy `zola serve` xem trước.
2. **CMS** — mở `/editor/`, đăng nhập GitHub PAT (`repo` scope), publish → file commit lên `main` qua API.
3. **Front matter** — `title`, `description`, `[taxonomies]`, `[extra]` (`thumbnail`, `seo_keyword`, `series`, `faq`, …).
4. **Sau merge** — Actions build lại site; bài mới xuất hiện trên trang chủ, feed Atom/RSS, sitemap.
5. **SEO hook** — `scripts/seo_qa_checker.py` / Bảng Vàng SEO chấm on-page; compliance audit theo dõi H1, taxonomy, độ sâu bài.

---

## SEO & hiệu năng

**Đã triển khai**

- `lang="vi"`, viewport, canonical, meta description, OG/Twitter
- JSON-LD (Article, WebSite, Breadcrumb, FAQPage khi có `extra.faq`)
- `robots.txt`, sitemap, Atom + RSS (`generate_feeds = true`)
- Ảnh hero có `width`/`height`, lazy-load below-fold, Web Vitals dashboard
- Compliance score build-time → `/insights/`

**Snapshot Lighthouse** (nguồn `data/pagespeed.json`, 18/06/2026)

| | Desktop | Mobile |
|---|---------|--------|
| Performance | 95 | 58 |
| SEO | 100 | 100 |
| LCP | ~1.2s | ~6.9s |
| CLS | ~0 | 0 |

Desktop đạt điểm cao; mobile LCP đang là hạng mục ưu tiên tối ưu (font, hero image).

---

## Tác giả & bản quyền

- **Tác giả:** [duynguyenlog](https://github.com/Banhang-Chogao) — blog **Duy Nguyen**
- **Bản quyền nội dung:** © 2026 Duy Nguyen — [Tuyên bố bản quyền](https://banhang-chogao.github.io/zola/copyright/)
- **Chính sách:** [Privacy](https://banhang-chogao.github.io/zola/privacy/) · [Terms](https://banhang-chogao.github.io/zola/terms/) · [Contact](https://banhang-chogao.github.io/zola/contact/)

Engine: [Zola](https://www.getzola.org/) · Comments: [Giscus](https://giscus.app)