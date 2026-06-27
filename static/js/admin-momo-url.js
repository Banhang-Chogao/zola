/**
 * Admin MoMo URL Manager
 *
 * Authentication: Google OAuth via the VIPZone backend (admin allowlist only).
 * UI: View all MoMo links, replace old with new.
 *
 * Auth state machine (auth-vaccine A1 — "OAuth callback success but UI stays
 * locked"): checking → authenticated | guest | unauthorized | error.
 *   - The session id is handed back in the URL fragment (#sid=...) and/or a
 *     cross-site cookie; ?auth=success is only a hint, never trusted on its own.
 *     We always verify with GET /auth/me (Bearer + credentials:"include").
 *   - The gate overlay is hidden via the `hidden` attribute; CSS forces
 *     `.auth-gate[hidden]{display:none!important}` so an authenticated admin is
 *     never trapped behind the modal.
 *   - /auth/me is single-flight + has a timeout so a cold backend can never spin
 *     forever; the URL is cleaned with history.replaceState so init never loops.
 */

(function () {
  // Single init guard — a duplicate <script> include must not double-wire the page.
  if (window.__momoAuthInitDone) return;
  window.__momoAuthInitDone = true;

  const AUTH_API = (() => {
    const m = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "https://blog-vipzone-api.onrender.com";
  })();

  const SESSION_KEY = "zola-cms-session-id";
  const AUTH_TIMEOUT_MS = 8000; // cold Render dynos: never hang the gate forever.

  const STATE = {
    CHECKING: "checking",
    AUTHENTICATED: "authenticated",
    GUEST: "guest",
    UNAUTHORIZED: "unauthorized",
    ERROR: "error",
  };

  let currentUser = null;
  let auditData = null;
  let authState = null;
  let mePromise = null;
  let cpData = null; // { placements:[], blocks:[] } from /admin/content-placements
  let cpEditingId = null; // block id being edited, or null when creating

  // ============= DOM Elements =============
  const authGate = document.getElementById("auth-gate");
  const adminContent = document.getElementById("admin-content");
  const googleLoginBtn = document.getElementById("google-login-btn");
  const switchAccountBtn = document.getElementById("switch-account-btn");
  const authRetryBtn = document.getElementById("auth-retry-btn");
  const logoutBtn = document.getElementById("logout-btn");
  const loadingState = document.getElementById("loading-state");
  const contentState = document.getElementById("content-state");
  const errorState = document.getElementById("error-state");
  const tableBody = document.getElementById("table-body");

  const replaceModal = document.getElementById("replace-modal");
  const detailsModal = document.getElementById("details-modal");

  // ============= Session Management =============
  function getSid() {
    try {
      return localStorage.getItem(SESSION_KEY) || "";
    } catch (e) {
      return "";
    }
  }

  function setSid(sid) {
    try {
      localStorage.setItem(SESSION_KEY, sid);
    } catch (e) {}
  }

  function clearSid() {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch (e) {}
  }

  /**
   * Process the OAuth callback once: capture #sid=... from the fragment, then
   * strip auth=success / auth_error / the sid fragment from the URL so a refresh
   * or re-init never re-processes it (prevents loops + cleans the address bar).
   * Returns { authSuccess, authError } parsed from the query before cleanup.
   */
  function consumeAuthCallback() {
    let sidFromHash = "";
    if (location.hash) {
      const m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
      if (m) sidFromHash = m[1];
    }
    if (sidFromHash) setSid(sidFromHash);

    const params = new URLSearchParams(location.search);
    const authError = params.get("auth_error") || "";
    const authSuccess = params.get("auth") === "success";

    if (sidFromHash || authSuccess || authError) {
      params.delete("auth");
      params.delete("auth_error");
      const qs = params.toString();
      try {
        history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
      } catch (e) {}
    }
    return { authSuccess, authError };
  }

  /**
   * Verify the current session. Single-flight (concurrent callers share one
   * request) + AbortController timeout. Resolves to { status, user, error }.
   */
  function fetchMe() {
    if (mePromise) return mePromise;
    mePromise = (async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), AUTH_TIMEOUT_MS);
      try {
        const opts = {
          credentials: "include",
          cache: "no-store",
          headers: {},
          signal: controller.signal,
        };
        const sid = getSid();
        if (sid) opts.headers["Authorization"] = "Bearer " + sid;

        const res = await fetch(AUTH_API + "/auth/me", opts);
        if (res.status === 401) return { status: 401, user: null };
        if (res.status === 403) return { status: 403, user: null };
        if (!res.ok) return { status: res.status, user: null, error: true };
        const user = await res.json();
        return { status: 200, user };
      } catch (e) {
        return { status: 0, user: null, error: true };
      } finally {
        clearTimeout(timer);
        mePromise = null; // allow an explicit retry from the error view
      }
    })();
    return mePromise;
  }

  async function logoutRemote() {
    const sid = getSid();
    if (!sid || !AUTH_API) {
      clearSid();
      return;
    }
    try {
      await fetch(AUTH_API + "/auth/logout", {
        method: "POST",
        headers: { Authorization: "Bearer " + sid },
        credentials: "include",
        keepalive: true,
      });
    } catch (e) {}
    clearSid();
  }

  // ============= Auth state machine =============
  function showGateView(view) {
    document.querySelectorAll("[data-auth-view]").forEach((el) => {
      el.hidden = el.getAttribute("data-auth-view") !== view;
    });
  }

  function setAuthState(state, detail) {
    authState = state;
    if (state === STATE.AUTHENTICATED) {
      authGate.hidden = true;
      adminContent.hidden = false;
      return;
    }
    // Every non-authenticated state shows the gate with the matching view.
    adminContent.hidden = true;
    authGate.hidden = false;
    showGateView(state);
    if (detail && detail.message) {
      const id =
        state === STATE.UNAUTHORIZED ? "unauth-message" : "auth-error-message";
      const el = document.getElementById(id);
      if (el) el.textContent = detail.message;
    }
  }

  function startLogin() {
    const returnPath = location.pathname; // already cleaned of auth params
    // Google only — this admin tool never uses GitHub OAuth.
    window.location.href =
      AUTH_API + "/auth/google/start?return_to=" + encodeURIComponent(returnPath);
  }

  async function runAuthCheck(callbackError) {
    setAuthState(STATE.CHECKING);
    const { user, status, error } = await fetchMe();

    if (user && (user.is_admin === true || user.is_super === true)) {
      currentUser = user;
      setAuthState(STATE.AUTHENTICATED);
      loadMoMoLinks();
      return;
    }
    if (user) {
      // Authenticated but not on the admin allowlist.
      setAuthState(STATE.UNAUTHORIZED, {
        message:
          (user.email ? "Tài khoản " + user.email + " " : "Tài khoản này ") +
          "không nằm trong danh sách quản trị. Vui lòng đăng nhập bằng tài khoản admin.",
      });
      return;
    }
    // A Google login by a non-whitelisted account creates NO session — the
    // backend signals it only via ?auth_error=access_denied. Surface that as the
    // unauthorized state (not the guest modal) so the user isn't stuck retrying.
    if (callbackError === "access_denied") {
      setAuthState(STATE.UNAUTHORIZED, {
        message:
          "Tài khoản Google của bạn không có quyền quản trị. Vui lòng đăng nhập bằng tài khoản admin được cấp phép.",
      });
      return;
    }
    if (status === 403) {
      setAuthState(STATE.UNAUTHORIZED);
      return;
    }
    if (status === 401) {
      setAuthState(STATE.GUEST);
      return;
    }
    if (error) {
      setAuthState(STATE.ERROR, {
        message:
          "Không kết nối được máy chủ xác thực (có thể đang khởi động). Vui lòng thử lại.",
      });
      return;
    }
    if (callbackError) {
      // Any other OAuth-callback error (token exchange, unreachable, etc.).
      setAuthState(STATE.ERROR, {
        message: "Đăng nhập không thành công (" + callbackError + "). Vui lòng thử lại.",
      });
      return;
    }
    setAuthState(STATE.GUEST);
  }

  // ============= UI State (admin content) =============
  function showLoading() {
    loadingState.hidden = false;
    contentState.hidden = true;
    errorState.hidden = true;
  }

  function showContent() {
    loadingState.hidden = true;
    contentState.hidden = false;
    errorState.hidden = true;
  }

  function showError(message) {
    loadingState.hidden = true;
    contentState.hidden = true;
    errorState.hidden = false;
    document.getElementById("error-message").textContent = message;
  }

  // ============= Data Loading =============
  async function loadMoMoLinks() {
    try {
      showLoading();

      const opts = {
        credentials: "include",
        cache: "no-store",
        headers: {},
      };

      const sid = getSid();
      if (sid) {
        opts.headers["Authorization"] = "Bearer " + sid;
      }

      const res = await fetch(AUTH_API + "/admin/momo-links", opts);

      // Session expired or revoked between the gate check and this call → fall
      // back to the gate instead of showing a confusing data error.
      if (res.status === 401) {
        setAuthState(STATE.GUEST);
        return;
      }
      if (res.status === 403) {
        setAuthState(STATE.UNAUTHORIZED);
        return;
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error: ${res.status} ${text}`);
      }

      auditData = await res.json();
      renderTable();
      updateSummary();
      showContent();
    } catch (e) {
      console.error("loadMoMoLinks error:", e);
      showError(`Tải dữ liệu thất bại: ${e.message}`);
    }
  }

  function renderTable() {
    if (!auditData || !auditData.links_by_url) {
      tableBody.innerHTML = "<tr><td colspan='5' class='text-center'>Không có dữ liệu</td></tr>";
      return;
    }

    tableBody.innerHTML = "";

    Object.entries(auditData.links_by_url).forEach(([url, link]) => {
      const row = document.createElement("tr");
      row.className = `category-${link.category.replace(/\s+/g, "-").toLowerCase()}`;

      const categoryBadge = getCategoryBadge(link.category);

      row.innerHTML = `
        <td class="col-url">
          <code class="url-code">${escapeHtml(url)}</code>
          <div class="url-actions">
            <button class="btn-icon" title="Copy" onclick="copyToClipboard('${escapeAttr(url)}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
              </svg>
            </button>
            <a href="${url}" target="_blank" class="btn-icon" title="Mở link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                <polyline points="15 3 21 3 21 9"></polyline>
                <line x1="10" y1="14" x2="21" y2="3"></line>
              </svg>
            </a>
          </div>
        </td>
        <td class="col-category">${categoryBadge}</td>
        <td class="col-locations">
          <button class="link-text" onclick="showDetailsModal('${escapeAttr(url)}')">
            ${link.count} vị trí
          </button>
        </td>
        <td class="col-count">${link.count}</td>
        <td class="col-actions">
          <button class="btn btn--small btn--secondary" onclick="openReplaceModal('${escapeAttr(url)}', '${escapeAttr(link.category)}', ${link.count})">
            Thay link
          </button>
        </td>
      `;

      tableBody.appendChild(row);
    });
  }

  function getCategoryBadge(category) {
    const badges = {
      "Premium default": '<span class="badge badge--primary">Premium</span>',
      "Donate": '<span class="badge badge--success">Donate</span>',
      "Premium post custom": '<span class="badge badge--info">Custom</span>',
      "Template/hardcoded": '<span class="badge badge--warning">Template</span>',
      "Workflow/env": '<span class="badge badge--secondary">Workflow</span>',
      "Documentation": '<span class="badge badge--light">Doc</span>',
    };
    return badges[category] || `<span class="badge">${escapeHtml(category)}</span>`;
  }

  function updateSummary() {
    if (!auditData || !auditData.summary) return;

    document.getElementById("summary-total").textContent = auditData.summary.total_unique_urls || 0;
    document.getElementById("summary-premium").textContent = auditData.summary.premium_default || 0;
    document.getElementById("summary-donate").textContent = auditData.summary.donate || 0;
    document.getElementById("summary-custom").textContent = auditData.summary.premium_post_custom || 0;
  }

  // ============= Replace Modal =============
  window.openReplaceModal = function (url, category, count) {
    document.getElementById("old-url-display").value = url;
    document.getElementById("new-url-input").value = "";
    document.getElementById("replace-count").textContent = count;

    const scopeRadios = document.querySelectorAll('input[name="replace-scope"]');
    scopeRadios[0].checked = true;
    updateReplaceScope();

    replaceModal.showModal();
  };

  function updateReplaceScope() {
    const scope = document.querySelector('input[name="replace-scope"]:checked').value;
    const locationDiv = document.getElementById("replace-location");
    const warning = document.getElementById("replace-warning");

    if (scope === "single") {
      locationDiv.hidden = false;
      warning.hidden = true;
      populateLocationSelect();
    } else {
      locationDiv.hidden = true;
      warning.hidden = false;
    }
  }

  function populateLocationSelect() {
    const url = document.getElementById("old-url-display").value;
    const link = auditData.links_by_url[url];
    const select = document.getElementById("location-select");

    if (!link || !link.locations) {
      select.innerHTML = '<option>Không tìm thấy vị trí</option>';
      return;
    }

    select.innerHTML = link.locations
      .map((loc) => `<option value="${escapeAttr(loc)}">${escapeHtml(loc)}</option>`)
      .join("");
  }

  function validateMoMoUrl(url) {
    if (!url) return false;
    if (!url.startsWith("https://me.momo.vn/")) return false;
    const parts = url.split("/");
    return parts.length >= 5;
  }

  async function submitReplace() {
    const oldUrl = document.getElementById("old-url-display").value;
    const newUrl = document.getElementById("new-url-input").value.trim();
    const scope = document.querySelector('input[name="replace-scope"]:checked').value;
    const target = document.getElementById("location-select").value;

    if (!newUrl) {
      alert("Vui lòng nhập URL mới");
      return;
    }

    if (!validateMoMoUrl(newUrl)) {
      alert("URL mới không hợp lệ. Phải là dạng: https://me.momo.vn/...");
      return;
    }

    if (oldUrl === newUrl) {
      alert("URL mới phải khác URL cũ");
      return;
    }

    showReplaceStatus(true);

    try {
      const opts = {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      };

      const sid = getSid();
      if (sid) {
        opts.headers["Authorization"] = "Bearer " + sid;
      }

      const res = await fetch(AUTH_API + "/admin/momo-links/replace", {
        ...opts,
        body: JSON.stringify({
          old_url: oldUrl,
          new_url: newUrl,
          scope,
          target: scope === "single" ? target : null,
        }),
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }

      const result = await res.json();
      showReplaceStatus(false);

      alert(
        `✓ Thay đổi thành công\n${result.files_modified.length} file được cập nhật:\n${result.files_modified.join(
          "\n"
        )}`
      );

      replaceModal.close();
      loadMoMoLinks(); // Reload
    } catch (e) {
      showReplaceStatus(false);
      alert(`❌ Thay đổi thất bại:\n${e.message}`);
    }
  }

  function showReplaceStatus(show) {
    document.getElementById("replace-status").hidden = !show;
    document.getElementById("confirm-replace-btn").disabled = show;
  }

  // ============= Details Modal =============
  window.showDetailsModal = function (url) {
    const link = auditData.links_by_url[url];
    if (!link) return;

    const content = document.getElementById("details-content");
    content.innerHTML = `
      <div class="details-list">
        <div class="details-item">
          <div class="details-label">Loại:</div>
          <div class="details-value">${escapeHtml(link.category)}</div>
        </div>
        <div class="details-item">
          <div class="details-label">URL:</div>
          <div class="details-value"><code>${escapeHtml(url)}</code></div>
        </div>
        ${link.post_title ? `
        <div class="details-item">
          <div class="details-label">Bài viết:</div>
          <div class="details-value">${escapeHtml(link.post_title)} (${escapeHtml(link.post_slug)})</div>
        </div>
        ` : ""}
        <div class="details-item">
          <div class="details-label">Sử dụng ở:</div>
          <div class="details-value">
            <ul class="location-list">
              ${link.locations.map((loc) => `<li><code>${escapeHtml(loc)}</code></li>`).join("")}
            </ul>
          </div>
        </div>
      </div>
    `;

    detailsModal.showModal();
  };

  // ============= Utility Functions =============
  window.copyToClipboard = function (text) {
    navigator.clipboard.writeText(text).then(() => {
      alert("Đã copy vào clipboard");
    });
  };

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str.replace(/'/g, "&#39;").replace(/"/g, "&quot;");
  }

  // ============= Event Listeners =============
  if (googleLoginBtn) {
    googleLoginBtn.addEventListener("click", (e) => {
      e.preventDefault();
      startLogin();
    });
  }

  if (switchAccountBtn) {
    switchAccountBtn.addEventListener("click", (e) => {
      e.preventDefault();
      clearSid();
      startLogin();
    });
  }

  if (authRetryBtn) {
    authRetryBtn.addEventListener("click", (e) => {
      e.preventDefault();
      runAuthCheck();
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      if (confirm("Bạn chắc chắn muốn đăng xuất?")) {
        await logoutRemote();
        setAuthState(STATE.GUEST);
      }
    });
  }

  document.getElementById("close-replace-modal").addEventListener("click", () => {
    replaceModal.close();
  });

  document.getElementById("cancel-replace-btn").addEventListener("click", () => {
    replaceModal.close();
  });

  document.getElementById("confirm-replace-btn").addEventListener("click", submitReplace);

  document.getElementById("close-details-modal").addEventListener("click", () => {
    detailsModal.close();
  });

  document.getElementById("retry-btn").addEventListener("click", loadMoMoLinks);

  document.querySelectorAll('input[name="replace-scope"]').forEach((radio) => {
    radio.addEventListener("change", updateReplaceScope);
  });

  // ============= Init =============
  function init() {
    // Process (and clean) any OAuth callback params before verifying — never
    // trust ?auth=success on its own, always confirm with /auth/me.
    const { authError } = consumeAuthCallback();
    runAuthCheck(authError);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
