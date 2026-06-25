/* ============================================================
   ===== THEME SWITCHER — Single Theme (Hilda only) =====
   ============================================================
   Persistent theme with localStorage (single theme, no switching)
*/

(function () {
  "use strict";

  var STORAGE_KEY = "blog-theme";
  var VALID_THEMES = ["hilda"];
  var DEFAULT_THEME = "hilda";
  var ATTR = "data-theme";
  var root = document.documentElement;

  /* ===== Get current theme from localStorage or DOM ===== */
  function getTheme() {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      /* localStorage blocked; silent fail, continue */
    }

    // Return stored theme if valid, otherwise get from DOM or use default
    if (stored && VALID_THEMES.indexOf(stored) > -1) {
      return stored;
    }

    var current = root.getAttribute(ATTR);
    return (current && VALID_THEMES.indexOf(current) > -1) ? current : DEFAULT_THEME;
  }

  /* ===== Apply theme to DOM + localStorage ===== */
  function setTheme(name) {
    // Validate theme
    if (VALID_THEMES.indexOf(name) === -1) {
      name = DEFAULT_THEME;
    }

    // Apply to DOM (triggers CSS variable changes)
    root.setAttribute(ATTR, name);

    // Persist to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      /* localStorage blocked; silent fail, theme still works */
    }

    // Dispatch custom event for external listeners
    document.dispatchEvent(new CustomEvent("themechange", {
      detail: {
        theme: name,
        timestamp: new Date().toISOString()
      }
    }));
  }

  /* ===== Initialize on DOM ready ===== */
  function init() {
    var savedTheme = getTheme();
    setTheme(savedTheme);
  }

  // Run init when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  /* ===== Expose Public API ===== */
  window.ThemeSwitcher = {
    getTheme: getTheme,
    setTheme: setTheme,
    toggleTheme: function() { return DEFAULT_THEME; }, // No-op: only 1 theme
    VALID_THEMES: VALID_THEMES,
    DEFAULT_THEME: DEFAULT_THEME
  };
})();
