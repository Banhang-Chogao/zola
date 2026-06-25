# sidebar_layout_vaccine — right-column menu must be in-grid, not overlay

**Date:** 2026-06-20
**Scope:** `sass/_side-nav.scss`, `sass/_sidebar.scss`, `sass/_layout.scss`,
`templates/base.html`, `scripts/qa_vaccines.py`, `scripts/test_qa_vaccines.py`
**Trigger:** screenshot — primary menu (Trang chủ pill · Insights · Công cụ · Bài
viết · Vụ Mùa · Tìm kiếm · Xoá cache) appearing to float/overlay page content
(introduced area: PR #526 right-column nav).

## Symptom
The right-column navigation looked like a floating card covering hero/content
(suspected `position: fixed/absolute` + high z-index overlay).

## Root cause (as found in source)
**No overlay exists in the committed CSS.** Audit of the actual source shows the
menu is already laid out correctly:
- `.side-nav` → `position: sticky; top: 1rem; z-index: 5` — **in-flow**, lives at
  the top of the right column (not fixed/absolute).
- `.sidebar` → `display: flex` static column, inside the page grid.
- `.layout-grid` desktop → `grid-template-columns: minmax(0, 1fr) 400px` — a real
  400px right column is reserved; `.main-column { min-width: 0 }` so content shrinks
  beside the sidebar and can never blow the grid.
- `@media (max-width: 960px)` → grid collapses to `1fr`, `.side-nav { display: none }`,
  navigation becomes the `.nav-drawer` which is `hidden` by default (closed state
  does not cover content).
- JS (`side-nav.js`) only toggles `.is-active` + drawer open/close — no float.

So the overlay was not reproducible from source (likely a pre-PR#526 state or a
stale cache). The durable fix is a **vaccine that locks the in-grid invariant** so
any future regression to a fixed/absolute overlay or single-track grid fails CI.

## Vaccine Summary

### Existing vaccines used
- **QA Vaccine Gate** (`qa_check.py` / `scripts/qa_vaccines.py`) — host for the new
  detector; gated the change (100/100).

### New vaccines created
- **`sidebar_layout_vaccine`** — `check_sidebar_layout` (code `UI-SIDEBAR`) in
  `scripts/qa_vaccines.py`, registered in `DETECTORS`. Static invariants:
  1. `.side-nav` is NOT `position: fixed/absolute` (must be sticky/static) → FAIL.
  2. `.sidebar` column is in-flow (not fixed/absolute) → FAIL.
  3. `.layout-grid` reserves a real 2nd (right) column on desktop (two-track
     `grid-template-columns`) → FAIL if single-track only.
  4. `.main-column { min-width: 0 }` present → WARN if missing.
  5. ≤960px hides `.side-nav` + `.nav-drawer` has `hidden` by default → WARN.
  Helper `_css_blocks()` brace-matches every rule body (covers media-query copies);
  track counting blanks parenthesised groups so `minmax(0,1fr) 400px` counts as 2.

### Existing vaccines upgraded
- None (additive detector only).

### Root cause prevented
A regression where the right-column menu/sidebar becomes a fixed/absolute
high-z overlay, or the desktop grid loses its reserved sidebar column, letting the
menu cover hero/content — now caught by the QA gate before deploy.

### Files changed
- `scripts/qa_vaccines.py` (+`_css_blocks`, +`check_sidebar_layout`, +DETECTORS entry)
- `scripts/test_qa_vaccines.py` (+`SidebarLayoutTest`: real-repo PASS · baseline PASS ·
  side-nav fixed FAIL · sidebar absolute FAIL · single-track grid FAIL · missing
  min-width WARN)

### Validation result
- `python3 scripts/qa_vaccines.py` → UI-SIDEBAR **PASS**, 19/19, 100/100
- `python3 -m unittest scripts.test_qa_vaccines` → 34/34 (incl. 6 sidebar)
- `python3 qa_check.py` → 100/100 PRODUCTION-SAFE
- `python3 scripts/check_internal_links.py` → OK
- `python3 qa-404-checker.py` → exit 0
- 0 conflict markers · `zola build` runs in CI
- Layout verified at desktop (≥961px 2-col), tablet/mobile (≤960px 1-col + hidden
  drawer): menu does not cover content; nav items remain clickable (in-flow links).

### Where saved
- Vaccine code/test: `scripts/qa_vaccines.py`, `scripts/test_qa_vaccines.py`
- This memory: `docs/memory/vaccine-sidebar-layout.md`

## Note
No CSS change was made: the committed layout already satisfies the requested
in-grid (non-overlay) pattern, so per "minimal delta / no redesign / don't break
working desktop" the fix is the regression-locking vaccine, not a layout rewrite.
