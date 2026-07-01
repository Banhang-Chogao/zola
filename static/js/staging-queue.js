/**
 * Staging Queue widget — fetch open PRs từ GitHub API + render vào widget
 * trên trang Changelog. Phân biệt rõ với entries đã deployed (changelog.json).
 *
 * Target: [data-staging-queue] root. Skip silently nếu không có element.
 *
 * Quota: 60/h unauth GitHub API. sessionStorage cache 60s → max 1 call/min/
 * visitor → khớp hạn mức (như deploy-status.js).
 *
 * Pagination: 10 items/trang. Ẩn pagination nếu ≤ 10 PRs.
 *
 * Render: textContent only → zero XSS. Empty-state fallback nếu fetch fail.
 */
(function () {
  "use strict";

  var REPO = "Banhang-Chogao/zola";
  var CACHE_KEY = "zola-staging-queue-cache";
  var CACHE_TTL = 60 * 1000;
  var PAGE_SIZE = 10;
  var MAX_PRS = 50;

  var root = document.querySelector("[data-staging-queue]");
  if (!root) return;

  var listEl = root.querySelector("[data-staging-list]");
  var countEl = root.querySelector("[data-staging-count]");
  var emptyEl = root.querySelector("[data-staging-empty]");
  var tpl = root.querySelector("[data-staging-template]");
  var paginationEl = root.querySelector("[data-staging-pagination]");
  var prevBtn = paginationEl && paginationEl.querySelector("[data-staging-prev]");
  var nextBtn = paginationEl && paginationEl.querySelector("[data-staging-next]");
  var pageNumbersEl = paginationEl && paginationEl.querySelector("[data-staging-page-numbers]");
  var pageStatusEl = paginationEl && paginationEl.querySelector("[data-staging-page-status]");
  if (!listEl || !countEl || !tpl) return;

  var prs = [];
  var currentPage = 1;
  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function fmtWait(iso) {
    if (!iso) return "";
    var diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return "chờ " + Math.max(0, Math.floor(diff)) + " giây";
    if (diff < 3600) return "chờ " + Math.floor(diff / 60) + " phút";
    if (diff < 86400) return "chờ " + Math.floor(diff / 3600) + " giờ";
    var d = Math.floor(diff / 86400);
    return "chờ " + d + " ngày";
  }

  function truncate(s, n) {
    if (!s) return "";
    var t = String(s).trim();
    return t.length <= n ? t : t.slice(0, n - 1) + "\u2026";
  }

  function clearList() {
    while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
  }

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderItem(pr) {
    var node = tpl.content.cloneNode(true);
    var titleEl = node.querySelector("[data-pr-title]");
    var bodyEl = node.querySelector("[data-pr-body]");
    var linkEl = node.querySelector("[data-pr-link]");
    var authorEl = node.querySelector("[data-pr-author]");
    var waitEl = node.querySelector("[data-pr-wait]");

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
    return node;
  }

  function renderPageNumbers() {
    if (!pageNumbersEl) return;
    var total = Math.max(1, Math.ceil(prs.length / PAGE_SIZE));
    pageNumbersEl.replaceChildren();
    var start = Math.max(1, currentPage - 2);
    var end = Math.min(total, currentPage + 2);
    for (var page = start; page <= end; page += 1) {
      var btn = element("button", "staging-queue__page-number", String(page));
      btn.type = "button";
      btn.setAttribute("aria-label", "Trang " + page);
      if (page === currentPage) {
        btn.classList.add("is-current");
        btn.setAttribute("aria-current", "page");
      }
      btn.addEventListener("click", (function (p) {
        return function () { showPage(p, true); };
      })(page));
      pageNumbersEl.appendChild(btn);
    }
  }

  function showPage(page, scroll) {
    var total = Math.max(1, Math.ceil(prs.length / PAGE_SIZE));
    currentPage = Math.min(Math.max(1, page), total);
    var start = (currentPage - 1) * PAGE_SIZE;

    clearList();
    for (var i = start; i < start + PAGE_SIZE && i < prs.length; i += 1) {
      listEl.appendChild(renderItem(prs[i]));
    }

    countEl.textContent = String(prs.length);
    root.hidden = false;

    if (emptyEl) emptyEl.hidden = prs.length > 0;

    if (prevBtn) prevBtn.disabled = currentPage === 1;
    if (nextBtn) nextBtn.disabled = currentPage === total;
    renderPageNumbers();
    if (pageStatusEl) {
      pageStatusEl.textContent = "Trang " + currentPage + " / " + total + " \xb7 " + prs.length + " PR";
    }
    if (paginationEl) {
      paginationEl.hidden = total <= 1;
    }
    if (scroll) {
      var behavior = prefersReducedMotion ? "instant" : "smooth";
      root.scrollIntoView({ behavior: behavior, block: "start" });
    }
  }

  function readCache() {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (Date.now() - data.fetched_at > CACHE_TTL) return null;
      return data.prs;
    } catch (e) { return null; }
  }

  function writeCache(data) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({
        fetched_at: Date.now(), prs: data,
      }));
    } catch (e) { /* sessionStorage disabled */ }
  }

  function initPageButtons() {
    if (prevBtn) {
      prevBtn.addEventListener("click", function () { showPage(currentPage - 1, true); });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () { showPage(currentPage + 1, true); });
    }
  }

  async function fetchOpenPRs() {
    var cached = readCache();
    if (cached) {
      prs = cached;
      showPage(1, false);
      return;
    }
    try {
      var url = "https://api.github.com/repos/" + REPO +
        "/pulls?state=open&sort=created&direction=desc&per_page=" + MAX_PRS;
      var res = await fetch(url, {
        headers: { Accept: "application/vnd.github+json" }
      });
      if (!res.ok) {
        if (res.status === 403) {
          console.warn("[StagingQueue] Rate limited");
          return;
        }
        throw new Error("HTTP " + res.status);
      }
      var raw = await res.json();
      prs = raw.map(function (pr) {
        return {
          number: pr.number,
          title: pr.title,
          body: pr.body || "",
          html_url: pr.html_url,
          created_at: pr.created_at,
          user: { login: pr.user && pr.user.login ? pr.user.login : "unknown" },
        };
      });
      showPage(1, false);
      writeCache(prs);
    } catch (e) {
      console.warn("[StagingQueue] Fetch failed:", e.message);
    }
  }

  initPageButtons();
  fetchOpenPRs();
})();
