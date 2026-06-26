# SEOMONEY

**SEO, AI WebOps & Personal Finance Blog — Static-first publishing system with FastAPI backend, Google auth, and AI-powered insights.**

[![Live site](https://img.shields.io/badge/Live-seomoney.org-003784?style=flat-square)](https://seomoney.org)
[![Zola](https://img.shields.io/badge/Zola-0.22.1-FF4900?style=flat-square&logo=rust&logoColor=white)](https://www.getzola.org/)
[![Deploy](https://img.shields.io/github/actions/workflow/status/Banhang-Chogao/zola/deploy.yml?branch=main&style=flat-square&label=deploy)](https://github.com/Banhang-Chogao/zola/actions/workflows/deploy.yml)
[![QA](https://img.shields.io/github/actions/workflow/status/Banhang-Chogao/zola/qa.yml?branch=main&style=flat-square&label=qa)](https://github.com/Banhang-Chogao/zola/actions/workflows/qa.yml)
[![License: EUPL 1.2](https://img.shields.io/badge/License-EUPL%201.2-blue.svg?style=flat-square)](LICENSE)

[🏠 Home](/) · [✍️ Editor (CMS)](/editor/) · [📊 Insights](/insights/) · [🔍 SEO](/seo-bang-vang/) · [⚡ Web Vitals](/stats/)

---

## Overview

**SEOMONEY** is a professional blogging platform combining:

- **Static-first frontend:** Zola (Rust SSG) + Tera templates + SCSS design system, deployed to GitHub Pages at **seomoney.org**
- **Live editor:** Web-based CMS at `/editor/` (publish via GitHub REST API without cloning)
- **Native commenting:** Google login integrated into article pages (Giscus kept as legacy fallback)
- **FastAPI backend:** VIPZone service on Render for editor APIs, admin tools, premium content, private reports
- **SEO automation:** Python QA checker, compliance audits, internal link validation, related-post embeddings
- **Personal finance tools:** Dashboard suite (F/L/O/H) for analyzing bank statements and invoices
- **Admin dashboard:** Insights, merge reports, build monitors, domain suggestions, vaccine autofixer

**Content:** ~150+ articles (Vietnamese) across technology, personal finance, news curated, and travel.

**Philosophy:** Ship fast with confidence. Every change goes through PR → CI gatekeeper → auto-merge → deploy. Quality gates are automated, not manual review.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SEOMONEY.ORG (GitHub Pages)                │
│                   Static site (Zola + SCSS + JS)                │
└──────────────────────┬──────────────────────────────────────────┘
                       ▲
        ┌──────────────┴──────────────┐
        │                             │
    GitHub Actions              Backend APIs
    (deploy.yml)               (FastAPI VIPZone)
        │                             │
        │                      ┌──────▼──────┐
        │                      │   Render    │
        │                      │ (blog-vip-  │
        │                      │  zone-api)  │
        │                      └──────┬──────┘
        │                             │
        └──────────────┬──────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
    Repo (Markdown)          CI/CD (Workflows)
    (content/)               (QA, builds, stats)
        │
        ▼
    Editor/CMS auth
    (Google OAuth + GitHub token)
```

**Flow:**
1. Content: Markdown in `content/` or via `/editor/` CMS
2. Build: `zola build` (Tera templates + SCSS) → static HTML/CSS/JS
3. QA: Python compliance checks, internal link validation, reference building
4. Deploy: GitHub Actions → GitHub Pages at seomoney.org
5. Admin: FastAPI backend handles editor sessions, private tools, reports, auth gates

---

## Tech Stack

### Static Site Generation & Frontend

| Component | Technology | Details |
|-----------|-----------|---------|
| **SSG** | [Zola](https://www.getzola.org/) **0.22.1** | Rust-based, compile SCSS, no `node_modules` |
| **Templates** | Tera | 32+ HTML layouts, partials, macros |
| **Styling** | SCSS + S-DNA design system | 45+ partials, responsive (mobile-first), semantic color tokens |
| **Fonts** | Ericsson Hilda (self-hosted) + Google Fonts | Nokia Pure/Headline for dashboard PDFs |
| **Syntax Highlighting** | Catppuccin Mocha | Dark/light mode support |
| **Client JS** | Vanilla JavaScript (35 modules, no framework) | IIFE/defer, utilities (auth-gate, search, editor, dashboards) |

### Backend Services

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Server** | FastAPI (Python 3.11) | Editor session, auth, admin tools, premium content gates |
| **Hosting** | Render | `blog-vipzone-api.onrender.com` |
| **Database** | In-process (JSON/file-based for now) | Session state, report metadata, user approvals |
| **Auth** | Google OAuth 2.0 + GitHub | Editor: Google/GitHub login; admin tools: Google email whitelist |

### Build Automation & QA

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Build Scripts** | Python 3.11 (70+ scripts) | Generate OG images, references, related posts, compliance scores, trends |
| **QA Gatekeeper** | `qa_check.py` + `qa.yml` | Conflict markers, SCSS lint, internal links, SEO on-page |
| **Link Validator** | `qa-404-checker.py` | Crawl `public/` for broken internal links; external links checked offline-safe |
| **Compliance Audit** | `compliance_audit.py` | H1 count, taxonomy coverage, article depth, readability |
| **CI/CD** | GitHub Actions | 28+ workflows (deploy, build, QA, domain checks, vaccine autofixer) |

### Data & Analytics

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Analytics** | Google Analytics 4 (GA4) | User behavior, traffic sources, conversions |
| **Search Console** | Google Search Console | Indexing, Core Web Vitals, search performance |
| **Site Search** | Google Programmable Search Engine (fallback: JSON index) | Full-text search on blog |
| **Web Vitals** | Web Vitals client-side API | Performance monitoring dashboard at `/stats/` |
| **Data Storage** | JSON files in `data/` | Compliance scores, build reports, related posts, SEO rankings |

### Content & SEO

| Feature | Implementation |
|---------|-----------------|
| **Canonical URLs** | Auto-generated, prevents duplicate indexing |
| **Open Graph / Twitter Cards** | OG images auto-generated (cairosvg + Pillow) |
| **JSON-LD** | Article, WebSite, Breadcrumb, FAQPage (for snippets) |
| **Feeds** | Atom + RSS (Zola built-in, `generate_feeds = true`) |
| **Sitemap** | Auto-generated, submitted to GSC |
| **Internal Linking** | Related posts via sentence-transformers embeddings (build-time) |
| **Mobile-first indexing** | Responsive design, viewport meta |

### Hosting & Infrastructure

| Layer | Service | Details |
|-------|---------|---------|
| **Static Site Hosting** | GitHub Pages | `seomoney.org` (custom domain via CNAME) |
| **API Backend** | Render | `blog-vipzone-api.onrender.com` (FastAPI, Python 3.11) |
| **Repository** | GitHub | `Banhang-Chogao/zola` (public, auto-merge + deploy) |
| **CI/CD** | GitHub Actions | 28 workflows, QA gatekeeper, auto-merge on main |
| **Secrets** | GitHub Secrets | `GITHUB_TOKEN`, `ZOLA_GH_TOKEN`, `DOMAIN_CHECK_API_KEY`, etc. |

---

## Directory Structure

```
zola/
├── README.md                    # This file
├── config.toml                  # Site config (author, domain, GA4, GSC, menus, taxonomies)
├── CLAUDE.md                    # Automation runbook + vaccine library
│
├── content/                     # Markdown content
│   ├── posting/                 # Main blog articles (~150 posts)
│   ├── baochi/                  # News curated articles
│   ├── pages/                   # Static pages (about, privacy, terms, contact)
│   ├── tools/                   # Tools & dashboards (f-dashboard, l-dashboard, h-dashboard, etc.)
│   └── _index.md                # Homepage, category pages
│
├── templates/                   # Tera HTML templates
│   ├── base.html                # Layout wrapper (nav, footer, CSP, JSON-LD)
│   ├── page.html                # Article layout (hero, TOC, content, related, tags)
│   ├── index.html               # Homepage + section listing
│   ├── taxonomy_single.html     # Category/tag pages
│   ├── editor.html              # Live CMS editor
│   ├── admin-*.html             # Admin dashboards
│   ├── f-dashboard.html         # Personal finance dashboard
│   ├── insights.html            # Admin insights (build, merge, compliance)
│   └── macros/                  # Template helpers (images, links, series, etc.)
│
├── sass/                        # SCSS stylesheets
│   ├── site.scss                # Main import (compiles to public/site.css)
│   ├── _reset.scss              # Normalize + base styles
│   ├── _typography.scss         # Type system, readability
│   ├── _brand.scss              # Color tokens, design system
│   ├── _layout.scss             # Grid, flexbox, responsive
│   ├── _components.scss         # Cards, buttons, nav
│   ├── _post.scss               # Article styles
│   ├── _editor.scss             # CMS UI
│   ├── _f-dashboard.scss        # Finance dashboard
│   ├── _responsive.scss         # Mobile overrides (≤720px)
│   └── ... (40+ partials)
│
├── static/                      # Static assets (served as-is)
│   ├── js/                      # Vanilla JavaScript modules
│   │   ├── auth-gate.js         # Google OAuth flow for CMS
│   │   ├── search.js            # Site search UI
│   │   ├── editor/              # CMS scripts
│   │   ├── f-dashboard/         # Finance tools (VietinBank parser, charts, export)
│   │   ├── l-dashboard/         # LPBank dashboard
│   │   ├── o-dashboard/         # Liobank dashboard
│   │   ├── h-dashboard/         # Invoice OCR dashboard (Tesseract.js)
│   │   └── ... (35+ modules)
│   ├── fonts/                   # Self-hosted fonts (Nokia Pure/Headline, Google Fonts preload)
│   ├── img/                     # Static images, placeholder SVGs
│   ├── css/                     # Vendor CSS (Catppuccin syntax themes)
│   └── vendor/                  # Third-party JS (highlight.js, Tesseract, etc.)
│
├── data/                        # Build-time JSON data (generated by scripts)
│   ├── seo-qa-scores.json       # SEO audit history for each post
│   ├── compliance-score.json    # Build compliance (H1, taxonomies, depth, links)
│   ├── references.json          # Internal + external links per post
│   ├── related.json             # Related posts (via embeddings)
│   ├── build-dashboard.json     # GitHub Actions build history
│   ├── merge-report.json        # PR merge history + summaries
│   ├── pagespeed.json           # Lighthouse PageSpeed snapshots
│   ├── categories.json          # Category registry
│   ├── qa-domain-selector-report.json  # Domain suggestions
│   └── ... (audit reports, state files)
│
├── scripts/                     # Python build + QA automation
│   ├── qa_check.py              # **GATEKEEPER** — conflicts, SCSS, internal links, frontmatter
│   ├── qa-404-checker.py        # Crawl public/ for broken links
│   ├── compliance_audit.py      # H1, taxonomy, depth, readability scoring
│   ├── build_references.py      # Extract internal + external links per post
│   ├── build_og_images.py       # Generate Open Graph images (cairosvg + Pillow)
│   ├── build_feed_pagination.py # Series + category pagination
│   ├── build_github_activity.py # Fetch GitHub runs, commits, activity
│   ├── seo_qa_checker.py        # On-page SEO scoring (title, description, keyword, depth)
│   ├── compliance_content_vaccine.py # Auto-fix thin articles + missing H1
│   ├── autofix_conflicts.py     # Auto-resolve merge conflicts
│   ├── vaccine_autofixer.py     # Daily vaccine application (fix known issues)
│   ├── f_dashboard_*.py         # Finance dashboard parsers (VietinBank, etc.)
│   ├── requirements-*.txt       # Pip dependencies per tool
│   └── test_*.py                # Unit tests (26+ test modules)
│
├── .github/workflows/           # GitHub Actions CI/CD
│   ├── deploy.yml               # Main: build → GitHub Pages (seomoney.org)
│   ├── qa.yml                   # Every PR: run qa_check.py, zola build, link checks
│   ├── build-related.yml        # Nightly: sentence-transformers embeddings → related.json
│   ├── pagespeed.yml            # Nightly: Lighthouse audit → pagespeed.json
│   ├── merge-report.yml         # Hourly: fetch PR merge history → merge-report.json
│   ├── domain-selector.yml      # 2h: suggest domain names → qa-domain-selector-report.json
│   ├── vaccine-autofixer.yml    # Daily 06:00 GMT+7: auto-fix known issues
│   ├── scheduled-publish.yml    # Daily 20:00 GMT+7: promote draft posts to live
│   ├── autofix-conflicts.yml    # 30m: auto-resolve merge conflicts on open PRs
│   └── ... (28 total workflows)
│
├── highlight_themes/            # Zola syntax highlighting themes
│   └── catppuccin-mocha.tmTheme # Dark theme (Catppuccin)
│
├── docs/                        # Documentation
│   ├── OPERATIONS.md            # PR / auto-merge / deploy runbook
│   ├── paywall.md               # Premium content gate setup
│   ├── security-guide.md        # CSP, auth, data protection
│   └── ...
│
├── public/                      # Build output (git-ignored, generated by `zola build`)
│   └── index.html, etc.
│
├── LICENSE                      # EUPL-1.2
└── .gitignore
```

---

## Local Development

### Requirements

- [Zola](https://www.getzola.org/documentation/getting-started/installation/) **≥ 0.22.1**
- Git
- Python **3.11+** (for build scripts and QA)

### Quick Start (Hot Reload)

```bash
git clone https://github.com/Banhang-Chogao/zola.git
cd zola
zola serve
# → http://127.0.0.1:1111 (auto-reload on file changes)
```

### Full Build (CI-like)

```bash
# Pre-build data generation
python3 scripts/build_feed_pagination.py
python3 scripts/build_references.py

# Optional: OG images, trends, GA integration
pip install -r scripts/requirements-og-images.txt
python3 scripts/build_og_images.py
python3 scripts/build_google_rank.py

# Strip premium content, then build
python3 scripts/paywall_prepare_build.py --strip
zola build
# Output: public/ (ready to deploy)
```

### Quality Checks (Before PR)

```bash
# QA gatekeeper (conflicts, SCSS, frontmatter, internal links)
python3 qa_check.py

# Full validation
python3 scripts/build_references.py
python3 scripts/check_internal_links.py
zola build
python3 scripts/compliance_audit.py --stdout

# Run all tests
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

---

## Build & Deployment

### Pull Request Workflow

| Step | Command | Details |
|------|---------|---------|
| **Create branch** | `git checkout -b feature/my-change origin/main` | Always branch from latest main |
| **Develop locally** | `zola serve` | Live preview in browser |
| **Test quality** | `python3 qa_check.py` | Gatekeeper pre-check (optional) |
| **Push & open PR** | `git push -u origin feature/my-change` then create PR on GitHub | Trigger CI automatically |
| **CI runs** | `qa.yml` executes: QA gatekeeper, Zola build, link validation, compliance audit | Auto-adds pass/fail badges |
| **Auto-merge** | When `qa-check` passes, `auto-merge.yml` merges PR to main | No manual approval needed |
| **Deploy** | `deploy.yml` runs on main: build → push to GitHub Pages | Site live at seomoney.org in ~2 min |

**Zero-barrier automation:** Every PR that passes CI is merged and deployed automatically. No bottleneck on human review.

### CI Workflows (28 total)

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **deploy.yml** | `push main` | Build site, deploy to GitHub Pages |
| **qa.yml** | Every PR | Gatekeeper (conflicts, SEO, links, compliance) |
| **build-related.yml** | Nightly | Sentence-transformers embeddings for related posts |
| **pagespeed.yml** | Nightly | Lighthouse audit (mobile/desktop) → Web Vitals dashboard |
| **merge-report.yml** | Hourly + `push main` | Fetch PR history for Insights dashboard |
| **qa-domain-selector.yml** | 2-hourly | Suggest domain names based on content analysis |
| **vaccine-autofixer.yml** | Daily 06:00 GMT+7 | Apply known fixes (safe auto-fixes + PR for risky ones) |
| **scheduled-publish.yml** | Daily 20:00 GMT+7 | Promote draft posts to live (if QA passes) |
| **autofix-conflicts.yml** | 30-minute intervals | Auto-resolve merge conflicts on open PRs |
| **build-failure-handler.yml** | `workflow_run` (deploy fail) | Auto-diagnose and fix build failures using vaccine library |
| + 18 more | Various | Analytics sync, comment moderation, data refresh, testing |

### Deploy Details

**Production:** [https://seomoney.org](https://seomoney.org) (GitHub Pages custom domain)

**Hosting:** GitHub Pages (custom domain via CNAME in repo)

**Build artifact:** Static HTML + CSS + JS in `public/`

**Deploy time:** ~2–3 minutes from merge to live

**Rollback:** Revert commit on main, push → auto-deploy previous version

---

## Content Workflow

### Writing a New Post

1. **Local edit:** Create `content/posting/my-post.md` with frontmatter:
   ```markdown
   +++
   title = "Post Title"
   description = "Meta description"
   date = 2026-06-26
   categories = ["Tất cả", "Technology"]
   tags = ["seo", "automation"]
   [extra]
   seo_keyword = "primary keyword"
   thumbnail = "image.webp"
   +++
   
   ## First Section
   ...
   ```

2. **SEO checklist:**
   - Title < 60 chars with focus keyword
   - Meta description < 155 chars
   - ≥ 1500 words (depth)
   - ≥ 5 internal links (include category hub)
   - 3–8 FAQ items in `[[extra.faq]]`
   - Include call-to-action (no dead-ends)

3. **Publish via CMS** (easier): Open `/editor/`, login with Google or GitHub PAT, paste markdown, hit Publish → auto-commits to main.

4. **Or via git:** Commit locally, push branch, open PR → CI validates → auto-merge → deploy.

5. **Preview:** Check live at seomoney.org within 2 minutes.

### Content Rules

**Categories:** All posts must have `"Tất cả"` (All) as first category, plus optional subtopic.

**Tags:** Minimum 3 tags per article (for taxonomy crawl).

**Images:** WebP only (no JPEG/PNG after optimization). Auto-generated Open Graph images from title + category.

**SEO:** Built-in compliance checker flags posts with:
- Missing focus keyword in title/intro/heading
- Weak metadata (title/description too long)
- Insufficient internal links
- Thin content (< 800 words for news, < 1500 for articles)

**Scheduled publishing:** Add `[extra] publish_at = "ISO8601+07:00"` + `draft = true` → auto-publish at scheduled time if QA passes.

---

## SEO & Analytics Integration

### Search Engine Optimization

**On-page:** Canonical URLs, meta descriptions, Open Graph, Twitter Cards, JSON-LD structured data

**Indexing:** Sitemap + robots.txt (allows Google, Bing, Mediapartners; disallows `/editor/`, `/admin/`, `/data/`)

**Internal linking:** Related posts auto-discovered via semantic embeddings (sentence-transformers, built at compile time)

**Compliance:** Automated audits check heading hierarchy (require at least one `<h1>` per page), taxonomy coverage, article depth, readability

**Crawlability:** Single-page app features (CMS, dashboards) bypass JavaScript with static HTML fallback; no client-side routing for core content

### Analytics Platforms

| Platform | Purpose | Status |
|----------|---------|--------|
| **Google Analytics 4** | User behavior, traffic sources, conversions | Connected via `config.toml` |
| **Google Search Console** | Indexing, query performance, Core Web Vitals | Verified, search performance tracked |
| **Google Programmable Search Engine** | Full-text blog search | Fallback to JSON-based search |
| **Web Vitals Dashboard** | Real user monitoring (LCP, CLS, FID) | Live at `/stats/` |

### Performance Metrics (Last Snapshot: 2026-06-18)

| Metric | Desktop | Mobile |
|--------|---------|--------|
| **Lighthouse SEO** | 100 | 100 |
| **Performance** | 95 | 58 |
| **Accessibility** | 95 | 95 |
| **Best Practices** | 92 | 92 |
| **LCP** | ~1.2s | ~6.9s |
| **CLS** | ~0 | ~0 |

**Mobile LCP priority:** Images and font loading are current optimization targets.

---

## Backend & API (VIPZone)

### VIPZone FastAPI Service

**Location:** `services/vipzone/` (Python FastAPI)

**Deployment:** Render (`blog-vipzone-api.onrender.com`)

**Purpose:** Editor sessions, auth, admin tools, premium gates, private reports

### API Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /auth/me` | Check current user session | Google OAuth + email whitelist |
| `POST /auth/login` | Start OAuth flow | None (public) |
| `GET /auth/callback` | OAuth redirect handler | None (public) |
| `GET /editor/draft` | List draft posts from GitHub | GitHub PAT scope `repo` |
| `POST /editor/publish` | Commit post to main via GitHub API | GitHub PAT |
| `GET /admin/insights` | Dashboard data (builds, merges, compliance) | Email whitelist |
| `POST /premium/<post_id>/unlock` | Verify payment, issue unlock code | Payment API + email |
| `GET /reports/<file>` | Download premium reports | Email whitelist |
| `GET /admin/comments` | Comment moderation queue | Email whitelist |

### Authentication

**Google OAuth 2.0:**
- Used by editor (`/editor/`) and new admin dashboards
- Email whitelist in `ADMIN_EMAILS` env var on Render
- Session stored in `sessionStorage` as `zola-cms-session-id`

**GitHub Token (Legacy):**
- CMS uses GitHub REST API to commit posts
- Scope: `repo` (read/write repo, public + private)
- Kept for backward compatibility; Google login is preferred for new tools

**Session Management:**
- Client: `sessionStorage` key `zola-cms-session-id`
- Backend: Cookie-based or JWT (implementation detail)
- Logout: Clear `sessionStorage` + `/auth/logout`

### Data Security

- **No database at seomoney.org:** Static site has zero server-side state
- **Backend secrets:** All sensitive keys (SMTP, OAuth, GitHub tokens) stored in Render env vars, never committed
- **User data:** Email + session metadata only; no persistent analytics PII
- **Paywall:** Premium content stays off static site until unlocked; full PDF watermarked with user email hash + trace ID

---

## Admin & Internal Tools

### Dashboard Suite

**Location:** `/insights/` (Insights main hub)

| Tool | URL | Purpose |
|------|-----|---------|
| **Merge Report** | `/insights/` | PR history, contributor activity, merge trends |
| **Build Monitor** | `/insights/` | GitHub Actions run history, deploy status, cancellations |
| **Compliance Score** | `/insights/` | H1 coverage, taxonomy depth, article quality, link health |
| **Vaccine Autofixer** | `/insights/` | Daily fix status, matched vaccines, auto-applied repairs |
| **Domain Suggestions** | `/insights/` | AI-suggested domains based on blog content, availability status |

### Editor (CMS)

**Location:** `/editor/`

**Auth:** Google login or GitHub PAT

**Features:**
- Live markdown preview
- Frontmatter editor (title, description, categories, tags, SEO keyword)
- Publish directly to main via GitHub REST API
- Draft auto-save (in-browser `IndexedDB`)

### Personal Finance Dashboards

| Tool | URL | Purpose |
|------|-----|---------|
| **F-Dashboard** | `/tools/f-dashboard/` | VietinBank statement upload & analysis |
| **L-Dashboard** | `/tools/l-dashboard/` | LPBank PDF import |
| **O-Dashboard** | `/tools/o-dashboard/` | Liobank PDF analysis |
| **H-Dashboard** | `/tools/h-dashboard/` | Invoice/receipt OCR + categorization (Tesseract.js) |

**Security:** All data stays in browser (`IndexedDB` AES-GCM encrypted). Export PDF/JSON → auto-wipe local storage. No upload to server.

### SEO Dashboard

**Location:** `/seo-bang-vang/` (SEO Scoreboard)

**Data:** `data/seo-qa-scores.json` (per-post on-page SEO scoring)

**Scoring:** 0–100 points based on title, keyword placement, internal links, depth, metadata completeness

**History:** Tracks improvements over time; visible only to admin

---

## Security & Privacy

### Content Security Policy (CSP)

**Base:** `base.html` contains `<meta>` CSP header (GitHub Pages doesn't support HTTP headers).

**Key directives:**
- `default-src 'self'`
- `script-src 'self' 'unsafe-inline' (for analytics script tags) cdn.jsdelivr.net`
- `style-src 'self' 'unsafe-inline'` (Zola compiled CSS)
- `img-src 'self' data: https:` (local + external images, including OG)
- `font-src 'self'` (self-hosted fonts)
- `connect-src 'self' https://www.google-analytics.com` (GA4 tracking)
- `frame-src giscus.app` (comments iframe, legacy)

**Updates for dashboards:**
- **H-Dashboard (invoice OCR):** Adds `worker-src 'self' blob: https://cdn.jsdelivr.net` + `connect-src https://tessdata.projectnaptha.com` (Tesseract.js core + traineddata)

### Data Protection

**Personal data:** None persisted on server by default (dashboards are client-side).

**Passwords:** Not stored. Auth via Google/GitHub OAuth.

**Reports:** Premium reports watermarked with user email hash (format: `{SHA256(email)[:16]}_{domain}`) for tracing.

**Paywall:** Premium post content never in `public/`; stored on backend, delivered post-payment only.

### Robot Access

**robots.txt:**
- Allow: `Googlebot`, `Bingbot`, `Mediapartners-Google`
- Disallow: `/editor/`, `/admin/`, `/data/`, other private paths

**Indexing:** Canonical URLs prevent duplicate content issues. No `noindex` on public posts.

---

## Development Workflow & Automation

### QA Gatekeeper (`qa_check.py`)

Runs on every PR. Fails the build if:

- **Conflict markers** found (unresolved merge conflicts)
- **Frontmatter syntax** invalid
- **SCSS syntax errors**
- **Internal links broken** (missing files/anchors)
- **SEO issues** (missing metadata, thin content)

Fix errors locally, push again → CI re-runs automatically.

### Auto-Merge Policy

**Rule:** When `qa-check` passes on a PR, `auto-merge.yml` automatically merges to main within seconds.

**No manual approval required.** This is zero-barrier automation to unblock rapid iteration.

**Override:** Add label `do-not-merge` to skip auto-merge (used for work-in-progress branches).

### Vaccine Library

**File:** `CLAUDE.md` § 4 (Thư Viện Vaccine)

**Purpose:** Catalog of known build failures + automated fixes. When CI fails, check against vaccine deastures → apply fix → rebuild.

**Examples:**
- V1: HuggingFace model ID format (`sentence-transformers/` prefix required)
- V2: Slack action version bump (v1 → v3 API change)
- V3–V12: Template conflicts, data file regen, series registration, compliance fixes

**Auto-apply:** Daily via `vaccine-autofixer.yml` (06:00 GMT+7) for safe fixes; risky fixes go to PR for review.

### Scheduled Publishing

**Draft posts:** Add `[extra] publish_at = "2026-06-27T20:00:00+07:00"` to schedule.

**Promotion:** `scheduled-publish.yml` runs daily at 20:00 GMT+7, checks QA, promotes to live if passing.

**Benefit:** Batch publish evening content without blocking other work.

---

## Repository Structure Quick Reference

| Path | Purpose |
|------|---------|
| `content/posting/` | Main blog articles (150+) |
| `content/baochi/` | Curated news |
| `content/tools/` | Tools & dashboards |
| `content/pages/` | Static pages (about, privacy, etc.) |
| `templates/` | Tera layouts |
| `sass/` | SCSS styles |
| `static/js/` | Vanilla JavaScript modules |
| `scripts/` | Python build + QA automation |
| `.github/workflows/` | 28 CI/CD workflows |
| `data/` | Generated JSON (compliance, SEO, reports) |
| `docs/` | Documentation (OPERATIONS, paywall, security) |
| `services/vipzone/` | FastAPI backend (editor, auth, admin) |

---

## Key Features

### Content Management

- ✅ Web-based CMS editor with live markdown preview
- ✅ Publish directly via GitHub REST API (no git CLI needed)
- ✅ Scheduled publishing (draft → live auto-promotion)
- ✅ Multi-language support (Vietnamese + English)
- ✅ Rich metadata (SEO keyword, thumbnail, series, FAQ, extra.* custom fields)

### SEO & Discovery

- ✅ Compliance audits (H1, taxonomy, depth, readability)
- ✅ Internal link validation (crawl-time static checks)
- ✅ Open Graph + Twitter Cards (auto-generated images)
- ✅ JSON-LD structured data (Article, FAQ, Breadcrumb)
- ✅ Related posts (semantic embeddings via sentence-transformers)
- ✅ Sitemap + RSS/Atom feeds
- ✅ Canonical URLs (prevent duplicate indexing)

### Quality Assurance

- ✅ QA gatekeeper on every PR (conflicts, syntax, links, SEO)
- ✅ Compliance score tracking (H1, taxonomy, article depth)
- ✅ Build failure handler (auto-diagnose + suggest fixes)
- ✅ Vaccine library (28+ known issue patterns + auto-fixes)
- ✅ Conflict auto-resolver (merge conflicts on PRs)
- ✅ Link validation crawl (broken internal links gate the build)

### Analytics & Monitoring

- ✅ Google Analytics 4 integration
- ✅ Web Vitals real-user monitoring dashboard
- ✅ PageSpeed Insights snapshots (Lighthouse audits)
- ✅ Build + deploy monitoring (GitHub Actions run history)
- ✅ Merge report (PR history, contributor activity)

### Admin Dashboard

- ✅ Insights hub (`/insights/` — merge reports, build monitor, compliance score, vaccine status)
- ✅ Domain suggestions (AI-powered domain name ideas)
- ✅ Comment moderation queue
- ✅ Paywall unlock approvals
- ✅ SEO scoreboard (`/seo-bang-vang/` — on-page metrics per post)

### Personal Finance Tools

- ✅ F-Dashboard (VietinBank statement upload + spending analysis)
- ✅ L-Dashboard (LPBank PDF import)
- ✅ O-Dashboard (Liobank analysis)
- ✅ H-Dashboard (Invoice/receipt OCR via Tesseract.js)
- ✅ Export to PDF/JSON/CSV with watermark + encryption

---

## Roadmap & Active Modules

### Recently Added (2026)

- ✅ Native Google login for comments (replacing Giscus)
- ✅ FastAPI VIPZone backend (editor, auth, admin tools)
- ✅ Vaccine autofixer (daily automated fixes)
- ✅ Build dashboard (GitHub Actions monitoring)
- ✅ Merge report (PR history tracking)
- ✅ Personal finance dashboards (F/L/O/H suite)
- ✅ Domain name suggester (AI-powered naming)
- ✅ Multi-series content support (topic clusters)

### Planned / In Development

- 🚧 Premium paywall gates (MoMo payment + unlock codes)
- 🚧 Improved mobile LCP (image optimization + font preloading)
- 🚧 Automated trending topics detector
- 🚧 SEO competitor analysis dashboard
- 🚧 Scheduled social media auto-posting
- 🚧 Comment analytics (engagement tracking)

---

## Contributing

This is a personal blog/product. If you spot a bug or have suggestions:

1. **Open an issue** on [GitHub Issues](https://github.com/Banhang-Chogao/zola/issues)
2. **For security issues:** Email author directly (do not open public issue)
3. **For content:** Contributions are case-by-case; contact author first

---

## License

**EUPL-1.2** (European Union Public License 1.2)

**Content:** © 2026 Duy Nguyen — Blog articles and curated content are copyrighted. Reuse subject to content terms.

**Code:** Open under EUPL-1.2. See [LICENSE](LICENSE) file.

---

## Author

**Duy Nguyen** ([@duynguyenlog](https://github.com/Banhang-Chogao))

- Blog: [seomoney.org](https://seomoney.org)
- GitHub: [Banhang-Chogao](https://github.com/Banhang-Chogao)
- Built with [Zola](https://www.getzola.org/)

---

## Quick Links

| Resource | Link |
|----------|------|
| **Blog** | [https://seomoney.org](https://seomoney.org) |
| **Editor (CMS)** | [/editor/](/editor/) |
| **Insights Dashboard** | [/insights/](/insights/) |
| **SEO Scoreboard** | [/seo-bang-vang/](/seo-bang-vang/) |
| **Web Vitals** | [/stats/](/stats/) |
| **Operations Runbook** | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| **Repository** | https://github.com/Banhang-Chogao/zola |
| **License** | [EUPL-1.2](LICENSE) |

---

**Last updated:** 2026-06-26  
**Commit:** Ready for branch `claude/seomoney-readme-rebuild-od348t`
