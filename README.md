<div align="center">

```
███████╗ ██████╗ ██╗      █████╗     ██████╗ ██╗      ██████╗  ██████╗
╚══███╔╝██╔═══██╗██║     ██╔══██╗    ██╔══██╗██║     ██╔═══██╗██╔════╝
  ███╔╝ ██║   ██║██║     ███████║    ██████╔╝██║     ██║   ██║██║  ███╗
 ███╔╝  ██║   ██║██║     ██╔══██║    ██╔══██╗██║     ██║   ██║██║   ██║
███████╗╚██████╔╝███████╗██║  ██║    ██████╔╝███████╗╚██████╔╝╚██████╔╝
╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝    ╚═════╝╚══════╝ ╚═════╝  ╚═════╝
```

### `> blog cá nhân của duynguyenlog _`

**Static · Blazing Fast · Zero-Backend · Vanilla JS · Hosted on GitHub Pages**

[![Built with Zola](https://img.shields.io/badge/Built%20with-Zola%200.22-FF4900?style=for-the-badge&logo=rust&logoColor=white)](https://www.getzola.org/)
[![Deployed on GitHub Pages](https://img.shields.io/badge/Deploy-GitHub%20Pages-181717?style=for-the-badge&logo=github&logoColor=white)](https://banhang-chogao.github.io/zola/)
[![CI](https://img.shields.io/github/actions/workflow/status/Banhang-Chogao/zola/deploy.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white&label=Deploy)](https://github.com/Banhang-Chogao/zola/actions)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](#)

[**🌐 Xem live**](https://banhang-chogao.github.io/zola/) · [**📝 Viết bài (CMS)**](https://banhang-chogao.github.io/zola/editor) · [**한 Korean Converter**](https://banhang-chogao.github.io/zola/converter/) · [**📊 Speed Insights**](https://banhang-chogao.github.io/zola/stats)

</div>

---

## 🔥 Tại sao blog này không tầm thường?

Đây không phải là một blog Zola "fork-and-deploy". Mỗi tính năng đều được build từ đầu, **không dùng framework JS**, và toàn bộ tương tác đều chạy **client-side thuần** trên trình duyệt visitor — không cần server, không cần database.

> **5,500+ dòng code · 50+ commits · 0 dependency runtime · 100% static**

---

## 🛠️ Tech Stack

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://www.getzola.org/"><img src="https://img.shields.io/badge/-Zola-FF4900?style=for-the-badge&logo=rust&logoColor=white" alt="Zola"/></a>
      <br><sub>SSG · Rust</sub>
    </td>
    <td align="center" width="120">
      <img src="https://img.shields.io/badge/-Tera-1F2D3D?style=for-the-badge&logo=jinja&logoColor=white" alt="Tera"/>
      <br><sub>Templates</sub>
    </td>
    <td align="center" width="120">
      <img src="https://img.shields.io/badge/-SCSS-CC6699?style=for-the-badge&logo=sass&logoColor=white" alt="SCSS"/>
      <br><sub>13 modules</sub>
    </td>
    <td align="center" width="120">
      <img src="https://img.shields.io/badge/-Vanilla%20JS-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="Vanilla JS"/>
      <br><sub>9 modules · 0 framework</sub>
    </td>
    <td align="center" width="120">
      <img src="https://img.shields.io/badge/-HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"/>
      <br><sub>Semantic</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://img.shields.io/badge/-GitHub%20Pages-222?style=for-the-badge&logo=github&logoColor=white" alt="GH Pages"/>
      <br><sub>Hosting</sub>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/-GH%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="Actions"/>
      <br><sub>CI/CD</sub>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/-GitHub%20REST-181717?style=for-the-badge&logo=github&logoColor=white" alt="REST API"/>
      <br><sub>Mini CMS</sub>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/-Giscus-2C2D2D?style=for-the-badge&logo=github&logoColor=white" alt="Giscus"/>
      <br><sub>Comments</sub>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/-GA4-E37400?style=for-the-badge&logo=googleanalytics&logoColor=white" alt="GA4"/>
      <br><sub>Analytics</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://img.shields.io/badge/-Web%20Vitals-34A853?style=for-the-badge&logo=google&logoColor=white" alt="Web Vitals"/>
      <br><sub>LCP · INP · CLS</sub>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/-marked.js-000?style=for-the-badge&logo=markdown&logoColor=white" alt="Marked"/>
      <br><sub>MD render</sub>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/-Catppuccin-F5C2E7?style=for-the-badge&logo=catppuccin&logoColor=black" alt="Catppuccin"/>
      <br><sub>Syntax theme</sub>
    </td>
  </tr>
</table>

---

## ✨ Tính năng — không phải chỉ là một blog

### 📝 Mini CMS viết bài trực tiếp trên trình duyệt
Trang `/editor/` cho phép **đăng nhập bằng GitHub PAT**, viết bài bằng Markdown live-preview (powered by `marked.js`), rồi **PUT thẳng vào `content/*.md`** qua GitHub REST API. GitHub Actions tự build & deploy sau ~1 phút. Không cần Netlify CMS, không cần backend.

### ⚡ Speed Insights (Core Web Vitals)
Tự đo **LCP / FCP / INP / CLS / TTFB** trên mọi page load qua thư viện [`web-vitals`](https://github.com/GoogleChrome/web-vitals) của Google. Lưu 500 sample gần nhất vào `localStorage`, hiển thị dashboard tại `/stats/`.

### 🎯 Featured & Random Posts cá nhân hoá
Sidebar JS đọc `posts-data` JSON inline, **weighted random** dựa trên view / click count lưu `localStorage` — mỗi visitor thấy một danh sách khác nhau.

### 🚦 GitHub Live Status Banner
Header rotator fetch GitHub API real-time để hiển thị:
- Commit message + hash + timestamp mới nhất
- Pending workflow queue (GitHub Actions đang chạy)
- Version blog tự động sinh từ commit count

### 💬 Giscus Comments
Comment system dùng **GitHub Discussions** làm backend — không spam, không cần auth riêng, mọi comment đều là issue/discussion thật trên repo.

### 🎨 Custom Design System
- **Font chính**: Ericsson Hilda (5 weight) — bộ font tự host
- **Webfont phụ**: Manrope + Poppins từ Google Fonts (preconnect optimized)
- **Syntax highlight**: Catppuccin Mocha theme
- **13 SCSS modules** organized BEM-style, build qua Zola native (`compile_sass = true`)

---

## 🏗️ Architecture

```
                       ┌────────────────────────────────┐
                       │   ✍  Author viết Markdown     │
                       │   (local OR /editor/ trên web) │
                       └──────────────┬─────────────────┘
                                      │
                                      │  git push / GitHub API PUT
                                      ▼
                       ┌────────────────────────────────┐
                       │      📦  GitHub Repo (main)    │
                       └──────────────┬─────────────────┘
                                      │
                       triggers .github/workflows/deploy.yml
                                      │
                                      ▼
            ┌──────────────────────────────────────────────────┐
            │  🦀  Zola build (Rust)                           │
            │  └─ Tera render → SCSS compile → static HTML     │
            └──────────────────────────┬───────────────────────┘
                                       │
                                       ▼
                       ┌────────────────────────────────┐
                       │   🌐  GitHub Pages CDN         │
                       └──────────────┬─────────────────┘
                                      │
                                      ▼
            ┌──────────────────────────────────────────────────┐
            │              👤  Visitor's Browser               │
            │  ┌────────────────────────────────────────────┐  │
            │  │  Vanilla JS modules — chạy hoàn toàn       │  │
            │  │  client-side, fetch các API:               │  │
            │  │    · GitHub API   (commit status, queue)   │  │
            │  │    · web-vitals   (Core Web Vitals)        │  │
            │  │    · GA4 gtag     (analytics)              │  │
            │  │    · Giscus       (comments)               │  │
            │  └────────────────────────────────────────────┘  │
            └──────────────────────────────────────────────────┘
```

---

## 📂 Cấu trúc project

```
zola/
├── 📄 config.toml                  # Zola config + GA4 measurement id
├── 🚀 push.sh                       # Shortcut commit & push
├── 📁 content/                      # Markdown bài viết
│   ├── _index.md
│   ├── pages/                       # About + static pages
│   ├── editor/                      # CMS landing
│   └── stats/                       # Speed Insights landing
├── 📁 templates/                    # Tera templates
│   ├── base.html                    # Shell layout (header + nav + sidebar)
│   ├── index.html / section.html / page.html
│   ├── editor.html                  # 📝 Mini CMS UI
│   └── stats.html                   # ⚡ Web Vitals dashboard
├── 📁 sass/                         # SCSS modules
│   ├── site.scss                    # Entry point
│   ├── _reset.scss / _layout.scss / _navbar.scss / _sidebar.scss
│   ├── _banner.scss / _post.scss / _single.scss
│   ├── _editor.scss / _stats.scss
│   ├── _footer.scss / _fonts.scss
├── 📁 static/
│   ├── 🔤 fonts/                    # Ericsson Hilda (5 weights)
│   ├── 🧮 converter/                # Korean number-to-words tool
│   └── 📜 js/                       # Vanilla JS modules
│       ├── header-rotator.js        # GitHub live status banner
│       ├── sidebar.js               # Featured / random posts
│       ├── editor.js                # Mini CMS logic (PAT auth + PUT)
│       ├── auth.js                  # OTP gate cho /editor/
│       ├── speed-vitals.js          # Core Web Vitals tracker
│       ├── stats-page.js            # Vitals dashboard renderer
│       └── post-stats.js            # Per-post analytics badge
├── 🎨 highlight_themes/             # Catppuccin Mocha .tmTheme
└── ⚙  .github/workflows/deploy.yml  # CI/CD pipeline
```

---

## 🚀 Quickstart

### Yêu cầu
- [**Zola**](https://www.getzola.org/documentation/getting-started/installation/) ≥ 0.22 (Rust binary, ~5MB)
- Git

### Chạy local

```bash
git clone https://github.com/Banhang-Chogao/zola.git
cd zola
zola serve
# → http://127.0.0.1:1111
```

Mỗi khi sửa `.md` / `.html` / `.scss` → Zola live-reload tức thì.

### Deploy

```bash
# Cách 1: dùng push.sh
./push.sh "your commit message"

# Cách 2: thủ công
git add . && git commit -m "..." && git push
```

GitHub Actions sẽ tự build & deploy lên Pages trong ~1 phút. Watch live status ngay trên header banner của blog.

### Viết bài qua trình duyệt (không cần clone)

1. Tạo [GitHub PAT](https://github.com/settings/tokens) với scope `repo`
2. Mở https://banhang-chogao.github.io/zola/editor
3. Paste PAT → viết bài → publish
4. Đợi ~1 phút, bài lên blog 🎉

---

## ⚙️ Configuration cheatsheet

Tất cả config nằm trong `config.toml`:

```toml
[extra]
# Google Analytics 4 — để trống = tắt tracking
ga_measurement_id = "G-XXXXXXXXXX"

# Menu navigation
menu = [
    {url = "$BASE_URL", name = "TRANG CHÍNH"},
    # ...
]
```

---

## 📊 Project stats

| Metric                  | Value          |
| ----------------------- | -------------- |
| Tổng lines of code      | **5,500+**     |
| Commits                 | **50+**        |
| Templates Tera          | 9              |
| SCSS modules            | 13             |
| JavaScript modules      | 9              |
| Runtime dependencies    | **0**          |
| Build time              | < 1s           |
| Lighthouse Performance  | 99 / 100       |
| Cost / month            | **$0**         |

---

## 🎯 Design principles

1. **Zero runtime dependencies** — không bundler, không `npm install`, không `node_modules/`. Mỗi JS file là IIFE chạy thẳng.
2. **Static-first** — toàn bộ HTML pre-render tại build time. JS chỉ enhance, không gate content.
3. **Progressive enhancement** — tắt JS vẫn đọc được bài, vẫn navigate được. JS chỉ thêm bell & whistle.
4. **Client-side everything** — analytics, CMS… đều fetch từ trình duyệt visitor → server cost = $0.
5. **Vietnamese-first** — UI, content, copy đều bằng tiếng Việt.

---

## 🤝 Credits

Built with ❤️ by [**@duynguyenlog**](https://github.com/Banhang-Chogao) · Static engine: [**Zola**](https://www.getzola.org/) by [@Keats](https://github.com/Keats) · Inspired by **Catppuccin** color palette · Comments powered by [**Giscus**](https://giscus.app)

<div align="center">

---

---

## 🎨 Theme System (Multi-theme Architecture)

Blog hiện hỗ trợ **multi-theme switching** với persistent localStorage:

### Theme

| Theme | Color Palette | Style | Font |
|---|---|---|---|
| **Hilda** (Default) | Ericsson Blue (#003784) | Professional, clean | Ericsson Hilda OTF |

### Adding a New Theme (Guide for Developers)

#### Step 1: Create Token Files

```bash
# Create color & typography tokens
touch sass/_mytheme-tokens.scss
touch sass/_mytheme-fonts.scss
```

**Example: `_mytheme-tokens.scss`**
```scss
$mytheme-primary:      #COLOR;
$mytheme-accent:       #COLOR;
$mytheme-border:       #COLOR;
$mytheme-radius-sm:    4px;
$mytheme-shadow-sm:    0 2px 4px rgba(0,0,0,0.08);
```

#### Step 2: Define Theme Variables in `_themes.scss`

```scss
:root[data-theme="mytheme"] {
  --c-bg-page:        #fff;
  --c-text-heading:   #000;
  --c-accent:         #COLOR;
  --c-border:         #COLOR;
  --c-shadow-md:      /* shadow value */;
  /* ...add all 15+ CSS variables... */
  font-family: 'Your Font', fallback, sans-serif;
}
```

#### Step 3: Add Component Overrides in `_theme-overrides.scss`

```scss
:root[data-theme="mytheme"] {
  @include theme-overrides(
    $radius-card:        4px,
    $radius-tag:         4px,
    $shadow-card:        $mytheme-shadow-sm,
    $shadow-card-hover:  $mytheme-shadow-lg,
    $kicker-spacing:     0.05em,
    $heading-ls:         -0.02em
  );
}
```

#### Step 4: Register in JavaScript

**`static/js/theme-switcher.js`**
```javascript
var VALID_THEMES = ["hilda"];  // Single theme: Hilda (Ericsson Blue)
```

#### Step 5: Update Imports

**`sass/site.scss`**
```scss
@import "mytheme-tokens";
@import "mytheme-fonts";  // if custom font
```

#### Step 6: Update Toggle Button

**`templates/base.html`** (optional, if supporting 3+ themes)
```html
<!-- Dropdown or multi-choice instead of binary toggle -->
```

### Verification Checklist

- [ ] All 15+ CSS variables defined (check against mixin params)
- [ ] Color contrast ≥ 4.5:1 for normal text (WCAG AA)
- [ ] Font loads correctly (use `font-display: swap` for OTF)
- [ ] All component classes styled (post-card, buttons, sidebar, etc.)
- [ ] Mobile responsive rules scoped to `@media (max-width: 720px)`
- [ ] localStorage persists theme choice
- [ ] Fade transition smooth (0.3s)
- [ ] SCSS compiles without errors

---

`< made with rust, sass, and a lot of vanilla js />`

</div>
