/**
 * Vụ Mùa — agricultural sales tracking + insights dashboard.
 *
 * Orchestrates the Data Entry Module (manual form + table) and the Insights
 * Module (KPIs, charts, narrative). 100% client-side; records live in
 * localStorage via VuMuaStorage. Designed to be extensible for an AI insights
 * engine (see VuMuaInsights.buildNarrative) and a future PDF import.
 */
(function () {
  "use strict";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  const Storage = window.VuMuaStorage;
  const Insights = window.VuMuaInsights;
  const Charts = window.VuMuaCharts;
  const ExportMod = window.VuMuaExport;

  const PAGE_SIZE = 12;
  let page = 1;
  let totalDirty = false; // user manually overrode THÀNH TIỀN

  /* ---------------------------------------------------------------- helpers */

  function num(v) {
    const n = Number(v);
    return isFinite(n) ? n : 0;
  }

  function formatVnd(n) {
    return num(n).toLocaleString("vi-VN") + " ₫";
  }

  function formatNum(n) {
    return num(n).toLocaleString("vi-VN");
  }

  function formatDate(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? m[3] + "/" + m[2] + "/" + m[1] : iso || "—";
  }

  function todayIso() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  let toastTimer = null;
  function toast(msg, type) {
    const el = $("#vm-toast");
    if (!el) return;
    el.textContent = msg;
    el.dataset.type = type || "info";
    el.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("is-visible"), 2600);
  }

  /* ------------------------------------------------------------- data entry */

  function recalcTotal() {
    if (totalDirty) return;
    const q = num($("#vm-quantity").value);
    const p = num($("#vm-unit-price").value);
    if (q > 0 && p > 0) $("#vm-total").value = Math.round(q * p);
  }

  function readForm() {
    return {
      product: $("#vm-product").value.trim(),
      quantity: num($("#vm-quantity").value),
      type: $("#vm-type").value.trim(),
      unitPrice: num($("#vm-unit-price").value),
      total: num($("#vm-total").value),
      buyer: $("#vm-buyer").value.trim(),
      date: $("#vm-date").value || todayIso(),
    };
  }

  function showFormError(msg) {
    const el = $("#vm-form-error");
    if (!el) return;
    if (msg) {
      el.textContent = msg;
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    const rec = readForm();

    if (!rec.product) {
      showFormError("Vui lòng nhập tên hàng hoá.");
      $("#vm-product").focus();
      return;
    }
    if (!(rec.quantity > 0)) {
      showFormError("Số lượng phải lớn hơn 0.");
      $("#vm-quantity").focus();
      return;
    }
    if (!(rec.total > 0)) {
      if (rec.unitPrice > 0 && rec.quantity > 0) {
        rec.total = Math.round(rec.quantity * rec.unitPrice);
      } else {
        showFormError("Nhập đơn giá hoặc thành tiền (> 0).");
        $("#vm-unit-price").focus();
        return;
      }
    }
    if (!rec.unitPrice && rec.quantity > 0) {
      rec.unitPrice = Math.round(rec.total / rec.quantity);
    }

    showFormError("");
    Storage.insert(rec);
    toast("Đã lưu giao dịch", "success");
    page = 1;
    resetForm(true);
    renderAll();
  }

  function resetForm(keepContext) {
    totalDirty = false;
    // Keep buyer/type/date when adding several items in a batch (keepContext).
    const keepBuyer = keepContext ? $("#vm-buyer").value : "";
    const keepType = keepContext ? $("#vm-type").value : "";
    const keepDate = keepContext ? $("#vm-date").value : todayIso();
    $("#vm-form").reset();
    $("#vm-buyer").value = keepBuyer;
    $("#vm-type").value = keepType;
    $("#vm-date").value = keepDate || todayIso();
    $("#vm-total").value = "";
    showFormError("");
    $("#vm-product").focus();
  }

  /* ------------------------------------------------------------------ table */

  function distinctTypes(records) {
    const seen = new Map();
    records.forEach((r) => {
      const k = (r.type || "").trim().toLowerCase();
      if (k && !seen.has(k)) seen.set(k, r.type.trim());
    });
    return Array.from(seen.values()).sort((a, b) => a.localeCompare(b, "vi"));
  }

  function getSorted() {
    return Storage.getAll().slice().sort((a, b) => {
      const da = (a.date || "") + (a.createdAt || "");
      const db = (b.date || "") + (b.createdAt || "");
      return db < da ? -1 : db > da ? 1 : 0;
    });
  }

  function getFiltered() {
    const kw = $("#vm-search").value.trim().toLowerCase();
    const type = $("#vm-filter-type").value;
    const from = $("#vm-filter-from").value;
    const to = $("#vm-filter-to").value;
    return getSorted().filter((r) => {
      if (type && (r.type || "").trim().toLowerCase() !== type.toLowerCase()) return false;
      const d = (r.date || "").slice(0, 10);
      if (from && d < from) return false;
      if (to && d > to) return false;
      if (kw) {
        const hay = (r.product + " " + r.buyer + " " + r.type).toLowerCase();
        if (hay.indexOf(kw) === -1) return false;
      }
      return true;
    });
  }

  function renderTable() {
    const tbody = $("#vm-table-body");
    const rows = getFiltered();
    const total = rows.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (page > pages) page = pages;
    const start = (page - 1) * PAGE_SIZE;
    const slice = rows.slice(start, start + PAGE_SIZE);

    $("#vm-table-count").textContent =
      total + " giao dịch" + (total !== Storage.getAll().length ? " (đã lọc)" : "");

    if (!slice.length) {
      tbody.innerHTML =
        '<tr><td colspan="8" class="vm-table__empty">' +
        (Storage.getAll().length ? "Không có giao dịch khớp bộ lọc." : "Chưa có giao dịch — hãy nhập ở mục phía trên.") +
        "</td></tr>";
    } else {
      tbody.innerHTML = slice
        .map((r, i) => {
          return (
            "<tr>" +
            "<td>" + (start + i + 1) + "</td>" +
            '<td class="vm-table__name">' + escapeHtml(r.product) + "</td>" +
            '<td class="vm-table__num">' + formatNum(r.quantity) + "</td>" +
            "<td>" + (r.type ? '<span class="vm-chip">' + escapeHtml(r.type) + "</span>" : "—") + "</td>" +
            '<td class="vm-table__num">' + formatVnd(r.unitPrice) + "</td>" +
            '<td class="vm-table__num vm-table__total">' + formatVnd(r.total) + "</td>" +
            "<td>" + (escapeHtml(r.buyer) || "—") + "</td>" +
            "<td>" + formatDate(r.date) + "</td>" +
            '<td><button type="button" class="vm-row-del" data-del="' + escapeHtml(r.id) + '" aria-label="Xoá giao dịch">✕</button></td>' +
            "</tr>"
          );
        })
        .join("");
    }
    renderPagination(pages);
  }

  function renderPagination(pages) {
    const wrap = $("#vm-pagination");
    if (pages <= 1) {
      wrap.innerHTML = "";
      return;
    }
    let html = "";
    html += '<button type="button" class="vm-page-btn" data-page="prev"' + (page === 1 ? " disabled" : "") + ">‹</button>";
    html += '<span class="vm-page-info">Trang ' + page + " / " + pages + "</span>";
    html += '<button type="button" class="vm-page-btn" data-page="next"' + (page === pages ? " disabled" : "") + ">›</button>";
    wrap.innerHTML = html;
  }

  function populateTypeFilter() {
    const sel = $("#vm-filter-type");
    const current = sel.value;
    const types = distinctTypes(Storage.getAll());
    sel.innerHTML =
      '<option value="">Tất cả loại</option>' +
      types.map((t) => '<option value="' + escapeHtml(t) + '">' + escapeHtml(t) + "</option>").join("");
    if (types.some((t) => t === current)) sel.value = current;
  }

  function refreshDatalists() {
    const records = Storage.getAll();
    const fill = (id, values) => {
      const dl = $(id);
      if (!dl) return;
      dl.innerHTML = values.map((v) => '<option value="' + escapeHtml(v) + '"></option>').join("");
    };
    const distinct = (field) => {
      const seen = new Map();
      records.forEach((r) => {
        const k = (r[field] || "").trim().toLowerCase();
        if (k && !seen.has(k)) seen.set(k, r[field].trim());
      });
      return Array.from(seen.values());
    };
    fill("#vm-product-list", distinct("product"));
    fill("#vm-type-list", distinct("type"));
    fill("#vm-buyer-list", distinct("buyer"));
  }

  /* --------------------------------------------------------------- insights */

  function kpiCard(label, value, sub) {
    return (
      '<div class="vm-kpi">' +
      '<span class="vm-kpi__label">' + label + "</span>" +
      '<span class="vm-kpi__value">' + value + "</span>" +
      (sub ? '<span class="vm-kpi__sub">' + sub + "</span>" : "") +
      "</div>"
    );
  }

  function renderKpis(s) {
    const range =
      s.dateFrom && s.dateTo
        ? formatDate(s.dateFrom) + " → " + formatDate(s.dateTo)
        : "Chưa có dữ liệu";
    $("#vm-kpis").innerHTML =
      kpiCard("Tổng doanh thu", formatVnd(s.revenue), range) +
      kpiCard("Tổng sản lượng", formatNum(s.quantity), s.types + " loại hàng") +
      kpiCard("Số giao dịch", formatNum(s.orders), "TB " + formatVnd(s.avgOrder) + "/đơn") +
      kpiCard("Sản phẩm", formatNum(s.products), "mặt hàng khác nhau") +
      kpiCard("Người mua", formatNum(s.buyers), "khách hàng") +
      kpiCard("Giá TB / đơn vị", formatVnd(s.avgUnitPrice), "bình quân gia quyền");
  }

  function barRow(label, value, max, valueText, accent) {
    const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
    return (
      '<div class="vm-bar">' +
      '<div class="vm-bar__head"><span class="vm-bar__label">' + escapeHtml(label) + "</span>" +
      '<span class="vm-bar__value">' + valueText + "</span></div>" +
      '<div class="vm-bar__track"><span class="vm-bar__fill' + (accent ? " vm-bar__fill--" + accent : "") + '" style="width:' + pct + '%"></span></div>' +
      "</div>"
    );
  }

  function renderSeasonCards(seasonal) {
    const el = $("#vm-season-cards");
    const totalRev = seasonal.reduce((a, s) => a + s.revenue, 0);
    if (!totalRev) {
      el.innerHTML = '<p class="vm-empty">Chưa đủ dữ liệu cho phân tích mùa vụ.</p>';
      return;
    }
    el.innerHTML = seasonal
      .map((s) => {
        const pct = totalRev ? Math.round((s.revenue / totalRev) * 100) : 0;
        return (
          '<div class="vm-season-card">' +
          '<span class="vm-season-card__name">' + s.label + "</span>" +
          '<span class="vm-season-card__rev">' + formatVnd(s.revenue) + "</span>" +
          '<span class="vm-season-card__meta">' + formatNum(s.quantity) + " sản lượng · " + s.orders + " đơn · " + pct + "%</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderProductList(products) {
    const el = $("#vm-product-table");
    if (!products.length) {
      el.innerHTML = '<p class="vm-empty">Chưa có dữ liệu sản phẩm.</p>';
      return;
    }
    const max = products[0].revenue || 1;
    el.innerHTML = products
      .slice(0, 8)
      .map((p) =>
        barRow(p.label, p.revenue, max, formatVnd(p.revenue) + " · " + formatNum(p.quantity) + " SL", "green")
      )
      .join("");
  }

  function renderBuyerList(buyers) {
    const el = $("#vm-buyer-list-out");
    if (!buyers.length) {
      el.innerHTML = '<p class="vm-empty">Chưa có dữ liệu người mua.</p>';
      return;
    }
    const max = buyers[0].revenue || 1;
    el.innerHTML = buyers
      .slice(0, 8)
      .map((b) =>
        barRow(b.label, b.revenue, max, formatVnd(b.revenue) + " · " + b.orders + " đơn", "amber")
      )
      .join("");
  }

  function renderPriceList(price) {
    const el = $("#vm-price-list");
    if (!price.length) {
      el.innerHTML = '<p class="vm-empty">Chưa có dữ liệu giá.</p>';
      return;
    }
    el.innerHTML =
      '<table class="vm-price-table"><thead><tr><th>Sản phẩm</th><th>Giá TB</th><th>Thấp nhất</th><th>Cao nhất</th></tr></thead><tbody>' +
      price
        .slice(0, 10)
        .map(
          (p) =>
            "<tr><td>" + escapeHtml(p.label) + "</td>" +
            '<td class="vm-table__num">' + formatVnd(p.avg) + "</td>" +
            '<td class="vm-table__num">' + formatVnd(p.min) + "</td>" +
            '<td class="vm-table__num">' + formatVnd(p.max) + "</td></tr>"
        )
        .join("") +
      "</tbody></table>";
  }

  function renderNarrative(narrative) {
    const el = $("#vm-narrative");
    if (!narrative.length) {
      el.innerHTML = "<li>Nhập giao dịch để nhận phân tích tự động.</li>";
      return;
    }
    el.innerHTML = narrative.map((n) => "<li>" + n + "</li>").join("");
  }

  function toggleChart(canvasId, hasData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const section = canvas.closest("[data-vm-chart]");
    if (!section) return;
    section.classList.toggle("vm-panel--empty", !hasData);
  }

  function renderInsights() {
    const records = Storage.getAll();
    const payload = Insights.compute(records);

    renderKpis(payload.summary);
    renderSeasonCards(payload.seasonal);
    renderProductList(payload.productDemand);
    renderBuyerList(payload.buyerPatterns);
    renderPriceList(payload.pricePerformance);
    renderNarrative(payload.narrative);

    toggleChart("vm-chart-revenue", payload.revenueTrend.labels.length > 0);
    toggleChart("vm-chart-season", payload.seasonal.some((s) => s.revenue > 0));
    toggleChart("vm-chart-product", payload.productDemand.length > 0);
    toggleChart("vm-chart-buyer", payload.buyerPatterns.length > 0);

    if (Charts) Charts.renderAll(payload);

    $("#vm-app").classList.toggle("vu-mua--empty", records.length === 0);
  }

  /* ----------------------------------------------------------------- export */

  function wireExport() {
    $("#vm-export-json").addEventListener("click", () => {
      const records = Storage.getAll();
      if (!records.length) return toast("Chưa có dữ liệu để xuất.", "warn");
      ExportMod.exportJson(records);
      toast("Đã xuất JSON", "success");
    });
    $("#vm-export-csv").addEventListener("click", () => {
      const records = Storage.getAll();
      if (!records.length) return toast("Chưa có dữ liệu để xuất.", "warn");
      ExportMod.exportCsv(records);
      toast("Đã xuất CSV", "success");
    });
    $("#vm-import-btn").addEventListener("click", () => $("#vm-import").click());
    $("#vm-import").addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      ExportMod.importJson(file)
        .then((records) => {
          const added = Storage.merge(records);
          toast("Đã nhập " + added + " giao dịch", "success");
          page = 1;
          renderAll();
        })
        .catch((err) => toast(err.message || "Nhập thất bại", "warn"))
        .finally(() => {
          e.target.value = "";
        });
    });
    $("#vm-clear").addEventListener("click", () => {
      if (!Storage.getAll().length) return;
      if (!window.confirm("Xoá toàn bộ giao dịch Vụ Mùa trên trình duyệt này? Hãy export trước nếu cần.")) return;
      Storage.clearAll();
      page = 1;
      renderAll();
      toast("Đã xoá toàn bộ dữ liệu", "info");
    });
  }

  /* ------------------------------------------------------------------- init */

  function renderAll() {
    populateTypeFilter();
    refreshDatalists();
    renderTable();
    renderInsights();
  }

  function init() {
    if (!$("#vm-app") || !Storage) return;

    $("#vm-date").value = todayIso();

    $("#vm-form").addEventListener("submit", handleSubmit);
    $("#vm-form-reset").addEventListener("click", () => resetForm(false));
    $("#vm-quantity").addEventListener("input", recalcTotal);
    $("#vm-unit-price").addEventListener("input", recalcTotal);
    $("#vm-total").addEventListener("input", () => {
      totalDirty = true;
    });

    ["#vm-search", "#vm-filter-type", "#vm-filter-from", "#vm-filter-to"].forEach((sel) => {
      const el = $(sel);
      const ev = el.tagName === "SELECT" || el.type === "date" ? "change" : "input";
      el.addEventListener(ev, () => {
        page = 1;
        renderTable();
      });
    });

    $("#vm-table-body").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-del]");
      if (!btn) return;
      Storage.remove(btn.dataset.del);
      renderAll();
      toast("Đã xoá giao dịch", "info");
    });

    $("#vm-pagination").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-page]");
      if (!btn || btn.disabled) return;
      page += btn.dataset.page === "next" ? 1 : -1;
      if (page < 1) page = 1;
      renderTable();
    });

    wireExport();
    renderAll();

    // Charts.js loads with `defer`; re-render once it (and Chart.js CDN) is ready.
    if (Charts && !Charts.hasChart()) {
      let tries = 0;
      const poll = setInterval(() => {
        tries += 1;
        if (Charts.hasChart()) {
          clearInterval(poll);
          renderInsights();
        } else if (tries > 40) {
          clearInterval(poll);
        }
      }, 150);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
