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
        /* Nhóm con (accordion) → focus tên nhóm đầu; bằng không → link đầu. */
        var first = dd.querySelector(".navbar__group-trigger, .navbar__submenu > li > a");
        if (first) first.focus();
      } else if (e.key === "Escape" || e.key === "Esc") {
        closeDropdown(dd);
      }
    });

    /* Bàn phím trong submenu: mũi tên lên/xuống + Escape về trigger.
       Chỉ link TRỰC TIẾP (không lấy link nằm trong nhóm accordion —
       các link đó do khối accordion bên dưới tự xử lý). */
    var links = Array.prototype.slice.call(
      dd.querySelectorAll(".navbar__submenu > li > a")
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

  /* ============================================================
     ACCORDION GROUPS — Công cụ → Content / Dashboard / Khác.
     Mỗi [data-nav-accordion] = 1 nhóm: <button.navbar__group-trigger>
     + panel .navbar__group-items. Click/tap hoặc Enter/Space (native
     button) để xổ/đóng. Mặc định đóng hết → submenu chỉ hiện 3 nhóm,
     không tràn màn hình. Đóng/mở độc lập nhau (cho phép nhiều nhóm mở).
     ============================================================ */
  var groups = Array.prototype.slice.call(
    document.querySelectorAll("[data-nav-accordion]")
  );

  function groupTriggerOf(g) {
    return g.querySelector(".navbar__group-trigger");
  }

  function collapseGroup(g) {
    g.classList.remove("is-expanded");
    var t = groupTriggerOf(g);
    if (t) t.setAttribute("aria-expanded", "false");
  }

  function expandGroup(g) {
    g.classList.add("is-expanded");
    var t = groupTriggerOf(g);
    if (t) t.setAttribute("aria-expanded", "true");
  }

  function toggleGroup(g) {
    if (g.classList.contains("is-expanded")) collapseGroup(g);
    else expandGroup(g);
  }

  groups.forEach(function (g) {
    var trigger = groupTriggerOf(g);
    if (!trigger) return;

    trigger.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation(); /* không để document handler đóng dropdown cha */
      toggleGroup(g);
    });

    trigger.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.key === "Esc") {
        e.preventDefault();
        collapseGroup(g);
      } else if (e.key === "ArrowDown" || e.key === "Down") {
        /* Mở nhóm + nhảy vào link đầu tiên. */
        e.preventDefault();
        expandGroup(g);
        var firstLeaf = g.querySelector(".navbar__group-items a");
        if (firstLeaf) firstLeaf.focus();
      }
    });

    /* Bàn phím trong nhóm: lên/xuống xoay vòng, Escape về tên nhóm. */
    var leaves = Array.prototype.slice.call(
      g.querySelectorAll(".navbar__group-items a")
    );
    leaves.forEach(function (link, idx) {
      link.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" || e.key === "Down") {
          e.preventDefault();
          var next = leaves[(idx + 1) % leaves.length];
          if (next) next.focus();
        } else if (e.key === "ArrowUp" || e.key === "Up") {
          e.preventDefault();
          var prev = leaves[(idx - 1 + leaves.length) % leaves.length];
          if (prev) prev.focus();
        } else if (e.key === "Escape" || e.key === "Esc") {
          e.preventDefault();
          collapseGroup(g);
          if (trigger) trigger.focus();
        }
      });
    });
  });

  /* Auto-mở + highlight nhóm chứa trang hiện tại (active item). `path` đã
     khai báo ở khối đánh dấu trigger cha phía trên. */
  groups.forEach(function (g) {
    var leaves = g.querySelectorAll(".navbar__group-items a");
    var hasActiveLeaf = false;
    Array.prototype.forEach.call(leaves, function (a) {
      try {
        var lp = new URL(a.href).pathname.replace(/\/$/, "") || "/";
        if (lp === path) hasActiveLeaf = true;
      } catch (err) {
        /* href lỗi → bỏ qua */
      }
    });
    if (hasActiveLeaf) {
      expandGroup(g);
      var t = groupTriggerOf(g);
      if (t) t.classList.add("is-active");
    }
  });
})();
