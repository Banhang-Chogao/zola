/* ============================================================
   ===== THEME SWITCHER — Z-X (ZaloPay · fintech) ONLY =====
   ============================================================
   Single theme system: Z-X (ZaloPay style).

   Persist: localStorage["blog-theme"] = "zx" (default)
   Anti-flash: Inline IIFE trong base.html <head> đã apply data-theme
   trước paint. File này handle UI interaction.

   API:
   - window.ThemeSwitcher.getTheme() : "zx"
   - window.ThemeSwitcher.setTheme("zx")
   - Event "themechange" trên document */

(function () {
  "use strict";

  var STORAGE_KEY = "blog-theme";
  var THEME = "zx";  // Z-X is the only theme
  var ATTR = "data-theme";
  var root = document.documentElement;

  /* ===== Get current theme from DOM ===== */
  function getTheme() {
    return THEME;
  }

  /* ===== Apply theme to DOM + localStorage ===== */
  function setTheme(name) {
    // Always Z-X
    name = THEME;

    // Apply to DOM
    root.setAttribute(ATTR, name);

    // Persist
    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      /* localStorage blocked; silent fail */
    }

    // Dispatch event for external listeners
    document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: name } }));
  }

  /* ===== Init on DOM ready ===== */
  function init() {
    setTheme(THEME);
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
    THEME: THEME
  };
})();
