(function () {
  const root = document.querySelector("[data-pr-sentinel]");
  if (!root) return;

  const list = root.querySelector("[data-pr-list]");
  const kpis = root.querySelectorAll("[data-kpi]");
  const filters = root.querySelectorAll("[data-filter]");
  let items = [];

  const esc = (value) => String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));

  function stateLabel(pr) {
    if (pr.is_draft) return "draft";
    if (pr.state === "success") return "passing";
    if (pr.state === "failure") return "failing";
    if (pr.state === "pending") return "pending";
    return "unknown";
  }

  function render(filter) {
    const shown = items.filter((pr) => {
      if (filter === "all") return true;
      if (filter === "draft") return pr.is_draft;
      return pr.state === filter;
    });

    if (!shown.length) {
      list.innerHTML = '<p class="pr-sentinel-empty">Không có PR phù hợp bộ lọc này.</p>';
      return;
    }

    list.innerHTML = shown.map((pr) => `
      <article class="pr-sentinel-card pr-state-${esc(pr.state)}">
        <div class="pr-sentinel-card-main">
          <p class="pr-sentinel-meta">#${esc(pr.number)} · ${esc(pr.author)} · ${esc(pr.branch)} → ${esc(pr.base)}</p>
          <h2><a href="${esc(pr.url)}" target="_blank" rel="noopener">${esc(pr.title)}</a></h2>
          <p class="pr-sentinel-checks">
            ${esc(pr.checks.success)} pass · ${esc(pr.checks.failure)} fail · ${esc(pr.checks.pending)} pending · ${esc(pr.checks.skipped)} skipped
          </p>
        </div>
        <span class="pr-sentinel-badge">${esc(stateLabel(pr))}</span>
      </article>
    `).join("");
  }

  fetch("/data/pr-sentinel.json")
    .then((response) => response.json())
    .then((data) => {
      items = data.items || [];

      kpis.forEach((el) => {
        const key = el.dataset.kpi;
        el.textContent = data.summary && data.summary[key] !== undefined
          ? data.summary[key]
          : 0;
      });

      if (data.error) {
        list.innerHTML = `<p class="pr-sentinel-empty">PR Sentinel đang dùng fallback vì chưa đọc được GitHub CLI.</p>`;
        return;
      }

      render("all");
    })
    .catch(() => {
      list.innerHTML = '<p class="pr-sentinel-empty">Không tải được dữ liệu PR Sentinel.</p>';
    });

  filters.forEach((button) => {
    button.addEventListener("click", () => {
      filters.forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      render(button.dataset.filter);
    });
  });
})();
