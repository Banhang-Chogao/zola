/**
 * Mobile burger menu toggle — Momo-style.
 *
 * Pattern:
 *   - Burger button → toggle .is-open trên .navbar
 *   - .is-open → CSS slide-down menu + show backdrop + burger thành X
 *   - Click backdrop hoặc menu link → đóng menu
 *   - body.navbar-open lock background scroll
 *
 * Accessibility:
 *   - aria-expanded sync với open state
 *   - aria-hidden trên backdrop
 *   - Escape key đóng menu
 */
(function () {
  "use strict";

  const navbar = document.getElementById("navbar");
  if (!navbar) return;

  const burger = navbar.querySelector("[data-burger]");
  const backdrop = navbar.querySelector("[data-backdrop]");
  const menu = document.getElementById("navbar-menu");
  if (!burger || !menu) return;

  function setOpen(open) {
    navbar.classList.toggle("is-open", open);
    document.body.classList.toggle("navbar-open", open);
    burger.setAttribute("aria-expanded", open ? "true" : "false");
    burger.setAttribute("aria-label", open ? "Đóng menu" : "Mở menu");
    if (backdrop) backdrop.setAttribute("aria-hidden", open ? "false" : "true");
  }

  burger.addEventListener("click", function () {
    setOpen(!navbar.classList.contains("is-open"));
  });

  // Click backdrop → close
  if (backdrop) {
    backdrop.addEventListener("click", function () { setOpen(false); });
  }

  // Click menu link → close (user đã chọn xong, ẩn menu)
  menu.querySelectorAll("a").forEach(function (a) {
    a.addEventListener("click", function () { setOpen(false); });
  });

  // Escape → close
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && navbar.classList.contains("is-open")) {
      setOpen(false);
    }
  });

  // Resize ra desktop → reset state (tránh stuck open khi user xoay tablet)
  let resizeT;
  window.addEventListener("resize", function () {
    clearTimeout(resizeT);
    resizeT = setTimeout(function () {
      if (window.innerWidth > 720 && navbar.classList.contains("is-open")) {
        setOpen(false);
      }
    }, 150);
  });
})();
