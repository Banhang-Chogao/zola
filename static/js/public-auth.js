/**
 * public-auth.js — optional authentication for public calendar at /tools/calendar/
 *
 * Unlike private-auth.js (GitHub-only, mandatory), this module:
 *   - loads public calendar data immediately (no auth required)
 *   - checks for existing CMS session to auto-unlock edit mode
 *   - shows read-only mode if not authenticated
 *   - reuses the blog editor's Google OAuth flow
 *   - gracefully handles backend unavailable (shows cached/public data)
 *
 * Flow:
 *   1. Boot: try fetch public calendar data
 *   2. Check for existing CMS session (zola-cms-session-id)
 *   3. If session: unlock edit mode; emit 'public-auth:authed'
 *   4. If no session: stay in read-only; emit 'public-auth:guest'
 *   5. If backend down: show read-only with notice; emit 'public-auth:offline'
 */
(function () {
  "use strict";

  var SESSION_KEY = "zola-cms-session-id"; // reuse editor session
  var AUTH_API = (function () {
    var m = document.querySelector('meta[name="vipzone-auth-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content");
    return "https://blog-vipzone-api.onrender.com";
  })();

  // Getter/setter for session (mirrors private-auth.js)
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

  // URL hash/query handling (mirrors private-auth.js)
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

  // Session validation with timeout
  var authPromise = null;
  var authCache = null;
  var authCacheTime = 0;

  async function fetchMe() {
    var sid = getSid();
    if (!sid || !AUTH_API) return null;

    // Return cached result if fresh (< 30 seconds)
    if (authCache && Date.now() - authCacheTime < 30000) return authCache;

    // Deduplicate in-flight requests
    if (authPromise) return authPromise;

    authPromise = (async function () {
      try {
        var controller = new AbortController();
        var timeout = setTimeout(function () { controller.abort(); }, 10000);
        var res = await fetch(AUTH_API + "/auth/me", {
          headers: { "Authorization": "Bearer " + sid },
          credentials: "omit",
          cache: "no-store",
          signal: controller.signal,
        });
        clearTimeout(timeout);
        if (res.status === 401) { clearSid(); return null; }
        if (!res.ok) return null;
        var data = await res.json();
        authCache = data;
        authCacheTime = Date.now();
        return data;
      } catch (e) {
        return null;
      } finally {
        authPromise = null;
      }
    })();

    return authPromise;
  }

  // Fetch public calendar events (no auth required)
  async function fetchPublicCalendar() {
    if (!AUTH_API) return null;
    try {
      var controller = new AbortController();
      var timeout = setTimeout(function () { controller.abort(); }, 8000);
      var res = await fetch(AUTH_API + "/calendar/events/public", {
        cache: "no-store",
        signal: controller.signal,
      });
      clearTimeout(timeout);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
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

  // Authenticated fetch for edit operations (mirrors private-auth.js)
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
      showGate("session_expired");
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

  /* ============================ UI state ============================ */
  function $(sel) { return document.querySelector(sel); }
  function show(el, on) { if (el) el.hidden = !on; }

  function showHint() { show($("[data-priv-hint]"), true); }
  function showError(msg) {
    var el = $("[data-priv-error]");
    if (el) { el.textContent = msg; el.hidden = false; }
  }

  // Show login gate (optional — doesn't block public mode)
  function showGate(reason) {
    show($("[data-priv-loading]"), false);
    show($("[data-priv-gate]"), true);
    var reasonEl = $("[data-priv-gate-reason]");
    if (reasonEl) {
      if (reason === "session_expired") {
        reasonEl.textContent = "Phiên đăng nhập hết hạn. Đăng nhập lại để chỉnh sửa.";
      } else {
        reasonEl.textContent = "Lịch được chia sẻ công khai, nhưng chỉ chủ sở hữu mới có thể tạo & chỉnh sửa.";
      }
    }
  }

  // Show public read-only mode
  function showPublic(profile) {
    show($("[data-priv-loading]"), false);
    show($("[data-priv-gate]"), false);
    show($("[data-priv-app]"), true);
    show($("[data-priv-userbar]"), false); // hide auth bar
    show($("[data-priv-pubbar]"), true);   // show public bar
    // Hide all edit-only controls
    $$("[data-cal-edit-only]").forEach(function (el) { el.hidden = true; });
  }

  // Show authenticated edit mode
  function showApp(profile) {
    show($("[data-priv-loading]"), false);
    show($("[data-priv-gate]"), false);
    show($("[data-priv-app]"), true);
    show($("[data-priv-userbar]"), true);  // show auth bar
    show($("[data-priv-pubbar]"), false);  // hide public bar
    // Show all edit-only controls
    $$("[data-cal-edit-only]").forEach(function (el) { el.hidden = false; });
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
    missing_params: "OAuth callback thiếu tham số. Thử lại.",
    token_exchange_failed: "Lỗi xác thực OAuth. Thử lại sau.",
    github_unreachable: "Không kết nối được backend. Kiểm tra mạng.",
    github_profile_fetch_failed: "Không đọc được profile. Thử lại.",
  };

  function bindButtons() {
    var loginBtn = $("[data-priv-login]");
    if (loginBtn) loginBtn.addEventListener("click", login);
    var showLoginBtn = $("[data-priv-show-login]");
    if (showLoginBtn) showLoginBtn.addEventListener("click", function () {
      showGate();
    });
    var logoutBtn = $("[data-priv-logout]");
    if (logoutBtn) logoutBtn.addEventListener("click", async function () {
      await logout();
      document.dispatchEvent(new CustomEvent("public-auth:denied"));
      showPublic(null);
    });
  }

  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  async function boot() {
    bindButtons();
    consumeUrlHashSid();
    var errCode = consumeAuthQuery();
    if (errCode) showError(AUTH_ERRORS[errCode] || ("Lỗi xác thực: " + errCode));

    try {
      // Fetch public calendar data first (always succeeds or fails gracefully)
      var publicData = await fetchPublicCalendar();
      if (!publicData) {
        showError("Không thể tải lịch công khai. Backend không khả dụng.");
        document.dispatchEvent(new CustomEvent("public-auth:offline", { detail: {} }));
        return;
      }

      // Check for existing CMS session
      var timeout = setTimeout(function () { }, 15000);
      var me = await fetchMe();
      clearTimeout(timeout);

      var ok = me && (me.is_admin || me.is_super);
      if (ok) {
        // Authenticated: unlock edit mode
        showApp(me);
        document.dispatchEvent(new CustomEvent("public-auth:authed", { detail: me }));
      } else {
        // Not authenticated: show public read-only mode
        showPublic(publicData);
        document.dispatchEvent(new CustomEvent("public-auth:guest", { detail: publicData }));
      }
    } catch (e) {
      showError("Lỗi kết nối: " + (e.message || "Thử lại sau."));
      document.dispatchEvent(new CustomEvent("public-auth:error"));
    }
  }

  window.PublicAuth = {
    api: api, fetchMe: fetchMe, login: login, logout: logout,
    getSid: getSid, AUTH_API: AUTH_API, fetchPublicCalendar: fetchPublicCalendar,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
