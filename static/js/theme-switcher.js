/* ============================================================
   ===== THEME SWITCHER — BrandingX ↔ Z-X (Dynamic) =====
   ============================================================
   Dual theme system with smooth transitions:
   - "brandingx" (default) — MoMo pink + red, warm playful
   - "zx" — ZaloPay electric blue, fintech trust

   Persist: localStorage["blog-theme"] = "zx" | "brandingx"
   Anti-flash: Inline IIFE dalam base.html <head> sudah apply
   data-theme sebelum paint. File ini handle UI interaction.

   API:
   - window.ThemeSwitcher.getTheme() : "brandingx" | "zx"
   - window.ThemeSwitcher.setTheme("zx")
   - window.ThemeSwitcher.toggle() : switch ke theme lain
   - Event "themechange" pada document dengan detail: { theme, prevTheme }
*/

(function () {
  "use strict";

  var STORAGE_KEY = "blog-theme";
  var THEMES = {
    brandingx: "brandingx",  // MoMo
    zx: "zx"                 // default: ZaloPay fintech
  };
  var DEFAULT_THEME = "zx";
  var ATTR = "data-theme";
  var root = document.documentElement;

  /* ===== Get current theme from DOM or localStorage ===== */
  function getTheme() {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      /* localStorage blocked */
    }

    // Use stored theme if valid, otherwise check DOM data-theme, fallback default
    if (stored && THEMES[stored]) {
      return stored;
    }

    var domTheme = root.getAttribute(ATTR);
    if (domTheme && THEMES[domTheme]) {
      return domTheme;
    }

    return DEFAULT_THEME;
  }

  /* ===== Apply theme to DOM + localStorage ===== */
  function setTheme(name) {
    // Validate theme name
    if (!THEMES[name]) {
      console.warn("[ThemeSwitcher] Invalid theme: " + name);
      return;
    }

    var prevTheme = getTheme();

    // Apply to DOM
    // Z-X is default: remove data-theme attribute for Z-X, set for others
    if (name === "zx") {
      root.removeAttribute(ATTR);
    } else {
      root.setAttribute(ATTR, name);
    }

    // Persist to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      /* localStorage blocked; silent fail */
    }

    // Dispatch event for external listeners (only if actually changed)
    if (name !== prevTheme) {
      document.dispatchEvent(
        new CustomEvent("themechange", {
          detail: { theme: name, prevTheme: prevTheme }
        })
      );
    }
  }

  /* ===== Toggle between BrandingX ↔ Z-X ===== */
  function toggle() {
    var current = getTheme();
    var next = current === "zx" ? "brandingx" : "zx";
    setTheme(next);
  }

  /* ===== Init on DOM ready (apply stored theme before paint) ===== */
  function init() {
    var current = getTheme();
    if (current !== DEFAULT_THEME) {
      root.setAttribute(ATTR, current);
    }
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
    toggle: toggle,
    THEMES: THEMES,
    DEFAULT_THEME: DEFAULT_THEME
  };
})();
