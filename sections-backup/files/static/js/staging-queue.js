/**
 * Staging Queue widget — fetch open PRs từ GitHub API + render vào widget
 * trên trang Changelog. Phân biệt rõ với entries đã deployed (changelog.json).
 *
 * Target: [data-staging-queue] root. Skip silently nếu không có element.
 *
 * Quota: 60/h unauth GitHub API. sessionStorage cache 60s → max 1 call/min/
 * visitor → khớp hạn mức (như deploy-status.js).
 *
 * Render: textContent only → zero XSS. Empty-state fallback nếu fetch fail.
 */
(function () {
  "use strict";

  const REPO = "Banhang-Chogao/zola";
  const CACHE_KEY = "zola-staging-queue-cache";
  const CACHE_TTL = 60 * 1000;
  const MAX_PRS = 10;

  const root = document.querySelector("[data-staging-queue]");
  if (!root) return;

  const listEl = root.querySelector("[data-staging-list]");
  const countEl = root.querySelector("[data-staging-count]");
  const emptyEl = root.querySelector("[data-staging-empty]");
  const tpl = root.querySelector("[data-staging-template]");
  if (!listEl || !countEl || !tpl) return;

  function fmtWait(iso) {
    if (!iso) return "";
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return "chờ " + Math.max(0, Math.floor(diff)) + " giây";
    if (diff < 3600) return "chờ " + Math.floor(diff / 60) + " phút";
    if (diff < 86400) return "chờ " + Math.floor(diff / 3600) + " giờ";
    const d = Math.floor(diff / 86400);
    return "chờ " + d + " ngày";
  }

  function truncate(s, n) {
    if (!s) return "";
    const t = String(s).trim();
    return t.length <= n ? t : t.slice(0, n - 1) + "…";
  }

  function clearList() {
    while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
  }

  function render(prs) {
    clearList();
    countEl.textContent = String(prs.length);
    root.hidden = false;

    if (!prs.length) {
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;

    prs.forEach(function (pr) {
      const node = tpl.content.cloneNode(true);
      const titleEl = node.querySelector("[data-pr-title]");
      const bodyEl = node.querySelector("[data-pr-body]");
      const linkEl = node.querySelector("[data-pr-link]");
      const authorEl = node.querySelector("[data-pr-author]");
      const waitEl = node.querySelector("[data-pr-wait]");

      if (titleEl) titleEl.textContent = pr.title || "(no title)";
      if (bodyEl) bodyEl.textContent = truncate(pr.body || "", 160);
      if (linkEl) {
        linkEl.textContent = "PR #" + pr.number;
        linkEl.href = pr.html_url;
      }
      if (authorEl) authorEl.textContent = "@" + (pr.user && pr.user.login ? pr.user.login : "unknown");
      if (waitEl) {
        waitEl.textContent = fmtWait(pr.created_at);
        waitEl.setAttribute("datetime", pr.created_at || "");
      }
      listEl.appendChild(node);
    });
  }

  function readCache() {
    try {
      const raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (Date.now() - data.fetched_at > CACHE_TTL) return null;
      return data.prs;
    } catch (e) { return null; }
  }

  function writeCache(prs) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({
        fetched_at: Date.now(), prs: prs,
      }));
    } catch (e) { /* sessionStorage disabled — skip */ }
  }

  async function fetchOpenPRs() {
    const cached = readCache();
    if (cached) {
      render(cached);
      return;
    }
    try {
      const url = "https://api.github.com/repos/" + REPO +
        "/pulls?state=open&sort=created&direction=desc&per_page=" + MAX_PRS;
      const res = await fetch(url, {
        headers: { Accept: "application/vnd.github+json" }
      });
      if (!res.ok) {
        if (res.status === 403) {
          console.warn("[StagingQueue] Rate limited — hide widget");
          return;
        }
        throw new Error("HTTP " + res.status);
      }
      const raw = await res.json();
      const prs = raw.map(function (pr) {
        return {
          number: pr.number,
          title: pr.title,
          body: pr.body || "",
          html_url: pr.html_url,
          created_at: pr.created_at,
          user: { login: pr.user && pr.user.login ? pr.user.login : "unknown" },
        };
      });
      render(prs);
      writeCache(prs);
    } catch (e) {
      console.warn("[StagingQueue] Fetch failed:", e.message);
    }
  }

  fetchOpenPRs();
})();
