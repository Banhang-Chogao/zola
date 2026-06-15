/**
 * Deploy status — fetch real-time GitHub Pages deployment state, update
 * .deploy-queue trong header (base.html) trên mọi page.
 *
 * Target HTML elements (data-* attrs):
 *   [data-deploy-status]  → root container, get classes toggled
 *   [data-deploy-badge]   → badge label (e.g. "✓ DEPLOYED")
 *   [data-deploy-text]    → message text (e.g. "Build hiện tại đã deploy…")
 *
 * Static fallback: nếu fetch fail (offline, rate-limited, CSP), HTML
 * baked sẵn "✓ DEPLOYED" giữ nguyên — không phá UX.
 *
 * Quota: 60/h unauth GitHub API. sessionStorage cache 60s → max 1 call/
 * min/visitor → ~60/h khớp hạn mức.
 */
(function () {
  "use strict";

  const REPO = "Banhang-Chogao/zola";
  const ENV = "github-pages";
  const CACHE_KEY = "zola-deploy-status-cache";
  const CACHE_TTL = 60 * 1000;

  const container = document.querySelector("[data-deploy-status]");
  if (!container) return;
  const badge = container.querySelector("[data-deploy-badge]");
  const text = container.querySelector("[data-deploy-text]");
  if (!badge || !text) return;

  const STATES = {
    success:     { label: "✓ DEPLOYED",   isSuccess: true,  msg: "Build hiện tại đã deploy lên GitHub Pages" },
    in_progress: { label: "⚙ PROCESSING", isSuccess: false, msg: "Build đang chạy trên GitHub Actions" },
    queued:      { label: "⏳ QUEUED",    isSuccess: false, msg: "Build đang xếp hàng chờ runner" },
    pending:     { label: "⏳ PENDING",   isSuccess: false, msg: "Build sắp khởi chạy" },
    waiting:     { label: "⏳ WAITING",   isSuccess: false, msg: "Đang đợi điều kiện trigger" },
    failure:     { label: "✗ FAILED",    isSuccess: false, msg: "Build/deploy fail — check Actions log" },
    error:       { label: "✗ ERROR",     isSuccess: false, msg: "Deploy error — check Actions log" },
    inactive:    { label: "○ INACTIVE",  isSuccess: false, msg: "Deployment inactive (rolled back)" },
  };

  function timeAgo(iso) {
    if (!iso) return "";
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return Math.max(0, Math.floor(diff)) + "s trước";
    if (diff < 3600) return Math.floor(diff / 60) + " phút trước";
    if (diff < 86400) return Math.floor(diff / 3600) + " giờ trước";
    return Math.floor(diff / 86400) + " ngày trước";
  }

  function render(state, updatedAt) {
    const cfg = STATES[state] || { label: String(state).toUpperCase(), isSuccess: false, msg: "Unknown state" };
    badge.textContent = cfg.label;
    badge.classList.toggle("deploy-queue__badge--success", cfg.isSuccess);
    const time = updatedAt ? " · " + timeAgo(updatedAt) : "";
    text.textContent = cfg.msg + time;
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

  function writeCache(state, updatedAt) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({
        fetched_at: Date.now(), state: state, updatedAt: updatedAt,
      }));
    } catch (e) { /* sessionStorage disabled — skip */ }
  }

  async function fetchStatus() {
    const cached = readCache();
    if (cached) {
      render(cached.state, cached.updatedAt);
      return;
    }
    try {
      // 1. Lấy deployment mới nhất cho env github-pages
      const dRes = await fetch(
        "https://api.github.com/repos/" + REPO + "/deployments?environment=" + ENV + "&per_page=1",
        { headers: { Accept: "application/vnd.github+json" } }
      );
      if (!dRes.ok) {
        if (dRes.status === 403) {
          console.warn("[Deploy] Rate limited — giữ static badge");
          return;
        }
        throw new Error("HTTP " + dRes.status);
      }
      const deployments = await dRes.json();
      if (!deployments.length) return;

      // 2. Lấy status mới nhất của deployment đó
      const sRes = await fetch(deployments[0].statuses_url + "?per_page=1", {
        headers: { Accept: "application/vnd.github+json" }
      });
      if (!sRes.ok) throw new Error("HTTP " + sRes.status);
      const statuses = await sRes.json();
      if (!statuses.length) return;

      const latest = statuses[0];
      render(latest.state, latest.updated_at);
      writeCache(latest.state, latest.updated_at);
    } catch (e) {
      console.warn("[Deploy] Status fetch failed:", e.message);
      // Static fallback giữ nguyên
    }
  }

  fetchStatus();
})();
