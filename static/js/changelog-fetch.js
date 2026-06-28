/**
 * Changelog fetch — load public changelog data from file-based changelog.json.
 * Public users can view entries. No admin authentication needed — changelog is public.
 */
(function () {
  "use strict";

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
      return `${day}/${month}/${year}`;
    } catch (e) {
      return isoDate;
    }
  }

  function renderEntry(item) {
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
        <span class="changelog__stats-rem">\u2212${removed} d\xf2ng x\xf3a</span>
        <span class="changelog__stats-dot">\xb7</span>
        <span class="changelog__stats-add">+${added} d\xf2ng th\xeam</span>
        <span class="changelog__stats-dot">\xb7</span>
        <span class="changelog__stats-net">Net ${net >= 0 ? "+" : ""}${net} d\xf2ng</span>
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
      const res = await fetch("/changelog.json", {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        credentials: "omit",
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      if (!data || !Array.isArray(data)) {
        throw new Error("Invalid response format");
      }

      // Sort by date descending (newest first)
      data.sort((a, b) => new Date(b.date) - new Date(a.date));

      // Render list
      list.innerHTML = "";
      if (data.length === 0) {
        list.innerHTML = '<li class="changelog__empty">Ch\u01b0a c\xf3 entry n\xe0o.</li>';
      } else {
        data.forEach((item) => {
          const node = renderEntry(item);
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

      if (!error) {
        list.innerHTML = '<li class="changelog__empty">L\u1ed7i t\u1ea3i d\u1eef li\u1ec7u.</li>';
        list.hidden = false;
      }
    }
  }

  // Load on page load
  loadChangelog();
})();
