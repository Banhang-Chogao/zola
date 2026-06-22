# Blog UI Audit vs B-DNA (2026-06-22)

## ✅ Current Strengths
- ✓ Existing theme tokens (`--c-*`) used throughout
- ✓ Responsive post cards with mobile optimization  
- ✓ Breadcrumbs, metadata, TOC in place
- ✓ Related articles + navigation structure
- ✓ Author box + tags footer

## ⚠️ B-DNA Alignment Gaps

### 1. Typography Hierarchy (B-DNA §03)
**Issue:** Multiple font families in use (Ericsson Hilda + Manrope + Inter + Be Vietnam Pro) instead of single family with weight/size hierarchy.
- Current: Mixed stacks per component
- B-DNA rule: "One family, inherited from site. Hierarchy from weight/size, not fonts."
**Status:** DEFER — affects config-level fonts; safe to improve locally per component (smaller scopes)

### 2. Card Structure (B-DNA §01 + §04)
**Issue:** Post cards don't follow B-DNA card primitive.
- Current: `.post-card` = custom grid layout, not `.bdna__card`-like
- B-DNA: "soft surface, thin border, generous padding, ~14px radius"
- **Safe fix:** Improve card padding, border consistency, radius uniformity

### 3. Spacing Scale (B-DNA §05)
**Issue:** Arbitrary rem/px values mixed with inconsistent 4px base scale.
- Examples: `gap: 1.25rem`, `padding: 1.5rem`, `margin: 0.5rem` 
- B-DNA: All steps off 4px (4/8/12/16/24/32/48/64)
- **Safe fix:** Update post-meta, post-card body padding to align 4px scale

### 4. Color Usage (B-DNA §02)
**Issue:** Some hardcoded hex values in older code (e.g., `.drive-post__content` colors).
- Current: `#1572bd`, `#d63d3d`, `#f5f5f5` hardcoded
- B-DNA: "Read color from `var(--c-*)`; hard-code hex = violation"
- **Safe fix:** Replace drive-post hardcodes with theme tokens

### 5. Component Hierarchy (B-DNA §07)
**Issue:** Post metadata (author, date, SEO badge) hierarchy could be stronger.
- Current: Small icons + text, similar visual weight
- B-DNA: "Large numbers earn weight; labels support; units whisper"
- **Safe fix:** Improve contrast, visual prominence of key info

### 6. Motion (B-DNA §06)
**Issue:** Most transitions are 0.15–0.25s (correct!), but some missing motion feedback.
- Current: `.post-card:hover` has shadow + scale, `.cat-tag` has no transition
- B-DNA: "Calm motion ≤250ms"
- **Safe fix:** Add smooth transitions to interactive elements

### 7. One Column of Meaning (B-DNA §01)
**Issue:** Blog layout good, but some sections have competing layouts.
- Current: TOC sidebar competes with toc-rail on desktop
- B-DNA: "Side rails for navigation/metadata, never primary message"
- **Status:** WORKING AS INTENDED (TOC rail is secondary)

## No Conflicts with CLAUDE.md
✓ URL format: Already `https://seomoney.org/[slug]/` (no category in path)
✓ Routing: No changes needed
✓ SEO/sitemap: No changes  
✓ Publish logic: UI-only refresh (no schema changes)

## Implementation Plan

### Phase 1: Safe CSS-only Improvements (THIS SESSION)
1. ✓ Post card padding/radius to B-DNA scale (4px)
2. ✓ Replace hardcoded colors in `.drive-post` with tokens
3. ✓ Improve post metadata hierarchy (font-weight, size)
4. ✓ Add smooth transitions to `.cat-tag`
5. ✓ Refine breadcrumb spacing + visual weight
6. ✓ Improve header layout spacing per 4px scale

### Phase 2: Font Migration (FUTURE — not in scope)
- Evaluate FreightSans Pro vs. current Hilda stack
- Requires `@font-face` + config changes
- Defer until separate font project

### Phase 3: Component Refactor (FUTURE)
- Align `.post-card` with B-DNA `.bdna__card` structure
- Unify article cards across templates
- Requires template changes (test on multiple pages)

---

## Files to Modify (Phase 1)

| File | Change | Scope |
|------|--------|-------|
| `sass/_post.scss` | Card padding, spacing scale, color tokens | Post cards, metadata |
| (NEW) `sass/_blog-ui-refresh.scss` | B-DNA-aligned improvements (hero, metadata, spacing) | Article page styling |

## Build + Validate
- `zola build` → no errors
- Check: post cards, article page, homepage, mobile (360/768/1024)
- Verify: no SEO/sitemap changes, no URL changes
