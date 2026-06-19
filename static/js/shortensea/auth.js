/**
 * ShortenSEA auth — guest sessions (public) + GitHub OAuth (admin / VIP).
 */
(function (global) {
  "use strict";

  var SESSION_KEY = "zola-shortensea-session-id";
  var GUEST_KEY = "zola-shortensea-guest-sid";

  var SSE_API = (function () {
    var m = document.querySelector('meta[name="zola-shortensea-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "";
  })();

  var AUTH_ERRORS = {
    access_denied: "Truy cập bị từ chối.",
    invalid_state: "Phiên đăng nhập hết hạn. Vui lòng thử lại.",
    missing_params: "GitHub callback thiếu tham số.",
    token_exchange_failed: "Lỗi xác thực GitHub.",
    github_unreachable: "Không kết nối được GitHub.",
    github_profile_fetch_failed: "Không đọc được profile GitHub.",
    oauth_not_configured: "OAuth chưa cấu hình trên backend Render.",
  };

  var currentUser = null;
  var sessionKind = null; // "github" | "guest"

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; }
  }

  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }

  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function getGuestSid() {
    try { return localStorage.getItem(GUEST_KEY) || ""; } catch (e) { return ""; }
  }

  function setGuestSid(sid) {
    try { localStorage.setItem(GUEST_KEY, sid); } catch (e) {}
  }

  function getActiveSid() {
    return getSid() || getGuestSid();
  }

  function consumeHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])ssid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    sessionKind = "github";
    try { localStorage.removeItem(GUEST_KEY); } catch (e) {}
    history.replaceState(null, "", location.pathname + location.search);
  }

  function buildReturnPath() {
    var params = new URLSearchParams(location.search);
    params.delete("auth_error");
    var qs = params.toString();
    return location.pathname + (qs ? "?" + qs : "");
  }

  // Render from the backend-resolved identity only — no hardcoded email/username
  // whitelist on the client (the backend's _is_super is the source of truth).
  function isSuper(profile) {
    if (!profile) return false;
    if (profile.permissions) return !!profile.permissions.can_superadmin;
    return !!profile.is_super || profile.role === "superadmin" || profile.role === "supervip";
  }

  function login(returnPath) {
    if (!SSE_API) {
      showLoginError("oauth_not_configured");
      return;
    }
    var rt = returnPath || buildReturnPath();
    window.location.href = SSE_API + "/auth/login?return_to=" + encodeURIComponent(rt);
  }

  async function ensureGuestSession() {
    if (!SSE_API) return null;
    var existing = getGuestSid();
    if (existing) {
      try {
        var res = await fetch(SSE_API + "/auth/me", {
          headers: { Authorization: "Bearer " + existing },
          credentials: "omit",
          cache: "no-store",
        });
        if (res.ok) {
          currentUser = await res.json();
          sessionKind = "guest";
          return currentUser;
        }
      } catch (e) {}
    }
    try {
      var createRes = await fetch(SSE_API + "/api/shortensea/guest/session", {
        method: "POST",
        credentials: "omit",
        cache: "no-store",
      });
      if (!createRes.ok) return null;
      var data = await createRes.json();
      if (data.session_id) setGuestSid(data.session_id);
      currentUser = data.account || data;
      sessionKind = "guest";
      return currentUser;
    } catch (e) {
      return null;
    }
  }

  async function fetchMe() {
    var sid = getSid();
    if (sid && SSE_API) {
      try {
        var res = await fetch(SSE_API + "/auth/me", {
          headers: { Authorization: "Bearer " + sid },
          credentials: "omit",
          cache: "no-store",
        });
        if (res.status === 401) { clearSid(); return null; }
        if (!res.ok) return null;
        currentUser = await res.json();
        sessionKind = "github";
        return currentUser;
      } catch (e) { return null; }
    }
    return null;
  }

  async function logout() {
    var sid = getSid();
    if (sid && SSE_API) {
      try {
        await fetch(SSE_API + "/auth/logout", {
          method: "POST",
          headers: { Authorization: "Bearer " + sid },
          credentials: "omit",
          keepalive: true,
        });
      } catch (e) {}
    }
    clearSid();
    currentUser = null;
    sessionKind = null;
  }

  function showView(name) {
    document.querySelectorAll("[data-sse-view]").forEach(function (el) {
      var v = el.getAttribute("data-sse-view");
      el.hidden = v !== name;
    });
  }

  function showLoginError(code) {
    var el = document.querySelector("[data-sse-login-error]");
    if (!el) return;
    el.textContent = AUTH_ERRORS[code] || "Lỗi đăng nhập: " + code;
    el.hidden = false;
  }

  function consumeAuthError() {
    var params = new URLSearchParams(location.search);
    var err = params.get("auth_error");
    if (!err) return;
    params.delete("auth_error");
    var qs = params.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
    showLoginError(err);
  }

  function populateUserBar(user) {
    var bar = document.querySelector("[data-sse-user-bar]");
    if (!bar) return;
    var avatar = bar.querySelector("[data-sse-avatar]");
    var name = bar.querySelector("[data-sse-name]");
    var email = bar.querySelector("[data-sse-email]");
    var badge = bar.querySelector("[data-sse-super-badge]");
    if (avatar) {
      if (user.avatar) { avatar.src = user.avatar; avatar.alt = user.name || ""; }
      else { avatar.hidden = true; }
    }
    if (name) name.textContent = user.name || user.username || "Khách";
    if (email) email.textContent = user.email || (user.is_guest ? "Tài khoản khách" : user.username || "");
    if (badge) badge.hidden = !user.is_super;
    bar.hidden = false;
  }

  function getUser() { return currentUser; }
  function getSessionKind() { return sessionKind; }
  function isGitHubSession() { return sessionKind === "github"; }
  function isAdminUser() { return currentUser && isSuper(currentUser); }

  /** Public page — guest session, no login wall. */
  async function initPublic() {
    consumeHashSid();
    consumeAuthError();
    var ghUser = await fetchMe();
    if (ghUser) {
      populateUserBar(ghUser);
      return ghUser;
    }
    var guest = await ensureGuestSession();
    if (guest) return guest;
    showLoginError("oauth_not_configured");
    return null;
  }

  /** Admin page — GitHub OAuth required, super user only. */
  async function initAdmin() {
    consumeHashSid();
    consumeAuthError();
    bindLoginButtons();

    if (!SSE_API) {
      showView("login");
      showLoginError("oauth_not_configured");
      return null;
    }

    var user = await fetchMe();
    if (user && isSuper(user)) {
      populateUserBar(user);
      showView("app");
      return user;
    }
    if (user && !isSuper(user)) {
      showView("denied");
      return null;
    }
    showView("login");
    return null;
  }

  /** Links / insights — guest or GitHub session. */
  async function initProtected() {
    consumeHashSid();
    consumeAuthError();
    bindLoginButtons();

    var user = await fetchMe();
    if (user) {
      populateUserBar(user);
      showView("app");
      return user;
    }
    user = await ensureGuestSession();
    if (user) {
      showView("app");
      return user;
    }
    showView("login");
    return null;
  }

  /** Upgrade page — guest or GitHub, no login wall. */
  async function initUpgrade() {
    return initPublic();
  }

  function bindLoginButtons() {
    document.querySelectorAll('[data-sse-action="login"]').forEach(function (btn) {
      if (btn._sseBound) return;
      btn._sseBound = true;
      btn.addEventListener("click", function () { login(); });
    });
    document.querySelectorAll('[data-sse-action="logout"]').forEach(function (btn) {
      if (btn._sseBound) return;
      btn._sseBound = true;
      btn.addEventListener("click", async function () {
        await logout();
        window.location.reload();
      });
    });
  }

  global.ShortenSEAAuth = {
    initPublic: initPublic,
    initAdmin: initAdmin,
    initProtected: initProtected,
    initUpgrade: initUpgrade,
    login: login,
    logout: logout,
    getSid: getActiveSid,
    getGitHubSid: getSid,
    getUser: getUser,
    getSessionKind: getSessionKind,
    isGitHubSession: isGitHubSession,
    isAdminUser: isAdminUser,
    showView: showView,
    populateUserBar: populateUserBar,
    getApiUrl: function () { return SSE_API; },
  };
})(window);