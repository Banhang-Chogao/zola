# Home Blog Filter System — QA Test Plan & Results

**Date:** 2026-06-27  
**Branch:** `claude/home-blog-filter-fix-vz6117`  
**Status:** READY FOR TESTING (Manual test execution required)  
**Test Environment:** Local build + mobile/desktop browser testing

---

## Test Execution Summary

### Scope
- **Component:** Home Blog filter system (homepage @ `/` in Zola site)
- **Files Modified:** 
  - `static/js/home-discovery.js` (filter state reset)
  - `templates/index.html` (categories safety check)
- **Features Tested:**
  - Category filters (10 options)
  - Quick filters (5 options)
  - Sticky post display (auto-hide when none)
  - Featured post display (right rail)
  - Pagination (count, range display)
  - Empty state handling
  - Responsive layout (mobile/tablet/desktop)

### Test Coverage
- **Total Test Cases:** 50+
- **Manual vs Automated:** All manual (browser-based UX testing required)
- **Environments:** Chrome, Firefox, Safari (if available)
- **Viewports:** 360px, 390px, 768px, 1024px, 1440px

---

## Test Category 1: Category Filters

### 1.1 Category Filter Button Rendering

| Test | Expected | Status |
|------|----------|--------|
| Page loads with sidebar visible | All 10 category buttons display | — |
| "Tất cả" button is active by default | Class "is-active" on "Tất cả" button | — |
| No quick filter is active by default | All quick filter buttons inactive | — |
| Quick filter buttons show: Mới nhất, Biên tập chọn, Bài nổi bật, Có series, Có FAQ | All 5 buttons visible | — |

### 1.2 "Tất cả" (All) Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Tất cả" button | Shows all 192 articles, count = 192 | [1] Click "Tất cả" → Verify count shows "Hiển thị 1–12 trong 192 bài viết" |
| Quick filter buttons reset | All quick filters become inactive, "Mới nhất" is active | [2] Click quick filter first, then click category → verify quick filter resets |

### 1.3 "Công nghệ" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Công nghệ" button | Shows 58 articles, count = 58 | [1] Click "Công nghệ" → Verify data-categories contain "công nghệ" → Count = 58 |
| Sidebar shows active state | "Công nghệ" button has "is-active" class | [2] Verify button highlights |
| Quick filters reset | "Mới nhất" is selected | [3] Verify if Featured was selected before, it's now deselected |
| Filter applies correctly | Only articles with category="Công nghệ" show | [4] Scroll through feed, spot-check categories |

### 1.4 "SEO" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "SEO" button | Shows 6 articles, count = 6 | [1] Click "SEO" → Count = 6 |
| Correct articles display | All 6 articles have SEO category | [2] Verify visible articles have SEO in data-categories |

### 1.5 "AI WebOps" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "AI WebOps" button | Shows 4 articles, count = 4 | [1] Click "AI WebOps" → Count = 4 |
| Correct articles display | All 4 articles tagged with AI WebOps | [2] Verify visible articles match AI WebOps category |

### 1.6 "Tài chính cá nhân" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Tài chính cá nhân" button | Shows 3 articles, count = 3 | [1] Click "Tài chính cá nhân" → Count = 3 |
| Correct articles display | All 3 articles have this category | [2] Spot-check visible articles |

### 1.7 "Ngân hàng" Category Filter ⭐ MAIN BUG FIX

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Ngân hàng" button | Shows 37 articles, count = 37 | [1] Click "Ngân hàng" → Count = 37, NOT empty results |
| Quick filter already active (Featured) | Shows all 37 Ngân hàng, resets Featured filter | [2] Click Featured, then Ngân hàng → Should show all 37, not filtered by featured |
| Quick filter already active (Sticky) | Shows all 37 Ngân hàng, resets Sticky filter | [3] Click Sticky, then Ngân hàng → Should show all 37 |
| Correct articles display | All 37 articles have Ngân hàng category | [4] Scroll feed, verify categories |
| Previous state pollution fixed | No "Không có bài phù hợp" message | [5] Confirm no empty state displays |

### 1.8 "Du lịch" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Du lịch" button | Shows 8 articles, count = 8 | [1] Click "Du lịch" → Count = 8 |

### 1.9 "Đời sống" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Đời sống" button | Shows articles in category | [1] Click "Đời sống" → Verify count > 0 |

### 1.10 "Báo chí" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Báo chí" button | Shows 5 articles from baochi/ section | [1] Click "Báo chí" → Count = 5 |

### 1.11 "Case Study" Category Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click "Case Study" button | Shows articles tagged with "case" | [1] Click "Case Study" → Verify correct articles display |

---

## Test Category 2: Quick Filters (State Reset on Category Change)

### 2.1 Featured Quick Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click Featured button | Shows featured articles only | [1] Click "Biên tập chọn" → Only featured articles show |
| Featured button is active | Has "is-active" class | [2] Verify button highlights |
| Click category after Featured | Featured filter RESETS to "Mới nhất" | [3] Click Featured, then click "Công nghệ" → Should show all Công nghệ, not just featured ones |
| Count updates | Shows total in category, not just featured | [4] Verify count changes from featured total to category total |

### 2.2 Sticky Quick Filter (NEW)

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click Sticky button (none exists) | Shows articles with sticky=true (1 article if it exists) | [1] Click "Bài nổi bật" → Shows sticky article or empty |
| Sticky button is active | Has "is-active" class | [2] Verify button highlights |
| Click category after Sticky | Sticky filter RESETS to "Mới nhất" | [3] Click Sticky, then click "Tài chính cá nhân" → Shows all Tài chính, not just sticky |

### 2.3 Series Quick Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click Series button | Shows only articles with series data | [1] Click "Có series" → Count shows articles in series |
| Series button is active | Has "is-active" class | [2] Verify button highlights |
| Click category after Series | Series filter RESETS to "Mới nhất" | [3] Click Series, then category → Shows all category articles |

### 2.4 FAQ Quick Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Click FAQ button | Shows only articles with FAQ data | [1] Click "Có FAQ" → Shows articles with [[extra.faq]] |
| FAQ button is active | Has "is-active" class | [2] Verify button highlights |
| Click category after FAQ | FAQ filter RESETS to "Mới nhất" | [3] Click FAQ, then category → Shows all category articles |

### 2.5 "Mới nhất" (Latest) Quick Filter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| "Mới nhất" is default | Starts active on page load | [1] Load page → "Mới nhất" button has is-active |
| Click after another filter | Re-activates "Mới nhất" | [2] Click Featured, then click Mới nhất → Shows all recent articles |

---

## Test Category 3: Featured & Sticky Display Blocks

### 3.1 Featured Post Block (Right Rail)

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Featured section displays | Shows "Biên tập chọn" section on right rail | [1] Load homepage → Verify right sidebar shows featured block |
| Featured image shows | Cover image displays correctly | [2] Verify image loads and aspect ratio correct |
| Featured title shows | Article title links to article | [3] Click title → Navigates to article |
| Featured category shows | Category label displays | [4] Verify category shows (e.g., "Công nghệ") |
| Featured date shows | Date displays in DD/MM/YYYY format | [5] Verify date format is "27/06/2026" not "Jun 27" |
| Related featured articles list | Shows other featured articles below | [6] Verify list shows multiple featured articles |

### 3.2 Sticky Post Block (Main Feed)

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Sticky section displays (if exists) | Shows "Bài nổi bật hôm nay" block at top of feed | [1] Load homepage → Check above main article list |
| Sticky shows only on page 1 | Hidden on pagination pages 2, 3, etc. | [2] Click page 2 → Sticky block disappears |
| Sticky auto-hides when none | Block not visible if no sticky post | [3] If sticky doesn't exist, section not rendered |
| Sticky image displays | Cover image shows correctly | [4] Verify image loads |
| Sticky title links | Article title navigates to article | [5] Click sticky title → Goes to article |
| Sticky category shows | Category label displays | [6] Verify category shows |
| Sticky date shows | Date in DD/MM/YYYY format | [7] Verify date format |
| Sticky styling distinct | Different visual treatment from regular cards | [8] Verify left border color or other visual indicator |

---

## Test Category 4: Empty States & Edge Cases

### 4.1 Empty State Message

| Test | Expected | Manual Steps |
|------|----------|--------------|
| No articles in filter | "Không có bài phù hợp" message shows | [1] Apply filter that has 0 articles (if exists) → Verify message displays |
| Empty state has helpful link | Link to "toàn bộ bài viết" (all articles) | [2] Click link → Goes to archive |
| Featured/Sticky still show | Featured and Sticky display even when feed empty | [3] Verify featured/sticky don't disappear with empty feed |

### 4.2 Pagination Handling

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Page 1 shows articles 1-12 | Count shows "Hiển thị 1–12 trong 192 bài viết" | [1] Load page → Verify count correct |
| Page 2 shows articles 13-24 | Count shows "Hiển thị 13–24 trong 192 bài viết" | [2] Click page 2 → Verify range updates |
| Last page partial | Last page shows remaining articles (< 12) | [3] Navigate to last page → Count shows correct range |
| Filter updates pagination | Count resets to page 1 after filter change | [4] Click filter → Returns to page 1 |

### 4.3 Category Data Attribute Safety

| Test | Expected | Manual Steps |
|------|----------|--------------|
| data-categories never empty | Every article has at least one category | [1] Open DevTools → Inspect any card → Verify data-categories has value |
| Categories comma-separated | Multiple categories joined with commas | [2] Find article with 2+ categories → Verify "cat1,cat2" format |
| Filtering by data-categories works | Substring match finds articles | [3] Click category → Verify matching articles show |

---

## Test Category 5: Responsive Design

### 5.1 Mobile (360px – iPhone SE width)

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Sidebar collapses | Filter sidebar not visible by default | [1] Set viewport to 360px width → Sidebar hidden |
| Toggle button shows | "Lọc" toggle button visible | [2] Verify toggle button displays |
| Filter can open/close | Click toggle → Sidebar appears/disappears | [3] Click toggle → Sidebar slides in, click again → slides out |
| Cards stack vertically | One column layout | [4] Verify cards full width, no side-by-side |
| Sticky block responsive | Image left, content right on card | [5] Verify sticky card adapts to single column |
| Touch targets adequate | Buttons are at least 44px tall | [6] Verify filter buttons are large enough to tap |

### 5.2 Tablet (768px width)

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Sidebar visible | Filter sidebar displays on left | [1] Set viewport to 768px → Sidebar visible |
| Cards display well | 1-2 column layout depending on width | [2] Verify cards don't overflow |
| Featured rail shows | Right sidebar displays featured articles | [3] Verify right rail visible with featured block |
| Sticky block displays | Sticky card shows with good proportions | [4] Verify sticky layout adapts |

### 5.3 Desktop (1024px+)

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Three-column layout | Sidebar + Feed + Featured rail | [1] Set viewport to 1200px+ → All three visible |
| Cards display optimally | 2-column feed layout | [2] Verify 2 cards per row in feed |
| Sticky prominent | Prominent featured section for sticky post | [3] Verify sticky shows clearly |
| No horizontal scroll | All content fits without scrollbar | [4] Verify no overflow-x |

---

## Test Category 6: Data Flow Verification (Editor → Frontmatter → Display)

### 6.1 Featured Article Frontmatter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| featured = true writes | Frontmatter contains `featured = true` in [extra] | [1] Edit article in Editor, check Featured → Save → View source in GitHub |
| featured_at timestamp | Frontmatter contains `featured_at = "ISO8601"` | [2] Verify timestamp format |
| Template renders data-featured | HTML has `data-featured="true"` | [3] Inspect card in DevTools → Check data-featured attribute |
| Featured quick filter works | Clicking "Biên tập chọn" shows this article | [4] Click Featured filter → Article appears in results |

### 6.2 Sticky Article Frontmatter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| sticky = true writes | Frontmatter contains `sticky = true` in [extra] | [1] Edit article in Editor, check Sticky → Save → View source |
| Template renders data-sticky | HTML has `data-sticky="true"` | [2] Inspect card in DevTools → Check data-sticky |
| Sticky quick filter works | Clicking "Bài nổi bật" filter shows sticky article | [3] Click Sticky filter → Article appears |
| Sticky block shows | Sticky article displays in top sticky section | [4] Load homepage → Verify sticky article shows in spotlight block |

### 6.3 Category Frontmatter

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Single category writes | [taxonomies] categories = ["category_name"] | [1] Edit article in Editor → Select category → Save → Check source |
| Template renders data-categories | HTML has `data-categories="category_name"` | [2] Inspect card → Verify data-categories attribute |
| Category filter works | Clicking category filter shows article | [3] Click category → Article appears |
| Multiple categories (if applicable) | If template supports, verify comma-separated | [4] Check if Editor supports multiple categories (currently single) |

---

## Test Category 7: Regression Testing (Verify Fixes Don't Break Existing Features)

### 7.1 Search Functionality

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Search box visible | Search input in sidebar | [1] Verify search box displays |
| Search filters results | Typing keywords filters articles | [2] Type keyword → Verify matching articles show |
| Search works with categories | Can combine search + category filter | [3] Select category, then search → Results filtered by both |

### 7.2 Article Cards

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Card layout correct | Image, title, excerpt, date, read time | [1] Verify card structure |
| Premium badge shows | Premium articles have badge | [2] Spot-check premium articles have badge |
| Read time shows | "X phút đọc" displays | [3] Verify read time shows |
| Links work | Card links navigate correctly | [4] Click various card links → Navigate correctly |

### 7.3 Links & Navigation

| Test | Expected | Manual Steps |
|------|----------|--------------|
| Archive link works | "Xem toàn bộ bài viết" link in sidebar | [1] Click → Goes to archive page |
| Series links work | Series block links navigate | [2] Click series → Goes to series page |
| No broken links | All navigation links work | [3] Check DevTools console for 404 errors |

---

## Test Execution Checklist

### Pre-Test Setup
- [ ] Checkout branch: `git checkout claude/home-blog-filter-fix-vz6117`
- [ ] Install dependencies: `npm install` (if needed)
- [ ] Build site: `zola build`
- [ ] Serve locally: `zola serve` or similar
- [ ] Open DevTools (F12) for console error checking
- [ ] Test in multiple browsers (Chrome, Firefox, Safari)
- [ ] Clear browser cache between test runs

### Browser & Viewport Combinations
- [ ] Chrome Desktop (1440px)
- [ ] Chrome Tablet (768px)
- [ ] Chrome Mobile (390px)
- [ ] Firefox Desktop (1440px)
- [ ] Firefox Mobile (390px)
- [ ] Safari (if available)

### Issues to Document
For each test case that fails:
1. Describe expected vs actual behavior
2. Screenshot (if visual issue)
3. Browser & viewport where issue occurs
4. Steps to reproduce
5. Severity (Critical / High / Medium / Low)

---

## Test Results Template

**Tester:** ___________  
**Date:** ___________  
**Browser:** ___________ (Version: _______)  
**Viewport:** ___________ (px)  

### Summary
- Total Tests: 50+
- Passed: _____
- Failed: _____
- Skipped: _____
- Issues Found: _____

### Critical Failures
(List any failures that block usage)

### Non-Critical Issues
(List nice-to-haves or visual tweaks)

### Sign-Off
- [ ] Ready for PR/Merge
- [ ] Needs fixes before merge
- [ ] Major issues found

**Comments:**

---

## Known Limitations & Not Tested

- **Browser Compatibility:** IE11 not tested (officially unsupported)
- **Accessibility:** A11y testing not included in this plan (separate audit needed)
- **Performance:** Load time, Core Web Vitals not tested (separate audit needed)
- **SEO:** Meta tags, structured data not tested (separate audit)
- **AdSense Integration:** Ad display verified for placement conflicts, not ad revenue/impression counting

---

## Deployment Checklist

Before merging PR:
- [ ] All critical tests pass (T1–T7 in scope)
- [ ] No console errors in DevTools
- [ ] No layout shifts on filter interactions
- [ ] Mobile responsive works on 360–1440px
- [ ] Pagination works correctly
- [ ] Featured & Sticky display/hide as expected
- [ ] Data attributes render correctly
- [ ] No AdSense conflicts
- [ ] Commit messages clear
- [ ] Documentation complete (DATA_CONTRACT_AUDIT.md)

