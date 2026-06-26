/**
 * CMS auth gate — GitHub OAuth là cổng đăng nhập duy nhất.
 *
 * Trước đây: OTP modal (4 số hashed SHA-256). Giờ thay bằng full OAuth flow
 * qua backend FastAPI (services/visitor-counter/main.py).
 *
 * Flow:
 *   1. User click [data-auth-trigger] (link Admin ở footer)
 *   2. Redirect đến BACKEND/auth/login?return_to=/editor/
 *   3. Backend redirect GitHub authorize
 *   4. User authorize → GitHub redirect BACKEND/auth/callback
 *   5. Backend check email whitelist → redirect BLOG_URL/editor/#sid=...
 *   6. /editor/ load editor.js, đọc #sid, lưu sessionStorage, validate qua /auth/me
 *
 * Config:
 *   - Backend URL bake từ <meta name="zola-cms-auth-api">
 *   - Nếu meta tag trống → user vào /editor/ thẳng, editor.js tự handle login UI
 *
 * Security:
 *   - KHÔNG OTP modal trên trang chủ (đã bỏ)
 *   - KHÔNG localStorage / cookie
 *   - sid là opaque, JWT thật giữ Redis-side trên backend
 */
(function () {
  "use strict";

  const triggers = document.querySelectorAll("[data-auth-trigger]");
  if (!triggers.length) return;

  const meta = document.querySelector('meta[name="zola-cms-auth-api"]');
  const apiUrl = (meta && meta.getAttribute("content")) || "";

  // Chọn endpoint OAuth start theo provider đang bật (hỏi /auth/config).
  // dual/google → Google start; github → GitHub start. Lỗi fetch → GitHub
  // (giữ hành vi cũ, an toàn). Cache trong 1 page load để khỏi gọi lặp.
  let startPathPromise = null;
  function resolveStartPath() {
    if (startPathPromise) return startPathPromise;
    startPathPromise = fetch(apiUrl + "/auth/config", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (cfg) {
        // Google khả dụng khi enabled === true VÀ configured === true (dual).
        if (cfg && cfg.google && cfg.google.enabled && cfg.google.configured) return "/auth/google/start";
        return "/auth/login";
      })
      .catch(function () { return "/auth/login"; });
    return startPathPromise;
  }

  triggers.forEach(function (el) {
    el.addEventListener("click", function (e) {
      // Nếu backend chưa configure → fallback navigate thẳng /editor/,
      // editor.js sẽ hiển thị thông báo "chưa config auth".
      if (!apiUrl) return;

      e.preventDefault();
      const returnTo = el.getAttribute("href") || "/editor/";
      // Chỉ truyền path tương đối — backend cũng validate lại để chống open redirect.
      let returnPath = "/editor/";
      try {
        const u = new URL(returnTo, location.origin);
        if (u.origin === location.origin) returnPath = u.pathname + u.search;
      } catch (err) { /* invalid href → giữ default */ }

      resolveStartPath().then(function (startPath) {
        window.location.href =
          apiUrl + startPath + "?return_to=" + encodeURIComponent(returnPath);
      });
    });
  });
})();
