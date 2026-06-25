/* side-nav.js — điều hướng chính sau khi gỡ top navbar.
 *
 *  - .side-nav  : khối nav sticky ở đầu cột phải (desktop, trên các widget).
 *  - .nav-drawer: panel trượt từ phải (mobile/tablet + desktop full-width pages).
 *  - .nav-toggle: nút hamburger fixed top-right mở drawer.
 *
 *  Vanilla JS, defer-safe, không phụ thuộc thư viện. Active link tô bằng
 *  pathname hiện tại (áp cho CẢ hai bản nav: side-nav + drawer).
 */
(function () {
  "use strict";

  // ---- Active link highlighting -------------------------------------------
  function norm(path) {
    path = (path || "/").split("#")[0].split("?")[0];
    if (path.length > 1 && path.charAt(path.length - 1) === "/") {
      path = path.slice(0, -1);
    }
    return path;
  }

  function markActive() {
    var links = Array.prototype.slice.call(document.querySelectorAll("[data-nav-link]"));
    if (!links.length) return;
    var cur = norm(window.location.pathname);

    var paths = links.map(function (l) {
      try { return norm(new URL(l.getAttribute("href"), window.location.href).pathname); }
      catch (e) { return ""; }
    });
    // Trang chủ = path ngắn nhất → chỉ active khi khớp tuyệt đối (không prefix-match).
    var homeBase = paths.reduce(function (a, b) {
      return (b && b.length < a.length) ? b : a;
    }, paths[0] || "");

    links.forEach(function (link, i) {
      var lp = paths[i];
      if (!lp) return;
      var active = lp === cur || (lp !== homeBase && cur.indexOf(lp + "/") === 0);
      link.classList.toggle("is-active", active);
      if (active) { link.setAttribute("aria-current", "page"); }
    });
  }

  // ---- Mobile drawer -------------------------------------------------------
  var drawer = document.querySelector("[data-nav-drawer]");
  var toggle = document.querySelector("[data-nav-toggle]");
  var CLOSE_MS = 280;
  var closeTimer = null;

  function openDrawer() {
    if (!drawer) return;
    if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; }
    drawer.hidden = false;
    // ép reflow rồi thêm .is-open ở frame kế → transition trượt vào.
    void drawer.offsetWidth;
    drawer.classList.add("is-open");
    document.body.classList.add("nav-drawer-open");
    if (toggle) toggle.setAttribute("aria-expanded", "true");
    var firstLink = drawer.querySelector("[data-nav-link]");
    if (firstLink) { try { firstLink.focus({ preventScroll: true }); } catch (e) {} }
  }

  function closeDrawer() {
    if (!drawer || drawer.hidden) return;
    drawer.classList.remove("is-open");
    document.body.classList.remove("nav-drawer-open");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
    closeTimer = window.setTimeout(function () { drawer.hidden = true; }, CLOSE_MS);
  }

  if (toggle && drawer) {
    toggle.addEventListener("click", function () {
      if (drawer.hidden) openDrawer(); else closeDrawer();
    });

    drawer.querySelectorAll("[data-nav-close]").forEach(function (btn) {
      btn.addEventListener("click", closeDrawer);
    });

    // Bấm 1 link điều hướng → đóng drawer (cùng trang anchor cũng đóng gọn).
    drawer.querySelectorAll("[data-nav-link]").forEach(function (link) {
      link.addEventListener("click", closeDrawer);
    });

    // Action (Tìm kiếm / Xoá cache) → đóng drawer để modal search nổi lên trên.
    drawer.querySelectorAll(".nav-drawer__actions button").forEach(function (btn) {
      btn.addEventListener("click", closeDrawer);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !drawer.hidden) { closeDrawer(); if (toggle) toggle.focus(); }
    });
  }

  markActive();
})();
