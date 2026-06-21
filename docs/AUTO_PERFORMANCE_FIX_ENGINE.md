# Auto Performance Fix Engine — Production Implementation Guide

## Overview

The Auto Performance Fix Engine is a production-grade system that:

1. **Fetches real data** from Google PageSpeed Insights API and GA4 Data API
2. **Detects issues** automatically (LCP > 2.5s, CLS > 0.1, SEO < 90, Perf < 90)
3. **Applies safe, reversible fixes** to code (templates, SCSS, content)
4. **Verifies changes** via QA check and Zola build
5. **Commits changes** via git (through GitHub Actions PR workflow)

## Architecture

```
┌─────────────────────────────────────┐
│  Google PageSpeed Insights API      │ (public, 25k/day free quota)
│  Google Analytics 4 Data API        │ (requires service account)
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Auto Performance Fix Engine        │
│  (scripts/auto_performance_fix_engine.py)
└──────────────┬──────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
  FETCH    ANALYZE    APPLY FIXES
     │         │         │
     └─────────┼─────────┘
               ▼
        ┌──────────────┐
        │ VERIFY BUILD │
        └──────┬───────┘
               ▼
        ┌──────────────────┐
        │  COMMIT + PR     │
        │  (GitHub Actions)│
        └──────────────────┘
```

## Thresholds

The engine targets Google Lighthouse standards:

| Metric | Target | Severity if below |
|--------|--------|-------------------|
| Mobile Performance | 90 | Critical if <50 |
| Desktop Performance | 90 | Critical if <50 |
| LCP (Largest Contentful Paint) | 2.5s | Critical if >4s |
| CLS (Cumulative Layout Shift) | 0.1 | Warning |
| FCP (First Contentful Paint) | 1.8s | — |
| SEO Score | 90 | Warning |

## Auto-Fix Rules

### 1. LCP > 2.5s → Lazy Loading + Preload

**Applied to:** Images in article content, thumbnails, hero images

**Changes:**
- Add `loading="lazy" decoding="async"` to `<img>` tags
- Preload hero/LCP images in `<head>`
- Optimize image dimensions + aspect-ratio CSS

**Reversibility:** ✅ Safe — only adds attributes, no content removal

**Example:**
```html
<!-- Before -->
<img src="hero.webp" alt="Hero" />

<!-- After -->
<img src="hero.webp" alt="Hero" loading="lazy" decoding="async" />
```

### 2. CLS > 0.1 → Image Dimensions + Aspect Ratio

**Applied to:** All images in templates and content

**Changes:**
- Add `width` / `height` attributes to images
- Add CSS `aspect-ratio` rules
- Add `object-fit: cover` for images in cards

**Reversibility:** ✅ Safe — CSS-only, no markup removal

**Example:**
```scss
/* New file: sass/_perf-images.scss */
img {
  aspect-ratio: auto;
  max-width: 100%;
  height: auto;
}

.post-card__image {
  aspect-ratio: 16 / 10;
  width: 100%;
  object-fit: cover;
}
```

### 3. SEO < 90 → Meta Tags + Schema

**Applied to:** `templates/base.html`

**Changes:**
- Ensure canonical URL is present
- Inject OpenGraph (og:image, og:title, og:description)
- Add JSON-LD schema (Article, FAQPage, BreadcrumbList)

**Reversibility:** ✅ Safe — only adds meta tags

### 4. Performance < 90 → CSS/JS Analysis

**Applied to:** Identified files with unused rules/code

**Changes:**
- Report unused CSS via PageSpeed Insights (manual review needed)
- Report unused JavaScript
- Suggest critical CSS extraction

**Reversibility:** ⚠️ Requires manual review — changes flagged for operator

## Fetch Real Data

### PageSpeed Insights API

The engine calls the **public Google PageSpeed Insights v5 API** (no auth required, 25k/day free quota).

**Endpoint:**
```
https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy={mobile|desktop}
```

**Output stored in:** `data/pagespeed.json`

**Data includes:**
- Performance / Accessibility / Best Practices / SEO scores
- Core Web Vitals: LCP, CLS, FCP, INP, TBT
- Resource breakdown (JS, CSS, images, fonts)
- Opportunities (unused CSS/JS, lazy loading, image optimization)

### GA4 Data API

The engine uses **Google Analytics 4 Data API** to fetch organic search metrics.

**Requires:** GitHub Secret `GA_SERVICE_ACCOUNT_KEY` (JSON service account with Analytics Viewer role)

**Query:** Last 7 days organic search
```
Property: 542421812 (seomoney.org GA4 property)
Filter: sessionDefaultChannelGroup = "Organic Search"
Metrics: activeUsers, sessions, screenPageViews
```

**Output stored in:** Report includes GA4 metrics (no separate file)

## Lock & Deduplication

The engine maintains `data/auto-performance-fix-state.json` to prevent:

1. **Concurrent runs:** Only one execution at a time
2. **Duplicate fixes:** Same issue won't be fixed twice in rapid succession
3. **Stale lock:** Lock expires after 30 minutes of inactivity

**Lock format:**
```json
{
  "last_run": "2026-06-21T10:15:30+07:00",
  "last_report_path": "data/auto-performance-fix-report.json",
  "status": "success"
}
```

## Usage

### CLI

```bash
# Default: fetch live API + apply safe fixes
python3 scripts/auto_performance_fix_engine.py

# With PageSpeed API key (higher quota)
python3 scripts/auto_performance_fix_engine.py \
  --pagespeed-key YOUR_API_KEY

# Dry-run: detect issues without applying fixes
python3 scripts/auto_performance_fix_engine.py --dry-run

# Offline: use cached PageSpeed data, skip GA4
python3 scripts/auto_performance_fix_engine.py --offline

# Skip build verification
python3 scripts/auto_performance_fix_engine.py --no-build

# Clear stale lock
python3 scripts/auto_performance_fix_engine.py --release-lock
```

### GitHub Actions Workflow

**File:** `.github/workflows/auto-performance-fix.yml`

**Triggers:**
- **Schedule:** Daily at 03:00 UTC (10:00 Asia/Ho_Chi_Minh)
- **Manual:** `workflow_dispatch` from GitHub Actions tab

**What it does:**
1. Fetches PageSpeed + GA4 data
2. Detects issues
3. Applies safe fixes
4. Verifies build
5. Creates/updates PR with changes (if fixes detected)
6. PR auto-merges if QA passes

## Output Reports

### Main Report: `data/auto-performance-fix-report.json`

```json
{
  "timestamp": "2026-06-21T10:15:30+07:00",
  "status": "success",
  "pagespeed_score_mobile": 57,
  "pagespeed_score_desktop": 83,
  "issues_detected": 3,
  "issues": [
    {
      "category": "lcp",
      "severity": "critical",
      "strategy": "mobile",
      "current_ms": 7882,
      "target_ms": 2500,
      "delta_ms": 5382
    },
    {
      "category": "performance",
      "severity": "critical",
      "strategy": "mobile",
      "current": 57,
      "target": 90,
      "delta": -33
    }
  ],
  "fixes_applied": 2,
  "fixes": [
    {
      "type": "img_lazy_loading",
      "status": "applied",
      "message": "Added lazy loading + decoding=async to images"
    },
    {
      "type": "img_dimensions",
      "status": "applied",
      "message": "Enforced aspect-ratio + explicit width/height on images"
    }
  ],
  "build_verified": true,
  "ga4_organic": {
    "users": 145,
    "sessions": 312,
    "pageviews": 654,
    "metric_date": "2026-06-21T10:15:00+07:00",
    "period": "7days"
  },
  "dry_run": false
}
```

### State File: `data/auto-performance-fix-state.json`

```json
{
  "last_run": "2026-06-21T10:15:30+07:00",
  "last_report_path": "data/auto-performance-fix-report.json",
  "status": "success"
}
```

### Log File: `data/auto-performance-fix.log`

Timestamped log of all steps:
```
[10:15:30] INFO: === Auto Performance Fix Engine Starting ===
[10:15:32] INFO: Step 1: Fetching real API data...
[10:15:45] INFO: PageSpeed: mobile 57/100, desktop 83/100
[10:15:46] INFO: Step 2: Detecting issues...
[10:15:46] INFO: Found 3 issue(s)
[10:15:47] INFO: Step 3: Applying safe fixes...
[10:15:49] INFO: Step 4: Verifying build...
[10:15:52] INFO: Build verification passed
[10:15:55] INFO: === Engine Complete: success ===
```

## GitHub Actions Integration

### Environment Secrets Required

```
GA_SERVICE_ACCOUNT_KEY=<JSON service account key with Analytics Viewer role>
WORKFLOW_BOT_PAT=<GitHub token for creating/updating PRs>
```

### PR Workflow

When the engine detects fixes:

1. **Creates/updates branch:** `auto-performance-fix`
2. **Creates/updates PR:** Titled `🚀 perf: Auto-fix performance issues (N fixes)`
3. **PR body includes:**
   - PageSpeed metrics (mobile/desktop scores)
   - Issues detected (category, severity, strategy)
   - Fixes applied (type, status, message)
   - GA4 organic search metrics
4. **Auto-merge:** When QA check passes
5. **Deploy:** Automatic via `deploy.yml`

### Concurrency

- Only one engine run at a time (lock-based)
- Prevents race conditions during rapid issue detection/fix cycles
- Lock expires after 30 minutes of inactivity

## Safety & Reversibility

### Safe Fixes (Deterministic, Reversible)

✅ Lazy loading attributes (`loading="lazy"`)
✅ Image dimensions (width/height)
✅ Aspect-ratio CSS rules
✅ Meta tags injection
✅ Schema markup

**Reversibility:** All changes can be reverted via `git revert <commit>`

### Risky Changes (Require Manual Review)

⚠️ CSS minification / dead-code removal
⚠️ JavaScript bundling changes
⚠️ Critical CSS extraction

These are **reported only** (not auto-applied). Operator must review in PR.

### Never Applied

❌ Content removal
❌ Breaking template changes
❌ Invasive refactors

## Testing

```bash
# Run unit tests
python3 -m unittest scripts.test_auto_performance_fix_engine -v

# Test detection logic
python3 -c "
from scripts.auto_performance_fix_engine import detect_issues
pagespeed = {
    'mobile': {'lcp_ms': 5000, 'cls_value': 0, 'performance': 50, 'seo': 100},
    'desktop': {'lcp_ms': 1500, 'cls_value': 0, 'performance': 85, 'seo': 100}
}
result = detect_issues(pagespeed)
print(f'Issues: {result[\"issue_count\"]}')
"

# Dry-run the engine
python3 scripts/auto_performance_fix_engine.py --dry-run --offline
```

## Troubleshooting

### Lock Stuck

```bash
python3 scripts/auto_performance_fix_engine.py --release-lock
```

### API Errors

- **PageSpeed:** Free quota (25k/day) — can pass API key via `--pagespeed-key`
- **GA4:** Requires service account with Analytics Viewer role — check `GA_SERVICE_ACCOUNT_KEY` secret
- **Offline mode:** Use `--offline` to skip API calls and use cached data

### Build Verification Failed

Check build errors:
```bash
zola build
python3 scripts/qa_check.py
```

Revert the last auto-fix PR if needed.

## Monitoring

### Insights Dashboard

The engine report is consumed by `/zola/insights/` dashboard:
- **Performance card:** Mobile/Desktop scores from latest PageSpeed run
- **Issues card:** Count and severity of detected issues
- **GA4 organic card:** 7-day organic search metrics
- **Auto-fix timeline:** History of applied fixes

### Alerts

Set up monitoring for:
- `data/auto-performance-fix-report.json` status = "error" (check workflow logs)
- Performance regressions (score drops between runs)
- GA4 organic search decline (5+ session drop in one day)

## FAQ

**Q: Why not auto-apply all fixes?**
A: Some fixes (CSS dead-code removal, JS bundling) require manual review to avoid regressions. The engine focuses on safe, deterministic changes and reports risky ones.

**Q: Does this require a Google API key?**
A: PageSpeed Insights API is public (25k/day free quota). GA4 API requires a service account (add `GA_SERVICE_ACCOUNT_KEY` secret to GitHub).

**Q: How often should the engine run?**
A: Daily (default schedule: 10:00 Asia/Ho_Chi_Minh). PageSpeed data is cached, so frequent runs use fresh local data until the next API call.

**Q: Can I disable auto-merge for engine PRs?**
A: Yes — add a label or comment on the PR to prevent auto-merge. Or modify the workflow to require manual approval.

**Q: What if the build breaks?**
A: The engine verifies build before committing. If verification fails, no PR is created. Check logs for root cause.

## References

- [Google PageSpeed Insights API](https://developers.google.com/speed/docs/insights/v5/about)
- [Google Analytics 4 Reporting API](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [Lighthouse Scoring](https://developer.chrome.com/docs/lighthouse/performance/scoring/)
- [Web Vitals](https://web.dev/vitals/)
