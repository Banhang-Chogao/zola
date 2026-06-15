/**
 * Scoring Card: client-side sort + filter cho table.
 * Server-render Tera đã build sẵn rows, JS chỉ reorder/show/hide.
 * Lý do client-side: data ≤ vài trăm rows, 0 cost reload, instant UX.
 */
(function () {
  "use strict";

  const tbody  = document.querySelector("[data-scoring-tbody]");
  const select = document.querySelector("[data-sort]");
  const chips  = document.querySelectorAll(".scoring__chip");
  const empty  = document.querySelector("[data-empty-msg]");
  if (!tbody) return;

  const allRows = Array.from(tbody.querySelectorAll(".scoring__row"));
  let currentFilter = "all"; // all | 7 | 30 | 90
  let currentSort   = "score-desc";

  function parseDate(str) {
    if (!str) return 0;
    // Frontmatter date có thể "2026-06-15" hoặc full ISO. Date constructor handle cả 2.
    const d = new Date(str);
    return isNaN(d.getTime()) ? 0 : d.getTime();
  }

  function applyFilter() {
    if (currentFilter === "all") {
      allRows.forEach((r) => r.hidden = false);
      return;
    }
    const days = parseInt(currentFilter, 10);
    const cutoff = Date.now() - days * 86400 * 1000;
    allRows.forEach((r) => {
      const ts = parseDate(r.dataset.date);
      r.hidden = ts === 0 ? false : ts < cutoff;
    });
  }

  function applySort() {
    const visible = allRows.filter((r) => !r.hidden);
    const sorters = {
      "score-desc": (a, b) => parseFloat(b.dataset.score) - parseFloat(a.dataset.score),
      "score-asc":  (a, b) => parseFloat(a.dataset.score) - parseFloat(b.dataset.score),
      "date-desc":  (a, b) => parseDate(b.dataset.date) - parseDate(a.dataset.date),
      "date-asc":   (a, b) => parseDate(a.dataset.date) - parseDate(b.dataset.date),
      "title-asc":  (a, b) => (a.dataset.title || "").localeCompare(b.dataset.title || "", "vi"),
    };
    const sorter = sorters[currentSort] || sorters["score-desc"];
    visible.sort(sorter);

    // Re-rank visible rows + re-append theo thứ tự mới
    const frag = document.createDocumentFragment();
    visible.forEach((row, i) => {
      const rankCell = row.querySelector(".scoring__td--rank");
      if (rankCell) rankCell.textContent = i + 1;
      frag.appendChild(row);
    });
    // Append hidden rows sau (giữ trong DOM nhưng không render)
    allRows.filter((r) => r.hidden).forEach((r) => frag.appendChild(r));
    tbody.appendChild(frag);

    if (empty) empty.hidden = visible.length > 0;
  }

  function refresh() {
    applyFilter();
    applySort();
  }

  // Filter chips
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("scoring__chip--active"));
      chip.classList.add("scoring__chip--active");
      currentFilter = chip.dataset.filter;
      refresh();
    });
  });

  // Sort dropdown
  if (select) {
    select.addEventListener("change", (e) => {
      currentSort = e.target.value;
      refresh();
    });
  }

  // Initial: server render default score-desc, không cần re-sort
})();
