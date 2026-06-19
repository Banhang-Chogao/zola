/**
 * Navbar GitHub Profile Badges — responsive truncation + mobile dropdown.
 * Data rendered server-side from data/github-profile-badges.json (same as Insights).
 */
(function () {
  "use strict";

  var zone = document.querySelector("[data-navbar-badges]");
  if (!zone) return;

  var inline = zone.querySelector(".navbar__badges-inline");
  var pills = Array.prototype.slice.call(
    zone.querySelectorAll(".navbar__badge-pill:not([data-badge-more]):not([data-badge-compact])")
  );
  var moreEl = zone.querySelector("[data-badge-more]");
  var moreText = moreEl ? moreEl.querySelector(".navbar__badge-more-text") : null;
  var compactEl = zone.querySelector("[data-badge-compact]");
  var compactCount = compactEl ? compactEl.querySelector("[data-badge-compact-count]") : null;
  var mobileBtn = zone.querySelector("[data-badges-trigger]");
  var mobileLabel = zone.querySelector("[data-badges-mobile-label]");
  var mobileCount = zone.querySelector("[data-badges-mobile-count]");
  var dropdown = zone.querySelector("[data-badges-dropdown]");

  var total = pills.length;
  var mqMobile = window.matchMedia("(max-width: 720px)");
  var rafId = null;

  function isMobile() {
    return mqMobile.matches;
  }

  function setHidden(el, hidden) {
    if (!el) return;
    if (hidden) {
      el.setAttribute("hidden", "");
    } else {
      el.removeAttribute("hidden");
    }
  }

  function resetVisibility() {
    pills.forEach(function (p) {
      setHidden(p, false);
    });
    setHidden(moreEl, true);
    setHidden(compactEl, true);
  }

  function fits() {
    if (!inline) return true;
    return inline.scrollWidth <= inline.clientWidth + 1;
  }

  function showMore(count) {
    if (!moreEl || !moreText) return;
    moreText.textContent = "+" + count;
    setHidden(moreEl, false);
  }

  function showCompact(count) {
    pills.forEach(function (p) {
      setHidden(p, true);
    });
    setHidden(moreEl, true);
    if (compactEl && compactCount) {
      compactCount.textContent = "+" + count;
      setHidden(compactEl, false);
    }
  }

  function layoutDesktop() {
    if (!inline) return;
    inline.style.display = "";
    setHidden(mobileBtn, true);

    resetVisibility();

    if (fits()) return;

    /* Step down: show fewer pills + +N */
    for (var visible = total - 1; visible >= 1; visible--) {
      resetVisibility();
      for (var i = visible; i < total; i++) {
        setHidden(pills[i], true);
      }
      showMore(total - visible);
      if (fits()) return;
    }

    /* Still overflow → compact pill */
    showCompact(total);
    if (!fits()) {
      /* Last resort: icon-only compact already applied */
    }
  }

  function updateMobileLabel() {
    if (!mobileBtn) return;
    setHidden(mobileBtn, false);
    if (mobileLabel) {
      mobileLabel.textContent = "\uD83C\uDFC5 Badges";
    }
    if (mobileCount && total > 0) {
      mobileCount.textContent = "+" + total;
      setHidden(mobileCount, false);
    }
  }

  function layoutMobile() {
    if (inline) inline.style.display = "none";
    updateMobileLabel();
  }

  function layout() {
    if (isMobile()) {
      layoutMobile();
    } else {
      layoutDesktop();
    }
  }

  function scheduleLayout() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(function () {
      rafId = null;
      layout();
    });
  }

  /* Mobile dropdown toggle */
  function closeDropdown() {
    if (!dropdown || !mobileBtn) return;
    dropdown.setAttribute("hidden", "");
    mobileBtn.setAttribute("aria-expanded", "false");
    zone.classList.remove("is-open");
  }

  function openDropdown() {
    if (!dropdown || !mobileBtn) return;
    dropdown.removeAttribute("hidden");
    mobileBtn.setAttribute("aria-expanded", "true");
    zone.classList.add("is-open");
  }

  if (mobileBtn && dropdown) {
    mobileBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (dropdown.hasAttribute("hidden")) {
        openDropdown();
      } else {
        closeDropdown();
      }
    });

    document.addEventListener("click", function (e) {
      if (!zone.contains(e.target)) closeDropdown();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.key === "Esc") closeDropdown();
    });
  }

  /* Tooltip: show on keyboard focus */
  pills.forEach(function (pill) {
    var tip = pill.querySelector(".navbar__badge-tip");
    if (!tip) return;
    tip.removeAttribute("hidden");
    pill.setAttribute("tabindex", "0");
  });

  if (typeof ResizeObserver !== "undefined" && inline) {
    var ro = new ResizeObserver(scheduleLayout);
    ro.observe(zone);
    if (zone.parentElement) ro.observe(zone.parentElement);
  }

  window.addEventListener("resize", scheduleLayout);
  if (mqMobile.addEventListener) {
    mqMobile.addEventListener("change", scheduleLayout);
  } else if (mqMobile.addListener) {
    mqMobile.addListener(scheduleLayout);
  }

  scheduleLayout();
})();