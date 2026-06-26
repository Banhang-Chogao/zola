# SEOMONEY Blog

[![Built with Zola](https://img.shields.io/badge/Built%20with-Zola-00aaff?style=flat-square)](https://www.getzola.org/)
[![Python](https://img.shields.io/badge/Python-36.2%25-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![HTML](https://img.shields.io/badge/HTML-22.5%25-E34F26?style=flat-square&logo=html5)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![JavaScript](https://img.shields.io/badge/JavaScript-22.1%25-F7DF1E?style=flat-square&logo=javascript)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![SCSS](https://img.shields.io/badge/SCSS-17.9%25-CC6699?style=flat-square&logo=sass)](https://sass-lang.com/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions)](https://github.com/features/actions)
[![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat-square&logo=render)](https://render.com/)
[![Storage](https://img.shields.io/badge/Storage-Cloudflare%20R2-orange?style=flat-square&logo=cloudflare)](https://developers.cloudflare.com/r2/)

> **Live Site:** [seomoney.org](https://seomoney.org/)

---

## 📋 Overview

| Aspect | Details |
|--------|---------|
| **Project** | SEO-focused blog at seomoney.org |
| **Static Site Generator** | Zola v0.22.1 |
| **Content** | Bilingual (Vietnamese/English) |
| **Hosting** | Cloudflare R2 + CDN |
| **Deployment** | Render via `render.yaml` |
| **CI/CD** | GitHub Actions (auto-fixes, compliance scoring, heartbeat) |

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|-------------|
| **Languages** | Python 36.2%, HTML 22.5%, JavaScript 22.1%, SCSS 17.9%, CSS 1.1%, Shell 0.1% |
| **Styling** | SCSS with Nokia-inspired theme (opt-in color switcher) |
| **Scripts** | `qa_check.py`, `seo_engine.js`, `push.sh`, `qa-domain-selector.py`, `qa-failed.py` |
| **Automation** | GitHub Actions, pre-commit hooks, Makefile |
| **Security** | Malware/injection scanning in `/reports` |

---

## 📂 Project Structure

```text
.
├── content/      # Blog posts (bilingual)
├── templates/    # Zola templates
├── sass/         # SCSS styling
├── static/       # Static assets
├── scripts/      # Automation scripts
├── backend/      # Backend utilities
├── services/     # Service integrations
├── ops/          # Operations scripts
├── reports/      # Security & compliance reports
├── data/         # Generated data (compliance scores)
├── memory/       # Project memory/context
├── tests/        # Test fixtures
├── config.toml   # Zola configuration
├── render.yaml   # Render deployment config
└── CLAUDE.md     # AI-assisted development rules
```

---

## 🔑 Key Scripts

| Script | Purpose |
|--------|---------|
| `qa_check.py` | Full-repo QA gatekeeper — conflict, secret, SEO, SCSS & vaccine checks |
| `seo_engine.js` | SEO engine — schema, meta, sitemap & internal-link generation |
| `push.sh` | Branch push helper for the CI/CD flow |
| `qa-domain-selector.py` | Domain selection & validation for QA / deploy targeting |
| `qa-failed.py` | QA failure triage & remediation reporting |

---

## 🚀 Key Features

### Content & SEO
- ✅ Bilingual blog posts (Vietnamese/English)
- ✅ Tags & categories support
- ✅ Automated frontmatter validation

### Infrastructure
- ✅ **Storage:** Cloudflare R2 with CDN integration
- ✅ **Deployment:** Render via `render.yaml`
- ✅ **CI/CD:** GitHub Actions (auto-fixes, compliance scoring, heartbeat)
- ✅ **Security:** Malware/injection scanning in `/reports`
- ✅ **Operations:** `ops/` directory for operational scripts
- ✅ **Memory:** `memory/` for persistent project context

### Quality Assurance
- ✅ Automated compliance scoring & auto-fix pipelines
- ✅ Pre-commit hooks for code quality
- ✅ QA scripts: `qa_check.py`, `qa-domain-selector.py`, `qa-failed.py`

---

## 🔧 Recent Updates

- ✅ **Re-enabled Cloudflare R2 connection** (opt-out kill-switch + CDN enhancement)
- ✅ **Removed hash prefix** from footer tags for cleaner appearance
- ✅ **Bilingual case-study** on fixing 7 failed CI/CD PRs
- ✅ **Nokia theme Phase 1** with opt-in color switcher
- ✅ **Full malware/injection scan** completed (no malware found)

---

## 🛠️ Development

### Prerequisites
- [Zola v0.22.1](https://www.getzola.org/documentation/getting-started/installation/)
- Python 3.x (for QA scripts)
- Make

### Quick Start
```bash
# Clone the repository
git clone https://github.com/Banhang-Chogao/zola.git
cd zola

# Serve locally
zola serve

# Build production
zola build

# Run QA checks
python qa_check.py
```

---

## 🔄 CI/CD Pipeline

The repository follows a **zero-barrier** automation doctrine — the machine verifies, fixes, merges, and deploys:

```text
Code → Push Branch → Auto PR Gatekeeper → Merge Conflict Preflight
     → QA Gatekeeper → Auto Merge → Deploy Production
```

Required gates that can never be bypassed: **merge conflicts**, **secret leaks**, **build failures**, and **QA failures**. CI must be green before merge.

### Automated workflows
- **GitHub Actions:** auto-fixes, compliance scoring, heartbeat
- **Pre-commit hooks:** code quality enforcement
- **Render:** automatic deployment on push

---

## 📊 Project Status

| Metric | Value |
|--------|-------|
| **Commits** | 227 |
| **Contributors** | 4 |
| **Last Commit** | Jun 26, 2026 |
| **Languages** | Python, HTML, JavaScript, SCSS, CSS, Shell |

---

## 🤝 Contributors

- **Banhang-Chogao (Duy Nguyen)** — Project Lead
- **claude** — AI-assisted development
- **github-actions[bot]** — CI/CD automation
- **dependabot[bot]** — Dependency management

---

## 📝 License

See the [`LICENSE`](./LICENSE) file for details.

---

<p align="center">Built with ❤️ and the <a href="https://www.getzola.org/">Zola</a> static site generator</p>
