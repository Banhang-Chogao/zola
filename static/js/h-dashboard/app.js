/**
 * H-Dashboard V2 — Highlands Coffee Life Analytics.
 * Receipt OCR → Coffee DNA, timeline, seasonality, personality.
 * Multi-upload · merge reports · print-to-PDF export.
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
  let selectedImportFiles = [];

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
    els.exportMonthlyPdf = $("#hd-export-monthly-pdf");
    els.clearSession = $("#hd-clear-session");
    els.importInput = $("#hd-import-reports");
    els.importBtn = $("#hd-import-reports-btn");
    els.importFiles = $("#hd-import-reports-files");
    els.importStatus = $("#hd-import-reports-status");
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

  function setImportStatus(msg, type) {
    if (!els.importStatus) return;
    els.importStatus.textContent = msg;
    els.importStatus.dataset.type = type || "info";
  }

  function updateExportButtons() {
    const hasData = allTransactions.length > 0;
    [els.exportJson, els.exportCsv, els.exportPdf, els.exportMonthlyPdf].forEach((btn) => {
      if (btn) btn.disabled = !hasData;
    });
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
      receipts_catalog: receiptsCatalog,
    };
  }

  function renderMeta() {
    if (!els.meta) return;
    const statements = receiptsCatalog.statements || [];
    if (!statements.length && statementMeta) {
      statements.push(statementMeta);
    }
    if (!statements.length) {
      els.meta.innerHTML =
        '<p class="hd-meta__empty">Upload PDF hóa đơn để hiển thị cửa hàng, ngày xuất và tổng tiền.</p>';
      return;
    }

    if (statements.length === 1) {
      els.meta.innerHTML = `<div class="hd-meta__grid">${renderMetaCells(statements[0])}</div>`;
      return;
    }

    const cards = statements
      .map((s) => renderMetaCard(s))
      .join("");
    els.meta.innerHTML = `
      <p class="hd-meta__aggregate">${statements.length} hóa đơn trong phiên</p>
      <div class="hd-meta__grid hd-meta__grid--multi">${cards}</div>`;
  }

  function renderMetaCells(s) {
    const dateLine = s.invoice_time
      ? `${s.invoice_date || "—"} ${s.invoice_time}`
      : s.invoice_date || "—";
    return `
        <div><span>Cửa hàng</span><strong>${escapeHtml(s.merchant || "—")}</strong><em>${escapeHtml(s.address || s.service_type || "")}</em></div>
        <div><span>Mã hóa đơn</span><strong>${escapeHtml(s.invoice_no || "—")}</strong><em>${escapeHtml(s.pos || "")}</em></div>
        <div><span>Ngày xuất</span><strong>${escapeHtml(dateLine)}</strong><em>${escapeHtml(s.currency || "VND")}</em></div>
        <div><span>Thu ngân</span><strong>${escapeHtml(s.cashier || "—")}</strong><em>${s.pager ? "Pager " + escapeHtml(s.pager) : ""}</em></div>
        <div><span>Tổng hóa đơn</span><strong>${fmt(s.total || 0)}</strong><em>${s.item_count || 0} mặt hàng</em></div>
        <div><span>Thanh toán</span><strong>${escapeHtml(s.payment_method || "—")}</strong><em>${s.shop_id ? "Shop " + escapeHtml(s.shop_id) : ""}</em></div>`;
  }

  function renderMetaCard(s) {
    return `<div class="hd-meta__card">${renderMetaCells(s)}</div>`;
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

  function statementSnapshot(stmt) {
    return {
      merchant: stmt.merchant,
      address: stmt.address,
      invoice_no: stmt.invoice_no,
      invoice_date: stmt.invoice_date,
      invoice_time: stmt.invoice_time,
      pos: stmt.pos,
      currency: stmt.currency,
      total: stmt.total,
      item_count: stmt.item_count,
      via_ocr: stmt.via_ocr,
    };
  }

  async function wipeSessionData() {
    await global.HDashboardStorage.clearAll();
    allTransactions = [];
    filteredTransactions = [];
    receiptsCatalog = { fingerprints: [], statements: [] };
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

  async function runClearSession() {
    if (!allTransactions.length) return;
    if (
      !confirm(
        "Xóa toàn bộ dữ liệu phiên trên trình duyệt này? Hành động không thể hoàn tác."
      )
    ) {
      return;
    }
    await wipeSessionData();
    setStatus("Đã xóa phiên — dữ liệu chỉ tồn tại local, không lưu server.", "success");
  }

  async function runExport(format, printOpts) {
    if (!allTransactions.length) return;
    const labels = {
      pdf: "PDF báo cáo",
      csv: "CSV",
      json: "JSON",
      monthly: "Monthly Combined PDF",
    };
    const label = labels[format] || "file";

    const btnMap = {
      pdf: els.exportPdf,
      csv: els.exportCsv,
      json: els.exportJson,
      monthly: els.exportMonthlyPdf,
    };
    const btn = btnMap[format];
    if (btn) btn.disabled = true;

    try {
      if (!coffeeModulesReady()) {
        throw new Error(COFFEE_MODULE_MSG);
      }
      const insights = getInsightsPayload();
      let payload;

      if (format === "pdf" || format === "monthly") {
        payload = await global.HDashboardExport.exportPdfWithJson(
          allTransactions,
          insights,
          format === "monthly" ? { mode: "monthly" } : { mode: "full" }
        );
        setStatus(
          `Đã tải ${label} + JSON · phiên giữ nguyên · trace: ${payload.watermark}`,
          "success"
        );
      } else {
        payload = await global.HDashboardExport.exportOnly(format, allTransactions, insights);
        setStatus(`Đã tải ${label} · phiên giữ nguyên · trace: ${payload.watermark}`, "success");
      }
    } catch (err) {
      console.error(err);
      setStatus(err.message || `Xuất ${label} thất bại.`, "error");
    } finally {
      updateExportButtons();
    }
  }

  function isSupportedUpload(file) {
    return /\.(pdf|png|jpe?g)$/i.test(file.name);
  }

  async function parseUploadFile(file, onStatus) {
    const buffer = await file.arrayBuffer();
    const parser = global.HDashboardInvoiceParser;
    if (/\.(png|jpe?g)$/i.test(file.name)) {
      return parser.parseInvoiceImageArrayBuffer(buffer, { onStatus });
    }
    return parser.parseInvoicePdfArrayBuffer(buffer, { onStatus });
  }

  async function processOneFile(file, fpSet) {
    const parsed = await parseUploadFile(file, (msg) =>
      setStatus(`[${file.name}] ${msg}`, "info")
    );

    if (!parsed || !Array.isArray(parsed.transactions) || !parsed.transactions.length) {
      throw new Error("Không tìm thấy mặt hàng trong " + file.name);
    }

    const fp =
      parsed.receipt_fingerprint ||
      (await global.HDashboardInvoiceParser.buildReceiptFingerprint(parsed.statement));

    if (fpSet.has(fp)) {
      const inv = parsed.statement.invoice_no || "?";
      return { status: "duplicate", invoice_no: inv, parsed };
    }

    const existingIds = await global.HDashboardStorage.getAllTransactionIds();
    const toInsert = [];
    let skippedTx = 0;
    for (const tx of parsed.transactions) {
      if (existingIds.has(tx.transaction_id)) {
        skippedTx++;
      } else {
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
      skippedTx,
      via_ocr: parsed.via_ocr,
      reconciliation: parsed.reconciliation,
      parsed,
    };
  }

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []).filter(isSupportedUpload).slice(0, MAX_BATCH_FILES);
    if (!files.length) {
      setStatus("Chọn file PDF hoặc ảnh (.png/.jpg) hóa đơn Highlands.", "error");
      return;
    }

    if (fileList && fileList.length > MAX_BATCH_FILES) {
      setStatus(`Chỉ xử lý tối đa ${MAX_BATCH_FILES} file mỗi lần.`, "info");
    }

    const stats = { selected: files.length, processed: 0, duplicate: 0, failed: 0 };
    const fpSet = new Set(receiptsCatalog.fingerprints || []);
    const dupMessages = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setStatus(
        `Đang xử lý ${i + 1}/${files.length}: ${file.name}…`,
        "info"
      );
      try {
        const result = await processOneFile(file, fpSet);
        if (result.status === "duplicate") {
          stats.duplicate++;
          dupMessages.push("Skipped duplicate receipt #" + result.invoice_no);
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

    let msg = `Selected: ${stats.selected} · Processed: ${stats.processed} · Duplicate: ${stats.duplicate} · Failed OCR: ${stats.failed}`;
    if (dupMessages.length) msg += " · " + dupMessages.join(" · ");
    setStatus(msg, stats.failed ? "error" : "success");

    if (els.upload) els.upload.value = "";
    if (els.uploadBatch) {
      els.uploadBatch.textContent = files.map((f) => f.name).join(" · ");
      els.uploadBatch.hidden = false;
    }
  }

  function updateImportUi() {
    const count = selectedImportFiles.length;
    if (els.importBtn) els.importBtn.disabled = count === 0;
    if (els.importFiles) {
      if (count) {
        els.importFiles.hidden = false;
        els.importFiles.textContent =
          count + " file: " + selectedImportFiles.map((f) => f.name).join(" · ");
      } else {
        els.importFiles.hidden = true;
        els.importFiles.textContent = "";
      }
    }
  }

  async function runImportReports() {
    if (!selectedImportFiles.length || !global.HDashboardImport) return;
    if (els.importBtn) els.importBtn.disabled = true;
    setImportStatus("Đang merge " + selectedImportFiles.length + " báo cáo…", "info");

    try {
      const result = await global.HDashboardImport.mergeImportedFiles(selectedImportFiles, {
        onStatus: setImportStatus,
        getCatalog: () => global.HDashboardStorage.getReceiptsCatalog(),
        saveCatalog: (c) => global.HDashboardStorage.setReceiptsCatalog(c),
        getExistingIds: () => global.HDashboardStorage.getAllTransactionIds(),
        insertTx: (txs) => global.HDashboardStorage.insertTransactions(txs),
        buildFingerprint: (stmt) =>
          global.HDashboardInvoiceParser.buildReceiptFingerprint(stmt),
      });

      receiptsCatalog = await global.HDashboardStorage.getReceiptsCatalog();
      await refresh();
      renderMeta();
      renderReconcile();

      let msg =
        "Đã merge " +
        result.merged +
        " mặt hàng · bỏ qua trùng " +
        result.duplicates +
        " · skipped tx " +
        result.skipped;
      if (result.warnings.length) msg += " · " + result.warnings.join(" · ");
      setImportStatus(msg, result.warnings.length ? "error" : "success");
      setStatus("Merge báo cáo xong — analytics đã cập nhật.", "success");

      selectedImportFiles = [];
      if (els.importInput) els.importInput.value = "";
      updateImportUi();
    } catch (err) {
      console.error(err);
      setImportStatus(err.message || "Import thất bại.", "error");
    } finally {
      updateImportUi();
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

  let printTableBackup = null;

  function renderAllRowsForPrint() {
    if (!els.tbody) return;
    printTableBackup = els.tbody.innerHTML;
    const txs = filteredTransactions.length ? filteredTransactions : allTransactions;
    if (!txs.length) return;
    els.tbody.innerHTML = txs
      .map((t, i) => {
        const txnDate = (window.ZolaDateTime && window.ZolaDateTime.formatTxnDate(t.date)) || "—";
        const desc = t.description ? escapeHtml(t.description) : "—";
        const store = t.merchant ? escapeHtml(t.merchant) : "—";
        return `<tr>
          <td>${i + 1}</td>
          <td>${txnDate}</td>
          <td class="hd-table__desc">${desc}</td>
          <td>${t.qty || 1}</td>
          <td class="hd-amount">${t.unit_price ? fmt(t.unit_price).replace(" ₫", "") : "—"}</td>
          <td class="hd-amount hd-amount--expense">${t.debit ? fmt(t.debit).replace(" ₫", "") : "—"}</td>
          <td>${store}</td>
        </tr>`;
      })
      .join("");
    if (els.pagination) els.pagination.style.display = "none";
  }

  function restoreTableAfterPrint() {
    if (printTableBackup && els.tbody) {
      els.tbody.innerHTML = printTableBackup;
      printTableBackup = null;
    }
    if (els.pagination) els.pagination.style.display = "";
    renderTable();
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
    if (els.exportMonthlyPdf)
      els.exportMonthlyPdf.addEventListener("click", () => runExport("monthly"));
    if (els.clearSession) els.clearSession.addEventListener("click", runClearSession);

    if (els.importInput) {
      els.importInput.addEventListener("change", (e) => {
        selectedImportFiles = Array.from(e.target.files || []);
        updateImportUi();
      });
    }
    if (els.importBtn) els.importBtn.addEventListener("click", runImportReports);

    document.addEventListener("hd-before-print", renderAllRowsForPrint);
    document.addEventListener("hd-after-print", restoreTableAfterPrint);
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
    renderMeta();
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