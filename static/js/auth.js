/**
 * CMS auth gate — GitHub OAuth là cổng đăng nhập duy nhất.
 *
 * Trước đây: OTP modal (4 số hashed SHA-256). Giờ thay bằng full OAuth flow
 * qua backend FastAPI (services/vipzone/cms_auth.py).
 *
 * Flow:
 *   1. User click [data-auth-trigger] (link Admin ở footer)
 *   2. Redirect đến BACKEND/auth/login?return_to=https://seomoney.org/cms-v6/
 *   3. Backend redirect GitHub authorize
 *   4. User authorize → GitHub redirect BACKEND/auth/callback
 *   5. Backend check email whitelist → redirect BLOG_URL/cms-v6/?success=1#sid=...
 *   6. CMS-V6 load cms-v6.js, đọc #sid, lưu sessionStorage, validate qua /auth/me
 *
 * Config:
 *   - Backend URL bake từ <meta name="zola-cms-auth-api">
 *   - Nếu meta tag trống → user vào CMS trực tiếp, page-level JS tự handle login UI
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
  const CMS_V6_RETURN_TO = "https://seomoney.org/cms-v6/";

  // Chọn endpoint OAuth start theo provider đang bật (hỏi /auth/config).
  // dual/google → Google start; github → GitHub start. Lỗi fetch → GitHub
  // (giữ hành vi cũ, an toàn). Cache trong 1 page load để khỏi gọi lặp.
  let startPathPromise = null;
  function resolveStartPath() {
    if (startPathPromise) return startPathPromise;
    startPathPromise = fetch(apiUrl + "/auth/config", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (cfg) {
        if (cfg && cfg.google && cfg.google.enabled) return "/auth/google/start";
        return "/auth/login";
      })
      .catch(function () { return "/auth/login"; });
    return startPathPromise;
  }

  triggers.forEach(function (el) {
    el.addEventListener("click", function (e) {
      // Nếu backend chưa configure thì giữ nguyên hành vi hiện tại của trang.
      if (!apiUrl) return;

      e.preventDefault();
      resolveStartPath().then(function (startPath) {
        window.location.href =
          apiUrl + startPath + "?return_to=" + encodeURIComponent(CMS_V6_RETURN_TO);
      });
    });
  });
})();
