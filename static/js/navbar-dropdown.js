/**
 * Navbar category dropdown — Category → Sub-category.
 *
 * Mỗi `[data-nav-dropdown]` là 1 nhóm: <button> trigger + <ul.navbar__submenu>.
 *  - Desktop (hover: hover): CSS lo phần hover mở. JS thêm click-to-pin + bàn phím.
 *  - Mobile / touch: tap trigger để mở/đóng (CSS hover bị tắt qua media query).
 *  - Click ra ngoài hoặc Escape → đóng. Chỉ 1 dropdown mở tại một thời điểm.
 *  - Nếu 1 child trùng URL hiện tại → đánh dấu cả trigger cha .is-active.
 *
 * Không phụ thuộc thư viện ngoài. Idempotent với navbar-mobile.js (file đó
 * lo active state cho <a>; file này lo active state cho trigger cha).
 */
(function () {
  "use strict";

  var dropdowns = Array.prototype.slice.call(
    document.querySelectorAll("[data-nav-dropdown]")
  );
  if (!dropdowns.length) return;

  var openDropdown = null;

  function triggerOf(dd) {
    return dd.querySelector(".navbar__dropdown-trigger");
  }

  function closeDropdown(dd) {
    if (!dd) return;
    dd.classList.remove("is-open");
    var t = triggerOf(dd);
    if (t) t.setAttribute("aria-expanded", "false");
    if (openDropdown === dd) openDropdown = null;
  }

  function openMenu(dd) {
    if (openDropdown && openDropdown !== dd) closeDropdown(openDropdown);
    dd.classList.add("is-open");
    var t = triggerOf(dd);
    if (t) t.setAttribute("aria-expanded", "true");
    openDropdown = dd;
  }

  function toggleDropdown(dd) {
    if (dd.classList.contains("is-open")) {
      closeDropdown(dd);
    } else {
      openMenu(dd);
    }
  }

  dropdowns.forEach(function (dd) {
    var trigger = triggerOf(dd);
    if (!trigger) return;

    trigger.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      toggleDropdown(dd);
    });

    trigger.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "Down") {
        e.preventDefault();
        openMenu(dd);
        var first = dd.querySelector(".navbar__submenu a");
        if (first) first.focus();
      } else if (e.key === "Escape" || e.key === "Esc") {
        closeDropdown(dd);
      }
    });

    /* Bàn phím trong submenu: mũi tên lên/xuống + Escape về trigger. */
    var links = Array.prototype.slice.call(
      dd.querySelectorAll(".navbar__submenu a")
    );
    links.forEach(function (link, idx) {
      link.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" || e.key === "Down") {
          e.preventDefault();
          var next = links[(idx + 1) % links.length];
          if (next) next.focus();
        } else if (e.key === "ArrowUp" || e.key === "Up") {
          e.preventDefault();
          var prev = links[(idx - 1 + links.length) % links.length];
          if (prev) prev.focus();
        } else if (e.key === "Escape" || e.key === "Esc") {
          e.preventDefault();
          closeDropdown(dd);
          if (trigger) trigger.focus();
        }
      });
    });
  });

  /* Click ngoài bất kỳ dropdown nào đang mở → đóng. */
  document.addEventListener(
    "click",
    function (e) {
      if (openDropdown && !openDropdown.contains(e.target)) {
        closeDropdown(openDropdown);
      }
    },
    true
  );

  /* Đánh dấu trigger cha .is-active nếu URL hiện tại khớp 1 child. */
  var path = window.location.pathname.replace(/\/$/, "") || "/";
  dropdowns.forEach(function (dd) {
    var links = dd.querySelectorAll(".navbar__submenu a");
    var hasActiveChild = false;
    Array.prototype.forEach.call(links, function (a) {
      try {
        var linkPath = new URL(a.href).pathname.replace(/\/$/, "") || "/";
        if (linkPath === path) hasActiveChild = true;
      } catch (err) {
        /* href lỗi → bỏ qua */
      }
    });
    if (hasActiveChild) {
      var t = triggerOf(dd);
      if (t) t.classList.add("is-active");
    }
  });

  /* ===== Mega menu — accordion nhóm (mobile) =====
     Mỗi .navbar__megagroup-toggle xổ/đóng .navbar__megagroup chứa nó. Trên
     desktop CSS ép body luôn hiện nên toggle vô hại; trên mobile (≤720px) CSS
     ẩn body trừ khi .is-open. aria-expanded đồng bộ cho screen reader.
     Mặc định: nhóm chứa link active mở sẵn, còn lại đóng. */
  var megaToggles = Array.prototype.slice.call(
    document.querySelectorAll(".navbar__megagroup-toggle")
  );
  megaToggles.forEach(function (btn) {
    var group = btn.closest(".navbar__megagroup");
    if (!group) return;

    /* Mở sẵn nhóm có link trùng URL hiện tại. */
    var groupLinks = group.querySelectorAll(".navbar__megagroup-body a");
    Array.prototype.forEach.call(groupLinks, function (a) {
      try {
        var lp = new URL(a.href).pathname.replace(/\/$/, "") || "/";
        if (lp === path) {
          group.classList.add("is-open");
          btn.setAttribute("aria-expanded", "true");
        }
      } catch (err) {
        /* href lỗi → bỏ qua */
      }
    });

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var open = group.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
})();
