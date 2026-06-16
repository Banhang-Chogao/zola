(function () {
  var dialog = document.querySelector("[data-site-search]");
  var openers = document.querySelectorAll("[data-search-open]");
  if (!dialog || !openers.length) return;

  var input = dialog.querySelector("[data-search-input], input.gsc-input");
  var lastFocus = null;

  function syncGoogleInput() {
    input = dialog.querySelector("[data-search-input], input.gsc-input") || input;
  }

  function openSearch() {
    lastFocus = document.activeElement;
    dialog.hidden = false;
    document.body.classList.add("search-open");
    window.setTimeout(function () {
      syncGoogleInput();
      if (input) input.focus();
    }, 80);
  }

  function closeSearch() {
    dialog.hidden = true;
    document.body.classList.remove("search-open");
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  openers.forEach(function (btn) {
    btn.addEventListener("click", openSearch);
  });

  dialog.querySelectorAll("[data-search-close]").forEach(function (btn) {
    btn.addEventListener("click", closeSearch);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !dialog.hidden) closeSearch();
  });
})();
