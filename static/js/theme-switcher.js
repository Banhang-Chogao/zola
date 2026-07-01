/* ============================================================
   ===== THEME SWITCHER — Hilda + Nokia Blog =====
   ============================================================
   Persistent theme with localStorage. Default: hilda.
*/

(function () {
  "use strict";

  var STORAGE_KEY = "blog-theme";
  var VALID_THEMES = ["hilda", "nokia"];
  var DEFAULT_THEME = "hilda";
  var ATTR = "data-theme";
  var root = document.documentElement;

  function getTheme() {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      /* localStorage blocked */
    }

    if (stored && VALID_THEMES.indexOf(stored) > -1) {
      return stored;
    }

    var current = root.getAttribute(ATTR);
    return (current && VALID_THEMES.indexOf(current) > -1) ? current : DEFAULT_THEME;
  }

  function setTheme(name) {
    if (VALID_THEMES.indexOf(name) === -1) {
      name = DEFAULT_THEME;
    }

    root.setAttribute(ATTR, name);

    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      /* silent */
    }

    document.dispatchEvent(new CustomEvent("themechange", {
      detail: {
        theme: name,
        timestamp: new Date().toISOString()
      }
    }));
  }

  function toggleTheme() {
    var current = getTheme();
    var idx = VALID_THEMES.indexOf(current);
    var next = VALID_THEMES[(idx + 1) % VALID_THEMES.length];
    setTheme(next);
    return next;
  }

  function init() {
    setTheme(getTheme());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.ThemeSwitcher = {
    getTheme: getTheme,
    setTheme: setTheme,
    toggleTheme: toggleTheme,
    VALID_THEMES: VALID_THEMES,
    DEFAULT_THEME: DEFAULT_THEME
  };
})();