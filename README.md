<div align="center">

# Duy Nguyen — Blog cá nhân

### `> chuyện viết code, xây sản phẩm phần mềm và những chuyến đi _`

Blog tiếng Việt về **công nghệ, tài chính số, du lịch và ẩm thực** — viết từ trải nghiệm thật.
Static site dựng bằng **Zola (Rust)**, vanilla JS không framework, deploy tự động lên **GitHub Pages**.

[![Built with Zola](https://img.shields.io/badge/Built%20with-Zola%200.22-FF4900?style=flat-square&logo=rust&logoColor=white)](https://www.getzola.org/)
[![Deploy](https://img.shields.io/github/actions/workflow/status/Banhang-Chogao/zola/deploy.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white&label=deploy)](https://github.com/Banhang-Chogao/zola/actions/workflows/deploy.yml)
[![GitHub Pages](https://img.shields.io/badge/hosting-GitHub%20Pages-181717?style=flat-square&logo=github&logoColor=white)](https://banhang-chogao.github.io/zola/)
[![Language](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-da291c?style=flat-square)](#)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20Redis-009688?style=flat-square&logo=fastapi&logoColor=white)](services/)

[**🌐 Xem live**](https://banhang-chogao.github.io/zola/) ·
[**📝 Viết bài (CMS)**](https://banhang-chogao.github.io/zola/editor) ·
[**📊 Insights**](https://banhang-chogao.github.io/zola/insights) ·
[**💰 F-Dashboard**](https://banhang-chogao.github.io/zola/tools/f-dashboard) ·
[**한 Korean Converter**](https://banhang-chogao.github.io/zola/converter/)

</div>

---

## 📖 Tổng quan

Đây không phải một blog Zola "fork-and-deploy". Phần lõi vẫn là static site siêu nhẹ, nhưng xung quanh nó là cả một hệ thống tự vận hành: **mini CMS viết bài trên trình duyệt**, **bộ công cụ tài chính cá nhân chạy 100% client-side**, **paywall premium**, **engine SEO ngữ nghĩa**, và một dàn **GitHub Actions tự build — tự kiểm thử — tự merge — tự deploy**.

Triết lý xuyên suốt:

- **Static-first** — toàn bộ HTML pre-render tại build time. JS chỉ *enhance*, không gate nội dung.
- **Zero runtime dependency phía blog** — không bundler, không `npm install`, không `node_modules/`. Mỗi file JS là IIFE chạy thẳng trên trình duyệt.
- **Client-side everything** — phân tích sao kê, dashboard tài chính, analytics… đều xử lý ngay trong trình duyệt visitor. Backend chỉ phục vụ những thứ *bắt buộc* phải có server (OAuth, paywall, đếm view).
- **Vietnamese-first** — UI, nội dung, ngày giờ (GMT+7, `dd/mm/yyyy`) đều theo chuẩn Việt Nam.

---

## ✨ Tính năng

### 📝 Nội dung & xuất bản
- Blog đa chuyên mục (công nghệ, ngân hàng, du lịch, khoa học, báo chí…) với taxonomy `categories` + `tags`, phân trang và **feed RSS/Atom** riêng cho từng taxonomy.
- **Mini CMS** tại `/editor/` — đăng nhập **GitHub OAuth**, soạn Markdown, ghi thẳng vào `content/*.md` qua GitHub API; Actions tự build & deploy.
- **Content Creator** — công cụ hỗ trợ soạn bài chuẩn SEO ngay trên web.
- **Đăng bài hẹn giờ** — lưu draft kèm `publish_at`, workflow cron tự phát hành khi tới hạn (chỉ khi qua QA).

### 💰 Bộ công cụ tài chính (100% client-side, mã hoá AES-GCM)
| Tool | Nguồn dữ liệu | Ghi chú |
|------|---------------|---------|
| **F-Dashboard** | Sao kê VietinBank (Excel) | SheetJS parser, health score, export JSON/PDF rồi *wipe* dữ liệu |
| **L-Dashboard** | Sao kê LPBank (PDF) | pdf.js text layer |
| **O-Dashboard** | Sao kê Liobank by OCB (PDF) | clone kiến trúc L |
| **H-Dashboard** | Hoá đơn mua hàng (PDF + OCR) | Tesseract.js `vie+eng` fallback |

Dữ liệu **chỉ nằm trong IndexedDB local của trình duyệt**, mã hoá AES-GCM, **không bao giờ upload server**. Truy cập qua GitHub OAuth.

### 🔒 Premium Paywall
Bài premium chỉ render *teaser* trong HTML tĩnh; nội dung đầy đủ nằm ở backend, mở khoá qua email + approve code (thanh toán MoMo, admin xác nhận thủ công).

### 🚀 SEO & Performance (tự động ở template)
- **TOC tự động** (bài ≥ 3 heading), **Related Articles ngữ nghĩa** (sentence-transformers / SBERT đa ngôn ngữ).
- Schema **Article / FAQPage / BreadcrumbList**, block **References** cuối bài, validate internal link (gate CI).
- **Speed Insights** (`/stats/`) đo Core Web Vitals (LCP · INP · CLS · FCP · TTFB) bằng thư viện `web-vitals` của Google.
- Pipeline ảnh **WebP** + sinh ảnh **OG** từ SVG cover; **IndexNow** ping cho Bing.

### 📊 Insights & tự vận hành
Trang `/insights/` tổng hợp dữ liệu do bot sinh ra: build dashboard, merge report, compliance score, SEO scoring, gợi ý tên miền, Google Trends VN. Toàn bộ chạy bằng GitHub Actions theo lịch.

### 🧩 Khác
Giscus comments (GitHub Discussions) · GA4 + Google Search Console · Korean number converter · Prompt Support tool · multi-theme switcher (localStorage) · header live-status banner fetch GitHub API.

---

## 🛠️ Tech stack

| Lớp | Công nghệ |
|-----|-----------|
| **Static Site Generator** | [Zola](https://www.getzola.org/) `0.22.1` (Rust) — `compile_sass`, native feeds, taxonomies |
| **Templating** | [Tera](https://keats.github.io/tera/) (Jinja-like) — `templates/` + macros + shortcodes |
| **Styles** | SCSS (44 module, BEM-ish), build native qua Zola |
| **Client JS** | Vanilla JS (40+ module, IIFE, **0 framework, 0 build step**) |
| **Thư viện browser** | `web-vitals`, SheetJS, pdf.js, Tesseract.js, marked.js |
| **Tooling / automation** | Python 3.11 (55+ script): SEO QA, related engine, compliance, dashboards, autofixer |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) + Redis trên [Render](https://render.com/) — `services/visitor-counter` (OAuth/CMS, view counter, reports), `services/paywall` |
| **CI/CD** | GitHub Actions (28 workflow) → GitHub Pages |
| **Chất lượng code** | pre-commit · Ruff · Mypy · test suite Python |
| **Tích hợp** | Giscus · Google Analytics 4 · Google Search Console · IndexNow |
| **Theme cú pháp** | Catppuccin Mocha · Font: Ericsson Hilda (self-hosted) |

---

## 📂 Cấu trúc thư mục

```text
zola/
├── config.toml                 # Cấu hình Zola + menu + GA4 + giscus + paywall/CMS API
├── content/                    # Nội dung Markdown
│   ├── posting/  baochi/        # Bài viết (blog · báo chí)
│   ├── du-lich/  dien-anh/      # Chuyên mục
│   ├── tools/                   # Trang công cụ (F/L/O/H-dashboard, content-creator)
│   ├── editor/  insights/  stats/  scoring/ …
│   └── pages/                   # Trang tĩnh (about, privacy, terms, copyright…)
├── templates/                  # Tera templates
│   ├── base.html  index.html  page.html  section.html  taxonomy_*.html
│   ├── editor.html  insights.html  *-dashboard.html  paywall-admin.html
│   ├── macros/                  # references, series-nav, paywall, giscus, github-activity…
│   └── shortcodes/
├── sass/                        # 44 SCSS module — site.scss là entry point
├── static/
│   ├── js/                      # Vanilla JS (root + f/l/o/h-dashboard/, content-creator/)
│   ├── fonts/                   # Ericsson Hilda
│   └── img/                     # Ảnh WebP + placeholder SVG
├── scripts/                     # Python tooling (build_references, build_related, seo_qa_checker,
│   │                            #   compliance_audit, autofix_conflicts, paywall_*, *dashboard*…)
│   └── requirements*.txt        # Deps theo nhóm (related/SBERT, f-dashboard, og-images…)
├── services/                    # Backend FastAPI + Redis (deploy Render)
│   ├── visitor-counter/          #   OAuth CMS auth · view counter · gated reports
│   └── paywall/                  #   Premium unlock API
├── data/                        # JSON do bot/CI sinh (related, scores, dashboards, reports)
├── docs/                        # OPERATIONS, paywall, seo-strategy…
├── highlight_themes/            # Catppuccin Mocha .tmTheme
├── render.yaml                  # Render Blueprint cho backend
└── .github/workflows/           # 28 workflow CI/CD + automation
```

---

## 🚀 Phát triển local

### Yêu cầu
- [**Zola**](https://www.getzola.org/documentation/getting-started/installation/) ≥ `0.22` (binary Rust ~5 MB)
- **Python 3.11** (cho các script SEO/build data — tùy chọn khi chỉ sửa nội dung/giao diện)
- Git

### Chạy blog

```bash
git clone https://github.com/Banhang-Chogao/zola.git
cd zola
zola serve            # → http://127.0.0.1:1111  (live-reload .md / .html / .scss)
```

### Build production (giống CI)

```bash
# (tùy chọn) sinh dữ liệu phụ trợ trước khi build
pip install -r scripts/requirements.txt
python3 scripts/build_references.py     # block "Tham khảo" cuối bài
python3 scripts/build_related.py        # related posts ngữ nghĩa (SBERT)
python3 scripts/paywall_prepare_build.py --strip   # giữ teaser cho bài premium

zola build           # xuất ra ./public
```

### Chạy backend (tùy chọn)

```bash
cd services/visitor-counter
pip install -r requirements.txt
uvicorn main:app --reload      # FastAPI + Redis (OAuth CMS, view counter, reports)
```

### Chất lượng code

```bash
pip install pre-commit && pre-commit install   # ruff + mypy + checks trước mỗi commit
python3 scripts/seo_qa_checker.py --all         # chấm SEO toàn bộ bài
python3 scripts/check_internal_links.py         # validate internal link (gate CI)
```

---

## 🔄 Quy trình nội dung & deploy

```text
✍  Viết Markdown (local hoặc /editor/ trên web)
        │  git push  /  GitHub API PUT
        ▼
📦 Branch → Pull Request → main
        │  push main triggers deploy.yml
        ▼
🦀 Zola build (Rust): OG images → references → related → strip premium → render
        ▼
🌐 GitHub Pages CDN
        ▼
👤 Trình duyệt visitor: vanilla JS fetch GitHub API · web-vitals · GA4 · Giscus
                         + FastAPI backend (OAuth / paywall / view counter)
```

**Quy ước Git:** mọi thay đổi đi qua **Pull Request** (không push thẳng `main`). PR pass QA → auto-merge → deploy. Chi tiết: [`docs/OPERATIONS.md`](docs/OPERATIONS.md) và [`.github/BRANCH-PROTECTION.md`](.github/BRANCH-PROTECTION.md).

### Viết bài qua trình duyệt (không cần clone)
1. Mở https://banhang-chogao.github.io/zola/editor
2. Đăng nhập GitHub OAuth → soạn Markdown live-preview → publish
3. Đợi ~1 phút, bài tự lên blog 🎉

---

## 📈 SEO & Performance

- **On-page tự động:** TOC, breadcrumb, FAQ schema, Article schema, related posts, references — sinh ở template/CI, không cần làm tay từng bài.
- **Related posts ngữ nghĩa:** embeddings SBERT đa ngôn ngữ + cosine similarity (fallback theo tag/category khi thiếu embedding).
- **Core Web Vitals:** đo real-user (LCP · INP · CLS · FCP · TTFB), dashboard tại `/stats/`.
- **Quality gate:** `seo_qa_checker.py` chấm điểm mỗi bài; `check_internal_links.py` + `qa-404-checker.py` chặn build khi còn link nội bộ hỏng.
- **Ảnh:** pipeline WebP (`to_webp.py`), placeholder SVG có thương hiệu, sinh ảnh OG 1200×630 từ cover SVG.
- **Index nhanh:** sitemap + feed + ping IndexNow (Bing) + Google Search Console verification.

---

## 👤 Tác giả & bản quyền

Xây dựng bởi **Duy Nguyen** ([@Banhang-Chogao](https://github.com/Banhang-Chogao)) — developer người Việt, viết về công nghệ, tài chính số, du lịch và ẩm thực từ trải nghiệm thật.

- **Mã nguồn:** dự án cá nhân, dùng làm tham khảo học tập.
- **Nội dung bài viết & hình ảnh:** © Duy Nguyen — vui lòng không sao chép/đăng lại khi chưa được phép (xem trang [Tuyên bố bản quyền](https://banhang-chogao.github.io/zola/copyright)).

<div align="center">

Static engine: [**Zola**](https://www.getzola.org/) by [@Keats](https://github.com/Keats) · Comments: [**Giscus**](https://giscus.app) · Syntax: [**Catppuccin**](https://github.com/catppuccin)

`< made with rust, sass & a lot of vanilla js />`

</div>
</content>
</invoke>
