# AdSense Audit System + Content Direction Integration Plan

**Status:** Planning phase  
**Date:** 2026-06-27  
**Target:** Unified content optimization system  
**Owner approval:** Pending

---

## Vision

SEOMONEY will have **one central place** to understand:
1. **AdSense monetization health** (daily, automated)
2. **Content optimization roadmap** (continuous, data-driven)
3. **Internal content map** (orphan posts, link gaps, clusters)

Three tools work together, not in isolation:
- **AdSense Audit V1** — Static archive (reference)
- **AdSense Audit V2** — Daily automated analysis + suggestions
- **Content Direction** — Internal linking map, topic clusters, orphan detection
- **AdSense Audit V3** (future) — Continuous "what to write next" engine

---

## Route Architecture (Final State)

```
/ad-report/                 ← Hub: latest recommendations + version cards
  ├─ V1 Archive card → /ad-report-v1/
  ├─ V2 Daily Audit card → /ad-report-v2/
  ├─ V3 Optimization card → /ad-report-v3/
  └─ Content Direction card → /tools/content-direction/

/ad-report-v1/              ← Static snapshot (2026-06-19)
/ad-report-v2/              ← Daily automated, fresh data, shows suggestions
/ad-report-v3/              ← Future: continuous optimization (not built yet)

/tools/content-direction/   ← Automated cluster map, orphans, link gaps
```

**Navigation (long-term):**
```
Công cụ → SEO & Phân tích → AdSense Audit → /ad-report/
```

No V1/V2/V3 as separate menu items. One entry point, version cards inside.

---

## PR Breakdown Strategy

### PR 1: Automation + Versioning (IMMEDIATE)

**Title:** `feat(automation): add content-direction workflow + ad-report versioning`

**Scope:**
- Add `.github/workflows/content-direction.yml` (daily cron + dispatch + PR-on-change)
- Add `/ad-report-v1/` alias to `content/ad-report.md`
- Add deprecation notice to V1: "See [V2 (daily automated)](/ad-report-v2/)"
- Add notice to V2: "See [all versions](/ad-report/) or [content map](/tools/content-direction/)"
- **Do NOT convert `/ad-report/` into hub yet**
- **Do NOT add suggestions section yet**
- **Do NOT build V3**

**Files changed:**
```
.github/workflows/content-direction.yml      (NEW)
content/ad-report.md                         (MODIFY: add alias + notice)
templates/ad-report-v2.html                  (MODIFY: add notice only)
templates/content-direction.html             (optional: add freshness note)
```

**QA:**
- `python3 scripts/content_direction.py` runs without error
- `data/content-direction/report.json` updated with fresh timestamp
- Workflow lint checks pass
- Routes `/ad-report/`, `/ad-report-v1/`, `/ad-report-v2/` all resolve

**Risk:** Low  
**Reversibility:** Yes — all changes are additive or move-only  
**Approval needed:** PR review + approval before merge

---

### PR 2: AdSense Hub + Version Navigation (AFTER PR 1)

**Title:** `feat(adsense): add audit hub and report version navigation`

**Scope:**
- Convert `/ad-report/` into a hub page (new or modified template)
- Move V1 canonical content to `/ad-report-v1/` (update aliases)
- Create `/ad-report/hub.html` template showing version cards:
  - V1 Archive (status, last updated, route, open button)
  - V2 Daily Audit (status, last updated, route, open button)
  - V3 Placeholder (status: "upcoming", route TBD)
  - Content Direction (status, last updated, route, open button)
- Add version switcher UI to both V1 and V2 headers
- Add "Latest Recommendation" section (placeholder, shows suggestions from V2 when available)

**Files changed:**
```
content/ad-report.md                 (MODIFY: frontmatter for hub)
templates/ad-report-hub.html         (NEW)
templates/ad-report.html             (MODIFY: add version switcher)
templates/ad-report-v2.html          (MODIFY: add version switcher)
templates/content-direction.html     (MODIFY: add "from hub" link)
sass/_ad-report.scss                 (enhance hub cards)
```

**QA:**
- `/ad-report/` renders as hub with 4 working cards
- `/ad-report-v1/` resolves to V1 content
- `/ad-report-v2/` still works and shows suggestions placeholder
- Version switchers clickable on both V1 and V2
- All routes backward-compatible

**Risk:** Medium (touches routing)  
**Reversibility:** Yes — can revert to simple redirect if needed  
**Approval needed:** Full review (routing + UX impact)

---

### PR 3: V2 Suggestions Section (AFTER PR 2)

**Title:** `feat(adsense): add content suggestions to V2 report`

**Scope:**
- Extend `scripts/build_ad_report_v2.py` to generate suggestions:
  - Topics to write next (from content gaps + high-monetization categories)
  - Posts to improve (thin content, low SEO score, zero internal links)
  - Category expansion opportunities (clusters with few posts)
  - Internal link actions (from content-direction report if available)
  - FAQ/schema opportunities (posts without structured data)
- Add `suggestions` object to `data/ad-report-v2.json`:
  ```json
  {
    "suggestions": {
      "next_topics": [
        {
          "topic": "Phí tài khoản ngân hàng",
          "reason": "Cụm ngân hàng có 12 bài nhưng chưa cover phí",
          "category": "Banking",
          "priority": "high",
          "monetization_potential": "high"
        }
      ],
      "posts_to_improve": [
        {
          "title": "...",
          "url": "...",
          "issue": "thin content / no internal links / low SEO",
          "suggested_action": "add 500 words / add 5 internal links / update FAQ"
        }
      ],
      "category_opportunities": [],
      "internal_link_actions": [],
      "cluster_opportunities": [],
      "summary": "Báo cáo ngày hôm nay gợi ý viết thêm 3 bài mới về phí, improve 8 bài hiện có, expand 2 cụm."
    }
  }
  ```
- Update `templates/ad-report-v2.html` to render `Gợi ý sau báo cáo` section
- Optionally read `static/data/content-direction/report.json` to cross-reference orphans + link gaps
- Add unit tests for suggestion generation

**Files changed:**
```
scripts/build_ad_report_v2.py        (MODIFY: add suggestion generation)
scripts/test_ad_report_v2.py         (MODIFY: test suggestions)
data/ad-report-v2.json               (regenerated with suggestions)
templates/ad-report-v2.html          (MODIFY: add suggestions section)
sass/_ad-report.scss                 (optional: style suggestions)
```

**QA:**
- `python3 scripts/build_ad_report_v2.py` generates suggestions without error
- Suggestion logic passes unit tests
- V2 page renders suggestions visibly (not just in JSON)
- Suggestions are actionable and based on real data
- No performance regression (script runtime ~same)

**Risk:** Medium (changes report data structure)  
**Reversibility:** Yes — can hide suggestions section if data is wrong  
**Approval needed:** Full review (data logic + UX)

---

### PR 4: AdSense Audit V3 (FUTURE, NOT NOW)

**Title:** `feat(adsense): add V3 continuous content optimization engine`

**Scope:**
- Build `scripts/build_ad_report_v3.py` — daily content health + optimization roadmap
- V3 outputs 5 buckets:
  - **Fix Now** (policy risk, thin content, missing schema)
  - **Improve Soon** (low SEO, weak internal links, high monetization potential)
  - **Monetization Opportunity** (strong content, under-monetized category)
  - **Safe / Healthy** (green light, keep momentum)
  - **Watchlist** (monitor, may need action next month)
- For each post, V3 includes:
  - Title, URL, category, tags, published, word count
  - Scores (content depth, AdSense suitability, SEO, internal links)
  - FAQ/schema status, image/OG status
  - Category monetization potential
  - Policy risk (low/med/high)
  - Thin content risk (yes/no)
  - **Recommended action** (write supporting article / improve internal links / add FAQ / update schema / etc)
  - Priority (P0/P1/P2)
  - Reason (why this action matters)
- V3 generates summary lists:
  - Top 10 posts to fix (by priority + impact)
  - Top 10 new content ideas (by gap + monetization)
  - Top 3 categories to expand
  - Top 10 internal links to add
  - Top 5 AdSense-safe opportunities
- Create `.github/workflows/ad-report-v3.yml` (daily cron + dispatch + PR-on-change)
- Create `/ad-report-v3/` route, template, styling
- Create `data/ad-report-v3.json`, manifest, archive in `reports/ad-report-v3/`
- Update hub to show V3 as current (move V2 to "previous")
- Add Theme Log entry for V3 milestone

**Files changed:** ~8–10 files (same pattern as V2)

**Risk:** High (new engine, complex logic)  
**Approval needed:** Detailed review + staged testing  
**Timeline:** After V2 is proven stable (suggest: 2–4 weeks after PR 3 merges)

---

## Content Direction + V2 Integration

### How They Work Together

**Content Direction** (`/tools/content-direction/`) answers:
```
Bài nào đang mồ côi?
Cụm chủ đề nào yếu?
Bài nào cần internal links?
Chuyên mục nào có khoảng trống?
Bài nào nên liên kết với bài nào?
```

**V2 Suggestions** consumes Content Direction insights:
```
Orphan posts from Content Direction → "Posts to Improve" section
Link gaps from Content Direction → "Internal Link Actions" section
Cluster opportunities → "Category Expansion" suggestions
```

**Integration approach (safe):**
1. PR 1 automates Content Direction generation
2. V2 generator checks if `static/data/content-direction/report.json` exists
3. If it exists and is fresh (< 24h old), V2 pulls:
   - Orphan post count + top 5 orphans by score
   - Link gap count + top 5 gaps by priority
   - Weak cluster names
4. V2 surfaces these as actionable suggestions
5. Example suggestion output:
   ```
   "Cụm Ngân hàng có 12 bài nhưng chưa cover phí tài khoản (link gap).
    Đề xuất: viết 1 bài mới về phí, rồi link từ các bài có sẵn."
   ```

**No hard dependency:** V2 still generates suggestions even if Content Direction is stale or missing. Suggestions will just be generic (from AdSense scores + SEO data).

---

## Theme Log Milestones

Add entries to `/tools/theme-log/` for each major system update:

### Milestone 1: AdSense Audit V1 Restored
- **Type:** Tool restoration
- **Title:** AdSense Audit V1 — Static monetization archive
- **Date:** 2026-06-19 (original creation)
- **PR:** #1122
- **Routes:** `/ad-report/`, `/ad-report-v1/` (alias)
- **Files:** `content/ad-report.md`, `templates/ad-report.html`
- **Purpose:** Baseline monetization strategy (static reference)
- **Status:** Archived (see V2 for updates)

### Milestone 2: AdSense Audit V2 Launched
- **Type:** Automated report system
- **Title:** AdSense Audit V2 — Daily automated monetization analysis
- **Date:** (when V2 workflow was created)
- **PR:** #1122 (or separate)
- **Routes:** `/ad-report-v2/`
- **Files:** `scripts/build_ad_report_v2.py`, `.github/workflows/ad-report-v2.yml`
- **Purpose:** Daily refresh of monetization metrics + suggestions
- **Automation:** Daily 06:00 GMT+7 + `workflow_dispatch`

### Milestone 3: Content Direction Automation
- **Type:** Content intelligence + linking
- **Title:** Content Direction — Automated internal content map
- **Date:** (when workflow is added in PR 1)
- **PR:** (PR 1)
- **Routes:** `/tools/content-direction/`
- **Files:** `.github/workflows/content-direction.yml`, `scripts/content_direction.py`
- **Purpose:** Daily analysis of orphan posts, link gaps, topic clusters
- **Automation:** Daily 05:00 GMT+7 + `workflow_dispatch`
- **Feeds:** V2 suggestions section

### Milestone 4: AdSense Hub
- **Type:** Navigation + version management
- **Title:** AdSense Audit Hub — Central optimization dashboard
- **Date:** (when hub is created in PR 2)
- **PR:** (PR 2)
- **Routes:** `/ad-report/` (now hub), `/ad-report-v1/`, `/ad-report-v2/`
- **Purpose:** One entry point for all AdSense + content optimization tools
- **Features:** Version switcher, latest recommendations, integrated roadmap

### Milestone 5: AdSense Audit V3 (Future)
- **Type:** Continuous optimization engine
- **Title:** AdSense Audit V3 — Continuous content optimization roadmap
- **Date:** (when V3 launches)
- **PR:** (PR 4)
- **Routes:** `/ad-report-v3/`
- **Files:** `scripts/build_ad_report_v3.py`, `.github/workflows/ad-report-v3.yml`
- **Purpose:** Daily "what to write next" + content health + priority roadmap
- **Automation:** Daily 06:30 GMT+7 + `workflow_dispatch`
- **Priority buckets:** Fix Now, Improve Soon, Monetization Opportunity, Safe, Watchlist

---

## Decision Matrix: PR 1 Implementation Details

### Content Direction Workflow

**File:** `.github/workflows/content-direction.yml`

```yaml
name: Content Direction

on:
  schedule:
    - cron: '0 22 * * *'  # 05:00 GMT+7 (before V2's 06:00)
  workflow_dispatch:       # Manual trigger
  push:
    paths:
      - 'content/posting/**'
      - 'content/baochi/**'
      - 'data/scores.json'
      - 'data/seo-qa-scores.json'
      - 'data/related.json'
      - 'categories.json'

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    concurrency:
      group: content-direction
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: python3 scripts/content_direction.py
      - run: python3 -m unittest scripts.test_content_direction -v 2>&1 || true
      - name: Detect changes
        id: diff
        run: |
          if git diff --cached --quiet static/data/content-direction/report.json; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
          fi
      - name: Generate summary
        run: |
          echo "## Content Direction Report" >> $GITHUB_STEP_SUMMARY
          echo "Generated at: $(date -u +'%Y-%m-%d %H:%M:%S Z')" >> $GITHUB_STEP_SUMMARY
          grep -E '"posts_count|"clusters_count|"orphans_count' static/data/content-direction/report.json | head -5 >> $GITHUB_STEP_SUMMARY || true
      - name: Create PR if changed
        if: steps.diff.outputs.changed == 'true'
        run: |
          git config user.name "SEOMONEY Bot"
          git config user.email "bot@seomoney.org"
          git add static/data/content-direction/report.json
          BRANCH="chore/content-direction-$(date +%Y%m%d-%H%M%S)"
          git checkout -b "$BRANCH"
          git commit -m "chore: update content direction report

Generated at: $(date -u +'%Y-%m-%d %H:%M:%S Z')
Auto-generated by content-direction.yml workflow."
          git push -u origin "$BRANCH"
          gh pr create \
            --title "chore: content direction daily update" \
            --body "Automated Content Direction report. Auto-merges when CI passes." \
            --label "chore,automation" \
            || echo "PR already exists"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Key points:**
- Runs daily + on-demand + on content/data changes
- Serialized (one run at a time, no cancellation)
- Opens PR only if data changed (idempotent)
- Workflow summary shows key metrics
- Uses repo's existing PR-on-change pattern
- No direct push to main

---

### Ad-Report V1 Versioning

**File:** `content/ad-report.md`

**Changes:**
```diff
[document]
title = "AdSense Audit V1"
slug = "ad-report"
- aliases = ["/ad-report/"]
+ aliases = ["/ad-report/", "/ad-report-v1/"]
description = "..."
date = 2026-06-19
+ [extra]
+ version = "v1"
+ version_status = "archived"
+ deprecation_notice = true
+ successor_url = "/ad-report-v2/"

---
## AdSense Audit V1

> **ℹ️ Version 1 (Archived)** — This is a static snapshot from 2026-06-19.  
> See [V2 (Daily Automated)](/ad-report-v2/) for updated analysis.  
> See [all versions & map](/ad-report/) for navigation.

[existing content...]
```

**Template change:** `templates/ad-report.html` — add notice at top:
```html
{% if page.extra.deprecation_notice %}
<div class="banner banner--info">
  <strong>ℹ️ Version 1 (Archived)</strong> — See 
  <a href="/ad-report-v2/">V2 (Daily Automated)</a> or 
  <a href="/ad-report/">all versions</a>.
</div>
{% endif %}
```

---

### Ad-Report V2 Navigation

**Template change:** `templates/ad-report-v2.html` — add notice:
```html
<div class="banner banner--secondary">
  Xem <a href="/ad-report/">trung tâm AdSense</a> (hub) | 
  <a href="/tools/content-direction/">Content Direction</a> (nội dung nội bộ)
</div>
```

---

## Current Situation → PR 1 Outcome

| Component | Before | After (PR 1) |
|-----------|--------|--------------|
| **Content Direction** | Manual snapshot (7 days old) | Automated daily + `workflow_dispatch` |
| **V1 route** | `/ad-report/` only | `/ad-report/` + `/ad-report-v1/` alias |
| **V1 UX** | No version info | Deprecation notice + link to V2 |
| **V2 UX** | No navigation context | Link to hub + Content Direction |
| **Hub** | Doesn't exist | Still doesn't exist (PR 2) |
| **Suggestions** | None | None yet (PR 3) |
| **V3** | Doesn't exist | Still doesn't exist (PR 4) |

---

## Final Decision Framework

### PR 1 Approval Checklist

- [ ] Content Direction workflow syntax validated
- [ ] Routes `/ad-report/`, `/ad-report-v1/`, `/ad-report-v2/` all work
- [ ] V1 and V2 pages show version notices
- [ ] Content Direction freshness timestamp displays correctly
- [ ] Notices are helpful, not intrusive
- [ ] No breaking changes to existing URLs
- [ ] Risk is low (additive, reversible)

### PR 2–4 Deferred

- PR 2 (Hub): Approve only after PR 1 merges and owner reviews notices
- PR 3 (Suggestions): Approve only after PR 2 merges and V2 hub design is proven
- PR 4 (V3): Propose timeline after PR 3 is stable (suggest 2–4 weeks)

---

## Files Summary (PR 1 Only)

```
NEW:
.github/workflows/content-direction.yml          (170 lines)

MODIFY:
content/ad-report.md                             (+5 lines alias + extra)
templates/ad-report.html                         (+3 lines notice)
templates/ad-report-v2.html                      (+3 lines link)

NO CHANGES NEEDED:
config.toml                                      (routes/menu can stay as-is)
templates/content-direction.html                 (optional: add freshness note)
static/data/content-direction/report.json        (regenerated by workflow)
```

---

## Next Steps

### If Approved:

1. Create PR with PR 1 scope only
2. Request review + approval
3. After merge, monitor workflow runs (first run at next scheduled time or manual dispatch)
4. Collect feedback from owner on:
   - Are notices helpful?
   - Is Content Direction freshness obvious?
   - Should V2 suggestions be added soon?
5. Plan PR 2 based on feedback

### If Changes Needed:

- List feedback here
- Update plan document
- Resubmit for approval

---

## Final Report

**Decision:**
- **AdSense versions entry point:** `/ad-report/` (hub, PR 2) with cards for V1/V2/V3/Content Direction
- **Content Direction role:** Automated internal content map; feeds V2 suggestions
- **PR 1 scope:** Content Direction workflow + V1/V2 notices + `/ad-report-v1/` alias
- **Future Hub:** PR 2 — converts `/ad-report/` into navigation hub
- **Future V2 suggestions:** PR 3 — adds actionable recommendations based on content gaps + monetization
- **Future V3:** PR 4 — continuous "what to write next" optimization engine
- **Theme Log milestones:** 5 milestones (V1 restore, V2 launch, Content Direction automation, Hub, V3)
- **Files changed (PR 1):** 5 files (1 new, 3 modified, 1 generated)
- **QA (PR 1):** Route verification + workflow syntax + notice rendering
- **Route verification (PR 1 outcome):**
  - `/ad-report/` → V1 content (with notice)
  - `/ad-report-v1/` → V1 content (via alias)
  - `/ad-report-v2/` → V2 content (with notice)
  - `/tools/content-direction/` → automated daily report
- **Next step:** Owner approval of this plan → implement PR 1 → gather feedback → plan PR 2

---

**Prepared by:** Claude Code  
**Date:** 2026-06-27  
**Session:** `/home/user/zola` (branch: `claude/seomoney-automation-audit-ozaow7`)
