/* ============================================================
   ===== THEME TOGGLE UI HANDLER =====
   ============================================================
   Handle dropdown menu interaction untuk theme switcher.
   - Toggle dropdown visibility (open/close)
   - Select theme dari menu
   - Update button label + checkmark
   - Keyboard navigation (Escape, Arrow keys)
   - Outside click dismiss
   - Call ThemeSwitcher.setTheme()
*/

(function () {
  "use strict";

  var ATTR_TOGGLE = "data-theme-toggle";
  var ATTR_MENU = "data-theme-menu";
  var ATTR_BTN = "data-theme-set";
  var ATTR_CURRENT = "data-theme-current";

  var toggle = document.querySelector("[" + ATTR_TOGGLE + "]");
  var button = toggle ? toggle.querySelector(".theme-toggle__btn") : null;
  var menu = toggle ? toggle.querySelector("[" + ATTR_MENU + "]") : null;
  var opts = menu ? menu.querySelectorAll("[" + ATTR_BTN + "]") : [];

  if (!toggle || !button || !menu) {
    return; /* skip if UI not found */
  }

  /* ===== Map theme name to display label ===== */
  var themeLabels = {
    "hilda": "Hilda (Ericsson Blue)"
  };

  /* ===== Get display label for theme ===== */
  function getThemeLabel(themeName) {
    return themeLabels[themeName] || themeName;
  }

  /* ===== Toggle dropdown visibility ===== */
  function toggleMenu(show) {
    if (show === undefined) {
      show = menu.hasAttribute("hidden");
    }

    if (show) {
      menu.removeAttribute("hidden");
      button.setAttribute("aria-expanded", "true");
    } else {
      menu.setAttribute("hidden", "");
      button.setAttribute("aria-expanded", "false");
    }
  }

  /* ===== Close menu ===== */
  function closeMenu() {
    toggleMenu(false);
  }

  /* ===== Update button label ===== */
  function updateButtonLabel(themeName) {
    var label = getThemeLabel(themeName === "brandingx" ? "" : themeName);
    var labelEl = button.querySelector("[" + ATTR_CURRENT + "]");
    if (labelEl) {
      labelEl.textContent = label;
    }
  }

  /* ===== Update checkmarks in menu ===== */
  function updateMenuChecks(themeName) {
    var normalizedName = themeName === "brandingx" ? "" : themeName;

    opts.forEach(function (opt) {
      var optName = opt.getAttribute(ATTR_BTN);
      var checked = optName === normalizedName;

      opt.setAttribute("aria-checked", checked ? "true" : "false");
    });
  }

  /* ===== Select theme ===== */
  function selectTheme(themeName) {
    var actualTheme = themeName === "" ? "brandingx" : themeName;

    // Call ThemeSwitcher API
    if (window.ThemeSwitcher && window.ThemeSwitcher.setTheme) {
      window.ThemeSwitcher.setTheme(actualTheme);
    }

    // Update UI
    updateButtonLabel(actualTheme);
    updateMenuChecks(actualTheme);
    closeMenu();
  }

  /* ===== Event: Button click → toggle menu ===== */
  button.addEventListener("click", function (e) {
    e.preventDefault();
    toggleMenu();
  });

  /* ===== Event: Menu option click ===== */
  opts.forEach(function (opt) {
    opt.addEventListener("click", function (e) {
      e.preventDefault();
      var themeName = opt.getAttribute(ATTR_BTN);
      selectTheme(themeName);
    });
  });

  /* ===== Event: Keyboard navigation ===== */
  menu.addEventListener("keydown", function (e) {
    var active = document.activeElement;
    var isMenuOpt = Array.prototype.indexOf.call(opts, active) >= 0;

    if (!isMenuOpt) return;

    switch (e.key) {
      case "Escape":
        e.preventDefault();
        closeMenu();
        button.focus();
        break;
      case "ArrowDown":
        e.preventDefault();
        var next = active.parentElement.nextElementSibling;
        if (next) {
          next.querySelector("[" + ATTR_BTN + "]").focus();
        }
        break;
      case "ArrowUp":
        e.preventDefault();
        var prev = active.parentElement.previousElementSibling;
        if (prev) {
          prev.querySelector("[" + ATTR_BTN + "]").focus();
        }
        break;
      case "Home":
        e.preventDefault();
        opts[0].focus();
        break;
      case "End":
        e.preventDefault();
        opts[opts.length - 1].focus();
        break;
    }
  });

  /* ===== Event: Click outside → close menu ===== */
  document.addEventListener("click", function (e) {
    if (!toggle.contains(e.target) && !menu.hasAttribute("hidden")) {
      closeMenu();
    }
  });

  /* ===== Event: ThemeSwitcher "themechange" → sync UI ===== */
  document.addEventListener("themechange", function (e) {
    var newTheme = e.detail && e.detail.theme;
    if (newTheme) {
      updateButtonLabel(newTheme);
      updateMenuChecks(newTheme);
    }
  });

  /* ===== Init: Set button label to current theme ===== */
  function init() {
    if (window.ThemeSwitcher && window.ThemeSwitcher.getTheme) {
      var current = window.ThemeSwitcher.getTheme();
      updateButtonLabel(current);
      updateMenuChecks(current);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
