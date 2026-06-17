/**
 * F-Dashboard main application controller.
 */
(function () {
  "use strict";

  const PAGE_SIZE = 20;
  let allTransactions = [];
  let filteredTransactions = [];
  let currentPage = 1;

  const els = {};

  function $(sel) {
    return document.querySelector(sel);
  }

  function cacheElements() {
    els.upload = $("#fd-upload");
    els.uploadZone = $("#fd-upload-zone");
    els.uploadStatus = $("#fd-upload-status");
    els.summary = $("#fd-summary");
    els.health = $("#fd-health");
    els.insights = $("#fd-insights-list");
    els.tbody = $("#fd-table-body");
    els.pagination = $("#fd-pagination");
    els.filterDate = $("#fd-filter-date");
    els.filterDateFrom = $("#fd-filter-date-from");
    els.filterDateTo = $("#fd-filter-date-to");
    els.filterMonth = $("#fd-filter-month");
    els.filterType = $("#fd-filter-type");
    els.filterKeyword = $("#fd-filter-keyword");
    els.clearData = $("#fd-clear-data");
  }

  function setStatus(msg, type) {
    if (!els.uploadStatus) return;
    els.uploadStatus.textContent = msg;
    els.uploadStatus.dataset.type = type || "info";
  }

  function applyFilters() {
    const dateVal = els.filterDate?.value || "";
    const dateFrom = els.filterDateFrom?.value || "";
    const dateTo = els.filterDateTo?.value || "";
    const monthVal = els.filterMonth?.value || "";
    const typeVal = els.filterType?.value || "all";
    const keyword = (els.filterKeyword?.value || "").toLowerCase().trim();

    filteredTransactions = allTransactions.filter((t) => {
      const day = t.date.slice(0, 10);
      if (dateVal && day !== dateVal) return false;
      if (dateFrom && day < dateFrom) return false;
      if (dateTo && day > dateTo) return false;
      if (monthVal && t.date.slice(0, 7) !== monthVal) return false;
      if (typeVal === "income" && t.amount <= 0) return false;
      if (typeVal === "expense" && t.amount >= 0) return false;
      if (keyword && !t.description.toLowerCase().includes(keyword)) return false;
      return true;
    });

    currentPage = 1;
    renderTable();
    renderFilteredSummary();
  }

  function renderFilteredSummary() {
    const payload = FDashboardInsights.buildInsightsPayload(
      filteredTransactions.length ? filteredTransactions : allTransactions
    );
    renderSummary(payload.summary);
    renderHealth(payload.health);
    FDashboardCharts.renderAll(payload.charts);
    renderInsights(payload.insights);
  }

  function renderSummary(summary) {
    if (!els.summary) return;
    const fmt = FDashboardInsights.formatVnd;
    const range =
      summary.date_from && summary.date_to
        ? `${summary.date_from} → ${summary.date_to}`
        : "—";

    els.summary.innerHTML = `
      <div class="fd-summary__item"><span class="fd-summary__label">Tổng thu</span><span class="fd-summary__value fd-summary__value--income">${fmt(summary.total_income)}</span></div>
      <div class="fd-summary__item"><span class="fd-summary__label">Tổng chi</span><span class="fd-summary__value fd-summary__value--expense">${fmt(summary.total_expense)}</span></div>
      <div class="fd-summary__item"><span class="fd-summary__label">Chênh lệch</span><span class="fd-summary__value">${fmt(summary.net_cash_flow)}</span></div>
      <div class="fd-summary__item"><span class="fd-summary__label">Số giao dịch</span><span class="fd-summary__value">${summary.transaction_count}</span></div>
      <div class="fd-summary__item fd-summary__item--wide"><span class="fd-summary__label">Khoảng thời gian</span><span class="fd-summary__value">${range}</span></div>
    `;
  }

  function renderHealth(health) {
    if (!els.health) return;
    const sr = Math.round(health.saving_rate * 100);
    const er = Math.round(health.expense_ratio * 100);
    els.health.innerHTML = `
      <div class="fd-health__metric"><span>Saving Rate</span><strong>${sr}%</strong></div>
      <div class="fd-health__metric"><span>Expense Ratio</span><strong>${er}%</strong></div>
      <div class="fd-health__metric"><span>Net Cash Flow</span><strong>${FDashboardInsights.formatVnd(health.net_cash_flow)}</strong></div>
      <div class="fd-health__metric fd-health__metric--score"><span>Financial Score</span><strong class="fd-health__score fd-health__score--${health.health_label.toLowerCase()}">${health.financial_score}</strong><em>${health.health_label}</em></div>
    `;
  }

  function renderInsights(insights) {
    if (!els.insights) return;
    els.insights.innerHTML = insights.map((t) => `<li>${t}</li>`).join("");
  }

  function renderTable() {
    if (!els.tbody) return;
    const total = filteredTransactions.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage > pages) currentPage = pages;

    const start = (currentPage - 1) * PAGE_SIZE;
    const slice = filteredTransactions.slice(start, start + PAGE_SIZE);
    const fmt = FDashboardInsights.formatVnd;

    if (!total) {
      els.tbody.innerHTML =
        '<tr><td colspan="5" class="fd-table__empty">Chưa có giao dịch — hãy upload sao kê VietinBank.</td></tr>';
      if (els.pagination) els.pagination.innerHTML = "";
      return;
    }

    els.tbody.innerHTML = slice
      .map((t, i) => {
        const cls = t.amount > 0 ? "fd-amount--income" : "fd-amount--expense";
        const sign = t.amount > 0 ? "+" : "";
        return `<tr>
          <td>${start + i + 1}</td>
          <td>${t.date.replace("T", " ")}</td>
          <td class="fd-table__desc">${escapeHtml(t.description)}</td>
          <td class="fd-amount ${cls}">${sign}${fmt(Math.abs(t.amount)).replace(" ₫", "")}</td>
          <td>${fmt(t.balance)}</td>
        </tr>`;
      })
      .join("");

    renderPagination(pages, total);
  }

  function renderPagination(pages, total) {
    if (!els.pagination) return;
    if (total <= PAGE_SIZE) {
      els.pagination.innerHTML = "";
      return;
    }

    let html = `<span class="fd-pagination__info">Trang ${currentPage}/${pages} · ${total} giao dịch</span>`;
    html += `<button type="button" class="fd-pagination__btn" data-page="prev" ${currentPage <= 1 ? "disabled" : ""}>← Trước</button>`;
    html += `<button type="button" class="fd-pagination__btn" data-page="next" ${currentPage >= pages ? "disabled" : ""}>Sau →</button>`;
    els.pagination.innerHTML = html;

    els.pagination.querySelectorAll("[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.page === "prev" && currentPage > 1) currentPage--;
        if (btn.dataset.page === "next" && currentPage < pages) currentPage++;
        renderTable();
      });
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function populateMonthFilter() {
    if (!els.filterMonth) return;
    const months = [...new Set(allTransactions.map((t) => t.date.slice(0, 7)))].sort().reverse();
    const current = els.filterMonth.value;
    els.filterMonth.innerHTML =
      '<option value="">Tất cả tháng</option>' +
      months.map((m) => `<option value="${m}">${m}</option>`).join("");
    if (current) els.filterMonth.value = current;
  }

  async function handleFile(file) {
    if (!file) return;
    if (!/\.xlsx?$/i.test(file.name)) {
      setStatus("Chỉ hỗ trợ file Excel VietinBank (.xlsx, .xls).", "error");
      return;
    }

    setStatus(`Đang đọc ${file.name}…`, "info");

    try {
      const buffer = await file.arrayBuffer();
      const parsed = await FDashboardParser.parseVietinbankArrayBuffer(buffer);
      const existingIds = await FDashboardStorage.getAllTransactionIds();
      const { inserted, skipped } = FDashboardParser.mergeTransactions(parsed, existingIds);

      if (inserted.length) {
        await FDashboardStorage.insertTransactions(inserted);
      }

      await refresh();
      setStatus(
        `Đã xử lý ${parsed.length} dòng · thêm mới ${inserted.length} · bỏ qua trùng ${skipped.length}.`,
        "success"
      );
    } catch (err) {
      console.error(err);
      setStatus(err.message || "Lỗi khi đọc file Excel.", "error");
    }
  }

  async function refresh() {
    allTransactions = await FDashboardStorage.getAllTransactions();
    filteredTransactions = [...allTransactions];
    populateMonthFilter();
    applyFilters();
  }

  function bindEvents() {
    if (els.upload) {
      els.upload.addEventListener("change", (e) => handleFile(e.target.files[0]));
    }

    if (els.uploadZone) {
      ["dragenter", "dragover"].forEach((ev) => {
        els.uploadZone.addEventListener(ev, (e) => {
          e.preventDefault();
          els.uploadZone.classList.add("fd-upload--active");
        });
      });
      ["dragleave", "drop"].forEach((ev) => {
        els.uploadZone.addEventListener(ev, (e) => {
          e.preventDefault();
          els.uploadZone.classList.remove("fd-upload--active");
        });
      });
      els.uploadZone.addEventListener("drop", (e) => {
        const file = e.dataTransfer?.files?.[0];
        handleFile(file);
      });
      els.uploadZone.addEventListener("click", () => els.upload?.click());
    }

    [els.filterDate, els.filterDateFrom, els.filterDateTo, els.filterMonth, els.filterType, els.filterKeyword].forEach((el) => {
      if (!el) return;
      const ev = el.tagName === "INPUT" ? "input" : "change";
      el.addEventListener(ev, applyFilters);
    });

    if (els.clearData) {
      els.clearData.addEventListener("click", async () => {
        if (!confirm("Xóa toàn bộ dữ liệu F-Dashboard trên trình duyệt này?")) return;
        await FDashboardStorage.clearAll();
        allTransactions = [];
        filteredTransactions = [];
        currentPage = 1;
        renderTable();
        renderFilteredSummary();
        setStatus("Đã xóa dữ liệu local.", "info");
      });
    }
  }

  async function init() {
    if (!document.querySelector(".f-dashboard")) return;
    cacheElements();
    bindEvents();
    await refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();