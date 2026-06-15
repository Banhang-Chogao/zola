/**
 * Changelog deploy status — fetch real-time GitHub Pages deployment state.
 *
 * Quota: 60 req/h unauthenticated GitHub API. Cache sessionStorage 60s →
 * 1 call/min/visitor tối đa → ~60/h khớp hạn mức, an toàn.
 *
 * Hiển thị: queued / processing / done / failed + timestamp tương đối.
 * Silent fail nếu offline hoặc rate-limited — UI fallback 'Status N/A'.
 */
(function () {
  "use strict";

  const REPO = "Banhang-Chogao/zola";
  const ENV = "github-pages";
  const CACHE_KEY = "zola-deploy-status-cache";
  const CACHE_TTL = 60 * 1000; // 60s

  const container = document.querySelector("[data-deploy-status]");
  if (!container) return;

  // Map GitHub deployment_status state → UI config
  // GitHub states: queued, pending, in_progress, waiting, success, failure, error, inactive
  const STATES = {
    queued:      { label: "QUEUED",      color: "queued",   icon: "⏳" },
    pending:     { label: "PENDING",     color: "queued",   icon: "⏳" },
    waiting:     { label: "WAITING",     color: "queued",   icon: "⏳" },
    in_progress: { label: "PROCESSING",  color: "progress", icon: "⚙" },
    success:     { label: "DONE",        color: "success",  icon: "✓" },
    failure:     { label: "FAILED",      color: "error",    icon: "✗" },
    error:       { label: "ERROR",       color: "error",    icon: "✗" },
    inactive:    { label: "INACTIVE",    color: "neutral",  icon: "○" },
  };

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function timeAgo(iso) {
    if (!iso) return "";
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return Math.max(0, Math.floor(diff)) + "s trước";
    if (diff < 3600) return Math.floor(diff / 60) + " phút trước";
    if (diff < 86400) return Math.floor(diff / 3600) + " giờ trước";
    return Math.floor(diff / 86400) + " ngày trước";
  }

  function render(state, updatedAt, deploymentUrl) {
    const cfg = STATES[state] || { label: String(state).toUpperCase(), color: "neutral", icon: "?" };
    container.className = "changelog__deploy changelog__deploy--" + cfg.color;
    const linkOpen = deploymentUrl ? '<a class="changelog__deploy-link" href="' + escapeHtml(deploymentUrl) + '" target="_blank" rel="noopener">' : '';
    const linkClose = deploymentUrl ? '</a>' : '';
    container.innerHTML =
      linkOpen +
      '<span class="changelog__deploy-icon" aria-hidden="true">' + cfg.icon + '</span>' +
      '<span class="changelog__deploy-label">DEPLOY:</span>' +
      '<span class="changelog__deploy-state">' + cfg.label + '</span>' +
      '<span class="changelog__deploy-time">' + escapeHtml(timeAgo(updatedAt)) + '</span>' +
      linkClose;
  }

  function renderUnknown(reason) {
    container.className = "changelog__deploy changelog__deploy--neutral";
    container.innerHTML =
      '<span class="changelog__deploy-icon" aria-hidden="true">○</span>' +
      '<span class="changelog__deploy-label">DEPLOY:</span>' +
      '<span class="changelog__deploy-state">N/A</span>' +
      '<span class="changelog__deploy-time">' + escapeHtml(reason || "không tải được") + '</span>';
  }

  function readCache() {
    try {
      const raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (Date.now() - data.fetched_at > CACHE_TTL) return null;
      return data;
    } catch (e) { return null; }
  }

  function writeCache(payload) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(
        Object.assign({ fetched_at: Date.now() }, payload)
      ));
    } catch (e) { /* sessionStorage disabled — skip */ }
  }

  async function fetchStatus() {
    const cached = readCache();
    if (cached) {
      render(cached.state, cached.updatedAt, cached.deploymentUrl);
      return;
    }

    try {
      // 1. Lấy deployment mới nhất cho env github-pages
      const dRes = await fetch(
        "https://api.github.com/repos/" + REPO + "/deployments?environment=" + ENV + "&per_page=1",
        { headers: { Accept: "application/vnd.github+json" } }
      );
      if (!dRes.ok) {
        if (dRes.status === 403) return renderUnknown("rate limited");
        throw new Error("HTTP " + dRes.status);
      }
      const deployments = await dRes.json();
      if (!deployments.length) return renderUnknown("không có deployment");
      const dep = deployments[0];

      // 2. Lấy status mới nhất của deployment đó
      const sRes = await fetch(dep.statuses_url + "?per_page=1", {
        headers: { Accept: "application/vnd.github+json" }
      });
      if (!sRes.ok) throw new Error("HTTP " + sRes.status);
      const statuses = await sRes.json();
      if (!statuses.length) return renderUnknown("chưa có status");
      const latest = statuses[0];

      const deploymentUrl = "https://github.com/" + REPO + "/deployments/" + ENV;
      render(latest.state, latest.updated_at, deploymentUrl);
      writeCache({ state: latest.state, updatedAt: latest.updated_at, deploymentUrl: deploymentUrl });
    } catch (e) {
      console.warn("[Changelog] Deploy status fetch failed:", e.message);
      renderUnknown(e.message);
    }
  }

  fetchStatus();
})();
