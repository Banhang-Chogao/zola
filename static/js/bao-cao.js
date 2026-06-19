/**
 * Báo cáo tổng kết — OAuth-gated download (chặn THẬT qua backend FastAPI).
 *
 * Khác bản cũ (UX-gate bằng PAT sessionStorage): report .md KHÔNG còn nằm trong
 * repo public. Nội dung lưu Redis trên backend, chỉ tải được qua endpoint
 * /reports/* sau khi /auth/me xác thực session OAuth GitHub + email whitelist.
 *
 * Flow:
 *   1. Đọc sid (#sid=... sau OAuth callback, hoặc sessionStorage 'zola-cms-session-id')
 *   2. /auth/me (Bearer sid) → guest hay admin
 *   3. Admin → GET /reports (list) + tải qua GET /reports/{file} → Blob download
 *   4. Guest → chỉ hiện banner + nút "Đăng nhập GitHub"
 */
(function () {
  "use strict";

  const SESSION_KEY = "zola-cms-session-id"; // giống editor.js

  const AUTH_API = (function () {
    const m1 = document.querySelector('meta[name="vipzone-auth-api"]');
    if (m1 && m1.getAttribute("content")) return m1.getAttribute("content");
    return "https://blog-vipzone-api.onrender.com";
  })().replace(/\/$/, "");

  // ---------- session id helpers ----------
  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; }
  }
  function setSid(s) { try { sessionStorage.setItem(SESSION_KEY, s); localStorage.setItem(SESSION_KEY, s); } catch (e) {} }
  function clearSid() { try { sessionStorage.removeItem(SESSION_KEY); localStorage.removeItem(SESSION_KEY); } catch (e) {} }

  function consumeUrlHashSid() {
    if (!location.hash) return;
    const m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  function fmtDate(iso) {
    if (!iso) return "";
    return (window.ZolaDateTime && window.ZolaDateTime.formatDisplayDateTime(iso)) || String(iso);
  }

  async function api(path, opts) {
    const sid = getSid();
    return fetch(AUTH_API + path, Object.assign({
      headers: { "Authorization": "Bearer " + sid },
      credentials: "omit",
      cache: "no-store",
    }, opts || {}));
  }

  async function fetchMe() {
    if (!getSid()) return null;
    try {
      const res = await api("/auth/me");
      if (res.status === 401) { clearSid(); return null; }
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  // ---------- download ----------
  async function downloadReport(filename, btn) {
    const old = btn ? btn.textContent : "";
    if (btn) { btn.textContent = "⏳ Đang tải…"; btn.disabled = true; }
    try {
      const res = await api("/reports/" + encodeURIComponent(filename));
      if (res.status === 401) { clearSid(); render(null); return; }
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      const blob = new Blob([data.content || ""], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Không tải được report: " + e.message);
    } finally {
      if (btn) { btn.textContent = old; btn.disabled = false; }
    }
  }

  // ---------- render ----------
  function render(user) {
    const anon = document.querySelector("[data-auth-anon]");
    const admin = document.querySelector("[data-auth-admin]");
    const listWrap = document.querySelector("[data-reports]");
    const isAdmin = !!(user && user.email);

    if (anon) anon.hidden = isAdmin;
    if (admin) admin.hidden = !isAdmin;
    if (!listWrap) return;

    if (!isAdmin) {
      listWrap.innerHTML =
        '<p class="bao-cao__empty">🔒 Đăng nhập admin để xem và tải báo cáo.</p>';
      return;
    }
    listWrap.innerHTML = '<p class="bao-cao__empty">Đang tải danh sách báo cáo…</p>';
    loadReports(listWrap);
  }

  async function loadReports(listWrap) {
    let data;
    try {
      const res = await api("/reports");
      if (res.status === 401) { clearSid(); render(null); return; }
      if (!res.ok) throw new Error("HTTP " + res.status);
      data = await res.json();
    } catch (e) {
      listWrap.innerHTML =
        '<p class="bao-cao__empty">⚠ Không tải được danh sách (backend offline?).</p>';
      return;
    }
    const reports = (data && data.reports) || [];
    if (reports.length === 0) {
      listWrap.innerHTML =
        '<p class="bao-cao__empty">Chưa có báo cáo nào. Gõ <code>??</code> trong chat để tạo.</p>';
      return;
    }

    const latest = reports[0];
    let html =
      '<article class="bao-cao__latest">' +
      '<header class="bao-cao__latest-head">' +
      '<h3 class="bao-cao__latest-title">Báo cáo mới nhất</h3>' +
      '<time class="bao-cao__latest-date">' + escapeHtml(fmtDate(latest.created_at)) + "</time>" +
      "</header>" +
      '<div class="bao-cao__latest-body">' + escapeHtml(latest.preview || "") + "…</div>" +
      '<button type="button" class="bao-cao__download" data-dl="' + escapeHtml(latest.filename) + '">' +
      "⬇ Tải file <code>" + escapeHtml(latest.filename) + "</code></button>" +
      "</article>";

    html +=
      '<section class="bao-cao__history">' +
      '<h3 class="bao-cao__history-title">Lịch sử báo cáo (' + reports.length + ")</h3><ul class=\"bao-cao__list\">";
    reports.forEach((r) => {
      html +=
        '<li class="bao-cao__item">' +
        '<span class="bao-cao__item-name"><code>' + escapeHtml(r.filename) + "</code></span>" +
        '<span class="bao-cao__item-date">' + escapeHtml(fmtDate(r.created_at)) + "</span>" +
        '<button type="button" class="bao-cao__item-download" data-dl="' + escapeHtml(r.filename) + '" title="Tải về">⬇</button>' +
        "</li>";
    });
    html += "</ul></section>";
    listWrap.innerHTML = html;

    listWrap.querySelectorAll("[data-dl]").forEach((btn) => {
      btn.addEventListener("click", () => downloadReport(btn.getAttribute("data-dl"), btn));
    });
  }

  // ---------- login ----------
  function wireLogin() {
    const btn = document.querySelector("[data-action='login']");
    if (!btn) return;
    btn.addEventListener("click", () => {
      if (!AUTH_API) { alert("Backend auth chưa cấu hình."); return; }
      location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(location.pathname);
    });
  }

  // ---------- init ----------
  consumeUrlHashSid();
  wireLogin();
  fetchMe().then(render);
})();
