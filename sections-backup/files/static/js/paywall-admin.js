/**
 * Paywall Admin — quản lý request + generate/send approve code.
 * Auth: PAYWALL_ADMIN_TOKEN lưu sessionStorage (không public).
 */
(function () {
  "use strict";

  var root = document.getElementById("paywall-admin-app");
  if (!root) return;

  var TOKEN_KEY = "paywall-admin-token";
  var API = (function () {
    var m = document.querySelector('meta[name="zola-paywall-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "";
  })();

  var state = {
    codeId: "",
    postTitle: "",
    postUrl: "",
    approveCode: "",
  };

  function $(s) { return root.querySelector(s); }
  function $$(s) { return Array.from(root.querySelectorAll(s)); }

  function getToken() {
    try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; }
  }
  function setToken(t) {
    try { sessionStorage.setItem(TOKEN_KEY, t); } catch (e) {}
  }
  function clearToken() {
    try { sessionStorage.removeItem(TOKEN_KEY); } catch (e) {}
  }

  function showView(name) {
    $$("[data-view]").forEach(function (v) { v.hidden = v.dataset.view !== name; });
  }

  function showStatus(msg, type) {
    var el = $("[data-admin-status]");
    if (!el) return;
    el.textContent = msg;
    el.className = "paywall-status paywall-status--" + (type || "info");
    el.hidden = false;
  }

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      Authorization: "Bearer " + getToken(),
    };
  }

  async function apiGet(path) {
    var res = await fetch(API + path, {
      headers: { Authorization: "Bearer " + getToken() },
      credentials: "omit",
      cache: "no-store",
    });
    if (res.status === 401) throw new Error("UNAUTHORIZED");
    var data = await res.json().catch(function () { return null; });
    if (!res.ok) throw new Error((data && data.detail) || ("HTTP " + res.status));
    return data;
  }

  async function apiPost(path, body) {
    var res = await fetch(API + path, {
      method: "POST",
      headers: authHeaders(),
      credentials: "omit",
      cache: "no-store",
      body: JSON.stringify(body),
    });
    if (res.status === 401) throw new Error("UNAUTHORIZED");
    var data = await res.json().catch(function () { return null; });
    if (!res.ok) throw new Error((data && data.detail) || ("HTTP " + res.status));
    return data;
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    return (window.ZolaDateTime && window.ZolaDateTime.formatDisplayDateTime(iso)) || String(iso);
  }

  function renderRequests(rows) {
    var tbody = $("[data-requests-body]");
    if (!tbody) return;
    if (!rows || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="5">Không có yêu cầu pending.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function (r) {
      return (
        "<tr>" +
        "<td>" + fmtDate(r.created_at) + "</td>" +
        "<td>" + escapeHtml(r.email) + "</td>" +
        "<td><code>" + escapeHtml(r.post_id) + "</code><br>" + escapeHtml(r.post_title) + "</td>" +
        "<td>" + escapeHtml(r.payment_note || "—") + "</td>" +
        '<td><button type="button" class="paywall-btn paywall-btn--primary paywall-btn--small" data-fill-request="' + escapeHtml(r.request_id) + '">Tạo code</button></td>' +
        "</tr>"
      );
    }).join("");

    $$("[data-fill-request]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var rid = btn.getAttribute("data-fill-request");
        var row = rows.find(function (x) { return x.request_id === rid; });
        if (!row) return;
        var form = $('[data-form="generate"]');
        if (!form) return;
        form.post_id.value = row.post_id;
        form.post_url.value = row.post_url;
        form.post_title.value = row.post_title;
        form.email.value = row.email;
        form.request_id.value = row.request_id;
        form.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadRequests() {
    if (!API) {
      showStatus("Paywall API chưa cấu hình trong config.toml (paywall_api_url).", "error");
      return;
    }
    try {
      var rows = await apiGet("/api/paywall/admin/requests?status=pending");
      renderRequests(rows);
    } catch (e) {
      if (e.message === "UNAUTHORIZED") {
        clearToken();
        showView("login");
        return;
      }
      showStatus(e.message || "Không tải được danh sách.", "error");
    }
  }

  async function initMain() {
    showView("main");
    await loadRequests();
  }

  $('[data-form="login"]').addEventListener("submit", function (e) {
    e.preventDefault();
    var token = (new FormData(e.target).get("token") || "").toString().trim();
    if (!token) return;
    setToken(token);
    initMain().catch(function (err) {
      if (err.message === "UNAUTHORIZED") {
        clearToken();
        var errEl = $("[data-login-error]");
        if (errEl) {
          errEl.textContent = "Token không hợp lệ.";
          errEl.hidden = false;
        }
      }
    });
  });

  $('[data-action="logout"]').addEventListener("click", function () {
    clearToken();
    showView("login");
  });

  $('[data-action="refresh"]').addEventListener("click", function () {
    loadRequests();
  });

  $('[data-form="generate"]').addEventListener("submit", async function (e) {
    e.preventDefault();
    var fd = new FormData(e.target);
    var body = {
      post_id: fd.get("post_id"),
      post_url: fd.get("post_url"),
      post_title: fd.get("post_title"),
      email: fd.get("email"),
      expires_days: parseInt(fd.get("expires_days"), 10) || 7,
      max_usage: parseInt(fd.get("max_usage"), 10) || 5,
      approve_code: (fd.get("approve_code") || "").toString().trim() || null,
      request_id: (fd.get("request_id") || "").toString().trim() || null,
    };
    try {
      var out = await apiPost("/api/paywall/admin/generate-code", body);
      state.codeId = out.code_id;
      state.approveCode = out.approve_code;
      state.postTitle = body.post_title;
      state.postUrl = body.post_url;
      var result = $("[data-code-result]");
      if (result) {
        result.hidden = false;
        result.innerHTML =
          "<strong>Approve code:</strong> " + escapeHtml(out.approve_code) +
          "<br><strong>Hết hạn:</strong> " + escapeHtml(out.expires_at) +
          "<br><strong>Code ID:</strong> " + escapeHtml(out.code_id);
      }
      var emailActions = $("[data-email-actions]");
      if (emailActions) emailActions.hidden = false;
      showStatus("Đã tạo approve code. Gửi email ngay để lưu plaintext trước khi server restart.", "success");
      loadRequests();
    } catch (err) {
      if (err.message === "UNAUTHORIZED") { clearToken(); showView("login"); return; }
      showStatus(err.message || "Tạo code thất bại.", "error");
    }
  });

  $('[data-action="send-email"]').addEventListener("click", async function () {
    if (!state.codeId) {
      showStatus("Chưa có code — generate trước.", "error");
      return;
    }
    try {
      await apiPost("/api/paywall/admin/send-code-email", {
        code_id: state.codeId,
        post_title: state.postTitle,
        post_url: state.postUrl,
      });
      showStatus("Đã gửi email cho người đọc.", "success");
    } catch (err) {
      if (err.message === "UNAUTHORIZED") { clearToken(); showView("login"); return; }
      showStatus(err.message || "Gửi email thất bại.", "error");
    }
  });

  if (getToken() && API) {
    initMain().catch(function () {
      clearToken();
      showView("login");
    });
  } else {
    showView("login");
  }
})();