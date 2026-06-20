# Mobile UX Improvements - Comprehensive Action Plan

**Status:** Ready for Implementation  
**Created:** 2026-06-18T23:15:00Z  
**Priority:** Critical (Mobile 58→90/100, LCP 6.9s→2.5s)

## Executive Summary

Mobile performance is currently **37 points below desktop** (58 vs 95). LCP is **4.4 seconds over target** (6.9s vs 2.5s target). This plan addresses the gap through 6 optimized phases.

### Current Baseline
```
Mobile:
  Performance: 58/100 (target: 90) — Δ32
  LCP: 6.9s (target: 2.5s) — Δ4.4s
  FCP: 3.9s
  TBT: 170ms
  CLS: 0.0 ✓
  SI: 8.8s

Desktop:
  Performance: 95/100 (target: 95) ✓
  LCP: 1.2s ✓

Resource Usage:
  Total: 896 KiB
  Unused CSS: 43.9 KiB
  Unused JS: 66.3 KiB
  Fonts: 282.7 KiB
```

### Success Criteria
- ✓ Mobile Performance: 90/100 (from 58)
- ✓ Desktop Performance: 95/100 (maintain)
- ✓ Mobile LCP: <2.5s (from 6.9s)
- ✓ CLS: <0.1 (currently 0.0, maintain)
- ✓ INP: <200ms
- ✓ No horizontal scrolling
- ✓ No layout shifts
- ✓ All touch targets ≥44px

---

## Implementation Plan

### Phase 1: Font Optimization (Week 1 - Quick Wins)

**Time:** 2-3 hours  
**Risk:** Very Low  
**Impact:** Reduce FCP by ~0.5s

#### Task 1.1: Verify font-display: swap
- Audit all @font-face declarations in `sass/_fonts.scss`
- Ensure every font has `font-display: swap`
- Verify Google Fonts link includes `display=swap`
- **Files:** `sass/_fonts.scss`, `templates/base.html`

#### Task 1.2: Preload Primary Font
- Add `<link rel="preload" as="font" href="...">` in `<head>` for Nokia Pure
- Use `crossorigin` attribute for CORS safety
- **Files:** `templates/base.html`
- **Impact:** ~500ms FCP improvement

#### Task 1.3: Font Subsetting (Optional)
- Create subset font files (Latin + Vietnamese diacritics only)
- Replace global font files with subsets
- Reduce font payload by 20-30%
- **Files:** `static/fonts/`, `sass/_fonts.scss`

### Phase 2: Asset Loading Optimization (Week 1-2 - Highest Impact)

**Time:** 4-5 hours  
**Risk:** Medium  
**Impact:** Reduce LCP by ~3-4s, reduce main-thread blocking

#### Task 2.1: CSS Code Splitting

**Current Issue:** 43.9 KiB unused CSS loaded on every page

**Solution:**
1. Audit `sass/site.scss` to identify template-specific rules
   - Home page: hero, featured posts
   - Single post: sidebar, related articles
   - Insights: dashboards, charts
   - Tools: form styles, canvas elements
   
2. Create template-specific SCSS files:
   - `sass/_home-specific.scss` — only home pages
   - `sass/_post-specific.scss` — only article pages
   - `sass/_insights-specific.scss` — only insights
   - `sass/_tools-specific.scss` — only tools
   - `sass/_core.scss` — always loaded

3. Update build config to generate separate CSS files
4. Conditionally load in templates via `<link rel="stylesheet">`

**Savings:** 43.9 KiB (100% unused CSS elimination)  
**Files:** `sass/site.scss`, `sass/_*.scss`, `templates/base.html`

#### Task 2.2: Defer Non-Critical JavaScript

**Current Issue:** 66.3 KiB unused JS, 170ms TBT (Total Blocking Time)

**Strategy:**
```javascript
// Pattern for deferred non-critical scripts
const deferScript = (src, timeout = 2000) => {
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => loadScript(src), timeout);
    });
  } else {
    setTimeout(() => loadScript(src), timeout);
  }
};
```

**Defer Candidates:**
1. **Google Analytics** (gtag/js)
   - Not critical for UX
   - Load after 2s idle
   - ~66 KiB savings
   
2. **Chart.js** (only /insights/)
   - Lazy-load on page type detection
   - Or load on scroll into view
   
3. **PDF.js** (only /tools/)
   - Load only when user clicks "Upload PDF"
   - Dynamic import: `import('pdfjs-dist')`
   
4. **Tesseract.js** (only /tools/h-dashboard/)
   - Load only when user selects image
   - ~3 MiB file, must be lazy

5. **Search/autocomplete** 
   - Load on input focus
   - Not on initial load

**Implementation:**
- Create `static/js/deferred-loader.js` with `deferScript()` utility
- Replace `<script>` tags with `<script data-defer="true" src="...">`
- Initialize deferred loader in base template
- **Files:** `static/js/deferred-loader.js`, `templates/base.html`, individual component scripts

**Impact:** 170ms → <50ms TBT, 66 KiB JS deferral

---

### Phase 3: Image Optimization (Week 2 - Moderate Impact)

**Time:** 2-3 hours  
**Risk:** Low  
**Impact:** Reduce LCP by ~1-2s (if hero image), prevent CLS

#### Task 3.1: Add Lazy Loading

**Apply to all content images:**
```html
<img ... loading="lazy" decoding="async">
```

**Files to update:**
- `templates/page.html` — post content images
- `templates/macros/post-card.html` — thumbnail images
- `templates/insights.html` — dashboard images
- Any dynamically loaded images

**Impact:** Defer below-the-fold images, save bandwidth

#### Task 3.2: Preload Hero Image

**For LCP optimization:**
- Add `<link rel="preload" as="image" href="...">` in `<head>`
- Calculate hero image dynamically or set in template variable
- Use correct media query for responsive images
- **Files:** `templates/base.html`, `templates/page.html`

**Impact:** ~2-3s LCP reduction

#### Task 3.3: Responsive Images

**Add sizing attributes to prevent layout shift (CLS):**
```html
<img ... width="1200" height="630" loading="lazy" decoding="async">
```

**For responsive images:**
```html
<img ... srcset="small.webp 480w, medium.webp 1024w, large.webp 1600w"
      sizes="(max-width: 600px) 100vw, (max-width: 1200px) 80vw, 1200px">
```

**Files:** `templates/macros/img.html`, update all image macros

---

### Phase 4: Critical CSS & LCP Optimization (Week 2-3 - Targeted Impact)

**Time:** 3-4 hours  
**Risk:** Medium  
**Impact:** Reduce FCP by 1-2s, LCP by 1-2s

#### Task 4.1: Identify LCP Element

1. Run Lighthouse DevTools on real device
2. Check Performance trace to identify LCP element
3. Likely candidates:
   - Hero image (most probable) → optimize via preload
   - Hero text/h1 (possible) → inline critical CSS
   - Web font (possible) → preload + subsetting

#### Task 4.2: Inline Critical CSS

**For above-the-fold content:**
1. Extract minimal CSS needed for initial viewport
2. Inline in `<style>` tag in `<head>`
3. Defer non-critical CSS with `media="print"` pattern (already done in base.html)

**Critical elements to style:**
- Header/navbar
- Hero image container
- First heading
- First paragraph
- Primary CTA button

**Estimated:** 2-5 KiB critical CSS

---

### Phase 5: Touch-Friendly UX (Week 3 - UX Improvements)

**Time:** 1-2 hours  
**Risk:** Low  
**Impact:** Mobile usability, accessibility

#### Task 5.1: Verify Touch Targets (44px minimum)

Audit all interactive elements:
- Buttons: `min-height: 44px`, `min-width: 44px`
- Links: add `padding` if needed
- Form inputs: `height: 44px`
- Navigation items: `padding: 12px 16px` (min 44px tap target)

**Files:** `sass/_reset.scss`, `sass/_button.scss`, `sass/_navigation.scss`

#### Task 5.2: Optimize Mobile Spacing

Reduce unnecessary vertical spacing on mobile:
```scss
@media (max-width: 720px) {
  body { padding: 0.75rem 0.5rem; } // reduce from 1rem
  h1 { margin: 0.5rem 0 0.75rem 0; } // tighter
  p { margin-bottom: 0.75rem; } // reduce
}
```

**Keep horizontal spacing:** Preserve proper padding for text readability

#### Task 5.3: Prevent Horizontal Overflow

Remove any `overflow-x: hidden` hacks:
```scss
// REMOVE: html, body { overflow-x: hidden; }
// INSTEAD: Use proper max-width and padding
.container { max-width: 100%; padding: 0 1rem; }
```

**Verify:** No horizontal scroll on 360px-to-1024px viewport

---

### Phase 6: DOM Complexity Reduction (Week 3-4 - Optional Refinement)

**Time:** 2-3 hours (optional)  
**Risk:** Medium  
**Impact:** ~10-15% initial load time improvement

#### Task 6.1: Lazy Render Accordions (if applicable)

If insights dashboards have large accordions:
```javascript
// Only render expanded sections initially
const accordion = document.querySelector('.accordion');
accordion.addEventListener('toggle', (e) => {
  if (e.target.open && !e.target.dataset.rendered) {
    renderSection(e.target);
    e.target.dataset.rendered = 'true';
  }
});
```

#### Task 6.2: Virtualization (if needed)

For long lists (changelog, dashboard data):
- Render only visible items
- Use Intersection Observer for item visibility
- Load more on scroll
- **Risk:** High, only if necessary

---

## Testing & Validation

### Local Testing
```bash
# 1. Run audit
python3 scripts/audit_mobile_performance.py

# 2. Run QA checks
python3 qa_check.py

# 3. Build site
zola build

# 4. Validate links
python3 scripts/check_internal_links.py
```

### Lighthouse Testing
```bash
# Desktop
lighthouse https://seomoney.org/ \
  --chrome-flags="--headless" --output=json

# Mobile
lighthouse https://seomoney.org/ \
  --form-factor=mobile --output=json
```

### Manual Testing
1. **Real mobile device** (iPhone 12 mini or similar)
2. **DevTools throttling:** Slow 3G, CPU 4x slowdown
3. **Check for:**
   - Layout shifts (CLS)
   - Horizontal overflow
   - Touch target sizes
   - Font loading flash (FOUT/FOIT)
   - Image loading delays

### Performance Targets
```
✓ Mobile Performance: 90/100
✓ Desktop Performance: 95/100
✓ LCP: <2.5s
✓ FCP: <2.5s
✓ CLS: <0.1
✓ TBT: <200ms
```

---

## Implementation Schedule

| Week | Phase | Effort | Status |
|------|-------|--------|--------|
| 1 | Phase 3 (Fonts) + Phase 2.1 (CSS) | 5h | Ready |
| 1-2 | Phase 2.2 (JS Deferral) | 5h | Ready |
| 2 | Phase 3 (Images) | 3h | Ready |
| 2-3 | Phase 4 (Critical CSS/LCP) | 4h | Ready |
| 3 | Phase 5 (Touch UX) | 2h | Ready |
| 3-4 | Phase 6 (DOM Complexity) | 2h | Optional |
| **Total** | | **≤23h** | |

---

## Rollback Plan

If any phase causes regression:
1. Revert commit
2. Re-run Lighthouse validation
3. Identify root cause
4. Fix in feature branch
5. Re-test before merging

**Critical Safety Check:** Desktop performance must never drop below 95/100

---

## Next Steps

1. **Approve Plan** — confirm with team
2. **Create PR branches:**
   - `feat/mobile-fonts-optimization`
   - `feat/mobile-css-splitting`
   - `feat/mobile-js-deferral`
   - `feat/mobile-image-optimization`
   - `feat/mobile-critical-css`
   - `feat/mobile-touch-ux`
3. **Run audits after each phase**
4. **Update dashboard** with progress
5. **Validate Lighthouse scores** — mobile 90+

---

**Generated:** 2026-06-18T23:15:00Z  
**Author:** Improvement Hotfix Framework  
**Related:** PR #459 (Improvement Progress Hotfix)
