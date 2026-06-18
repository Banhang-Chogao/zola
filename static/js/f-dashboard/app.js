/**
 * F-Dashboard main application controller.
 */
(function () {
  "use strict";

  const PAGE_SIZE = 20;
  let allTransactions = [];
  let filteredTransactions = [];
  let currentPage = 1;
  let dashboardReady = false;
  let selectedPdfFiles = [];

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
    els.geo = $("#fd-geo");
    els.tbody = $("#fd-table-body");
    els.pagination = $("#fd-pagination");
    els.filterDate = $("#fd-filter-date");
    els.filterDateFrom = $("#fd-filter-date-from");
    els.filterDateTo = $("#fd-filter-date-to");
    els.filterMonth = $("#fd-filter-month");
    els.filterType = $("#fd-filter-type");
    els.filterKeyword = $("#fd-filter-keyword");
    els.exportJson = $("#fd-export-json");
    els.exportPdf = $("#fd-export-pdf");
    els.mergePdfInput = $("#fd-merge-pdf-input");
    els.mergePdfBtn = $("#fd-merge-pdf-btn");
    els.mergePdfFiles = $("#fd-merge-pdf-files");
    els.mergePdfStatus = $("#fd-merge-pdf-status");
  }

  function setStatus(msg, type) {
    if (!els.uploadStatus) return;
    els.uploadStatus.textContent = msg;
    els.uploadStatus.dataset.type = type || "info";
  }

  function updateExportButtons() {
    const hasData = allTransactions.length > 0;
    if (els.exportJson) els.exportJson.disabled = !hasData;
    if (els.exportPdf) els.exportPdf.disabled = !hasData;
  }

  function setMergeStatus(msg, type) {
    if (!els.mergePdfStatus) return;
    els.mergePdfStatus.textContent = msg;
    els.mergePdfStatus.dataset.type = type || "info";
  }

  function updateMergePdfUi() {
    const count = selectedPdfFiles.length;
    if (els.mergePdfBtn) els.mergePdfBtn.disabled = count === 0;
    if (els.mergePdfFiles) {
      if (count) {
        els.mergePdfFiles.hidden = false;
        els.mergePdfFiles.textContent =
          count + " file: " + selectedPdfFiles.map((f) => f.name).join(" · ");
      } else {
        els.mergePdfFiles.hidden = true;
        els.mergePdfFiles.textContent = "";
      }
    }
  }

  async function runMergePdf() {
    if (!selectedPdfFiles.length) return;

    if (els.mergePdfBtn) els.mergePdfBtn.disabled = true;
    setMergeStatus("Đang gộp " + selectedPdfFiles.length + " file PDF…", "info");

    try {
      const result = await FDashboardExport.mergePdfReports(selectedPdfFiles);
      setMergeStatus(
        "Đã gộp " +
          result.fileCount +
          " báo cáo · " +
          result.pageCount +
          " trang → f-dashboard-merged-*.pdf",
        "success"
      );
      selectedPdfFiles = [];
      if (els.mergePdfInput) els.mergePdfInput.value = "";
      updateMergePdfUi();
    } catch (err) {
      console.error(err);
      setMergeStatus(err.message || "Gộp PDF thất bại.", "error");
      updateMergePdfUi();
    }
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

  function getInsightsPayload() {
    const txs = filteredTransactions.length ? filteredTransactions : allTransactions;
    return FDashboardInsights.buildInsightsPayload(txs);
  }

  // Display guards (display-only — never alter parsing/export math).
  function pct(value) {
    if (value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value)) {
      return "—";
    }
    return Math.round(value * 100) + "%";
  }

  function safeLabel(value) {
    const s = (value === null || value === undefined) ? "" : String(value).trim();
    return s || "—";
  }

  function safeText(value, fallback) {
    const s = (value === null || value === undefined) ? "" : String(value).trim();
    return s || (fallback === undefined ? "—" : fallback);
  }

  function renderFilteredSummary() {
    const payload = getInsightsPayload();
    renderSummary(payload.summary);
    renderHealth(payload.health);
    FDashboardCharts.renderAll(payload.charts);
    renderInsights(payload.insights);
    highlightHealthLegend(payload.health.health_label);

    const geoTxs = filteredTransactions.length ? filteredTransactions : allTransactions;
    if (window.FDashboardGeo && els.geo) window.FDashboardGeo.render(geoTxs, els.geo);
  }

  function highlightHealthLegend(label) {
    const legend = $("#fd-health-legend");
    if (!legend) return;
    const key = (label || "").toLowerCase();
    legend.querySelectorAll(".fd-health-legend__item").forEach((el) => {
      el.classList.toggle("fd-health-legend__item--active", el.classList.contains("fd-health-legend__item--" + key));
    });
  }

  function renderSummary(summary) {
    if (!els.summary) return;
    const fmt = FDashboardInsights.formatVnd;
    const range =
      summary.date_from && summary.date_to
        ? `${summary.date_from} → ${summary.date_to}`
        : "—";
    const count = Number.isFinite(summary.transaction_count) ? summary.transaction_count : 0;

    els.summary.innerHTML = `
      <div class="fd-summary__item"><span class="fd-summary__label">Tổng thu</span><span class="fd-summary__value fd-summary__value--income">${fmt(summary.total_income)}</span></div>
      <div class="fd-summary__item"><span class="fd-summary__label">Tổng chi</span><span class="fd-summary__value fd-summary__value--expense">${fmt(summary.total_expense)}</span></div>
      <div class="fd-summary__item"><span class="fd-summary__label">Chênh lệch</span><span class="fd-summary__value">${fmt(summary.net_cash_flow)}</span></div>
      <div class="fd-summary__item"><span class="fd-summary__label">Số giao dịch</span><span class="fd-summary__value">${count}</span></div>
      <div class="fd-summary__item fd-summary__item--wide"><span class="fd-summary__label">Khoảng thời gian</span><span class="fd-summary__value">${safeText(range)}</span></div>
    `;
  }

  function renderHealth(health) {
    if (!els.health) return;
    const sr = pct(health.saving_rate);
    const er = pct(health.expense_ratio);
    const label = safeLabel(health.health_label);
    const scoreCls = label === "—" ? "" : label.toLowerCase();
    const score = (typeof health.financial_score === "number" && Number.isFinite(health.financial_score))
      ? health.financial_score
      : "—";
    els.health.innerHTML = `
      <div class="fd-health__metric"><span>Saving Rate</span><strong>${sr}</strong></div>
      <div class="fd-health__metric"><span>Expense Ratio</span><strong>${er}</strong></div>
      <div class="fd-health__metric"><span>Net Cash Flow</span><strong>${FDashboardInsights.formatVnd(health.net_cash_flow)}</strong></div>
      <div class="fd-health__metric fd-health__metric--score"><span>Financial Score</span><strong class="fd-health__score fd-health__score--${scoreCls}">${score}</strong><em>${escapeHtml(label)}</em></div>
    `;
  }

  function renderInsights(insights) {
    if (!els.insights) return;
    if (!insights.length) {
      els.insights.innerHTML = "<li>Upload sao kê để nhận nhận xét tự động từ dữ liệu giao dịch.</li>";
      return;
    }
    els.insights.innerHTML = insights.map((t) => `<li>${escapeHtml(t)}</li>`).join("");
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
        const dateText = safeText(t.date ? String(t.date).replace("T", " ") : "");
        const descText = safeText(escapeHtml(t.description), "—");
        const amountText = fmt(Math.abs(t.amount)).replace(" ₫", "") || "—";
        return `<tr>
          <td>${start + i + 1}</td>
          <td>${dateText}</td>
          <td class="fd-table__desc">${descText}</td>
          <td class="fd-amount ${cls}">${amountText === "—" ? "—" : sign + amountText}</td>
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

  async function wipeSessionData() {
    await FDashboardStorage.clearAll();
    allTransactions = [];
    filteredTransactions = [];
    currentPage = 1;
    if (els.filterDate) els.filterDate.value = "";
    if (els.filterDateFrom) els.filterDateFrom.value = "";
    if (els.filterDateTo) els.filterDateTo.value = "";
    if (els.filterKeyword) els.filterKeyword.value = "";
    if (els.filterType) els.filterType.value = "all";
    populateMonthFilter();
    renderTable();
    renderFilteredSummary();
    updateExportButtons();
  }

  async function runExport(format) {
    if (!allTransactions.length) return;

    const label = format === "pdf" ? "PDF báo cáo" : "JSON";
    if (!confirm(`Tải ${label} về máy và xóa ngay toàn bộ dữ liệu phiên? (Không lưu online)`)) return;

    const btn = format === "pdf" ? els.exportPdf : els.exportJson;
    if (btn) btn.disabled = true;

    try {
      const { watermark } = await FDashboardExport.exportAndWipe(
        format,
        allTransactions,
        getInsightsPayload(),
        wipeSessionData
      );
      setStatus(`Đã tải ${label} · phiên đã xóa · trace: ${watermark}`, "success");
    } catch (err) {
      console.error(err);
      setStatus(err.message || `Xuất ${label} thất bại.`, "error");
      updateExportButtons();
    }
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
    updateExportButtons();
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

    if (els.exportJson) els.exportJson.addEventListener("click", () => runExport("json"));
    if (els.exportPdf) els.exportPdf.addEventListener("click", () => runExport("pdf"));

    if (els.mergePdfInput) {
      els.mergePdfInput.addEventListener("change", (e) => {
        selectedPdfFiles = Array.from(e.target.files || []);
        updateMergePdfUi();
        if (selectedPdfFiles.length) {
          setMergeStatus(
            "Đã chọn " + selectedPdfFiles.length + " file — bấm Gộp để tải PDF tích lũy.",
            "info"
          );
        } else {
          setMergeStatus("Chọn các file PDF đã export trước đó — không cần phiên sao kê đang mở.", "info");
        }
      });
    }
    if (els.mergePdfBtn) els.mergePdfBtn.addEventListener("click", runMergePdf);
  }

  async function startDashboard() {
    if (dashboardReady) return;
    dashboardReady = true;
    cacheElements();
    bindEvents();
    await refresh();
  }

  async function init() {
    if (!document.getElementById("fd-app")) return;

    const user = await FDashboardAuth.init();
    if (user) {
      await startDashboard();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();