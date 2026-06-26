/**
 * CMS auth gate — GitHub OAuth là cổng đăng nhập duy nhất.
 *
 * Full OAuth flow qua backend FastAPI (vipzone service).
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
 *   - Backend URL bake từ <meta name="vipzone-auth-api">
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

  const meta = document.querySelector('meta[name="vipzone-auth-api"]');
  const apiUrl = (meta && meta.getAttribute("content")) || "";

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

      const url = apiUrl + "/auth/login?return_to=" + encodeURIComponent(returnPath);
      window.location.href = url;
    });
  });
})();
