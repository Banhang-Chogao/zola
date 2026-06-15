/**
 * Mobile navbar — Momo-style horizontal scroll tabs.
 *
 * Mobile (≤720px):
 *   - KHÔNG dùng burger drawer nữa
 *   - Menu hiển thị ngang dạng tabs scroll horizontal
 *   - Strip emoji prefix khỏi menu items (text-only như momo)
 *   - Active tab có underline đỏ
 *   - Scroll active tab vào view khi load
 *
 * Desktop (>720px):
 *   - Menu inline bình thường, không can thiệp
 *   - Emoji giữ nguyên
 */
(function () {
  "use strict";

  const navbar = document.getElementById("navbar");
  if (!navbar) return;

  const menu = document.getElementById("navbar-menu");
  if (!menu) return;

  const links = Array.from(menu.querySelectorAll("a"));

  // Cache original text (có emoji) để restore khi rotate sang desktop
  links.forEach((a) => {
    if (!a.dataset.originalText) {
      a.dataset.originalText = a.textContent.trim();
    }
  });

  /**
   * Strip leading non-letter characters (emoji, ✎, ✈️, 📊, ✓, etc.)
   * Regex \p{L} = unicode letter, \p{N} = unicode number, /u flag bắt buộc.
   * Trim whitespace + space sau emoji.
   */
  function stripEmoji(text) {
    return text.replace(/^[^\p{L}\p{N}]+/u, "").trim();
  }

  function applyMobileText() {
    const isMobile = window.matchMedia("(max-width: 720px)").matches;
    links.forEach((a) => {
      a.textContent = isMobile ? stripEmoji(a.dataset.originalText) : a.dataset.originalText;
    });
  }

  /**
   * Đánh dấu active tab dựa trên current URL path.
   * Logic: link href trùng với pathname hiện tại → add is-active.
   */
  function markActive() {
    const path = window.location.pathname.replace(/\/$/, "") || "/";
    links.forEach((a) => {
      try {
        const url = new URL(a.href);
        const linkPath = url.pathname.replace(/\/$/, "") || "/";
        a.classList.toggle("is-active", linkPath === path);
      } catch (e) {
        // ignore malformed href
      }
    });
  }

  /**
   * Scroll active tab vào giữa viewport mobile (UX tốt nhất).
   * Chỉ chạy lần đầu load + khi resize sang mobile.
   */
  function scrollActiveIntoView() {
    const isMobile = window.matchMedia("(max-width: 720px)").matches;
    if (!isMobile) return;
    const active = menu.querySelector("a.is-active");
    if (!active) return;
    // setTimeout đợi layout ổn định trước khi scroll
    setTimeout(() => {
      active.scrollIntoView({ inline: "center", block: "nearest", behavior: "auto" });
    }, 50);
  }

  // Init
  applyMobileText();
  markActive();
  scrollActiveIntoView();

  // Resize handler
  let resizeT;
  window.addEventListener("resize", function () {
    clearTimeout(resizeT);
    resizeT = setTimeout(function () {
      applyMobileText();
      scrollActiveIntoView();
    }, 150);
  });
})();
