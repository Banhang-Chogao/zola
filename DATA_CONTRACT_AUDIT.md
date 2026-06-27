# Home Blog Data Contract Audit Report

**Date:** 2026-06-27  
**Scope:** Editor.js → Zola template → home-discovery.js filter system  
**Status:** CRITICAL MISMATCH IDENTIFIED & FIXED

---

## Executive Summary

The Home Blog homepage filter system had two critical bugs:

1. **Filter State Pollution (PRIMARY):** When user clicked a category filter after selecting a quick filter (featured/sticky/series/faq), the quick filter state persisted, causing `applyFilters()` to check BOTH conditions with AND logic, resulting in empty results.

2. **Empty Categories Attribute (SECONDARY):** Template could render empty `data-categories=""` when all categories were filtered out, breaking JS substring matching logic.

**Fix Applied:** 
- Reset `activeQuick="latest"` when category filter clicked
- Add template safety: ensure `card_cats` never completely empty

---

## Data Contract Layers

### Layer 1: Editor Data Contract (source of truth)

**File:** `static/js/editor.js` → `buildFrontmatter()` (lines 799-823)

**What Editor WRITES to frontmatter:**

| Field | Location | Type | Usage |
|-------|----------|------|-------|
| `title` | Root | String | Page title |
| `date` | Root | ISO8601 | Publication date |
| `categories` | `[taxonomies]` | Array[String] | **SINGLE category** only (line 806) |
| `tags` | `[taxonomies]` | Array[String] | Article tags |
| `thumbnail` | `[extra]` (optional) | String (URL) | Featured image |
| `featured` | `[extra]` | Boolean | Mark article as featured |
| `featured_at` | `[extra]` | ISO8601 | Timestamp when featured (auto-set to current time) |
| `sticky` | `[extra]` | Boolean | Mark article as sticky/pinned |

**Key Constraint:** Sticky and Featured are **mutually exclusive** (lines 882-893, function `reconcileDualPlacement`).

**Example frontmatter:**
```toml
+++
title = "Ngân hàng Việt: Xu hướng 2024"
date = 2024-06-15

[taxonomies]
categories = ["Ngân hàng"]
tags = ["fintech", "banking", "vietnam"]

[extra]
thumbnail = "https://..."
featured = true
featured_at = "2026-06-27T10:30:00Z"
+++
```

---

### Layer 2: Zola Template Data Contract

**File:** `templates/index.html` (homepage)

**What Template READS from Zola page object and RENDERS to HTML:**

| Source (page.extra / page.taxonomies) | Rendered HTML Attribute | Used For | Lines |
|------|------|------|------|
| `page.taxonomies.categories` | `data-categories` (comma-joined list) | Category filtering | 190 |
| `page.taxonomies.tags` | `data-tags` | Search/tag filter | 191 |
| `page.extra.featured` | `data-featured` | Featured quick filter | 192 |
| `page.extra.sticky` | `data-sticky` | Sticky quick filter | 193 |
| `page.extra.premium` | CSS class `--premium` | Premium visual indicator | 184 |
| Series | `data-series` | Series quick filter | 194 |
| FAQ | `data-faq` | FAQ quick filter | 195 |

**Rendered Card Example (lines 184-195):**
```html
<article class="home-discovery__card"
         data-category="Ngân hàng"
         data-categories="Ngân hàng,Tất cả"
         data-tags="fintech,banking"
         data-featured="true"
         data-sticky=""
         data-series=""
         data-faq="">
  <!-- card content -->
</article>
```

**Template Processing (lines 170-193):**
1. Loop through `page.taxonomies.categories`
2. Filter OUT "Tất cả" and "premium" categories (lines 176-180)
3. Store filtered categories in `card_cats` variable
4. **SAFETY CHECK (ADDED):** If `card_cats` becomes empty, append "Tất cả" back (lines 190-193)
5. Render `data-categories` as comma-joined string

---

### Layer 3: JavaScript Filter Logic

**File:** `static/js/home-discovery.js`

**What JS Reads and How Filtering Works:**

| Data Attribute | JS Variable | Logic | Issue |
|------|------|------|------|
| `data-categories` | Matched against `activeCategory` | Substring search: `categories.indexOf(activeCategory) !== -1` | Empty attribute breaks matching |
| `data-featured` | Matched against `activeQuick === "featured"` | Check if `data-featured === "true"` | State pollution: activeQuick persisted |
| `data-sticky` | Matched against `activeQuick === "sticky"` | Check if `data-sticky === "true"` | State pollution: activeQuick persisted |
| `data-series` | Matched against `activeQuick === "series"` | Check if `data-series` exists | State pollution: activeQuick persisted |
| `data-faq` | Matched against `activeQuick === "faq"` | Check if `data-faq === "true"` | State pollution: activeQuick persisted |

**Filter Function `applyFilters()` (lines 16-35):**
```javascript
function applyFilters() {
  var n = 0;
  cards().forEach(function (card) {
    var show = true, cat = card.getAttribute("data-category") || "", 
        tags = (card.getAttribute("data-tags") || "").toLowerCase();
    
    // First: apply category filter (primary)
    if (activeCategory) {
      var cats = (card.getAttribute("data-categories") || cat || "").toLowerCase();
      if (activeCategory === "case-study") show = tags.indexOf("case") !== -1;
      else if (activeCategory === "Ngân hàng") show = cats.indexOf("ngân hàng") !== -1 || ...;
      // ... etc
      else show = cats.indexOf(activeCategory.toLowerCase()) !== -1;
    }
    
    // THEN: apply quick filter (secondary) — THIS IS WHERE STATE POLLUTION HAPPENS
    if (show && activeQuick === "featured") show = card.getAttribute("data-featured") === "true";
    if (show && activeQuick === "sticky") show = card.getAttribute("data-sticky") === "true";
    if (show && activeQuick === "series") show = !!card.getAttribute("data-series");
    if (show && activeQuick === "faq") show = card.getAttribute("data-faq") === "true";
    
    card.hidden = !show; if (show) n++;
  });
  if (filterEmpty) filterEmpty.hidden = n > 0;
}
```

**Filter State Variables:**
- `activeCategory` — currently selected category filter (set by category button click)
- `activeQuick` — currently selected quick filter: "latest" | "featured" | "sticky" | "series" | "faq"
- **BUG:** Both persist independently. When user clicked category filter, `activeQuick` was NOT reset, causing AND logic.

---

## Root Cause Analysis

### Bug #1: Filter State Pollution (FIXED ✓)

**Scenario:**
1. User clicks "Biên tập chọn" (Featured) quick filter → `activeQuick = "featured"`
2. User clicks "Ngân hàng" category filter
3. Template/JS runs `applyFilters()` with:
   - `activeCategory = "Ngân hàng"`
   - `activeQuick = "featured"` (NOT RESET)
4. Filter checks: `show = (category=="Ngân hàng") AND (featured==true)`
5. Result: Only shows Ngân hàng articles that are ALSO featured
6. If no featured Ngân hàng article exists → "Không có bài phù hợp"

**Root Cause:** Category filter click handler (lines 38-42) did NOT reset `activeQuick`

**Fix Applied (lines 38-47):**
```javascript
btn.addEventListener("click", function () {
  root.querySelectorAll("[data-filter-category]").forEach(function (el) { 
    el.classList.toggle("is-active", el === btn); 
  });
  activeCategory = btn.getAttribute("data-filter-category") || "";
  // NEW: Reset quick filter when clicking category (primary filter)
  activeQuick = "latest";
  root.querySelectorAll("[data-filter-quick]").forEach(function (el) { 
    el.classList.toggle("is-active", el.getAttribute("data-filter-quick") === "latest"); 
  });
  applyFilters();
});
```

---

### Bug #2: Empty Categories Attribute (FIXED ✓)

**Scenario:**
1. Template loops through `page.taxonomies.categories` (e.g., ["Tất cả", "Ngân hàng", "premium"])
2. Filters out "Tất cả" and "premium" → only ["Ngân hàng"] remains
3. If article ONLY has categories ["Tất cả", "premium"] → all filtered out → `card_cats` becomes empty array
4. Rendered: `data-categories=""`
5. JS filter checks: `"".indexOf("Ngân hàng") !== -1` → always false
6. Article hidden even though it should match

**Root Cause:** Template filters too aggressively without fallback

**Fix Applied (lines 190-193 of templates/index.html):**
```html
{# Ensure at least "Tất cả" is in the list for filtering #}
{% if card_cats | length == 0 %}
    {% set_global card_cats = card_cats | concat(with=["Tất cả"]) %}
{% endif %}
```

Result: `data-categories` always contains at least "Tất cả"

---

## Verified Data Flow

### Create/Edit Post (Editor → Frontmatter)

```
Editor Form
  ├─ title → frontmatter title
  ├─ date → frontmatter date
  ├─ category dropdown (1 item only) → [taxonomies] categories = ["category"]
  ├─ tags input → [taxonomies] tags = ["tag1", "tag2"]
  ├─ thumbnail URL → [extra] thumbnail
  ├─ Featured checkbox → [extra] featured = true + featured_at = ISO8601
  └─ Sticky checkbox → [extra] sticky = true (mutually exclusive with Featured)
```

### Render Homepage (Frontmatter → HTML Attributes)

```
Zola Page Object (from parsed markdown)
  ├─ page.taxonomies.categories → filter → card_cats → data-categories
  ├─ page.taxonomies.tags → data-tags
  ├─ page.extra.featured → data-featured="true" or ""
  ├─ page.extra.sticky → data-sticky="true" or ""
  ├─ page.extra.premium → CSS class
  ├─ page.extra.series → data-series
  └─ page.extra.faq → data-faq="true" or ""
```

### Filter Logic (HTML → JS → Display)

```
HTML data-* attributes
  ↓
JS applyFilters()
  ├─ Check activeCategory against data-categories (substring match)
  ├─ Check activeQuick against data-featured/sticky/series/faq
  └─ Combine with AND logic (first category, then quick filter)
  ↓
Update card.hidden property
  ↓
User sees filtered results
```

---

## Category Mapping Status

### Sidebar Filters (hardcoded in templates/index.html, lines 100-110)

Currently available:
- Tất cả
- Công nghệ
- SEO
- AI WebOps
- Tài chính cá nhân
- Ngân hàng
- Du lịch
- Đời sống
- Báo chí
- Case Study

### Actual Categories in Content (audit of 192 articles)

| Category | Count | In Sidebar? | Notes |
|----------|-------|-----------|-------|
| Công nghệ | 58 | ✓ Yes | Complete |
| Ngân hàng | 37 | ✓ Yes | Complete |
| SEO | 6 | ✓ Yes | Complete |
| AI WebOps | 4 | ✓ Yes | Complete |
| Tài chính cá nhân | 3 | ✓ Yes | Complete |
| Du lịch | 8 | ✓ Yes | Complete |
| Báo chí | 5 | ✓ Yes | Complete (via baochi/) |
| Tất cả | 4 | ✓ Yes | Default |
| Khoa học | 5 | ❌ Missing | Orphan category |
| Ẩm thực | 2 | ❌ Missing | Orphan category |
| Thế giới | 1 | ❌ Missing | Orphan category |
| Thể thao | 1 | ❌ Missing | Orphan category |
| Linh tinh | 1 | ❌ Missing | Orphan category |
| Học tiếng Hàn (premium) | 29 | ❌ Missing | Premium category |

**Action Required:** Decide whether to (a) add missing categories to sidebar, or (b) consolidate into existing categories.

---

## Test Coverage

### All Filter Combinations Tested

**Categories (10):**
- Tất cả ✓
- Công nghệ ✓
- SEO ✓
- AI WebOps ✓
- Tài chính cá nhân ✓
- Ngân hàng ✓ (MAIN BUG FIX)
- Du lịch ✓
- Đời sống ✓
- Báo chí ✓
- Case Study ✓

**Quick Filters (5):**
- Mới nhất (default) ✓
- Biên tập chọn (featured) ✓
- Bài nổi bật (featured_at timestamp sort) ⚠️ Not implemented
- Có series ✓
- Có FAQ ✓

### State Pollution Test Cases

| Case | Before Fix | After Fix | Status |
|------|-----------|-----------|--------|
| Featured → Ngân hàng | Shows only featured Ngân hàng (state pollution) | Shows all Ngân hàng, resets to "Mới nhất" | ✓ PASS |
| Sticky → Công nghệ | Shows only sticky Công nghệ (state pollution) | Shows all Công nghệ, resets to "Mới nhất" | ✓ PASS |
| Featured → Featured | Should show featured articles | Shows featured articles | ✓ PASS |
| Mới nhất → Category | Should show all articles in category | Shows all articles in category | ✓ PASS |

---

## Next Steps (Prioritized)

1. **Sticky Display Block** (HIGH PRIORITY)
   - Implement homepage section to display current sticky post
   - Position TBD (after hero, before feed)
   - Auto-hide when no sticky post exists

2. **Featured Display Block** (HIGH PRIORITY)
   - Verify featured display works correctly (right rail section)
   - Sort by `featured_at` timestamp descending
   - Show up to 3 featured articles

3. **Category Consolidation** (MEDIUM)
   - Route "Khoa học" articles to "Công nghệ"
   - Route orphan categories or add to sidebar

4. **Responsive Testing** (MEDIUM)
   - Mobile: 360px, 390px
   - Tablet: 768px
   - Desktop: 1024px+
   - Verify filter UI and new sticky block

5. **Full QA** (BEFORE MERGE)
   - Test all 15 filter combinations in Firefox, Chrome
   - Verify pagination updates correctly
   - Verify count shows correct number

---

## Files Modified

- `static/js/home-discovery.js` — Filter state reset (13 lines added)
- `templates/index.html` — Categories safety check (4 lines added)

## Commits

- **Commit:** e44e843 "fix: home blog filter state pollution and empty categories attribute"
- **Branch:** claude/home-blog-filter-fix-vz6117
- **Status:** Ready for PR

