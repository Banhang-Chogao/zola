# Quy trình vận hành — ZERO_BARRIER_AUTOMATION

> **Hiệu lực:** 18/06/2026. Vẫn qua PR; **100% auto-merge** khi CI pass → deploy production ngay.

## Nguyên tắc

Mọi thay đổi **phải đi qua Pull Request**. **Không** push/commit trực tiếp `main`.

**Auto-merge:** `auto-merge.yml` + `scripts/try_auto_merge.py` — policy `data/auto-merge-policy.json`.

**Required checks (job names):** `qa-check` (QA Gatekeeper). Build + link checker nằm trong `qa-check`. Không có PR Policy gate.

**Manual review:** ❌ Không — blog sạch, không protected domain, không label chặn.

**Theo dõi:** `data/merge-report.json` (script `fetch_merge_report.py`).

**Workflow fail trên main:** `build-failure-handler.yml` + `qa-rule-checker.yml` auto-trigger → phân tích + auto-fix PR → auto-merge khi CI pass.

## Quy trình cho mỗi yêu cầu

1. `git fetch origin main && git checkout -b <prefix>/<mô-tả> origin/main`
2. Commit toàn bộ thay đổi của **một** yêu cầu/tính năng
3. `git push -u origin <branch>` → tạo PR vào `main`
4. CI pass → **auto-merge** (không chờ review tay)
5. `deploy.yml` chạy sau merge → build & deploy production
6. `merge-report.yml` cập nhật lịch sử merge

### Quy ước tên branch

| Prefix | Dùng khi |
|--------|----------|
| `feature/` | Tính năng mới |
| `fix/` | Sửa bug |
| `qa/` | QA checker, audit automation |
| `content/` | Bài viết, copy |
| `chore/` | Data refresh, changelog, tooling |
| `policy/` | Rule, CI, branch protection |

Ví dụ: `fix/performance-audit-checker`, `qa/lighthouse-auto-checker`

## Build failed trên PR

- Chỉ thêm commit fix vào **cùng branch/PR**
- Không push `main`
- Không tạo PR mới trừ khi là yêu cầu/tính năng khác

## Automation (GitHub Actions / bot)

Workflow automation **không được** `git push origin HEAD:main`.

Pattern: `.github/scripts/push_via_pr.sh` → branch riêng → PR → **auto-merge** khi CI pass.

Workflow tuân thủ: `auto-merge`, `merge-report`, `perf-audit`, `self-healing`, `pagespeed`, `build-dashboard`, `ga-stats`, `changelog-update`, `scheduled-publish`, `optimize-images`, `compliance-score`, `build-related`, `security-audit`, `qa-rule-checker` (schedule 48h + `workflow_dispatch` + fail-trigger).

## Branch protection (`main`)

Cấu hình khuyến nghị (Settings → Branches → Add rule):

- Require pull request before merging
- Required approvals: **0** (auto-merge — xem `.github/BRANCH-PROTECTION.md`)
- Dismiss stale approvals when new commits are pushed
- Require status checks: `QA Gatekeeper` / `qa-check`
- Require conversation resolution
- **Do not allow bypassing** (kể cả admin, kể cả bot)
- Restrict who can push: **nobody** (chỉ merge qua PR)
- Allow force pushes: **disabled**
- Allow deletions: **disabled**

Chi tiết: [.github/BRANCH-PROTECTION.md](../.github/BRANCH-PROTECTION.md)

## Deploy production

Deploy **chỉ** xảy ra khi PR đã được merge vào `main` (push event từ merge). Đây là luồng hợp lệ duy nhất để cập nhật production.

## QA theo severity (deployment immune system)

QA là **deployment immune system**, không phải cảnh sát chặn deploy. Chỉ chặn lỗi
thật sự làm hỏng production; còn lại report / auto-heal / đưa vào backlog.

```text
PASS       nếu P0 == 0 và build thành công.
AUTO_HEAL  nếu P1 > 0 và có known safe fix.
FAIL       chỉ khi P0 > 0, hoặc auto-healing đã thử nhưng vẫn fail.
P2 / P3    không bao giờ block deploy.
```

- **P0** (hard block): `zola build` vỡ · Tera/SCSS lỗi · frontmatter TOML invalid ·
  conflict markers · workflow YAML invalid · secret commit · critical route hỏng
  (homepage/nav/sitemap/canonical/editor-admin) · auth/VIPZone nguy hiểm.
- **P1** (auto-heal / hotfix PR): generated JSON conflict · report stale · missing
  generated data có script regen · known vaccine pattern. Thử auto-heal **trước** khi fail.
- **P2** (advisory, không block): SEO/title/thin-content/FAQ/internal-link/compliance/
  PageSpeed/external-link/GA-GSC fetch fail → ghi report cho Editor/Insights.
- **P3** (info): UX/taxonomy/internal-linking/OG suggestions.

Chi tiết đầy đủ + auto-healing + public/private agent memory: **`../CULTURE_OF_DEPLOYMENT.md`**.

## Tài liệu liên quan

- `../CULTURE_OF_DEPLOYMENT.md` — deployment & QA culture, severity model, auto-healing
- `CLAUDE.md` — rule cho AI agent (public-safe; private memory → `CLAUDE_PRIVATE.md`, gitignored)
- `shortcuts.md` §4.5 — rule cho phím tắt
- `.github/workflows/main-guard.yml` — chặn push trực tiếp (bot + human không qua PR)