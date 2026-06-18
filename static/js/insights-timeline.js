/**
 * Insights timeline pagination — left PR list on /insights/.
 * Shows 10 rows per page; hides pager when total <= 10.
 */
(function () {
  "use strict";

  var PAGE_SIZE = 10;
  var timeline = document.querySelector("[data-insights-timeline]");
  if (!timeline) return;

  var rows = Array.prototype.slice.call(
    timeline.querySelectorAll("[data-timeline-row]")
  );
  if (!rows.length) return;

  var pager = document.querySelector("[data-timeline-pager]");
  var prevBtn = document.querySelector("[data-timeline-prev]");
  var nextBtn = document.querySelector("[data-timeline-next]");
  var pageInfo = document.querySelector("[data-timeline-page-info]");

  var totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  var currentPage = 1;

  function readPageFromUrl() {
    try {
      var n = parseInt(new URLSearchParams(window.location.search).get("page") || "1", 10);
      if (!isFinite(n) || n < 1) return 1;
      return Math.min(n, totalPages);
    } catch (e) {
      return 1;
    }
  }

  function syncUrl(page) {
    try {
      var url = new URL(window.location.href);
      if (page <= 1) {
        url.searchParams.delete("page");
      } else {
        url.searchParams.set("page", String(page));
      }
      window.history.replaceState({ timelinePage: page }, "", url.pathname + url.search + url.hash);
    } catch (e) { /* ignore */ }
  }

  function lastVisibleIndex(start, end) {
    for (var i = end - 1; i >= start; i--) {
      if (rows[i]) return i;
    }
    return -1;
  }

  function renderPage(page) {
    currentPage = page;
    var start = (page - 1) * PAGE_SIZE;
    var end = Math.min(start + PAGE_SIZE, rows.length);
    var lastIdx = lastVisibleIndex(start, end);

    rows.forEach(function (row, idx) {
      var visible = idx >= start && idx < end;
      row.hidden = !visible;
      row.classList.toggle("insights__pr--last-visible", visible && idx === lastIdx);
    });

    if (pager) pager.hidden = totalPages <= 1;
    if (pageInfo) {
      pageInfo.textContent = "Trang " + page + " / " + totalPages;
    }
    if (prevBtn) prevBtn.disabled = page <= 1;
    if (nextBtn) nextBtn.disabled = page >= totalPages;
    syncUrl(page);
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", function () {
      if (currentPage > 1) renderPage(currentPage - 1);
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      if (currentPage < totalPages) renderPage(currentPage + 1);
    });
  }

  window.addEventListener("popstate", function () {
    renderPage(readPageFromUrl());
  });

  renderPage(readPageFromUrl());
})();