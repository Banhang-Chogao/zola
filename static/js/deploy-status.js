/**
 * Deploy status — fetch real-time GitHub Pages deployment state, update
 * mọi [data-deploy-status] element trên page (header banner + changelog card).
 *
 * Target HTML elements (data-* attrs, optional, render skip nếu không có):
 *   [data-deploy-status]  → root container (1 hoặc nhiều element), get state class
 *   [data-deploy-badge]   → badge label trong header (e.g. "✓ DEPLOYED")
 *   [data-deploy-text]    → message text trong header
 *   [data-deploy-icon]    → icon text/symbol trong card (✓, ⚙, ⏳, ✗)
 *   [data-deploy-verb]    → verb trong card (e.g. "deployed", "deploying")
 *   [data-deploy-time]    → relative time element
 *
 * Static fallback: nếu fetch fail (offline, rate-limited, CSP), HTML baked
 * sẵn '✓ DEPLOYED' giữ nguyên — không phá UX.
 *
 * Quota: 60/h unauth GitHub API. sessionStorage cache 60s → max 1 call/min/
 * visitor → ~60/h khớp hạn mức.
 *
 * Performance: 2 API call serial sau initial load, defer script không block
 * page parse, render qua textContent (zero XSS, zero reflow).
 */
(function () {
  "use strict";

  const REPO = "Banhang-Chogao/zola";
  const ENV = "github-pages";
  const CACHE_KEY = "zola-deploy-status-cache";
  const CACHE_TTL = 60 * 1000;

  const containers = document.querySelectorAll("[data-deploy-status]");
  if (!containers.length) return;

  const STATES = {
    success:     { label: "✓ DEPLOYED",   isSuccess: true,  msg: "Build hiện tại đã deploy lên GitHub Pages", icon: "✓", verb: "deployed",  cls: "is-success" },
    in_progress: { label: "⚙ PROCESSING", isSuccess: false, msg: "Build đang chạy trên GitHub Actions",       icon: "⚙", verb: "deploying", cls: "is-progress" },
    queued:      { label: "⏳ QUEUED",    isSuccess: false, msg: "Build đang xếp hàng chờ runner",            icon: "⏳", verb: "queued",    cls: "is-queued"   },
    pending:     { label: "⏳ PENDING",   isSuccess: false, msg: "Build sắp khởi chạy",                       icon: "⏳", verb: "pending",   cls: "is-queued"   },
    waiting:     { label: "⏳ WAITING",   isSuccess: false, msg: "Đang đợi điều kiện trigger",                icon: "⏳", verb: "waiting",   cls: "is-queued"   },
    failure:     { label: "✗ FAILED",    isSuccess: false, msg: "Build/deploy fail — check Actions log",     icon: "✗", verb: "failed",    cls: "is-error"    },
    error:       { label: "✗ ERROR",     isSuccess: false, msg: "Deploy error — check Actions log",          icon: "✗", verb: "errored",   cls: "is-error"    },
    inactive:    { label: "○ INACTIVE",  isSuccess: false, msg: "Deployment inactive (rolled back)",         icon: "○", verb: "inactive",  cls: "is-queued"   },
  };

  const STATE_CLASSES = ["is-success", "is-progress", "is-queued", "is-error"];

  function timeAgo(iso) {
    if (!iso) return "";
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return Math.max(0, Math.floor(diff)) + "s ago";
    if (diff < 3600) {
      const m = Math.floor(diff / 60);
      return m + (m === 1 ? " minute ago" : " minutes ago");
    }
    if (diff < 86400) {
      const h = Math.floor(diff / 3600);
      return h + (h === 1 ? " hour ago" : " hours ago");
    }
    const d = Math.floor(diff / 86400);
    return d + (d === 1 ? " day ago" : " days ago");
  }

  function renderInto(container, cfg, updatedAt) {
    // State class trên container (cho variant styling)
    STATE_CLASSES.forEach((c) => container.classList.remove(c));
    container.classList.add(cfg.cls);

    // Header banner format
    const badge = container.querySelector("[data-deploy-badge]");
    if (badge) {
      badge.textContent = cfg.label;
      badge.classList.toggle("deploy-queue__badge--success", cfg.isSuccess);
    }
    const text = container.querySelector("[data-deploy-text]");
    if (text) {
      const time = updatedAt ? " · " + timeAgo(updatedAt) : "";
      text.textContent = cfg.msg + time;
    }

    // Card format (changelog)
    const icon = container.querySelector("[data-deploy-icon]");
    if (icon) icon.textContent = cfg.icon;
    const verb = container.querySelector("[data-deploy-verb]");
    if (verb) verb.textContent = cfg.verb;
    const time = container.querySelector("[data-deploy-time]");
    if (time) time.textContent = updatedAt ? timeAgo(updatedAt) : "—";
  }

  function render(state, updatedAt) {
    const cfg = STATES[state] || {
      label: String(state).toUpperCase(), isSuccess: false,
      msg: "Unknown state", icon: "?", verb: "in state " + state, cls: "is-queued",
    };
    containers.forEach((c) => renderInto(c, cfg, updatedAt));
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
      const dRes = await fetch(
        "https://api.github.com/repos/" + REPO + "/deployments?environment=" + ENV + "&per_page=1",
        { headers: { Accept: "application/vnd.github+json" } }
      );
      if (!dRes.ok) {
        if (dRes.status === 403) {
          console.warn("[Deploy] Rate limited — giữ static");
          return;
        }
        throw new Error("HTTP " + dRes.status);
      }
      const deployments = await dRes.json();
      if (!deployments.length) return;

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
    }
  }

  fetchStatus();
})();
