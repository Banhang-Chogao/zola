/**
 * Mobile navbar drawer (< 1024px).
 *
 * Thay pattern horizontal-scroll-tabs + dropdown floating cũ bằng drawer trượt
 * từ trái + accordion (đúng UX mobile, không che/kẹt nội dung).
 *
 *   - Burger (data-burger) mở/đóng drawer.
 *   - Backdrop (data-backdrop) + nút đóng (data-drawer-close) + phím Escape đóng.
 *   - Bấm 1 link trong menu → đóng drawer.
 *   - Body scroll-lock khi drawer mở (class .navbar-open — CSS khoá overflow).
 *   - Accordion top-level do navbar-dropdown.js lo (toggle .is-open trên
 *     [data-nav-dropdown]); file này chỉ quản lý drawer + active state link đơn.
 *   - Resize sang desktop (≥ 1024px) → tự reset state để không kẹt.
 *
 * Desktop (≥ 1024px): drawer ẩn hoàn toàn (CSS), JS không can thiệp menu inline.
 */
(function () {
  "use strict";

  var navbar = document.getElementById("navbar");
  if (!navbar) return;

  var menu = document.getElementById("navbar-menu");
  var burger = navbar.querySelector("[data-burger]");
  var backdrop = navbar.querySelector("[data-backdrop]");
  var closeBtn = navbar.querySelector("[data-drawer-close]");
  if (!menu || !burger) return;

  var mqDesktop = window.matchMedia("(min-width: 1024px)");

  function isOpen() {
    return navbar.classList.contains("is-drawer-open");
  }

  function openDrawer() {
    navbar.classList.add("is-drawer-open");
    document.body.classList.add("navbar-open");
    burger.setAttribute("aria-expanded", "true");
    if (backdrop) backdrop.setAttribute("aria-hidden", "false");
  }

  function closeDrawer() {
    navbar.classList.remove("is-drawer-open");
    document.body.classList.remove("navbar-open");
    burger.setAttribute("aria-expanded", "false");
    if (backdrop) backdrop.setAttribute("aria-hidden", "true");
  }

  function toggleDrawer() {
    if (isOpen()) closeDrawer();
    else openDrawer();
  }

  burger.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    toggleDrawer();
  });

  if (backdrop) {
    backdrop.addEventListener("click", closeDrawer);
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", function (e) {
      e.preventDefault();
      closeDrawer();
    });
  }

  /* Bấm 1 link điều hướng trong drawer → đóng (chỉ <a> có href thật, không
     phải <button> trigger accordion). */
  menu.addEventListener("click", function (e) {
    var link = e.target.closest("a[href]");
    if (link && menu.contains(link)) {
      closeDrawer();
    }
  });

  /* Escape đóng drawer (desktop/tablet có bàn phím). */
  document.addEventListener("keydown", function (e) {
    if ((e.key === "Escape" || e.key === "Esc") && isOpen()) {
      closeDrawer();
      burger.focus();
    }
  });

  /* Resize sang desktop → reset để không kẹt class drawer/lock. */
  function onDesktopChange(e) {
    if (e.matches) closeDrawer();
  }
  if (mqDesktop.addEventListener) {
    mqDesktop.addEventListener("change", onDesktopChange);
  } else if (mqDesktop.addListener) {
    mqDesktop.addListener(onDesktopChange);
  }

  /* Active state cho link top-level đơn (vd Trang chủ). Dropdown cha do
     navbar-dropdown.js đánh dấu. */
  (function markActiveTopLinks() {
    var path = window.location.pathname.replace(/\/$/, "") || "/";
    var links = menu.querySelectorAll(":scope > .navbar__item > a");
    Array.prototype.forEach.call(links, function (a) {
      try {
        var linkPath = new URL(a.href).pathname.replace(/\/$/, "") || "/";
        if (linkPath === path) a.classList.add("is-active");
      } catch (err) {
        /* href lỗi → bỏ qua */
      }
    });
  })();
})();
