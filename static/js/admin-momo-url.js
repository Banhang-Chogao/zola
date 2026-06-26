/**
 * Admin MoMo URL Manager
 *
 * Authentication: Google OAuth via VIPZone backend
 * UI: View all MoMo links, replace old with new
 */

(function () {
  const AUTH_API = (() => {
    const m = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content");
    return "https://blog-vipzone-api.onrender.com";
  })();

  const SESSION_KEY = "zola-cms-session-id";
  let currentUser = null;
  let auditData = null;

  // ============= DOM Elements =============
  const authGate = document.getElementById("auth-gate");
  const adminContent = document.getElementById("admin-content");
  const googleLoginBtn = document.getElementById("google-login-btn");
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

  function consumeUrlHashSid() {
    if (!location.hash) return;
    const m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  async function fetchMe() {
    const opts = {
      credentials: "include",
      cache: "no-store",
      headers: {},
    };

    const sid = getSid();
    if (sid) {
      opts.headers["Authorization"] = "Bearer " + sid;
    }

    try {
      const res = await fetch(AUTH_API + "/auth/me", opts);
      if (res.ok) {
        const user = await res.json();
        return user;
      }
    } catch (e) {
      console.warn("fetchMe error:", e);
    }

    return null;
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

  // ============= UI State =============
  function showAuthGate() {
    authGate.hidden = false;
    adminContent.hidden = true;
  }

  function showAdminContent() {
    authGate.hidden = true;
    adminContent.hidden = false;
  }

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

      if (res.status === 403) {
        showAuthGate();
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
  googleLoginBtn.addEventListener("click", (e) => {
    e.preventDefault();
    const returnTo = location.pathname;
    const loginUrl = `${AUTH_API}/auth/login?return_to=${encodeURIComponent(returnTo)}`;
    location.href = loginUrl;
  });

  logoutBtn.addEventListener("click", async () => {
    if (confirm("Bạn chắc chắn muốn đăng xuất?")) {
      await logoutRemote();
      location.reload();
    }
  });

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
  async function init() {
    consumeUrlHashSid();
    const user = await fetchMe();

    if (!user) {
      showAuthGate();
      return;
    }

    currentUser = user;
    showAdminContent();
    loadMoMoLinks();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
