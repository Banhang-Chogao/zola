/**
 * Changelog fetch — load admin-gated changelog data from VIPZone backend.
 * Requires GitHub OAuth session (CMS auth). Falls back to login if not authenticated.
 */
(function () {
  "use strict";

  const VIPZONE_API = "https://blog-vipzone-api.onrender.com";
  const AUTH_API = "https://blog-vipzone-api.onrender.com";

  const loader = document.querySelector("[data-changelog-loader]");
  const error = document.querySelector("[data-changelog-error]");
  const errorText = document.querySelector("[data-error-text]");
  const list = document.querySelector("[data-changelog-list]");
  const template = document.querySelector("[data-changelog-template]");

  if (!loader || !list || !template) {
    console.warn("[changelog] Required elements not found");
    return;
  }

  function formatDate(isoDate) {
    try {
      const d = new Date(isoDate);
      const day = String(d.getDate()).padStart(2, "0");
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const year = d.getFullYear();
      return `${day}-${month}-${year}`;
    } catch (e) {
      return isoDate;
    }
  }

  function renderEntry(item, index) {
    const node = template.content.cloneNode(true);
    const li = node.querySelector("li");
    const titleEl = node.querySelector("[data-title]");
    const tagEl = node.querySelector("[data-tag]");
    const highlightsEl = node.querySelector("[data-highlights]");
    const dateEl = node.querySelector("[data-date]");
    const prLink = node.querySelector("[data-pr-link]");
    const statsEl = node.querySelector("[data-stats]");

    if (li) li.setAttribute("data-entry-id", item.id || "");
    if (titleEl) titleEl.textContent = item.title || "";
    if (tagEl) {
      tagEl.textContent = item.tag || "chore";
      tagEl.className = `changelog__tag changelog__tag--${item.tag || "chore"}`;
    }

    // Highlights
    if (highlightsEl && item.highlights && item.highlights.length) {
      highlightsEl.innerHTML = "";
      item.highlights.forEach((h) => {
        const li = document.createElement("li");
        li.textContent = h;
        highlightsEl.appendChild(li);
      });
    } else if (highlightsEl) {
      highlightsEl.hidden = true;
    }

    // Date
    if (dateEl) {
      dateEl.textContent = formatDate(item.date);
      dateEl.setAttribute("datetime", item.date);
    }

    // PR link
    if (prLink && item.pr) {
      prLink.textContent = `PR #${item.pr}`;
      prLink.href = `https://github.com/Banhang-Chogao/zola/pull/${item.pr}`;
      prLink.hidden = false;
    }

    // Stats
    const added = item.lines_added || 0;
    const removed = item.lines_removed || 0;
    const net = added - removed;
    if (added > 0 || removed > 0) {
      const statsHtml = `
        <span class="changelog__stats-rem">−${removed} dòng xóa</span>
        <span class="changelog__stats-dot">·</span>
        <span class="changelog__stats-add">+${added} dòng thêm</span>
        <span class="changelog__stats-dot">·</span>
        <span class="changelog__stats-net">Net ${net >= 0 ? "+" : ""}${net} dòng</span>
      `;
      if (statsEl) {
        statsEl.innerHTML = statsHtml;
        statsEl.hidden = false;
      }
    }

    return node;
  }

  async function loadChangelog() {
    loader.hidden = false;
    list.hidden = true;
    if (error) error.hidden = true;

    try {
      // Get session ID from sessionStorage (set by CMS auth flow)
      const sid = sessionStorage.getItem("zola-cms-session-id");
      if (!sid) {
        throw new Error("Not authenticated");
      }

      // Fetch changelog from backend
      const res = await fetch(`${VIPZONE_API}/api/vipzone/admin/changelog`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${sid}`,
          "Content-Type": "application/json",
        },
        credentials: "omit",
      });

      if (res.status === 401 || res.status === 403) {
        throw new Error("Access denied — please log in as admin");
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const data = await res.json();
      if (!data.items || !Array.isArray(data.items)) {
        throw new Error("Invalid response format");
      }

      // Render list
      list.innerHTML = "";
      if (data.items.length === 0) {
        list.innerHTML = '<li class="changelog__empty">Chưa có entry nào.</li>';
      } else {
        data.items.forEach((item, i) => {
          const node = renderEntry(item, i);
          list.appendChild(node);
        });
      }

      loader.hidden = true;
      list.hidden = false;
    } catch (err) {
      console.error("[changelog] Load failed:", err.message);
      loader.hidden = true;

      if (error) {
        if (errorText) {
          errorText.textContent = err.message || "Failed to load changelog data";
        }
        error.hidden = false;
      }

      // Show empty state if no error element
      if (!error) {
        list.innerHTML = '<li class="changelog__empty">Lỗi tải dữ liệu. Bạn có thể cần đăng nhập.</li>';
        list.hidden = false;
      }
    }
  }

  // Load on page load
  loadChangelog();
})();
