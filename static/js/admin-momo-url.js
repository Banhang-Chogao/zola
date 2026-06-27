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
      // Preload placements data in background
      loadPlacements().catch(() => {});
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

  // ============= Content Placements =============
  async function loadPlacements() {
    try {
      const opts = {
        credentials: "include",
        cache: "no-store",
        headers: {},
      };
      const sid = getSid();
      if (sid) opts.headers["Authorization"] = "Bearer " + sid;

      const res = await fetch(AUTH_API + "/admin/content-placements", opts);
      if (res.status === 401 || res.status === 403) {
        setAuthState(STATE.GUEST);
        return;
      }
      if (!res.ok) throw new Error(`API error: ${res.status}`);

      cpData = await res.json();
      renderPlacementRegistry();
      renderBlocksTable();
    } catch (e) {
      console.error("loadPlacements error:", e);
      alert(`Tải placement dữ liệu thất bại: ${e.message}`);
    }
  }

  function renderPlacementRegistry() {
    if (!cpData || !cpData.placements) return;
    const tbody = document.getElementById("cp-registry-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    cpData.placements.forEach((placement) => {
      const row = document.createElement("tr");
      const blockCount = (cpData.blocks || []).filter(
        (b) => b.placement_id === placement.id
      ).length;

      row.innerHTML = `
        <td><code>${escapeHtml(placement.id)}</code></td>
        <td>${escapeHtml(placement.label)}</td>
        <td><span class="badge">${escapeHtml(placement.scope)}</span></td>
        <td><small>${escapeHtml(placement.template_hint || "—")}</small></td>
        <td><strong>${blockCount}</strong></td>
        <td>${placement.hooked ? '✓' : '—'}</td>
        <td>${placement.enabled ? '✓' : '—'}</td>
      `;
      tbody.appendChild(row);
    });
  }

  function renderBlocksTable() {
    if (!cpData || !cpData.blocks) return;
    const tbody = document.getElementById("cp-blocks-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const sorted = [...cpData.blocks].sort((a, b) => (a.priority || 100) - (b.priority || 100));
    sorted.forEach((block) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><code>${escapeHtml(block.id)}</code></td>
        <td>${escapeHtml(block.placement_id)}</td>
        <td><span class="badge badge--sm">${escapeHtml(block.type)}</span></td>
        <td>${escapeHtml(block.title || "—")}</td>
        <td>${block.enabled ? '✓' : '—'}</td>
        <td>
          <button class="btn btn--small btn--secondary" onclick="window.editBlock('${escapeAttr(block.id)}')">Sửa</button>
          <button class="btn btn--small btn--danger" onclick="window.deleteBlock('${escapeAttr(block.id)}')">Xóa</button>
        </td>
      `;
      tbody.appendChild(row);
    });
  }

  function getPlacementDropdown() {
    if (!cpData || !cpData.placements) return "";
    return cpData.placements
      .map((p) => `<option value="${escapeAttr(p.id)}">${escapeHtml(p.label)}</option>`)
      .join("");
  }

  window.openBlockModal = function (blockId = null) {
    cpEditingId = blockId;
    const modal = document.getElementById("block-modal");
    if (!modal) return;

    const form = document.getElementById("block-form");
    const placementSelect = document.getElementById("block-placement");

    // Populate placement dropdown
    if (placementSelect && cpData && cpData.placements) {
      placementSelect.innerHTML = cpData.placements
        .map((p) => `<option value="${escapeAttr(p.id)}">${escapeHtml(p.label)}</option>`)
        .join("");
    }

    if (blockId && cpData && cpData.blocks) {
      const block = cpData.blocks.find((b) => b.id === blockId);
      if (block) {
        document.getElementById("block-id").value = block.id;
        document.getElementById("block-id").disabled = true;
        document.getElementById("block-placement").value = block.placement_id;
        document.getElementById("block-type").value = block.type;
        document.getElementById("block-title").value = block.title || "";
        document.getElementById("block-body").value = block.body || "";
        document.getElementById("block-button").value = block.button_text || "";
        document.getElementById("block-url").value = block.url || "";
        document.getElementById("block-style").value = block.style || "default";
        document.getElementById("block-priority").value = block.priority || 100;
        document.getElementById("block-enabled").checked = block.enabled || false;
        document.getElementById("block-pages").value = (block.pages || ["*"]).join(", ");
        document.getElementById("block-exclude").value = (block.exclude_pages || []).join(", ");
        document.getElementById("block-start").value = block.start_date || "";
        document.getElementById("block-end").value = block.end_date || "";
      }
    } else {
      // Reset for create
      document.getElementById("block-id").disabled = false;
      form.reset();
      document.getElementById("block-id").focus();
    }

    updateTypeWarning();
    renderBlockPreview();
    modal.showModal();
  };

  window.editBlock = function (blockId) {
    openBlockModal(blockId);
  };

  window.deleteBlock = async function (blockId) {
    if (!confirm(`Xóa block "${blockId}"?`)) return;

    try {
      const opts = {
        method: "DELETE",
        credentials: "include",
        headers: {},
      };
      const sid = getSid();
      if (sid) opts.headers["Authorization"] = "Bearer " + sid;

      const res = await fetch(AUTH_API + `/admin/content-blocks/${encodeURIComponent(blockId)}`, opts);
      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const result = await res.json();
      await loadPlacements();
      showCommitStatus(result);
      alert("✓ Block đã xóa");
    } catch (e) {
      alert(`❌ Xóa thất bại: ${e.message}`);
    }
  };

  function updateTypeWarning() {
    const type = document.getElementById("block-type").value;
    const warning = document.getElementById("html-safe-warning");
    if (warning) warning.hidden = type !== "html_safe";
  }

  function renderBlockPreview() {
    const title = document.getElementById("block-title").value;
    const body = document.getElementById("block-body").value;
    const button = document.getElementById("block-button").value;
    const url = document.getElementById("block-url").value;
    const type = document.getElementById("block-type").value;
    const style = document.getElementById("block-style").value;

    const stage = document.getElementById("cp-preview-stage");
    if (!stage) return;

    const ctaHtml =
      button && url
        ? `<a href="#" class="placement-block__cta" onclick="return false">${escapeHtml(button)}</a>`
        : "";

    stage.innerHTML = `
      <div class="placement-block placement-block--${escapeHtml(type)} placement-block--${escapeHtml(style)}">
        ${title ? `<h3 class="placement-block__title">${escapeHtml(title)}</h3>` : ""}
        ${body ? `<p class="placement-block__body">${escapeHtml(body)}</p>` : ""}
        ${ctaHtml}
      </div>
    `;
  }

  async function submitBlock() {
    const id = document.getElementById("block-id").value.trim();
    const placement = document.getElementById("block-placement").value;
    const type = document.getElementById("block-type").value;
    const title = document.getElementById("block-title").value;
    const body = document.getElementById("block-body").value;
    const button = document.getElementById("block-button").value;
    const url = document.getElementById("block-url").value;
    const style = document.getElementById("block-style").value;
    const priority = parseInt(document.getElementById("block-priority").value) || 100;
    const enabled = document.getElementById("block-enabled").checked;
    const pagesStr = document.getElementById("block-pages").value;
    const excludeStr = document.getElementById("block-exclude").value;
    const start = document.getElementById("block-start").value;
    const end = document.getElementById("block-end").value;

    if (!id || !placement || !type) {
      alert("Vui lòng điền tất cả trường bắt buộc");
      return;
    }

    const payload = {
      id: id,
      placement_id: placement,
      type: type,
      title: title || null,
      body: body || null,
      button_text: button || null,
      url: url || null,
      style: style || "default",
      priority: priority,
      enabled: enabled,
      pages: pagesStr ? pagesStr.split(",").map((s) => s.trim()) : ["*"],
      exclude_pages: excludeStr ? excludeStr.split(",").map((s) => s.trim()) : [],
      start_date: start || null,
      end_date: end || null,
    };

    try {
      const opts = {
        method: cpEditingId ? "PATCH" : "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      };
      const sid = getSid();
      if (sid) opts.headers["Authorization"] = "Bearer " + sid;

      const url_path = cpEditingId
        ? `/admin/content-blocks/${encodeURIComponent(cpEditingId)}`
        : "/admin/content-blocks";

      const res = await fetch(AUTH_API + url_path, {
        ...opts,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }

      const result = await res.json();
      await loadPlacements();
      showCommitStatus(result);

      document.getElementById("block-modal").close();
      cpEditingId = null;
      alert("✓ Block " + (cpEditingId ? "cập nhật" : "tạo") + " thành công");
    } catch (e) {
      alert(`❌ Lưu block thất bại: ${e.message}`);
    }
  }

  function showCommitStatus(result) {
    const status = document.getElementById("cp-commit-status");
    if (!status) return;

    if (result.committed) {
      status.innerHTML = `
        <div class="commit-ok">
          ✓ Đã commit: <a href="${escapeHtml(result.commit_url)}" target="_blank">${result.commit_sha.slice(0, 7)}</a>
          <br/>Deploy: ${escapeHtml(result.deploy_eta || "1-2 phút")}
        </div>
      `;
    } else {
      status.innerHTML = `
        <div class="commit-warning">
          ⚠ Lưu cục bộ (chưa commit): ${escapeHtml(result.reason || "không có token")}
        </div>
      `;
    }
    status.hidden = false;
  }

  function switchTab(tabName) {
    document.querySelectorAll(".cp-tab").forEach((btn) => {
      btn.classList.toggle("cp-tab--active", btn.getAttribute("data-tab") === tabName);
      btn.setAttribute("aria-selected", btn.getAttribute("data-tab") === tabName);
    });

    document.querySelectorAll(".cp-panel").forEach((panel) => {
      panel.hidden = panel.getAttribute("data-tab-panel") !== tabName;
    });

    // Load placements data on first switch to tabs 2 or 3
    if ((tabName === "placements" || tabName === "blocks") && !cpData) {
      loadPlacements();
    }
  }

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

  // Tab switching
  document.querySelectorAll(".cp-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchTab(btn.getAttribute("data-tab"));
    });
  });

  // Block form
  const blockModal = document.getElementById("block-modal");
  if (blockModal) {
    document.getElementById("block-placement").addEventListener("change", () => {
      renderBlockPreview();
    });
    document.getElementById("block-type").addEventListener("change", () => {
      updateTypeWarning();
      renderBlockPreview();
    });
    document.getElementById("block-title").addEventListener("input", () => {
      renderBlockPreview();
    });
    document.getElementById("block-body").addEventListener("input", () => {
      renderBlockPreview();
    });
    document.getElementById("block-button").addEventListener("input", () => {
      renderBlockPreview();
    });
    document.getElementById("block-url").addEventListener("input", () => {
      renderBlockPreview();
    });
    document.getElementById("block-style").addEventListener("change", () => {
      renderBlockPreview();
    });

    document.getElementById("close-block-modal")?.addEventListener("click", () => {
      blockModal.close();
      cpEditingId = null;
    });
    document.getElementById("cancel-block-btn")?.addEventListener("click", () => {
      blockModal.close();
      cpEditingId = null;
    });
    document.getElementById("submit-block-btn")?.addEventListener("click", submitBlock);
  }

  const cpCreateBtn = document.getElementById("cp-create-btn");
  if (cpCreateBtn) {
    cpCreateBtn.addEventListener("click", () => {
      openBlockModal();
    });
  }

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
