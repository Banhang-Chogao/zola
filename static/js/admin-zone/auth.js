/**
 * Admin Zone Authentication
 * Reuses Editor auth pattern: GitHub OAuth via FastAPI backend
 */

(function () {
  window.AdminZoneAuth = window.AdminZoneAuth || {};

  const SESSION_KEY = "zola-cms-session-id";

  const AUTH_API = (function () {
    const m = document.querySelector('meta[name="vipzone-auth-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content");
    return "https://blog-vipzone-api.onrender.com";
  })();

  let currentUser = null;

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; }
    catch (e) { return ""; }
  }

  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
    try { localStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }

  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
    try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function consumeUrlHashSid() {
    if (!location.hash) return;
    const m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  function consumeUrlAuthError() {
    const params = new URLSearchParams(location.search);
    const err = params.get("auth_error");
    if (!err) return null;
    params.delete("auth_error");
    const newQs = params.toString();
    history.replaceState(null, "", location.pathname + (newQs ? "?" + newQs : ""));
    return err;
  }

  async function fetchMe() {
    const sid = getSid();
    if (!sid || !AUTH_API) return null;
    try {
      const res = await fetch(AUTH_API + "/auth/me", {
        headers: { "Authorization": "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
      });
      if (res.status === 401) { clearSid(); return null; }
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  async function logoutRemote() {
    const sid = getSid();
    if (!sid || !AUTH_API) { clearSid(); return; }
    try {
      await fetch(AUTH_API + "/auth/logout", {
        method: "POST",
        headers: { "Authorization": "Bearer " + sid },
        credentials: "omit",
        keepalive: true,
      });
    } catch (e) { /* network fail OK */ }
    clearSid();
  }

  const AUTH_ERROR_MESSAGES = {
    access_denied:                "Truy cập bị từ chối: Bạn không có quyền quản trị.",
    invalid_state:                "Phiên đăng nhập hết hạn. Vui lòng thử lại.",
    missing_params:               "GitHub callback thiếu tham số. Thử lại.",
    token_exchange_failed:        "Lỗi xác thực GitHub. Thử lại sau.",
    github_unreachable:           "Không kết nối được GitHub. Kiểm tra mạng.",
    github_profile_fetch_failed:  "Không đọc được profile GitHub. Thử lại.",
  };

  function showLoginError(code) {
    const el = document.querySelector("[data-login-error]");
    if (!el) return;
    el.textContent = AUTH_ERROR_MESSAGES[code] || ("Lỗi xác thực: " + code);
    el.hidden = false;
  }

  function showLoginHint() {
    const el = document.querySelector("[data-login-hint]");
    if (el) el.hidden = false;
  }

  function populateUserBar(user) {
    const bar = document.querySelector("[data-user-bar]");
    if (!bar) return;
    const avatar = document.querySelector("[data-user-avatar]");
    const name = document.querySelector("[data-user-name]");
    const email = document.querySelector("[data-user-email]");
    if (avatar && user.avatar) {
      avatar.src = user.avatar;
      avatar.alt = user.username || "";
    }
    if (name)  name.textContent  = user.name || user.username || "";
    if (email) email.textContent = user.email || "";
    bar.hidden = false;
  }

  // Public API
  Object.assign(window.AdminZoneAuth, {
    getSid,
    setSid,
    clearSid,
    consumeUrlHashSid,
    consumeUrlAuthError,
    fetchMe,
    logoutRemote,
    showLoginError,
    showLoginHint,
    populateUserBar,
    get currentUser() { return currentUser; },
    set currentUser(val) { currentUser = val; },
    get AUTH_API() { return AUTH_API; },
  });
})();
