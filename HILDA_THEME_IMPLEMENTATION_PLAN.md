# Hilda Theme Implementation Plan (Option C)

**Status:** 🔄 Planning Phase — Awaiting User Approval  
**Date:** 2026-06-16  
**Architecture:** Multi-theme restore + Hilda secondary theme

---

## 1. Executive Summary

### Current State
- Z-X only system (single theme, hardcoded in JavaScript)
- Multi-theme infrastructure removed (BrandingX, E-X token files deleted)
- `theme-switcher.js` hardcoded to prevent switching

### Target State (Option C)
- **Z-X remains default** (ZaloPay fintech blue)
- **Hilda added as secondary theme** (Ericsson professional style)
- Multi-theme infrastructure **restored with improvements**
- Theme switcher **re-enabled** with localStorage persistence
- Zero breaking changes to existing Z-X implementation

---

## 2. Branding Specifications (Hilda - Ericsson)

### Color Palette
```
Primary:        #003784 (Ericsson Blue) — headings, primary CTAs, accents
Secondary:      #00A69D (Teal) — secondary elements, hover states
Background:     #FFFFFF (White) + #F4F4F4 (Light Gray)
Text Heading:   #000000 (Pure Black)
Text Body:      #333333 (Charcoal)
Text Muted:     #666666 (Gray)
Accent CTA:     #E30613 (Red) — action buttons, alerts
Border:         #E0E0E0 (Light Divider)
Shadow:         rgba(0, 55, 132, 0.08) — professional depth
```

### Typography
```
Font Family:    Inter or Roboto (Google Fonts fallback for proprietary Hilda)
Base Size:      16px
Font Weights:   400 (Regular), 600 (SemiBold), 700 (Bold)
Letter Spacing: Professional (Hilda: -0.02em, Z-X: -0.025em)
```

### Design System
```
Border Radius:  4px (sharp, professional — vs Z-X 14px soft)
Spacing:        8px base unit (8, 16, 24, 32, 40px)
Shadows:        Minimal (Hilda) vs Prominent (Z-X)
```

---

## 3. Architecture Changes

### 3.1 File Structure Changes

**NEW FILES to create:**
```
sass/
├── _hilda-tokens.scss       (NEW: Hilda color + spacing tokens)
├── _hilda-fonts.scss        (NEW: Hilda typography settings)
└── _hilda-overrides.scss    (NEW: Hilda component overrides)
```

**FILES to RESTORE/MODIFY:**
```
sass/
├── _themes.scss             (MODIFY: Add Hilda theme block + restore data-theme structure)
├── _theme-overrides.scss    (MODIFY: Add Hilda component scoping)
├── site.scss                (UPDATE: Add new imports)

static/js/
└── theme-switcher.js        (REWRITE: Multi-theme support + localStorage)

templates/
└── base.html                (VERIFY: Ensure data-theme attribute applied)
```

### 3.2 CSS Variable Architecture

**Root level (`:root`)** — Z-X defaults (unchanged):
```scss
:root {
  --c-bg-page:        #f5f8ff;    /* Z-X Mist */
  --c-bg-surface:     #ffffff;    /* Z-X Snow */
  --c-text-heading:   #0b1834;    /* Z-X Ink-900 */
  --c-accent:         #0068ff;    /* Z-X Blue-600 */
  /* ... 15+ variables ... */
}
```

**Scoped to Hilda** — `:root[data-theme="hilda"]`:
```scss
:root[data-theme="hilda"] {
  --c-bg-page:        #f4f4f4;    /* Hilda Light Gray */
  --c-bg-surface:     #ffffff;    /* Hilda White */
  --c-text-heading:   #000000;    /* Hilda Black */
  --c-accent:         #003784;    /* Hilda Ericsson Blue */
  /* ... override 15+ variables ... */
}
```

---

## 4. Implementation Phases

### Phase 1: Token Files (SASS variables)

**File: `sass/_hilda-tokens.scss`**
```scss
/* Hilda Color Tokens - Ericsson Professional Style */
$hilda-primary:          #003784;  /* Ericsson Blue */
$hilda-secondary:        #00A69D;  /* Teal */
$hilda-white:            #ffffff;
$hilda-light-gray:       #f4f4f4;
$hilda-text-heading:     #000000;
$hilda-text-body:        #333333;
$hilda-text-muted:       #666666;
$hilda-accent-cta:       #e30613;  /* Red action buttons */
$hilda-border:           #e0e0e0;
$hilda-shadow-sm:        0 2px 4px rgba(0, 55, 132, 0.08);
$hilda-shadow-lg:        0 8px 16px rgba(0, 55, 132, 0.12);

/* Hilda Spacing & Radius */
$hilda-radius-sm:        4px;      /* Sharp, professional */
$hilda-radius-md:        4px;      /* Consistent sharp corners */
$hilda-radius-lg:        4px;      /* No soft curves */

/* Hilda Typography */
$hilda-font-family:      'Inter', 'Roboto', sans-serif;
$hilda-font-size-base:   16px;
$hilda-weight-regular:   400;
$hilda-weight-semibold:  600;
$hilda-weight-bold:      700;
$hilda-letter-spacing:   -0.02em;
```

**File: `sass/_hilda-fonts.scss`**
```scss
/* Import Google Fonts - Inter (primary choice) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* Fallback font stack */
:root[data-theme="hilda"] {
  font-family: 'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --hilda-font-family: 'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

### Phase 2: Theme Definition (`_themes.scss`)

**Modify: `sass/_themes.scss`**

Add Hilda theme block:
```scss
/* ===== HILDA (Ericsson - Professional) ===== */
:root[data-theme="hilda"] {
  /* Background */
  --c-bg-page:        #f4f4f4;    /* Light Gray */
  --c-bg-surface:     #ffffff;    /* White */
  --c-bg-soft:        #f4f4f4;    /* Soft background */

  /* Text */
  --c-text-heading:   #000000;    /* Pure Black */
  --c-text-body:      #333333;    /* Charcoal */
  --c-text-muted:     #666666;    /* Gray */

  /* Accent & CTA */
  --c-accent:         #003784;    /* Ericsson Blue (primary) */
  --c-accent-hover:   #002566;    /* Darker blue for hover */
  --c-accent-soft:    rgba(0, 55, 132, 0.1);  /* Soft blue bg */

  /* Secondary & Decoration */
  --c-secondary:      #00a69d;    /* Teal */
  --c-decoration:     #e30613;    /* Red for CTAs */

  /* Border & Shadow */
  --c-border:         #e0e0e0;    /* Light divider */
  --c-border-strong:  #d0d0d0;    /* Darker divider */
  --c-shadow-md:      0 2px 4px rgba(0, 55, 132, 0.08);
  --c-shadow-lg:      0 8px 16px rgba(0, 55, 132, 0.12);

  /* Status */
  --c-success:        #00a69d;    /* Green/Teal */
  --c-warning:        #ff9500;    /* Orange */

  /* Focus Ring */
  --c-focus-ring:     rgba(0, 55, 132, 0.35);

  /* Color Scheme */
  color-scheme: light;
}
```

### Phase 3: Component Overrides (`_theme-overrides.scss`)

**Modify: `sass/_theme-overrides.scss`**

Create Hilda-specific mixin:
```scss
@mixin theme-overrides-hilda(
  $radius-card:       4px,
  $radius-tag:        4px,
  $shadow-card:       0 2px 4px rgba(0, 55, 132, 0.08),
  $shadow-card-hover: 0 8px 16px rgba(0, 55, 132, 0.12),
  $kicker-spacing:    0.05em,      /* Tighter than Z-X */
  $heading-ls:        -0.02em
) {
  /* Post card, sidebar, related articles, etc. */
  /* (Same component selectors as Z-X, different param values) */
}

/* Apply Hilda overrides */
:root[data-theme="hilda"] {
  @include theme-overrides-hilda(
    $radius-card:       4px,
    $radius-tag:        4px,
    $shadow-card:       $hilda-shadow-sm,
    $shadow-card-hover: $hilda-shadow-lg,
    $kicker-spacing:    0.05em,
    $heading-ls:        -0.02em
  );
}
```

### Phase 4: Theme Switcher JavaScript

**REWRITE: `static/js/theme-switcher.js`**

```javascript
(function () {
  "use strict";

  var STORAGE_KEY = "blog-theme";
  var VALID_THEMES = ["zx", "hilda"];
  var DEFAULT_THEME = "zx";
  var ATTR = "data-theme";
  var root = document.documentElement;

  /* ===== Get current theme from DOM or localStorage ===== */
  function getTheme() {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      /* localStorage blocked; silent fail */
    }
    
    var current = root.getAttribute(ATTR) || DEFAULT_THEME;
    return (stored && VALID_THEMES.indexOf(stored) > -1) ? stored : current;
  }

  /* ===== Apply theme to DOM + localStorage ===== */
  function setTheme(name) {
    // Validate theme
    if (VALID_THEMES.indexOf(name) === -1) {
      name = DEFAULT_THEME;
    }

    // Apply to DOM
    root.setAttribute(ATTR, name);

    // Persist to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      /* localStorage blocked; silent fail */
    }

    // Dispatch event for external listeners
    document.dispatchEvent(new CustomEvent("themechange", { 
      detail: { theme: name } 
    }));
  }

  /* ===== Toggle theme ===== */
  function toggleTheme() {
    var current = getTheme();
    var next = current === "zx" ? "hilda" : "zx";
    setTheme(next);
    return next;
  }

  /* ===== Init on DOM ready ===== */
  function init() {
    var savedTheme = getTheme();
    setTheme(savedTheme);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  /* ===== Expose API ===== */
  window.ThemeSwitcher = {
    getTheme: getTheme,
    setTheme: setTheme,
    toggleTheme: toggleTheme,
    VALID_THEMES: VALID_THEMES,
    DEFAULT_THEME: DEFAULT_THEME
  };
})();
```

### Phase 5: Toggle Button HTML (Template)

**Add to `templates/base.html`** (in navbar or suitable location):

```html
<button id="theme-toggle-btn" class="theme-toggle" aria-label="Toggle theme">
  <span class="theme-icon">🎨</span>
  <span class="theme-label" id="theme-label">Hilda</span>
</button>

<script>
  document.getElementById("theme-toggle-btn")?.addEventListener("click", function() {
    var nextTheme = window.ThemeSwitcher.toggleTheme();
    var label = document.getElementById("theme-label");
    if (label) {
      label.textContent = nextTheme === "zx" ? "Z-X" : "Hilda";
    }
  });
</script>
```

### Phase 6: Import Updates (`site.scss`)

**Modify: `sass/site.scss`**

```scss
@charset "utf-8";

@import "brand-vars";
@import "zx-tokens";        /* Z-X defaults */
@import "hilda-tokens";     /* NEW: Hilda tokens */
@import "hilda-fonts";      /* NEW: Hilda font imports */
@import "themes";           /* Modified: includes both Z-X + Hilda */
@import "fonts";
@import "reset";
@import "layout";
@import "navbar";
@import "post";
@import "sidebar";
@import "single";
@import "banner";
@import "footer";
@import "editor";
@import "stats";
@import "changelog";
@import "insights";
@import "baochi";
@import "du-lich";
@import "scoring";
@import "bao-cao";
@import "zx";
@import "theme-overrides";   /* Modified: includes Hilda overrides */
@import "theme-switcher-styles";  /* NEW: Toggle button styles */
```

### Phase 7: Toggle Button Styles

**Create: `sass/_theme-switcher-styles.scss`**

```scss
/* Theme Toggle Button */
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--c-bg-soft);
  border: 1px solid var(--c-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-body);

  &:hover {
    background: var(--c-accent);
    color: var(--c-bg-surface);
    border-color: var(--c-accent);
  }

  &:active {
    transform: scale(0.98);
  }

  .theme-icon {
    font-size: 16px;
  }

  .theme-label {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
}

/* Responsive: Stack on mobile */
@media (max-width: 640px) {
  .theme-toggle {
    .theme-label {
      display: none; /* Show icon only on mobile */
    }
  }
}
```

---

## 5. Testing Strategy

### 5.1 Visual Testing
- [ ] Z-X theme displays correctly (no regression)
- [ ] Hilda theme colors match specs exactly
- [ ] Toggle button works (Z-X ↔ Hilda)
- [ ] localStorage persists theme on page reload
- [ ] Responsive design intact on mobile (≤720px)
- [ ] Desktop layout unchanged

### 5.2 Browser Compatibility
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (iOS 14+)
- [ ] localStorage fallback (works without localStorage)

### 5.3 Performance
- [ ] No layout shift on theme toggle (CLS test)
- [ ] CSS variables load efficiently
- [ ] JavaScript bundle size minimal

---

## 6. Risk Assessment & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Multi-theme CSS bloat | Higher file size | Use SCSS mixins to minimize duplication |
| localStorage fails silently | User loses preference | Fallback to default Z-X always works |
| Theme toggle broken layout | Visual regression | Test all components across themes |
| Font loading delay (Google Fonts) | FOUC (Flash of Unstyled Content) | Use font-display: swap in @import |
| data-theme attribute missing | Theme not applied | Set inline style in `<head>` IIFE |

---

## 7. Timeline & Phases

| Phase | Deliverable | Estimated Time |
|---|---|---|
| 1-3 | Token files + Themes + Overrides | 4 hours |
| 4 | Theme switcher JS | 2 hours |
| 5-7 | Templates + Styles + Testing | 3 hours |
| Review & Refinement | Bug fixes, polishing | 1-2 hours |

**Total: ~10-12 hours** (split across 2-3 commits)

---

## 8. Rollback Plan

If Hilda implementation causes issues:
1. Revert all new files (hilda-tokens, hilda-fonts, hilda-overrides)
2. Restore theme-switcher.js to Z-X only
3. Remove data-theme attribute from base.html
4. Run `zola build` to verify Z-X still works

---

## 9. Success Criteria

- ✅ Z-X theme works identically to before
- ✅ Hilda theme renders correctly per specifications
- ✅ Theme switcher toggles instantly without reload
- ✅ localStorage persists user preference
- ✅ All CLAUDE.md responsive design rules maintained
- ✅ No breaking changes to existing components
- ✅ Mobile (≤720px) and Desktop both tested
- ✅ Zola build passes with no errors

---

## Questions for User Review

1. **Font Import Strategy**: Use Google Fonts `@import` or `<link>` in base.html?
2. **Toggle Button Placement**: Navbar? Sidebar? Floating fixed button?
3. **Animation**: Fade transition between themes or instant switch?
4. **Default Theme Behavior**: Should Hilda be available on first visit, or Z-X default always?
5. **Testing Scope**: Should we test 100% of components or focus on high-priority ones?

---

**Status**: ⏳ Awaiting your approval before implementation starts.
