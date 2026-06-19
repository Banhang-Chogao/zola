/**
 * H-Dashboard V2 — Highlands Coffee Life Analytics.
 * Receipt OCR → Coffee DNA, timeline, seasonality, personality.
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
    return HDashboardCoffee.formatVnd(n);
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
    const txs = filteredTransactions.length ? filteredTransactions : allTransactions;
    const payload = HDashboardCoffee.buildCoffeePayload(txs);

    if (window.HDashboardGeo && txs.length) {
      const geo = HDashboardGeo.analyze(txs);
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
    if (!els.meta || !statementMeta) return;
    const s = statementMeta;
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
    const payload = getCoffeePayload();
    renderSummary(payload);
    HDashboardCoffeeUI.renderAll(payload);
    HDashboardCharts.renderAll(payload);

    const geoTxs = filteredTransactions.length ? filteredTransactions : allTransactions;
    if (window.HDashboardGeo && els.geo) {
      window.HDashboardGeo.render(geoTxs, els.geo);
      if (els.geoSummary && payload.geoHint) {
        els.geoSummary.textContent = payload.geoHint;
      }
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