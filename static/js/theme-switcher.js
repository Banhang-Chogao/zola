/* ============================================================
   ===== THEME SWITCHER — runtime toggle BrandingX <-> Z-X =====
   ============================================================
   API:
   - window.ThemeSwitcher.getTheme() : "default" | "zx"
   - window.ThemeSwitcher.setTheme(name)
   - window.ThemeSwitcher.toggle()
   - Event "themechange" trên document khi switch

   Persistence: localStorage["blog-theme"] = "zx" | "default"
   Default theme nếu chưa set: "default" (BrandingX MoMo style)

   Anti-flash: IIFE inline trong <head> (xem base.html) ĐÃ set
   data-theme TRƯỚC khi script này load → khi load xong chỉ cần
   wire button click. */
(function () {
  'use strict';

  var STORAGE_KEY = 'blog-theme';
  var THEMES = ['default', 'zx'];
  var ATTR = 'data-theme';
  var root = document.documentElement;

  function getTheme() {
    var attr = root.getAttribute(ATTR);
    if (THEMES.indexOf(attr) !== -1) return attr;
    return 'default';
  }

  function setTheme(name) {
    if (THEMES.indexOf(name) === -1) name = 'default';

    if (name === 'default') {
      root.removeAttribute(ATTR);
    } else {
      root.setAttribute(ATTR, name);
    }

    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      // localStorage có thể bị block (private browsing iOS); im lặng skip.
    }

    updateButtonState(name);
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: name } }));
  }

  function toggle() {
    var current = getTheme();
    setTheme(current === 'zx' ? 'default' : 'zx');
  }

  function updateButtonState(theme) {
    var btn = document.getElementById('theme-switch-btn');
    if (!btn) return;
    var labelMomo = btn.querySelector('[data-theme-label="default"]');
    var labelZx = btn.querySelector('[data-theme-label="zx"]');
    if (theme === 'zx') {
      btn.setAttribute('aria-pressed', 'true');
      btn.setAttribute('aria-label', 'Đang dùng theme Z-X. Click chuyển về BrandingX');
      if (labelMomo) labelMomo.hidden = true;
      if (labelZx) labelZx.hidden = false;
    } else {
      btn.setAttribute('aria-pressed', 'false');
      btn.setAttribute('aria-label', 'Đang dùng theme BrandingX. Click chuyển sang Z-X');
      if (labelMomo) labelMomo.hidden = false;
      if (labelZx) labelZx.hidden = true;
    }
  }

  function wireButton() {
    var btn = document.getElementById('theme-switch-btn');
    if (!btn) return;
    btn.addEventListener('click', function (ev) {
      ev.preventDefault();
      toggle();
    });
    updateButtonState(getTheme());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireButton);
  } else {
    wireButton();
  }

  window.ThemeSwitcher = {
    getTheme: getTheme,
    setTheme: setTheme,
    toggle: toggle,
    THEMES: THEMES.slice()
  };
})();
