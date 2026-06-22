/**
 * private-auth.js — shared GitHub-OAuth guard for the private /tools/calendar/
 * workspace (Calendar + 3M Whiteboard). It REUSES the blog editor's auth, not a
 * second system:
 *   - same session key  (zola-cms-session-id)
 *   - same backend       (<meta vipzone-auth-api> → VIPZone FastAPI)
 *   - same flow          (redirect /auth/login → #sid= fragment → /auth/me)
 *
 * The page ships NO private data in its HTML/JS. This module checks the session
 * first; only an authenticated allowlisted admin reveals [data-priv-app] and gets
 * a `private-auth:authed` event (so calendar/whiteboard then fetch their data).
 * Everyone else sees the login gate and gets `private-auth:denied`.
 *
 * Security mirrors editor.js: the sid is an opaque token, the GitHub access_token
 * never reaches the client, requests use Bearer + credentials:"omit", and the
 * allowlist check is enforced server-side (this gate is convenience, not the wall).
 */
(function () {
  "use strict";

  var SESSION_KEY = "zola-cms-session-id"; // identical to editor.js → single sign-on
  var AUTH_API = (function () {
    var m = document.querySelector('meta[name="vipzone-auth-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content");
    return "https://blog-vipzone-api.onrender.com";
  })();

  function getSid() {
    try { var s = sessionStorage.getItem(SESSION_KEY); if (s) return s; } catch (e) {}
    try { return localStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; }
  }
  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
    try { localStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }
  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
    try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  // Read #sid=... left by the OAuth callback redirect, then scrub it from the URL.
  function consumeUrlHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }
  function consumeAuthQuery() {
    var params = new URLSearchParams(location.search);
    var err = params.get("auth_error");
    if (params.has("auth")) params.delete("auth");
    if (err) params.delete("auth_error");
    var qs = params.toString();
    if (location.search !== (qs ? "?" + qs : "")) {
      history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
    }
    return err;
  }

  async function fetchMe() {
    var sid = getSid();
    if (!sid || !AUTH_API) return null;
    try {
      var res = await fetch(AUTH_API + "/auth/me", {
        headers: { "Authorization": "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
      });
      if (res.status === 401) { clearSid(); return null; }
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  function login() {
    if (!AUTH_API) { showHint(); return; }
    var returnTo = location.pathname + location.search;
    location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(returnTo);
  }

  async function logout() {
    var sid = getSid();
    if (sid && AUTH_API) {
      try {
        await fetch(AUTH_API + "/auth/logout", {
          method: "POST",
          headers: { "Authorization": "Bearer " + sid },
          credentials: "omit",
          keepalive: true,
        });
      } catch (e) { /* network — client session cleared regardless */ }
    }
    clearSid();
  }

  /* Authenticated fetch helper for the calendar/whiteboard apps.
     opts.body (object) is JSON-encoded. Throws Error(.status) on non-2xx; a 401
     bounces the user back to the login gate. */
  async function api(path, opts) {
    opts = opts || {};
    var sid = getSid();
    if (!sid) { var e = new Error("not_authenticated"); e.status = 401; throw e; }
    var headers = { "Authorization": "Bearer " + sid };
    var init = { method: opts.method || "GET", headers: headers, credentials: "omit", cache: "no-store" };
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    var res = await fetch(AUTH_API + path, init);
    if (res.status === 401) {
      clearSid();
      showGate();
      var e2 = new Error("session_expired"); e2.status = 401; throw e2;
    }
    if (!res.ok) {
      var detail = "";
      try { detail = (await res.json()).detail || ""; } catch (x) {}
      var e3 = new Error(detail || ("HTTP " + res.status)); e3.status = res.status; throw e3;
    }
    if (res.status === 204) return {};
    return res.json();
  }

  /* ============================ gate UI ============================ */
  function $(sel) { return document.querySelector(sel); }
  function show(el, on) { if (el) el.hidden = !on; }

  function showHint() { show($("[data-priv-hint]"), true); }
  function showError(msg) {
    var el = $("[data-priv-error]");
    if (el) { el.textContent = msg; el.hidden = false; }
  }

  function showGate() {
    show($("[data-priv-loading]"), false);
    show($("[data-priv-app]"), false);
    show($("[data-priv-gate]"), true);
  }
  function showApp(profile) {
    show($("[data-priv-loading]"), false);
    show($("[data-priv-gate]"), false);
    show($("[data-priv-app]"), true);
    populateUserBar(profile);
  }

  function populateUserBar(p) {
    var bar = $("[data-priv-userbar]");
    if (!bar) return;
    var avatar = $("[data-priv-avatar]");
    var name = $("[data-priv-name]");
    var email = $("[data-priv-email]");
    if (avatar && p.avatar) { avatar.src = p.avatar; avatar.alt = p.username || ""; }
    if (name) name.textContent = p.name || p.username || "";
    if (email) email.textContent = p.email || "";
    bar.hidden = false;
  }

  var AUTH_ERRORS = {
    access_denied: "Truy cập bị từ chối: tài khoản không có quyền.",
    invalid_state: "Phiên đăng nhập hết hạn. Thử lại.",
    missing_params: "GitHub callback thiếu tham số. Thử lại.",
    token_exchange_failed: "Lỗi xác thực GitHub. Thử lại sau.",
    github_unreachable: "Không kết nối được GitHub. Kiểm tra mạng.",
    github_profile_fetch_failed: "Không đọc được profile GitHub. Thử lại.",
  };

  function bindButtons() {
    var loginBtn = $("[data-priv-login]");
    if (loginBtn) loginBtn.addEventListener("click", login);
    var logoutBtn = $("[data-priv-logout]");
    if (logoutBtn) logoutBtn.addEventListener("click", async function () {
      await logout();
      document.dispatchEvent(new CustomEvent("private-auth:denied"));
      showGate();
    });
  }

  async function boot() {
    bindButtons();
    consumeUrlHashSid();
    var errCode = consumeAuthQuery();
    if (errCode) showError(AUTH_ERRORS[errCode] || ("Lỗi xác thực: " + errCode));

    var me = await fetchMe();
    var ok = me && (me.is_admin || me.is_super);
    if (ok) {
      showApp(me);
      document.dispatchEvent(new CustomEvent("private-auth:authed", { detail: me }));
    } else {
      if (me && !ok) showError("Tài khoản này không có quyền truy cập công cụ riêng tư.");
      showGate();
      document.dispatchEvent(new CustomEvent("private-auth:denied"));
    }
  }

  window.PrivateAuth = {
    api: api, fetchMe: fetchMe, login: login, logout: logout,
    getSid: getSid, AUTH_API: AUTH_API,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
