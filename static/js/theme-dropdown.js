/* ============================================================
   ===== THEME DROPDOWN — Interactive Menu Handler =====
   ============================================================
   Manages dropdown open/close, item selection, keyboard navigation,
   and outside click handling.

   Depends on: theme-switcher.js (window.ThemeSwitcher API)
*/

(function () {
  "use strict";

  var dropdown = document.querySelector("[data-theme-dropdown]");
  if (!dropdown) return;

  var trigger = dropdown.querySelector("[aria-haspopup]");
  var menu = dropdown.querySelector("[role='listbox']");
  var items = dropdown.querySelectorAll("[role='option']");

  if (!trigger || !menu || items.length === 0) return;

  var isOpen = false;
  var selectedIndex = 0;

  /* ===== Update UI to reflect current theme ===== */
  function syncMenuState() {
    if (!window.ThemeSwitcher) return;

    var currentTheme = window.ThemeSwitcher.getTheme();

    items.forEach(function (item, index) {
      var button = item.querySelector("button");
      var themeValue = button ? button.getAttribute("data-theme-value") : null;
      var isSelected = themeValue === currentTheme;

      item.setAttribute("aria-selected", isSelected);
      button.setAttribute("aria-selected", isSelected);

      if (isSelected) {
        selectedIndex = index;
      }
    });
  }

  /* ===== Open dropdown menu ===== */
  function openMenu() {
    if (isOpen) return;

    menu.removeAttribute("hidden");
    trigger.setAttribute("aria-expanded", "true");
    isOpen = true;

    syncMenuState();

    /* Focus first item on open */
    if (items[selectedIndex]) {
      var btn = items[selectedIndex].querySelector("button");
      if (btn) btn.focus();
    }
  }

  /* ===== Close dropdown menu ===== */
  function closeMenu() {
    if (!isOpen) return;

    menu.setAttribute("hidden", "");
    trigger.setAttribute("aria-expanded", "false");
    isOpen = false;

    /* Return focus to trigger */
    trigger.focus();
  }

  /* ===== Toggle dropdown menu ===== */
  function toggleMenu() {
    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  }

  /* ===== Select theme from menu ===== */
  function selectTheme(themeValue) {
    if (!window.ThemeSwitcher) return;

    window.ThemeSwitcher.setTheme(themeValue);
    syncMenuState();
    closeMenu();
  }

  /* ===== Keyboard navigation ===== */
  function handleKeydown(event) {
    if (!isOpen) {
      /* Open menu on Enter or Space when trigger is focused */
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openMenu();
      }
      return;
    }

    switch (event.key) {
      case "Escape":
        event.preventDefault();
        closeMenu();
        break;

      case "ArrowDown":
        event.preventDefault();
        selectedIndex = (selectedIndex + 1) % items.length;
        var nextBtn = items[selectedIndex].querySelector("button");
        if (nextBtn) nextBtn.focus();
        break;

      case "ArrowUp":
        event.preventDefault();
        selectedIndex = (selectedIndex - 1 + items.length) % items.length;
        var prevBtn = items[selectedIndex].querySelector("button");
        if (prevBtn) prevBtn.focus();
        break;

      case "Enter":
      case " ":
        event.preventDefault();
        var selectedBtn = items[selectedIndex].querySelector("button");
        if (selectedBtn) {
          var themeValue = selectedBtn.getAttribute("data-theme-value");
          selectTheme(themeValue);
        }
        break;

      case "Home":
        event.preventDefault();
        selectedIndex = 0;
        var firstBtn = items[0].querySelector("button");
        if (firstBtn) firstBtn.focus();
        break;

      case "End":
        event.preventDefault();
        selectedIndex = items.length - 1;
        var lastBtn = items[items.length - 1].querySelector("button");
        if (lastBtn) lastBtn.focus();
        break;
    }
  }

  /* ===== Click outside to close ===== */
  function handleOutsideClick(event) {
    if (isOpen && !dropdown.contains(event.target)) {
      closeMenu();
    }
  }

  /* ===== Initialize event listeners ===== */
  trigger.addEventListener("click", toggleMenu);
  trigger.addEventListener("keydown", handleKeydown);

  items.forEach(function (item) {
    var button = item.querySelector("button");
    if (!button) return;

    button.addEventListener("click", function () {
      var themeValue = button.getAttribute("data-theme-value");
      selectTheme(themeValue);
    });

    button.addEventListener("keydown", handleKeydown);
  });

  document.addEventListener("click", handleOutsideClick, true);

  /* ===== Sync on theme change (from other triggers) ===== */
  document.addEventListener("themechange", function () {
    syncMenuState();
  });

  /* ===== Initial sync ===== */
  syncMenuState();
})();
