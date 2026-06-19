/**
 * F-Dashboard — GitHub OAuth gate (cùng flow CMS /editor/).
 * Dùng chung session `zola-cms-session-id` → đăng nhập CMS = vào được F-Dashboard.
 */
(function (global) {
  "use strict";

  const SESSION_KEY = "zola-cms-session-id";

  const AUTH_API = (function () {
    const m1 = document.querySelector('meta[name="vipzone-auth-api"]');
    if (m1 && m1.getAttribute("content")) return m1.getAttribute("content").replace(/\/$/, "");
    return "https://blog-vipzone-api.onrender.com";
  })();

  const AUTH_ERRORS = {
    access_denied: "Truy cập bị từ chối: tài khoản GitHub không trong white-list admin.",
    invalid_state: "Phiên đăng nhập hết hạn. Vui lòng thử lại.",
    missing_params: "GitHub callback thiếu tham số. Thử lại.",
    token_exchange_failed: "Lỗi xác thực GitHub. Thử lại sau.",
    github_unreachable: "Không kết nối được GitHub. Kiểm tra mạng.",
    github_profile_fetch_failed: "Không đọc được profile GitHub. Thử lại.",
  };

  let currentUser = null;

  function getSid() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || "";
    } catch (e) {
      return "";
    }
  }

  function setSid(sid) {
    try {
      sessionStorage.setItem(SESSION_KEY, sid);
      localStorage.setItem(SESSION_KEY, sid);
    } catch (e) {}
  }

  function clearSid() {
    try {
      sessionStorage.removeItem(SESSION_KEY);
      localStorage.removeItem(SESSION_KEY);
    } catch (e) {}
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
    const qs = params.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
    return err;
  }

  async function fetchMe() {
    const sid = getSid();
    if (!sid || !AUTH_API) return null;
    try {
      const res = await fetch(AUTH_API + "/auth/me", {
        headers: { Authorization: "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
      });
      if (res.status === 401) {
        clearSid();
        return null;
      }
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  /** Path tương đối gửi backend — strip cache-bust / auth_error khỏi query. */
  function buildReturnPath() {
    const params = new URLSearchParams(location.search);
    params.delete("_fresh");
    params.delete("auth_error");
    const qs = params.toString();
    return location.pathname + (qs ? "?" + qs : "");
  }

  function login() {
    if (!AUTH_API) return;
    const returnPath = buildReturnPath();
    window.location.href =
      AUTH_API + "/auth/login?return_to=" + encodeURIComponent(returnPath);
  }

  async function logout() {
    const sid = getSid();
    if (sid && AUTH_API) {
      try {
        await fetch(AUTH_API + "/auth/logout", {
          method: "POST",
          headers: { Authorization: "Bearer " + sid },
          credentials: "omit",
          keepalive: true,
        });
      } catch (e) {}
    }
    clearSid();
    currentUser = null;
  }

  function showView(name) {
    document.querySelectorAll("[data-fd-view]").forEach((el) => {
      el.hidden = el.dataset.fdView !== name;
    });
  }

  function populateUserBar(user) {
    const bar = document.querySelector("[data-fd-user-bar]");
    if (!bar) return;
    const avatar = bar.querySelector("[data-fd-user-avatar]");
    const name = bar.querySelector("[data-fd-user-name]");
    const email = bar.querySelector("[data-fd-user-email]");
    if (avatar && user.avatar) {
      avatar.src = user.avatar;
      avatar.alt = user.username || "";
    }
    if (name) name.textContent = user.name || user.username || "";
    if (email) email.textContent = user.email || "";
    bar.hidden = false;
  }

  function showLoginError(code) {
    const el = document.querySelector("[data-fd-login-error]");
    if (!el) return;
    el.textContent = AUTH_ERRORS[code] || "Lỗi xác thực: " + code;
    el.hidden = false;
  }

  async function init() {
    const root = document.getElementById("fd-app");
    if (!root) return null;

    consumeUrlHashSid();
    const errCode = consumeUrlAuthError();
    if (errCode) showLoginError(errCode);

    const loginBtn = root.querySelector("[data-fd-action='github-login']");
    const logoutBtn = root.querySelector("[data-fd-action='logout']");
    const hint = root.querySelector("[data-fd-login-hint]");

    if (loginBtn) {
      loginBtn.addEventListener("click", () => {
        if (!AUTH_API) {
          if (hint) hint.hidden = false;
          return;
        }
        login();
      });
    }

    if (logoutBtn) {
      logoutBtn.addEventListener("click", async () => {
        await logout();
        showView("login");
      });
    }

    if (!AUTH_API) {
      if (hint) hint.hidden = false;
      showView("login");
      return null;
    }

    const sid = getSid();
    if (sid) {
      showView("dashboard");
      const user = await fetchMe();
      if (user) {
        currentUser = user;
        populateUserBar(user);
        showView("dashboard");
        return user;
      }
      showView("login");
      return null;
    }

    showView("login");
    return null;
  }

  global.FDashboardAuth = {
    init,
    getUser: () => currentUser,
    logout,
    showView,
    getApiUrl: () => AUTH_API,
  };
})(typeof window !== "undefined" ? window : globalThis);
