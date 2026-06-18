/**
 * H-Dashboard — purchase invoice / receipt analyzer (PDF, OCR fallback).
 * Clone of L/O-Dashboard logic & UI; data source = retail invoices (hóa đơn).
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
    els.upload = $("#hd-upload");
    els.uploadZone = $("#hd-upload-zone");
    els.uploadStatus = $("#hd-upload-status");
    els.meta = $("#hd-meta");
    els.reconcile = $("#hd-reconcile");
    els.summary = $("#hd-summary");
    els.health = $("#hd-health");
    els.insights = $("#hd-insights-list");
    els.geo = $("#hd-geo");
    els.tbody = $("#hd-table-body");
    els.pagination = $("#hd-pagination");
    els.filterDate = $("#hd-filter-date");
    els.filterDateFrom = $("#hd-filter-date-from");
    els.filterDateTo = $("#hd-filter-date-to");
    els.filterMonth = $("#hd-filter-month");
    els.filterType = $("#hd-filter-type");
    els.filterKeyword = $("#hd-filter-keyword");
    els.exportJson = $("#hd-export-json");
    els.exportCsv = $("#hd-export-csv");
    els.exportPdf = $("#hd-export-pdf");
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
        const hay = `${t.description} ${t.merchant || ""}`.toLowerCase();
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
    const base = HDashboardInsights.buildInsightsPayload(txs);
    if (statementMeta) {
      base.summary.opening_balance = statementMeta.opening_balance;
      base.summary.ending_balance = statementMeta.ending_balance;
      base.summary.total_debit = statementMeta.total_debit;
      base.summary.total_credit = statementMeta.total_credit;
    }
    const debits = txs.filter((t) => t.debit > 0);
    base.summary.max_debit = debits.length
      ? debits.reduce((a, b) => (a.debit >= b.debit ? a : b))
      : null;
    base.summary.max_credit = null;
    return base;
  }

  function renderMeta() {
    if (!els.meta || !statementMeta) return;
    const s = statementMeta;
    const fmt = HDashboardInsights.formatVnd;
    const dateLine = s.invoice_time ? `${s.invoice_date || "—"} ${s.invoice_time}` : (s.invoice_date || "—");
    els.meta.innerHTML = `
      <div class="hd-meta__grid">
        <div><span>Cửa hàng</span><strong>${escapeHtml(s.merchant || "—")}</strong><em>${escapeHtml(s.service_type || s.address || "")}</em></div>
        <div><span>Mã hóa đơn</span><strong>${escapeHtml(s.invoice_no || "—")}</strong><em>${escapeHtml(s.pos || "")}</em></div>
        <div><span>Ngày xuất</span><strong>${escapeHtml(dateLine)}</strong><em>${escapeHtml(s.currency || "VND")}</em></div>
        <div><span>Thu ngân</span><strong>${escapeHtml(s.cashier || "—")}</strong><em>${s.pager ? "Pager " + escapeHtml(s.pager) : ""}</em></div>
        <div><span>Tổng hóa đơn</span><strong>${fmt(s.total || 0)}</strong><em>${s.item_count || 0} mặt hàng</em></div>
        <div><span>Hình thức TT</span><strong>${escapeHtml(s.payment_method || "—")}</strong><em>${s.shop_id ? "Shop " + escapeHtml(s.shop_id) : ""}</em></div>
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
    const fmt = HDashboardInsights.formatVnd;
    const ok = reconciliation.ok;
    const ocrNote = statementMeta && statementMeta.via_ocr ? " · đọc bằng OCR (ảnh scan)" : "";
    els.reconcile.dataset.type = ok ? "success" : "error";
    els.reconcile.innerHTML = ok
      ? `✓ Đối soát khớp — Tổng mặt hàng ${fmt(reconciliation.sum_debit)} = Tổng hóa đơn ${fmt(reconciliation.expected_ending)}${ocrNote}`
      : `⚠ ${reconciliation.message} — Tổng mặt hàng ${fmt(reconciliation.sum_debit)} · Tổng hóa đơn ${fmt(reconciliation.expected_debit)}${ocrNote}`;
  }

  function renderFilteredSummary() {
    const payload = getInsightsPayload();
    renderSummary(payload.summary);
    renderHealth(payload.health);
    HDashboardCharts.renderAll(payload.charts);
    renderInsights(payload.insights);
    highlightHealthLegend(payload.health.health_label);

    const geoTxs = filteredTransactions.length ? filteredTransactions : allTransactions;
    if (window.HDashboardGeo && els.geo) window.HDashboardGeo.render(geoTxs, els.geo);
  }

  function highlightHealthLegend(label) {
    const legend = $("#hd-health-legend");
    if (!legend) return;
    const key = (label || "").toLowerCase();
    legend.querySelectorAll(".hd-health-legend__item").forEach((el) => {
      el.classList.toggle("hd-health-legend__item--active", el.classList.contains("hd-health-legend__item--" + key));
    });
  }

  function renderSummary(summary) {
    if (!els.summary) return;
    const fmt = HDashboardInsights.formatVnd;
    const range =
      summary.date_from && summary.date_to
        ? `${summary.date_from} → ${summary.date_to}`
        : "—";

    const maxDb = summary.max_debit
      ? `${fmt(summary.max_debit.debit).replace(" ₫", "")} · ${escapeHtml(summary.max_debit.description || "")}`
      : "—";

    els.summary.innerHTML = `
      <div class="hd-summary__item"><span class="hd-summary__label">Tổng chi tiêu</span><span class="hd-summary__value hd-summary__value--expense">${fmt(summary.total_expense)}</span></div>
      <div class="hd-summary__item"><span class="hd-summary__label">Hoàn / thu lại</span><span class="hd-summary__value hd-summary__value--income">${fmt(summary.total_income)}</span></div>
      <div class="hd-summary__item"><span class="hd-summary__label">Chi ròng</span><span class="hd-summary__value">${fmt(Math.abs(summary.net_cash_flow))}</span></div>
      <div class="hd-summary__item"><span class="hd-summary__label">Số mặt hàng</span><span class="hd-summary__value">${summary.transaction_count}</span></div>
      <div class="hd-summary__item hd-summary__item--wide"><span class="hd-summary__label">Mặt hàng đắt nhất</span><span class="hd-summary__value">${maxDb}</span></div>
      <div class="hd-summary__item hd-summary__item--wide"><span class="hd-summary__label">Khoảng thời gian</span><span class="hd-summary__value">${range}</span></div>
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
      <div class="hd-health__metric"><span>Saving Rate</span><strong>${pct(health.saving_rate)}</strong></div>
      <div class="hd-health__metric"><span>Expense Ratio</span><strong>${pct(health.expense_ratio)}</strong></div>
      <div class="hd-health__metric"><span>Net Cash Flow</span><strong>${HDashboardInsights.formatVnd(health.net_cash_flow)}</strong></div>
      <div class="hd-health__metric hd-health__metric--score"><span>Financial Score</span><strong class="hd-health__score hd-health__score--${labelKey}">${score}</strong><em>${escapeHtml(label)}</em></div>
    `;
  }

  function renderInsights(insights) {
    if (!els.insights) return;
    if (!insights.length) {
      els.insights.innerHTML = "<li>Upload hóa đơn PDF để nhận nhận xét tự động.</li>";
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
    const fmt = HDashboardInsights.formatVnd;

    if (!total) {
      els.tbody.innerHTML =
        '<tr><td colspan="7" class="hd-table__empty">Chưa có mặt hàng — hãy upload hóa đơn PDF.</td></tr>';
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
          <td class="hd-table__desc">${desc}</td>
          <td>${t.qty || 1}</td>
          <td class="hd-amount">${t.unit_price ? fmt(t.unit_price).replace(" ₫", "") : "—"}</td>
          <td class="hd-amount hd-amount--expense">${t.debit ? fmt(t.debit).replace(" ₫", "") : "—"}</td>
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
    let html = `<span class="hd-pagination__info">Trang ${currentPage}/${pages} · ${total} mặt hàng</span>`;
    html += `<button type="button" class="hd-pagination__btn" data-page="prev" ${currentPage <= 1 ? "disabled" : ""}>← Trước</button>`;
    html += `<button type="button" class="hd-pagination__btn" data-page="next" ${currentPage >= pages ? "disabled" : ""}>Sau →</button>`;
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
    await HDashboardStorage.clearAll();
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
      const { watermark } = await HDashboardExport.exportAndWipe(
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
      setStatus("Chỉ hỗ trợ hóa đơn dạng PDF (.pdf).", "error");
      return;
    }

    setStatus(`Đang đọc ${file.name}…`, "info");

    try {
      const buffer = await file.arrayBuffer();
      const parsed = await HDashboardInvoiceParser.parseInvoicePdfArrayBuffer(buffer, {
        onStatus: (msg) => setStatus(msg, "info"),
      });
      if (!parsed || !Array.isArray(parsed.transactions)) {
        throw new Error("Không đọc được mặt hàng từ PDF — kiểm tra đúng định dạng hóa đơn.");
      }
      if (!parsed.transactions.length) {
        setStatus(
          "Không tìm thấy mặt hàng nào trong hóa đơn. Nếu là ảnh scan mờ, hãy thử ảnh rõ hơn.",
          "error"
        );
        return;
      }
      statementMeta = parsed.statement || null;
      reconciliation = parsed.reconciliation || { ok: true, message: "" };

      const existingIds = await HDashboardStorage.getAllTransactionIds();
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
        await HDashboardStorage.insertTransactions(toInsert);
      }

      await refresh();
      renderMeta();
      renderReconcile();

      const ocrNote = parsed.via_ocr ? " · OCR ảnh scan" : "";
      const warn = reconciliation.ok ? "" : ` · ${reconciliation.message}`;
      setStatus(
        `Đã đọc ${parsed.transactions.length} mặt hàng · thêm mới ${toInsert.length} · bỏ qua trùng ${skipped}${ocrNote}${warn}`,
        reconciliation.ok ? "success" : "error"
      );
    } catch (err) {
      console.error(err);
      setStatus(err.message || "Lỗi khi đọc PDF hóa đơn.", "error");
    }
  }

  async function refresh() {
    allTransactions = await HDashboardStorage.getAllTransactions();
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
          els.uploadZone.classList.add("hd-upload--active");
        });
      });
      ["dragleave", "drop"].forEach((ev) => {
        els.uploadZone.addEventListener(ev, (e) => {
          e.preventDefault();
          els.uploadZone.classList.remove("hd-upload--active");
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
    if (!document.getElementById("hd-app")) return;
    const user = await HDashboardAuth.init();
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
