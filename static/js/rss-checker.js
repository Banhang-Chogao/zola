/**
 * RSS Checker frontend — /baochi/ page.
 *
 * Flow:
 *   1. Check session_id sessionStorage → validate /auth/me
 *      - OK → show main view (form + result)
 *      - Fail → show login view
 *   2. Submit form → POST URL → backend /api/check-rss?url=...
 *      - 200 → render 10 entries (title + link)
 *      - 400/401 → error message
 *
 * Privacy: KHÔNG log URL hoặc entries vào console/localStorage.
 * Trải nghiệm: loading spinner trong button, error state inline.
 *
 * Shared với /editor/: SESSION_KEY, AUTH_API meta tag, populateUserBar.
 */
(function () {
  "use strict";

  const SESSION_KEY = "zola-cms-session-id";
  const AUTH_API = (function () {
    const meta = document.querySelector('meta[name="zola-cms-auth-api"]');
    return (meta && meta.getAttribute("content")) || "";
  })();

  const root = document.getElementById("baochi-app");
  if (!root) return;

  function $(sel) { return root.querySelector(sel); }
  function $$(sel) { return Array.from(root.querySelectorAll(sel)); }

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; }
    catch (e) { return ""; }
  }
  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }
  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function showView(name) {
    $$("[data-view]").forEach(function (v) {
      v.hidden = v.dataset.view !== name;
    });
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

  const AUTH_ERROR_MESSAGES = {
    access_denied:               "Truy cập bị từ chối: Bạn không có quyền quản trị blog này.",
    invalid_state:               "Phiên đăng nhập hết hạn. Vui lòng thử lại.",
    missing_params:              "GitHub callback thiếu tham số. Thử lại.",
    token_exchange_failed:       "Lỗi xác thực GitHub. Thử lại sau.",
    github_unreachable:          "Không kết nối được GitHub. Kiểm tra mạng.",
    github_profile_fetch_failed: "Không đọc được profile GitHub. Thử lại.",
  };

  function showLoginError(code) {
    const el = $("[data-login-error]");
    if (!el) return;
    el.textContent = AUTH_ERROR_MESSAGES[code] || ("Lỗi xác thực: " + code);
    el.hidden = false;
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
    } catch (e) { return null; }
  }

  function populateUserBar(user) {
    const bar = $("[data-user-bar]");
    if (!bar) return;
    const avatar = $("[data-user-avatar]");
    const name   = $("[data-user-name]");
    const email  = $("[data-user-email]");
    if (avatar && user.avatar) { avatar.src = user.avatar; avatar.alt = user.username || ""; }
    if (name)  name.textContent  = user.name || user.username || "";
    if (email) email.textContent = user.email || "";
    bar.hidden = false;
  }

  // Login button → redirect OAuth
  const loginBtn = $("[data-action='github-login']");
  if (loginBtn) {
    loginBtn.addEventListener("click", function () {
      if (!AUTH_API) { $("[data-login-hint]").hidden = false; return; }
      location.href = AUTH_API + "/auth/login?return_to=" +
        encodeURIComponent(location.pathname);
    });
  }

  // Logout
  const logoutBtn = $("[data-action='logout']");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async function () {
      if (!confirm("Đăng xuất khỏi CMS?")) return;
      const sid = getSid();
      if (sid && AUTH_API) {
        try {
          await fetch(AUTH_API + "/auth/logout", {
            method: "POST",
            headers: { "Authorization": "Bearer " + sid },
            credentials: "omit",
            keepalive: true,
          });
        } catch (e) {}
      }
      clearSid();
      $("[data-user-bar]").hidden = true;
      showView("login");
    });
  }

  // Escape HTML để chống XSS từ feed title (vd feed của site độc hại có
  // <script> trong title). textContent là an toàn nhưng dùng escapeHtml +
  // innerHTML để compose nhanh hơn — vẫn safe vì input đã escape.
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c]);
    });
  }

  // ============= RSS Form =============
  const form        = $("[data-form='rss']");
  const urlInput    = $("[name='url']");
  const extractBtn  = $("[data-extract-btn]");
  const extractLbl  = $("[data-extract-label]");
  const spinner     = $("[data-extract-spinner]");
  const resultBox   = $("[data-result]");
  const errorBox    = $("[data-error]");
  const errorMsg    = $("[data-error-msg]");
  const list        = $("[data-list]");
  const countEl     = $("[data-count]");
  const sourceTitle = $("[data-source-title]");

  function setLoading(on) {
    extractBtn.disabled = on;
    if (extractLbl) extractLbl.textContent = on ? "Đang lấy…" : "Extract";
    if (spinner)    spinner.hidden = !on;
  }

  function showResult(data) {
    errorBox.hidden = true;
    resultBox.hidden = false;
    if (sourceTitle) {
      sourceTitle.textContent = data.source_title || "Kết quả";
    }
    if (countEl) countEl.textContent = data.count + " bài";
    list.innerHTML = (data.items || []).map(function (it, idx) {
      return '<li class="baochi-item">' +
        '<span class="baochi-item__idx">' + (idx + 1) + '</span>' +
        '<a class="baochi-item__link" href="' + escapeHtml(it.link) +
        '" target="_blank" rel="noopener noreferrer">' +
          escapeHtml(it.title) +
        '</a>' +
      '</li>';
    }).join("");
  }

  function showError(msg) {
    resultBox.hidden = true;
    errorBox.hidden = false;
    errorMsg.textContent = msg || "Không thể lấy tin từ nguồn này.";
  }

  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      if (!AUTH_API) { showError("Backend chưa cấu hình."); return; }
      const url = (urlInput.value || "").trim();
      if (!url) return;

      setLoading(true);
      resultBox.hidden = true;
      errorBox.hidden = true;

      try {
        const sid = getSid();
        const res = await fetch(AUTH_API + "/api/check-rss?url=" + encodeURIComponent(url), {
          headers: { "Authorization": "Bearer " + sid },
          credentials: "omit",
          cache: "no-store",
        });
        if (res.status === 401) {
          clearSid();
          showView("login");
          return;
        }
        if (!res.ok) {
          showError("Không thể lấy tin từ nguồn này.");
          return;
        }
        const data = await res.json();
        if (!data.items || !data.items.length) {
          showError("Không thể lấy tin từ nguồn này.");
          return;
        }
        showResult(data);
      } catch (err) {
        showError("Lỗi kết nối backend. Thử lại.");
      } finally {
        setLoading(false);
      }
    });
  }

  // ============= INIT =============
  async function init() {
    consumeUrlHashSid();
    const errCode = consumeUrlAuthError();
    if (errCode) showLoginError(errCode);

    if (!AUTH_API) {
      $("[data-login-hint]").hidden = false;
      showView("login");
      return;
    }

    const user = await fetchMe();
    if (user) {
      populateUserBar(user);
      showView("main");
      urlInput.focus();
    } else {
      showView("login");
    }
  }

  init();
})();
