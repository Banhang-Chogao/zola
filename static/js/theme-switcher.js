/* ============================================================
   ===== THEME SWITCHER — Dropdown 3-state =====
   ============================================================
   API:
   - window.ThemeSwitcher.getTheme()         → tên theme hiện tại
   - window.ThemeSwitcher.switchTheme(name)  → set trực tiếp
   - window.ThemeSwitcher.THEMES             → snapshot mảng cấu hình
   - Event "themechange" trên document khi switch

   THEMES = single source of truth. Thêm theme thứ 4 (Hila Ericsson…):
   1. Push 1 entry vào THEMES (name + label + desc + icon SVG)
   2. Thêm block :root[data-theme="<name>"] vào sass/_themes.scss
   3. Thêm key vào anti-flash IIFE trong base.html (allowed list)
   KHÔNG cần đụng macro navbar.html — JS tự render <li> trong menu.

   Persistence: localStorage["blog-theme"]. DEFAULT_THEME không set
   attribute (default render khi không có data-theme).

   Anti-flash: IIFE inline <head> (base.html) ĐÃ set data-theme TRƯỚC
   khi script này load → đây chỉ wire dropdown UI. */
(function () {
  'use strict';

  var STORAGE_KEY = 'blog-theme';
  var ATTR = 'data-theme';
  var DEFAULT_THEME = 'default';

  /* SVG icon strings — inline để KHÔNG cần fetch + cùng currentColor
     style với navbar. width=18 height=18 đồng nhất với button trigger. */
  var ICON_SUN =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<circle cx="12" cy="12" r="4"></circle>' +
      '<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"></path>' +
    '</svg>';
  var ICON_MOON =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>' +
    '</svg>';
  var ICON_NEWSROOM =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path>' +
      '<path d="M18 14h-8"></path>' +
      '<path d="M15 18h-5"></path>' +
      '<path d="M10 6h8v4h-8z"></path>' +
    '</svg>';

  var THEMES = [
    {
      name: 'default',
      label: 'BrandingX',
      desc: 'MoMo — warm playful',
      icon: ICON_SUN
    },
    {
      name: 'zx',
      label: 'Z-X',
      desc: 'ZaloPay — trust fintech',
      icon: ICON_MOON
    },
    {
      name: 'ex',
      label: 'E-X',
      desc: 'Ericsson Newsroom — corporate',
      icon: ICON_NEWSROOM
    }
  ];

  var root = document.documentElement;
  var container = null;
  var trigger = null;
  var triggerIconEl = null;
  var menu = null;

  /* ===== Lookup helpers ===== */
  function findTheme(name) {
    for (var i = 0; i < THEMES.length; i++) {
      if (THEMES[i].name === name) return THEMES[i];
    }
    return null;
  }

  function getTheme() {
    var attr = root.getAttribute(ATTR);
    if (attr && findTheme(attr)) return attr;
    return DEFAULT_THEME;
  }

  /* ===== Apply theme: set attribute + persist + sync UI ===== */
  function switchTheme(name) {
    if (!findTheme(name)) name = DEFAULT_THEME;

    if (name === DEFAULT_THEME) {
      root.removeAttribute(ATTR);
    } else {
      root.setAttribute(ATTR, name);
    }

    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch (e) {
      /* localStorage có thể bị block (private browsing iOS); im lặng skip. */
    }

    updateButtonState(name);
    closeMenu();
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: name } }));
  }

  /* ===== UI sync — icon trigger + aria-checked options ===== */
  function updateButtonState(theme) {
    if (!trigger) return;

    var active = findTheme(theme) || findTheme(DEFAULT_THEME);

    if (triggerIconEl) {
      triggerIconEl.innerHTML = active.icon;
    }
    trigger.setAttribute(
      'aria-label',
      'Chọn theme giao diện — đang dùng ' + active.label
    );

    if (!menu) return;
    var options = menu.querySelectorAll('[data-theme-value]');
    for (var i = 0; i < options.length; i++) {
      var isActive = options[i].getAttribute('data-theme-value') === active.name;
      options[i].setAttribute('aria-checked', isActive ? 'true' : 'false');
      options[i].classList.toggle('is-active', isActive);
    }
  }

  /* ===== Dropdown open/close ===== */
  function openMenu() {
    if (!menu || !trigger) return;
    menu.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    container.classList.add('is-open');

    var activeOption = menu.querySelector('[data-theme-value][aria-checked="true"]');
    if (activeOption) activeOption.focus();
  }

  function closeMenu() {
    if (!menu || !trigger) return;
    menu.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    container.classList.remove('is-open');
  }

  function toggleMenu() {
    if (menu.hidden) openMenu();
    else closeMenu();
  }

  /* ===== Render menu options from THEMES config ===== */
  function renderMenu() {
    if (!menu) return;
    var html = '';
    for (var i = 0; i < THEMES.length; i++) {
      var t = THEMES[i];
      html +=
        '<li role="none">' +
          '<button class="theme-switcher__option" type="button"' +
                  ' role="menuitemradio"' +
                  ' aria-checked="false"' +
                  ' data-theme-value="' + t.name + '">' +
            '<span class="theme-switcher__option-icon" aria-hidden="true">' + t.icon + '</span>' +
            '<span class="theme-switcher__option-text">' +
              '<strong class="theme-switcher__option-label">' + t.label + '</strong>' +
              '<span class="theme-switcher__option-desc">' + t.desc + '</span>' +
            '</span>' +
            '<span class="theme-switcher__option-check" aria-hidden="true">' +
              '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<polyline points="3 8.5 6.5 12 13 4.5"></polyline>' +
              '</svg>' +
            '</span>' +
          '</button>' +
        '</li>';
    }
    menu.innerHTML = html;
  }

  /* ===== Event handlers ===== */
  function onTriggerClick(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    toggleMenu();
  }

  function onMenuClick(ev) {
    var btn = ev.target.closest('[data-theme-value]');
    if (!btn) return;
    ev.preventDefault();
    switchTheme(btn.getAttribute('data-theme-value'));
    trigger.focus();
  }

  /* Outside click → close. Bind ở document level vì menu floating
     ngoài flow → cần global listener. */
  function onDocumentClick(ev) {
    if (!container || menu.hidden) return;
    if (!container.contains(ev.target)) closeMenu();
  }

  /* Keyboard: Escape đóng menu + return focus, Arrow Up/Down navigate
     options khi menu open. */
  function onKeydown(ev) {
    if (menu.hidden) return;

    if (ev.key === 'Escape') {
      ev.preventDefault();
      closeMenu();
      trigger.focus();
      return;
    }

    if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
      var options = Array.prototype.slice.call(
        menu.querySelectorAll('[data-theme-value]')
      );
      if (!options.length) return;
      var idx = options.indexOf(document.activeElement);
      if (idx === -1) {
        options[0].focus();
      } else {
        var next = ev.key === 'ArrowDown' ? idx + 1 : idx - 1;
        if (next < 0) next = options.length - 1;
        if (next >= options.length) next = 0;
        options[next].focus();
      }
      ev.preventDefault();
    }
  }

  /* ===== Init ===== */
  function wireUI() {
    container = document.querySelector('[data-theme-switcher]');
    if (!container) return;
    trigger = container.querySelector('#theme-switch-btn');
    triggerIconEl = container.querySelector('[data-theme-trigger-icon]');
    menu = container.querySelector('#theme-switch-menu');
    if (!trigger || !menu) return;

    renderMenu();
    trigger.addEventListener('click', onTriggerClick);
    menu.addEventListener('click', onMenuClick);
    document.addEventListener('click', onDocumentClick);
    document.addEventListener('keydown', onKeydown);

    updateButtonState(getTheme());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireUI);
  } else {
    wireUI();
  }

  /* Public API — switchTheme thay cho setTheme/toggle cũ. Giữ shape
     mảng THEMES snapshot (chỉ name) để legacy code không break. */
  window.ThemeSwitcher = {
    getTheme: getTheme,
    switchTheme: switchTheme,
    THEMES: THEMES.map(function (t) { return t.name; })
  };
})();
