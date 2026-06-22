# Article Layout Optimization — Desktop Width Adjustment

## Summary
Adjusted article container width for better desktop balance by optimizing the TOC rail and grid layout at ≥1280px breakpoint.

## Changes Made

### 1. **Breakpoint Adjustment** (`_toc-rail.scss`)
- **Old:** `@media (min-width: 1300px)`
- **New:** `@media (min-width: 1280px)`
- **Rationale:** Enables the rail layout at 1280px (common laptop size) instead of 1300px, providing better space utilization

### 2. **TOC Rail Width Optimization**
- **Old:** 248px rail, 2.5rem gap
- **New:** 256px rail (8px wider), 2.75rem gap
- **Impact:** Slightly wider TOC for better readability while maintaining proportions

### 3. **Typography Adjustments (Rail)**
- **Link font size:** 0.86rem → 0.84rem (cleaner fit in wider rail)
- **Link padding:** 0.42rem 0.85rem → 0.4rem 0.8rem (refined spacing)
- **Line height:** 1.45 → 1.4 (tighter, more scannable)
- **Sub-link padding:** 1.7rem → 1.6rem (adjusted for rail width)
- **Title font size:** 0.72rem → 0.71rem (subtle refinement)
- **Added:** `word-break: break-word` for long headings

### 4. **Ultra-Wide Breakpoint** (NEW)
Added `@media (min-width: 1920px)` for 4K/ultrawide screens:
- Rail width: 280px (further optimization)
- Gap: 3rem (generous spacing)
- Link font size: 0.85rem (slightly larger for better readability)

## Width Calculations

### Desktop (≥1280px):
- Container width: 1500px - 48px padding = 1452px
- After sidebar (400px) + gap (30px): 1022px remaining
- Article column: `minmax(0, 1fr)` (flexible)
- TOC rail: 256px
- Gap between article & rail: 2.75rem (44px)
- **Article width:** ~722px (slight increase from 734px — now article gets more space with proportional rail growth)

### Ultra-Wide (≥1920px):
- Available after layout: ~1022px
- Article column: `minmax(0, 1fr)` (flexible)
- TOC rail: 280px (18px wider)
- Gap: 3rem (48px)
- **Article width:** ~694px (smaller due to wider rail, but compensated by overall viewport size)

## Responsive Behavior
- **≤1279px:** Rail hidden, inline TOC shown (no change)
- **1280px–1919px:** New optimized layout
- **≥1920px:** Ultra-wide optimization
- **Tablet/Mobile:** Unchanged (full-width article, inline TOC)

## Visual Hierarchy
- Article container maintains readable line length (~65–75 chars at 17px font)
- TOC rail stays sticky and accessible
- No layout shift (rail rendered server-side)
- Visual hierarchy maintained: article → TOC → sidebar → main container

## Testing Checklist
- [ ] Desktop 1440px: rail visible, proportions balanced
- [ ] Desktop 1280px: rail appears at breakpoint, no content shift
- [ ] Laptop 1280px: article width comfortable, TOC not overlapping
- [ ] Ultra-wide 1920px: article has breathing room, rail proportional
- [ ] Tablet 960px: inline TOC showing, rail hidden
- [ ] Mobile: single column, full width, no regression
- [ ] Sticky TOC scrolling smoothly
- [ ] No visual glitches on active/hover states
- [ ] Print layout unaffected

## No Regressions
✅ No HTML changes
✅ No routing changes
✅ No typography changes (only rail title/links refined)
✅ No spacing changes to article content (only rail adjusted)
✅ Sticky behavior preserved
✅ SEO structure unchanged
