/**
 * H-Dashboard V2 — Highlands Coffee Life Analytics.
 * Receipt OCR → Coffee DNA, timeline, seasonality, personality.
 */
(function (global) {
  "use strict";

  const COFFEE_MODULE_MSG =
    "Coffee Analytics V2 chưa tải xong. Hãy tải lại trang (Ctrl+Shift+R). Upload vẫn hoạt động.";

  const PAGE_SIZE = 20;
  const MAX_BATCH_FILES = 10;
  let allTransactions = [];
  let filteredTransactions = [];
  let receiptsCatalog = { fingerprints: [], statements: [] };
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
    els.uploadBatch = $("#hd-upload-batch");
    els.meta = $("#hd-meta");
    els.reconcile = $("#hd-reconcile");
    els.summary = $("#hd-summary");
    els.insights = $("#hd-insights-list");
    els.geo = $("#hd-geo");
    els.geoSummary = $("#hd-geo-summary");
    els.tbody = $("#hd-table-body");
    els.pagination = $("#hd-pagination");
    els.filterDate = $("#hd-filter-date");
    els.filterDateFrom = $("#hd-filter-date-from");
    els.filterDateTo = $("#hd-filter-date-to");
    els.filterMonth = $("#hd-filter-month");
    els.filterKeyword = $("#hd-filter-keyword");
    els.exportJson = $("#hd-export-json");
    els.exportCsv = $("#hd-export-csv");
    els.exportPdf = $("#hd-export-pdf");
    els.coffeeModuleError = $("#hd-coffee-module-error");
  }

  function coffeeEngine() {
    return global.HDashboardCoffee || null;
  }

  function coffeeUi() {
    return global.HDashboardCoffeeUI || null;
  }

  function coffeeCharts() {
    return global.HDashboardCharts || null;
  }

  function coffeeModulesReady() {
    return !!(coffeeEngine() && coffeeUi() && coffeeCharts());
  }

  function showCoffeeModuleError(msg) {
    const text = msg || COFFEE_MODULE_MSG;
    if (els.coffeeModuleError) {
      els.coffeeModuleError.hidden = false;
      els.coffeeModuleError.textContent = text;
    }
    console.error("[H-Dashboard]", text);
  }

  function clearCoffeeModuleError() {
    if (els.coffeeModuleError) els.coffeeModuleError.hidden = true;
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

  function fmt(n) {
    const coffee = coffeeEngine();
    if (coffee && coffee.formatVnd) return coffee.formatVnd(n);
    const v = Number(n);
    return Number.isFinite(v) ? new Intl.NumberFormat("vi-VN").format(v) + " ₫" : "—";
  }

  function applyFilters() {
    const dateVal = els.filterDate?.value || "";
    const dateFrom = els.filterDateFrom?.value || "";
    const dateTo = els.filterDateTo?.value || "";
    const monthVal = els.filterMonth?.value || "";
    const keyword = (els.filterKeyword?.value || "").toLowerCase().trim();

    filteredTransactions = allTransactions.filter((t) => {
      const day = t.date.slice(0, 10);
      if (dateVal && day !== dateVal) return false;
      if (dateFrom && day < dateFrom) return false;
      if (dateTo && day > dateTo) return false;
      if (monthVal && t.date.slice(0, 7) !== monthVal) return false;
      if (keyword) {
        const hay = `${t.description} ${t.merchant || ""} ${t.address || ""}`.toLowerCase();
        if (!hay.includes(keyword)) return false;
      }
      return true;
    });

    currentPage = 1;
    renderTable();
    renderFilteredSummary();
  }

  function getCoffeePayload() {
    const coffee = coffeeEngine();
    if (!coffee || !coffee.buildCoffeePayload) {
      throw new ReferenceError("HDashboardCoffee is not defined");
    }
    const txs = filteredTransactions.length ? filteredTransactions : allTransactions;
    const payload = coffee.buildCoffeePayload(txs);

    if (global.HDashboardGeo && txs.length) {
      const geo = global.HDashboardGeo.analyze(txs);
      const top = geo.locations.slice(0, 2).map((l) => l.name);
      if (top.length) {
        const hint = `Bạn thường uống cà phê quanh ${top.join(" và ")}.`;
        payload.executiveSummary = payload.executiveSummary
          ? payload.executiveSummary + " " + hint
          : hint;
        payload.geoHint = hint;
      }
    }
    return payload;
  }

  function getInsightsPayload() {
    const coffee = getCoffeePayload();
    return {
      coffee,
      summary: {
        total_expense: coffee.dna.totalSpend,
        transaction_count: allTransactions.length,
        visit_count: coffee.dna.totalVisits,
        date_from: allTransactions.length
          ? allTransactions.map((t) => t.date).sort()[0].slice(0, 10)
          : "",
        date_to: allTransactions.length
          ? allTransactions.map((t) => t.date).sort().slice(-1)[0].slice(0, 10)
          : "",
      },
      insights: coffee.narrativeInsights,
    };
  }

  function renderMeta() {
    if (!els.meta) return;
    const statements = (receiptsCatalog.statements || []).length
      ? receiptsCatalog.statements
      : statementMeta
        ? [statementMeta]
        : [];
    if (!statements.length) return;
    if (statements.length > 1) {
      els.meta.innerHTML =
        `<p class="hd-meta__aggregate">${statements.length} hóa đơn trong phiên</p>` +
        statements
          .map((s) => {
            const dateLine = s.invoice_time
              ? `${s.invoice_date || "—"} ${s.invoice_time}`
              : s.invoice_date || "—";
            return `<div class="hd-meta__mini"><strong>#${escapeHtml(s.invoice_no || "—")}</strong> · ${escapeHtml(s.merchant || "—")} · ${escapeHtml(dateLine)} · ${fmt(s.total || 0)}</div>`;
          })
          .join("");
      return;
    }
    const s = statements[0];
    const dateLine = s.invoice_time ? `${s.invoice_date || "—"} ${s.invoice_time}` : (s.invoice_date || "—");
    els.meta.innerHTML = `
      <div class="hd-meta__grid">
        <div><span>Cửa hàng</span><strong>${escapeHtml(s.merchant || "—")}</strong><em>${escapeHtml(s.address || s.service_type || "")}</em></div>
        <div><span>Mã hóa đơn</span><strong>${escapeHtml(s.invoice_no || "—")}</strong><em>${escapeHtml(s.pos || "")}</em></div>
        <div><span>Ngày xuất</span><strong>${escapeHtml(dateLine)}</strong><em>${escapeHtml(s.currency || "VND")}</em></div>
        <div><span>Thu ngân</span><strong>${escapeHtml(s.cashier || "—")}</strong><em>${s.pager ? "Pager " + escapeHtml(s.pager) : ""}</em></div>
        <div><span>Tổng hóa đơn</span><strong>${fmt(s.total || 0)}</strong><em>${s.item_count || 0} mặt hàng</em></div>
        <div><span>Thanh toán</span><strong>${escapeHtml(s.payment_method || "—")}</strong><em>${s.shop_id ? "Shop " + escapeHtml(s.shop_id) : ""}</em></div>
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
    const ok = reconciliation.ok;
    const ocrNote = statementMeta && statementMeta.via_ocr ? " · đọc bằng OCR (ảnh scan)" : "";
    els.reconcile.dataset.type = ok ? "success" : "error";
    els.reconcile.innerHTML = ok
      ? `✓ Đối soát khớp — Tổng mặt hàng ${fmt(reconciliation.sum_debit)} = Tổng hóa đơn ${fmt(reconciliation.expected_ending)}${ocrNote}`
      : `⚠ ${reconciliation.message} — Tổng mặt hàng ${fmt(reconciliation.sum_debit)} · Tổng hóa đơn ${fmt(reconciliation.expected_debit)}${ocrNote}`;
  }

  function renderFilteredSummary() {
    if (!allTransactions.length) {
      clearCoffeeModuleError();
      return;
    }
    if (!coffeeModulesReady()) {
      showCoffeeModuleError();
      return;
    }
    try {
      const payload = getCoffeePayload();
      clearCoffeeModuleError();
      renderSummary(payload);
      coffeeUi().renderAll(payload);
      coffeeCharts().renderAll(payload);

      const geoTxs = filteredTransactions.length ? filteredTransactions : allTransactions;
      if (global.HDashboardGeo && els.geo) {
        global.HDashboardGeo.render(geoTxs, els.geo);
        if (els.geoSummary && payload.geoHint) {
          els.geoSummary.textContent = payload.geoHint;
        }
      }
    } catch (err) {
      console.error(err);
      showCoffeeModuleError(err.message || COFFEE_MODULE_MSG);
    }
  }

  function renderSummary(payload) {
    if (!els.summary) return;
    const dna = payload.dna || {};
    const dates = allTransactions.map((t) => t.date).sort();
    const range =
      dates.length ? `${dates[0].slice(0, 10)} → ${dates[dates.length - 1].slice(0, 10)}` : "—";

    els.summary.innerHTML = `
      <div class="hd-summary__item"><span class="hd-summary__label">Tổng chi tiêu</span><span class="hd-summary__value">${fmt(dna.totalSpend || 0)}</span></div>
      <div class="hd-summary__item"><span class="hd-summary__label">Lần ghé</span><span class="hd-summary__value">${dna.totalVisits || 0}</span></div>
      <div class="hd-summary__item"><span class="hd-summary__label">Hóa đơn TB</span><span class="hd-summary__value">${fmt(dna.avgBill || 0)}</span></div>
      <div class="hd-summary__item"><span class="hd-summary__label">Đồ uống</span><span class="hd-summary__value">${dna.totalDrinks || 0}</span></div>
      <div class="hd-summary__item hd-summary__item--wide"><span class="hd-summary__label">Signature drink</span><span class="hd-summary__value">${escapeHtml(payload.drinks?.signature || "—")}</span></div>
      <div class="hd-summary__item hd-summary__item--wide"><span class="hd-summary__label">Khoảng thời gian</span><span class="hd-summary__value">${range}</span></div>
    `;
  }

  function renderTable() {
    if (!els.tbody) return;
    const total = filteredTransactions.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage > pages) currentPage = pages;

    const start = (currentPage - 1) * PAGE_SIZE;
    const slice = filteredTransactions.slice(start, start + PAGE_SIZE);

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
        const store = t.merchant ? escapeHtml(t.merchant) : "—";
        return `<tr>
          <td>${start + i + 1}</td>
          <td>${txnDate}</td>
          <td class="hd-table__desc">${desc}</td>
          <td>${t.qty || 1}</td>
          <td class="hd-amount">${t.unit_price ? fmt(t.unit_price).replace(" ₫", "") : "—"}</td>
          <td class="hd-amount hd-amount--expense">${t.debit ? fmt(t.debit).replace(" ₫", "") : "—"}</td>
          <td>${store}</td>
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
    await global.HDashboardStorage.clearAll();
    allTransactions = [];
    filteredTransactions = [];
    statementMeta = null;
    reconciliation = null;
    currentPage = 1;
    if (els.filterDate) els.filterDate.value = "";
    if (els.filterDateFrom) els.filterDateFrom.value = "";
    if (els.filterDateTo) els.filterDateTo.value = "";
    if (els.filterKeyword) els.filterKeyword.value = "";
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
      if (!coffeeModulesReady()) {
        throw new Error(COFFEE_MODULE_MSG);
      }
      const { watermark } = await global.HDashboardExport.exportAndWipe(
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

  function statementSnapshot(stmt) {
    return {
      merchant: stmt.merchant,
      address: stmt.address,
      invoice_no: stmt.invoice_no,
      invoice_date: stmt.invoice_date,
      invoice_time: stmt.invoice_time,
      total: stmt.total,
      item_count: stmt.item_count,
      via_ocr: stmt.via_ocr,
    };
  }

  async function processOneFile(file, fpSet) {
    if (!/\.pdf$/i.test(file.name)) {
      throw new Error("Chỉ hỗ trợ PDF: " + file.name);
    }

    const buffer = await file.arrayBuffer();
    const parsed = await global.HDashboardInvoiceParser.parseInvoicePdfArrayBuffer(buffer, {
      onStatus: (msg) => setStatus(`[${file.name}] ${msg}`, "info"),
    });

    if (!parsed || !Array.isArray(parsed.transactions) || !parsed.transactions.length) {
      throw new Error("Không tìm thấy mặt hàng trong " + file.name);
    }

    const fp =
      parsed.receipt_fingerprint ||
      (await global.HDashboardInvoiceParser.buildReceiptFingerprint(parsed.statement));

    if (fpSet.has(fp)) {
      const inv = parsed.statement.invoice_no || "?";
      return { status: "duplicate", invoice_no: inv };
    }

    const existingIds = await global.HDashboardStorage.getAllTransactionIds();
    const toInsert = [];
    for (const tx of parsed.transactions) {
      if (!existingIds.has(tx.transaction_id)) {
        toInsert.push(tx);
        existingIds.add(tx.transaction_id);
      }
    }

    if (toInsert.length) {
      await global.HDashboardStorage.insertTransactions(toInsert);
    }

    fpSet.add(fp);
    receiptsCatalog.fingerprints = Array.from(fpSet);
    receiptsCatalog.statements.push(statementSnapshot(parsed.statement));
    await global.HDashboardStorage.setReceiptsCatalog(receiptsCatalog);

    statementMeta = parsed.statement;
    reconciliation = parsed.reconciliation || { ok: true, message: "" };

    return {
      status: "ok",
      inserted: toInsert.length,
      item_count: parsed.transactions.length,
      via_ocr: parsed.via_ocr,
      reconciliation: parsed.reconciliation,
    };
  }

  async function handleFiles(fileList) {
    const files = Array.from(fileList || [])
      .filter((f) => /\.pdf$/i.test(f.name))
      .slice(0, MAX_BATCH_FILES);

    if (!files.length) {
      setStatus("Chọn ít nhất 1 file PDF hóa đơn Highlands.", "error");
      return;
    }

    if (fileList && fileList.length > MAX_BATCH_FILES) {
      setStatus(`Chỉ xử lý tối đa ${MAX_BATCH_FILES} file — đã lấy ${MAX_BATCH_FILES} file đầu.`, "info");
    }

    receiptsCatalog = await global.HDashboardStorage.getReceiptsCatalog();
    const fpSet = new Set(receiptsCatalog.fingerprints || []);
    const stats = { selected: files.length, processed: 0, duplicate: 0, failed: 0 };
    const dupNotes = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setStatus(`Đang xử lý ${i + 1}/${files.length}: ${file.name}…`, "info");
      try {
        const result = await processOneFile(file, fpSet);
        if (result.status === "duplicate") {
          stats.duplicate++;
          dupNotes.push("Skipped duplicate receipt #" + result.invoice_no);
        } else {
          stats.processed++;
        }
      } catch (err) {
        console.error(err);
        stats.failed++;
      }
    }

    await refresh();
    renderMeta();
    renderReconcile();

    let msg =
      "Selected: " +
      stats.selected +
      " · Processed: " +
      stats.processed +
      " · Duplicate: " +
      stats.duplicate +
      " · Failed OCR: " +
      stats.failed;
    if (dupNotes.length) msg += " · " + dupNotes.join(" · ");

    setStatus(msg, stats.failed > 0 ? "error" : "success");

    if (els.upload) els.upload.value = "";
    if (els.uploadBatch) {
      els.uploadBatch.textContent = files.map((f) => f.name).join(" · ");
      els.uploadBatch.hidden = false;
    }
  }

  async function refresh() {
    allTransactions = await global.HDashboardStorage.getAllTransactions();
    receiptsCatalog = await global.HDashboardStorage.getReceiptsCatalog();
    filteredTransactions = [...allTransactions];
    populateMonthFilter();
    applyFilters();
    updateExportButtons();
  }

  function bindEvents() {
    if (els.upload) {
      els.upload.addEventListener("change", (e) => handleFiles(e.target.files));
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
      els.uploadZone.addEventListener("drop", (e) => handleFiles(e.dataTransfer?.files));
      els.uploadZone.addEventListener("click", () => els.upload?.click());
    }

    [els.filterDate, els.filterDateFrom, els.filterDateTo, els.filterMonth, els.filterKeyword].forEach(
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
    if (!coffeeModulesReady()) {
      showCoffeeModuleError();
    }
    await refresh();
  }

  async function init() {
    if (!document.getElementById("hd-app")) return;
    const user = await global.HDashboardAuth.init();
    if (user) {
      await startDashboard();
    }
  }

  function boot() {
    if (!coffeeEngine()) {
      console.warn("[H-Dashboard] HDashboardCoffee not yet defined — waiting for scripts");
    }
    init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof window !== "undefined" ? window : globalThis);