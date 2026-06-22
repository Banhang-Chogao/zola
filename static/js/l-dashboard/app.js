/**
 * L-Dashboard — LPBank statement analyzer (PDF).
 */
(function () {
  "use strict";

  const PAGE_SIZE = 20;
  let allTransactions = [];
  let filteredTransactions = [];
  let statementMeta = null;
  let reconciliation = null;
  let currentPage = 1;
  let dashboardReady = false;

  const els = {};

  function $(sel) {
    return document.querySelector(sel);
  }

  function cacheElements() {
    els.upload = $("#ld-upload");
    els.uploadZone = $("#ld-upload-zone");
    els.uploadStatus = $("#ld-upload-status");
    els.meta = $("#ld-meta");
    els.reconcile = $("#ld-reconcile");
    els.summary = $("#ld-summary");
    els.health = $("#ld-health");
    els.insights = $("#ld-insights-list");
    els.geo = $("#ld-geo");
    els.tbody = $("#ld-table-body");
    els.pagination = $("#ld-pagination");
    els.filterDate = $("#ld-filter-date");
    els.filterDateFrom = $("#ld-filter-date-from");
    els.filterDateTo = $("#ld-filter-date-to");
    els.filterMonth = $("#ld-filter-month");
    els.filterType = $("#ld-filter-type");
    els.filterKeyword = $("#ld-filter-keyword");
    els.exportJson = $("#ld-export-json");
    els.exportCsv = $("#ld-export-csv");
    els.exportPdf = $("#ld-export-pdf");
  }

  function setStatus(msg, type) {
    if (!els.uploadStatus) return;
    els.uploadStatus.textContent = msg;
    els.uploadStatus.dataset.type = type || "info";
  }

  function updateExportButtons() {
    const hasData = allTransactions.length > 0;
    if (els.exportJson) els.exportJson.disabled = !hasData;
    if (els.exportCsv) els.exportCsv.disabled = !hasData;
    if (els.exportPdf) els.exportPdf.disabled = !hasData;
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
      if (keyword) {
        const hay = `${t.description} ${t.txn_no || ""}`.toLowerCase();
        if (!hay.includes(keyword)) return false;
      }
      return true;
    });

    currentPage = 1;
    renderTable();
    renderFilteredSummary();
  }

  function getInsightsPayload() {
    const txs = filteredTransactions.length ? filteredTransactions : allTransactions;
    const base = LDashboardInsights.buildInsightsPayload(txs);
    if (statementMeta) {
      base.summary.opening_balance = statementMeta.opening_balance;
      base.summary.ending_balance = statementMeta.ending_balance;
      base.summary.total_debit = statementMeta.total_debit;
      base.summary.total_credit = statementMeta.total_credit;
    }
    const debits = txs.filter((t) => t.debit > 0);
    const credits = txs.filter((t) => t.credit > 0);
    base.summary.max_debit = debits.length
      ? debits.reduce((a, b) => (a.debit >= b.debit ? a : b))
      : null;
    base.summary.max_credit = credits.length
      ? credits.reduce((a, b) => (a.credit >= b.credit ? a : b))
      : null;
    return base;
  }

  function renderMeta() {
    if (!els.meta || !statementMeta) return;
    const s = statementMeta;
    const fmt = LDashboardInsights.formatVnd;
    els.meta.innerHTML = `
      <div class="ld-meta__grid">
        <div><span>Tài khoản</span><strong>${escapeHtml(s.account_name || "—")}</strong><em>${escapeHtml(s.account_number || "")}</em></div>
        <div><span>Khách hàng</span><strong>${escapeHtml(s.customer_name || "—")}</strong><em>CIF ${escapeHtml(s.cif_no || "—")}</em></div>
        <div><span>Kỳ sao kê</span><strong>${escapeHtml(s.from_date || "—")} → ${escapeHtml(s.to_date || "—")}</strong><em>${escapeHtml(s.currency || "VND")}</em></div>
        <div><span>Số dư đầu kỳ</span><strong>${fmt(s.opening_balance || 0)}</strong></div>
        <div><span>Số dư cuối kỳ</span><strong>${fmt(s.ending_balance || 0)}</strong></div>
        <div><span>In sao kê</span><strong>${escapeHtml(s.printing_date || "—")}</strong><em>${escapeHtml(s.printing_time || "")}</em></div>
      </div>
    `;
  }

  function renderReconcile() {
    if (!els.reconcile) return;
    if (!reconciliation) {
      els.reconcile.hidden = true;
      return;
    }
    els.reconcile.hidden = false;
    const fmt = LDashboardInsights.formatVnd;
    const ok = reconciliation.ok;
    els.reconcile.dataset.type = ok ? "success" : "error";
    els.reconcile.innerHTML = ok
      ? `✓ Đối soát khớp — Tổng ghi nợ ${fmt(reconciliation.sum_debit)} · Tổng ghi có ${fmt(reconciliation.sum_credit)} · Số dư cuối ${fmt(reconciliation.expected_ending)}`
      : `⚠ ${reconciliation.message} — Parse: nợ ${fmt(reconciliation.sum_debit)} / có ${fmt(reconciliation.sum_credit)} · Kỳ vọng: nợ ${fmt(reconciliation.expected_debit)} / có ${fmt(reconciliation.expected_credit)}`;
  }

  function renderFilteredSummary() {
    const payload = getInsightsPayload();
    renderSummary(payload.summary);
    renderHealth(payload.health);
    LDashboardCharts.renderAll(payload.charts);
    renderInsights(payload.insights);
    highlightHealthLegend(payload.health.health_label);

    const geoTxs = filteredTransactions.length ? filteredTransactions : allTransactions;
    if (window.LDashboardGeo && els.geo) window.LDashboardGeo.render(geoTxs, els.geo);
  }

  function highlightHealthLegend(label) {
    const legend = $("#ld-health-legend");
    if (!legend) return;
    const key = (label || "").toLowerCase();
    legend.querySelectorAll(".ld-health-legend__item").forEach((el) => {
      el.classList.toggle("ld-health-legend__item--active", el.classList.contains("ld-health-legend__item--" + key));
    });
  }

  function renderSummary(summary) {
    if (!els.summary) return;
    const fmt = LDashboardInsights.formatVnd;
    const range =
      summary.date_from && summary.date_to
        ? `${summary.date_from} → ${summary.date_to}`
        : "—";

    const maxCr = summary.max_credit
      ? `${fmt(summary.max_credit.credit)} · ${escapeHtml(summary.max_credit.txn_no || "")}`
      : "—";
    const maxDb = summary.max_debit
      ? `${fmt(summary.max_debit.debit)} · ${escapeHtml(summary.max_debit.txn_no || "")}`
      : "—";

    els.summary.innerHTML = `
      <div class="ld-summary__item"><span class="ld-summary__label">Tổng thu (ghi có)</span><span class="ld-summary__value ld-summary__value--income">${fmt(summary.total_income)}</span></div>
      <div class="ld-summary__item"><span class="ld-summary__label">Tổng chi (ghi nợ)</span><span class="ld-summary__value ld-summary__value--expense">${fmt(summary.total_expense)}</span></div>
      <div class="ld-summary__item"><span class="ld-summary__label">Chênh lệch</span><span class="ld-summary__value">${fmt(summary.net_cash_flow)}</span></div>
      <div class="ld-summary__item"><span class="ld-summary__label">Số giao dịch</span><span class="ld-summary__value">${summary.transaction_count}</span></div>
      <div class="ld-summary__item"><span class="ld-summary__label">Ghi có lớn nhất</span><span class="ld-summary__value">${maxCr}</span></div>
      <div class="ld-summary__item"><span class="ld-summary__label">Ghi nợ lớn nhất</span><span class="ld-summary__value">${maxDb}</span></div>
      <div class="ld-summary__item ld-summary__item--wide"><span class="ld-summary__label">Khoảng thời gian</span><span class="ld-summary__value">${range}</span></div>
    `;
  }

  function pct(n) {
    const v = Math.round(Number(n) * 100);
    return Number.isFinite(v) ? `${v}%` : "—";
  }

  function renderHealth(health) {
    if (!els.health) return;
    const label = health.health_label || "—";
    const labelKey = (health.health_label || "").toLowerCase();
    const score = Number.isFinite(Number(health.financial_score)) ? health.financial_score : "—";
    els.health.innerHTML = `
      <div class="ld-health__metric"><span>Saving Rate</span><strong>${pct(health.saving_rate)}</strong></div>
      <div class="ld-health__metric"><span>Expense Ratio</span><strong>${pct(health.expense_ratio)}</strong></div>
      <div class="ld-health__metric"><span>Net Cash Flow</span><strong>${LDashboardInsights.formatVnd(health.net_cash_flow)}</strong></div>
      <div class="ld-health__metric ld-health__metric--score"><span>Financial Score</span><strong class="ld-health__score ld-health__score--${labelKey}">${score}</strong><em>${escapeHtml(label)}</em></div>
    `;
  }

  function renderInsights(insights) {
    if (!els.insights) return;
    if (!insights.length) {
      els.insights.innerHTML = "<li>Upload sao kê LPBank PDF để nhận nhận xét tự động.</li>";
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
    const fmt = LDashboardInsights.formatVnd;

    if (!total) {
      els.tbody.innerHTML =
        '<tr><td colspan="8" class="ld-table__empty">Chưa có giao dịch — hãy upload sao kê LPBank PDF.</td></tr>';
      if (els.pagination) els.pagination.innerHTML = "";
      return;
    }

    els.tbody.innerHTML = slice
      .map((t, i) => {
        const txnDate = (window.ZolaDateTime && window.ZolaDateTime.formatTxnDate(t.date)) || "—";
        const desc = t.description ? escapeHtml(t.description) : "—";
        return `<tr>
          <td>${start + i + 1}</td>
          <td>${txnDate}</td>
          <td>${escapeHtml(t.value_date || "—")}</td>
          <td class="ld-table__desc">${desc}</td>
          <td><code>${escapeHtml(t.txn_no || "—")}</code></td>
          <td class="ld-amount ld-amount--expense">${t.debit ? fmt(t.debit).replace(" ₫", "") : "—"}</td>
          <td class="ld-amount ld-amount--income">${t.credit ? fmt(t.credit).replace(" ₫", "") : "—"}</td>
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
    let html = `<span class="ld-pagination__info">Trang ${currentPage}/${pages} · ${total} giao dịch</span>`;
    html += `<button type="button" class="ld-pagination__btn" data-page="prev" ${currentPage <= 1 ? "disabled" : ""}>← Trước</button>`;
    html += `<button type="button" class="ld-pagination__btn" data-page="next" ${currentPage >= pages ? "disabled" : ""}>Sau →</button>`;
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
    await LDashboardStorage.clearAll();
    allTransactions = [];
    filteredTransactions = [];
    statementMeta = null;
    reconciliation = null;
    currentPage = 1;
    if (els.filterDate) els.filterDate.value = "";
    if (els.filterDateFrom) els.filterDateFrom.value = "";
    if (els.filterDateTo) els.filterDateTo.value = "";
    if (els.filterKeyword) els.filterKeyword.value = "";
    if (els.filterType) els.filterType.value = "all";
    if (els.meta) els.meta.innerHTML = "";
    renderReconcile();
    populateMonthFilter();
    renderTable();
    renderFilteredSummary();
    updateExportButtons();
  }

  async function runExport(format) {
    if (!allTransactions.length) return;
    const labels = { pdf: "PDF báo cáo", csv: "CSV", json: "JSON" };
    const label = labels[format] || "file";
    if (!confirm(`Tải ${label} về máy và xóa ngay toàn bộ dữ liệu phiên? (Không lưu online)`)) return;

    const btn =
      format === "pdf" ? els.exportPdf : format === "csv" ? els.exportCsv : els.exportJson;
    if (btn) btn.disabled = true;

    try {
      const { watermark } = await LDashboardExport.exportAndWipe(
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
    if (!/\.pdf$/i.test(file.name)) {
      setStatus("Chỉ hỗ trợ sao kê LPBank dạng PDF (.pdf).", "error");
      return;
    }

    setStatus(`Đang đọc ${file.name}…`, "info");

    try {
      const buffer = await file.arrayBuffer();
      const parsed = await LDashboardLpbankParser.parseLpbankPdfArrayBuffer(buffer);
      if (!parsed || !Array.isArray(parsed.transactions)) {
        throw new Error("Không đọc được giao dịch từ PDF — kiểm tra đúng định dạng sao kê LPBank.");
      }
      statementMeta = parsed.statement || null;
      reconciliation = parsed.reconciliation || { ok: true, message: "" };

      const existingIds = await LDashboardStorage.getAllTransactionIds();
      const toInsert = [];
      let skipped = 0;
      for (const tx of parsed.transactions) {
        if (existingIds.has(tx.transaction_id)) {
          skipped++;
        } else {
          toInsert.push(tx);
        }
      }

      if (toInsert.length) {
        await LDashboardStorage.insertTransactions(toInsert);
      }

      await refresh();
      renderMeta();
      renderReconcile();

      const warn = reconciliation.ok ? "" : ` · ${reconciliation.message}`;
      setStatus(
        `Đã parse ${parsed.transactions.length} giao dịch · thêm mới ${toInsert.length} · bỏ qua trùng ${skipped}${warn}`,
        reconciliation.ok ? "success" : "error"
      );
    } catch (err) {
      console.error(err);
      setStatus(err.message || "Lỗi khi đọc PDF LPBank.", "error");
    }
  }

  async function refresh() {
    allTransactions = await LDashboardStorage.getAllTransactions();
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
          els.uploadZone.classList.add("ld-upload--active");
        });
      });
      ["dragleave", "drop"].forEach((ev) => {
        els.uploadZone.addEventListener(ev, (e) => {
          e.preventDefault();
          els.uploadZone.classList.remove("ld-upload--active");
        });
      });
      els.uploadZone.addEventListener("drop", (e) => handleFile(e.dataTransfer?.files?.[0]));
      els.uploadZone.addEventListener("click", () => els.upload?.click());
    }

    [els.filterDate, els.filterDateFrom, els.filterDateTo, els.filterMonth, els.filterType, els.filterKeyword].forEach(
      (el) => {
        if (!el) return;
        const ev = el.tagName === "INPUT" ? "input" : "change";
        el.addEventListener(ev, applyFilters);
      }
    );

    if (els.exportJson) els.exportJson.addEventListener("click", () => runExport("json"));
    if (els.exportCsv) els.exportCsv.addEventListener("click", () => runExport("csv"));
    if (els.exportPdf) els.exportPdf.addEventListener("click", () => runExport("pdf"));
  }

  async function startDashboard() {
    if (dashboardReady) return;
    dashboardReady = true;
    cacheElements();
    bindEvents();
    await refresh();
  }

  async function init() {
    if (!document.getElementById("ld-app")) return;
    const user = await LDashboardAuth.init();
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