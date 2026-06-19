/**
 * ShortenSEA auth — GitHub OAuth via ShortenSEA API or CMS session fallback.
 */
(function (global) {
  "use strict";

  var SESSION_KEY = "zola-shortensea-session-id";
  var CMS_SESSION_KEY = "zola-cms-session-id";

  var SSE_API = (function () {
    var m = document.querySelector('meta[name="zola-shortensea-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "";
  })();

  var CMS_API = (function () {
    var m1 = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m1 && m1.getAttribute("content")) return m1.getAttribute("content").replace(/\/$/, "");
    var m2 = document.querySelector('meta[name="zola-visitor-api"]');
    if (m2 && m2.getAttribute("content")) return m2.getAttribute("content").replace(/\/$/, "");
    return "https://blog-visitor-api.onrender.com";
  })();

  var SUPER_USERNAMES = ["banhang-chogao"];
  var SUPER_EMAILS = ["292648126+banhang-chogao@users.noreply.github.com"];

  var currentUser = null;

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; }
  }

  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }

  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function consumeHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])ssid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  function buildReturnPath() {
    var params = new URLSearchParams(location.search);
    params.delete("auth_error");
    var qs = params.toString();
    return location.pathname + (qs ? "?" + qs : "");
  }

  function isSuper(profile) {
    if (!profile) return false;
    var u = (profile.username || "").toLowerCase();
    var e = (profile.email || "").toLowerCase();
    return profile.is_super || SUPER_USERNAMES.indexOf(u) >= 0 || SUPER_EMAILS.indexOf(e) >= 0;
  }

  function login() {
    if (SSE_API) {
      window.location.href = SSE_API + "/auth/login?return_to=" + encodeURIComponent(buildReturnPath());
      return;
    }
    if (CMS_API) {
      window.location.href = CMS_API + "/auth/login?return_to=" + encodeURIComponent(buildReturnPath());
      return;
    }
    initPrototypeUser();
  }

  function initPrototypeUser() {
    // TODO(production): Remove prototype login when ShortenSEA API OAuth is live.
    try {
      var stored = localStorage.getItem("zola-shortensea-user");
      if (stored) {
        currentUser = JSON.parse(stored);
        return;
      }
    } catch (e) {}
    currentUser = {
      user_id: "proto-admin",
      username: "banhang-chogao",
      email: "292648126+banhang-chogao@users.noreply.github.com",
      name: "Duy Nguyen",
      avatar: "https://github.com/banhang-chogao.png",
      plan: "super",
      is_super: true,
      links_month_count: 0,
      custom_halves_used: 0,
      links_month_key: new Date().toISOString().slice(0, 7)
    };
    try { localStorage.setItem("zola-shortensea-user", JSON.stringify(currentUser)); } catch (e) {}
    localStorage.setItem("zola-shortensea-prototype", "1");
  }

  async function fetchMe() {
    var sid = getSid();
    if (sid && SSE_API) {
      try {
        var res = await fetch(SSE_API + "/auth/me", {
          headers: { Authorization: "Bearer " + sid },
          credentials: "omit",
          cache: "no-store"
        });
        if (res.status === 401) { clearSid(); return null; }
        if (!res.ok) return null;
        currentUser = await res.json();
        return currentUser;
      } catch (e) { return null; }
    }

    var cmsSid = "";
    try { cmsSid = sessionStorage.getItem(CMS_SESSION_KEY) || ""; } catch (e) {}
    if (cmsSid && CMS_API) {
      try {
        if (SSE_API) {
          var bridgeRes = await fetch(SSE_API + "/auth/cms-bridge", {
            method: "POST",
            headers: { Authorization: "Bearer " + cmsSid },
            credentials: "omit",
            cache: "no-store"
          });
          if (bridgeRes.ok) {
            var bridge = await bridgeRes.json();
            if (bridge.session_id) setSid(bridge.session_id);
            currentUser = bridge.account || bridge;
            return currentUser;
          }
        }
        var res2 = await fetch(CMS_API + "/auth/me", {
          headers: { Authorization: "Bearer " + cmsSid },
          credentials: "omit",
          cache: "no-store"
        });
        if (!res2.ok) return null;
        var cms = await res2.json();
        currentUser = {
          user_id: "cms-" + (cms.username || "user"),
          email: cms.email,
          username: cms.username,
          name: cms.name,
          avatar: cms.avatar,
          plan: isSuper(cms) ? "super" : "free",
          is_super: isSuper(cms),
          links_month_count: 0,
          custom_halves_used: 0,
          links_month_key: new Date().toISOString().slice(0, 7)
        };
        return currentUser;
      } catch (e) { return null; }
    }

    if (!SSE_API) {
      initPrototypeUser();
      return currentUser;
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
          keepalive: true
        });
      } catch (e) {}
    }
    clearSid();
    currentUser = null;
    try { localStorage.removeItem("zola-shortensea-user"); } catch (e) {}
  }

  function showView(name) {
    document.querySelectorAll("[data-sse-view]").forEach(function (el) {
      var v = el.getAttribute("data-sse-view");
      el.hidden = v !== name;
    });
  }

  function getUser() { return currentUser; }

  global.ShortenSEAAuth = {
    init: async function () {
      consumeHashSid();
      var err = new URLSearchParams(location.search).get("auth_error");
      if (err) {
        var el = document.querySelector("[data-sse-login-error]");
        if (el) { el.textContent = "Lỗi đăng nhập: " + err; el.hidden = false; }
      }
      var user = await fetchMe();
      if (user) {
        showView("app");
        return user;
      }
      showView("login");
      return null;
    },
    login: login,
    logout: logout,
    getSid: getSid,
    getUser: getUser,
    showView: showView
  };
})(window);