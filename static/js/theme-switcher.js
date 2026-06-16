/* ============================================================
   ===== THEME SWITCHER — 4-option dropdown (Hybrid refactor) =====
   ============================================================
   Phase 2: Refactor từ 2-option toggle → 4-option dropdown.

   Themes: "" (BrandingX), "zx" (Z-X), "ex" (E-X), "hila" (Hila)
   Persist: localStorage["blog-theme"] — key KHÔNG đổi (backward compat)
   Migration: "default" (old) → "" (new) tự động

   Anti-flash: Inline IIFE trong base.html <head> đã apply data-theme
   trước paint. File này handle UI interaction (dropdown toggle/select).

   API (backward compat):
   - window.ThemeSwitcher.getTheme() : "" | "zx" | "ex" | "hila"
   - window.ThemeSwitcher.setTheme(name)
   - window.ThemeSwitcher.toggle() : iterate next theme
   - Event "themechange" trên document khi switch */

(function () {
  "use strict";

  var STORAGE_KEY = "blog-theme";
  var THEME_NAMES = {
    "":      "BrandingX",
    "zx":    "Z-X",
    "ex":    "E-X",
    "hila":  "Hila Ericsson"
  };
  var VALID_THEMES = ["zx", "ex", "hila"];
  var ALL_THEMES = ["", "zx", "ex", "hila"];
  var ATTR = "data-theme";
  var root = document.documentElement;

  /* ===== Get current theme from DOM ===== */
  function getTheme() {
    var attr = root.getAttribute(ATTR) || "";
    return attr;
  }

  /* ===== Migrate old localStorage "default" → "" ===== */
  function migrateStorage() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "default") {
        localStorage.setItem(STORAGE_KEY, "");
      }
    } catch (e) {}
  }

  /* ===== Apply theme to DOM + localStorage ===== */
  function setTheme(name) {
    // Normalize: "default" → "", invalid → ""
    if (name === "default" || (name && VALID_THEMES.indexOf(name) === -1)) {
      name = "";
    }

    // Apply to DOM
    if (name === "") {
      root.removeAttribute(ATTR);
    } else {
      root.setAttribute(ATTR, name);
    }

    // Persist
    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      /* localStorage blocked (iOS private mode); silent fail */
    }

    // Update UI (dropdown)
    updateDropdownState(name);

    // Dispatch event for external listeners
    document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: name } }));
  }

  /* ===== Iterate to next theme (for toggle API) ===== */
  function toggle() {
    var current = getTheme();
    var idx = ALL_THEMES.indexOf(current);
    if (idx === -1) idx = 0;
    var next = ALL_THEMES[(idx + 1) % ALL_THEMES.length];
    setTheme(next);
  }

  /* ===== Update dropdown UI state ===== */
  function updateDropdownState(theme) {
    var toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) return;

    var btn = toggle.querySelector(".theme-toggle__btn");
    var currentLabel = toggle.querySelector("[data-theme-current]");
    var opts = toggle.querySelectorAll("[data-theme-set]");

    if (currentLabel) {
      currentLabel.textContent = THEME_NAMES[theme] || "BrandingX";
    }

    opts.forEach(function (opt) {
      var optTheme = opt.getAttribute("data-theme-set") || "";
      var isMatch = optTheme === theme;
      opt.setAttribute("aria-checked", isMatch ? "true" : "false");
    });
  }

  /* ===== Wire dropdown: open/close/select ===== */
  function wireDropdown() {
    var toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) return;

    var btn = toggle.querySelector(".theme-toggle__btn");
    var menu = toggle.querySelector("[data-theme-menu]");
    var opts = toggle.querySelectorAll("[data-theme-set]");

    if (!btn || !menu) return;

    function openMenu() {
      menu.hidden = false;
      btn.setAttribute("aria-expanded", "true");
    }

    function closeMenu() {
      menu.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    }

    function toggleMenu() {
      if (menu.hidden) {
        openMenu();
      } else {
        closeMenu();
      }
    }

    // Button click → toggle dropdown
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleMenu();
    });

    // Option click → select theme + close
    opts.forEach(function (opt) {
      opt.addEventListener("click", function (e) {
        e.stopPropagation();
        var nextTheme = opt.getAttribute("data-theme-set") || "";
        setTheme(nextTheme);
        closeMenu();
      });
    });

    // Close on outside click
    document.addEventListener("click", function (e) {
      if (!toggle.contains(e.target)) {
        closeMenu();
      }
    });

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !menu.hidden) {
        closeMenu();
        btn.focus();
      }
    });

    // Sync UI on load
    updateDropdownState(getTheme());
  }

  /* ===== Fallback: wire old toggle button (for backward compat) ===== */
  function wireOldToggleButton() {
    var btn = document.getElementById("theme-switch-btn");
    if (!btn) return;

    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      toggle();
    });

    // Update old button labels if present
    var labelMomo = btn.querySelector('[data-theme-label="default"]');
    var labelZx = btn.querySelector('[data-theme-label="zx"]');
    var current = getTheme();

    if (current === "zx") {
      btn.setAttribute("aria-pressed", "true");
      btn.setAttribute("aria-label", "Đang dùng theme Z-X. Click chuyển về BrandingX");
      if (labelMomo) labelMomo.hidden = true;
      if (labelZx) labelZx.hidden = false;
    } else {
      btn.setAttribute("aria-pressed", "false");
      btn.setAttribute("aria-label", "Đang dùng theme BrandingX. Click chuyển sang Z-X");
      if (labelMomo) labelMomo.hidden = false;
      if (labelZx) labelZx.hidden = true;
    }
  }

  /* ===== Init on DOM ready ===== */
  function init() {
    migrateStorage();
    wireDropdown();
    wireOldToggleButton();
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
    THEMES: ALL_THEMES.slice(),
    THEME_NAMES: THEME_NAMES
  };
})();
