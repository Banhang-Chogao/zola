/* vu-mua/app.js — Vụ Mùa: nhập liệu + phân tích bán hàng nông sản theo mùa vụ.
 *
 * 100% client-side: dữ liệu chỉ lưu trong localStorage của trình duyệt, KHÔNG
 * upload server (đồng bộ mô hình static-site + H/L/O-Dashboard). Không phụ thuộc
 * thư viện ngoài — biểu đồ vẽ bằng SVG nội bộ → CSP-safe, nhẹ.
 *
 * Schema giao dịch: { id, name, qty, type, unitPrice, amount, buyer, date }
 *   date = "YYYY-MM-DD". amount tự tính qty*unitPrice nếu bỏ trống.
 *
 * Mở rộng: window.VuMua expose API (getEntries/addEntry/computeInsights…) +
 * hook AI insights (renderAI) cho tương lai.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "vu-mua-entries-v1";
  var root = document.getElementById("vm-app");
  if (!root) return;

  // ---- Format helpers ------------------------------------------------------
  var vnd = new Intl.NumberFormat("vi-VN");
  function fMoney(n) { return vnd.format(Math.round(n || 0)) + " đ"; }
  function fNum(n) {
    n = +n || 0;
    return Number.isInteger(n) ? vnd.format(n) : vnd.format(Math.round(n * 100) / 100);
  }
  function fDate(iso) {
    if (!iso) return "";
    var p = String(iso).slice(0, 10).split("-");
    return p.length === 3 ? p[2] + "/" + p[1] + "/" + p[0] : iso;
  }
  function monthKey(iso) { return String(iso || "").slice(0, 7); } // YYYY-MM
  function monthLabel(key) { var p = key.split("-"); return p.length === 2 ? p[1] + "/" + p[0] : key; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // ---- Storage -------------------------------------------------------------
  var entries = [];
  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      entries = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(entries)) entries = [];
    } catch (e) { entries = []; }
  }
  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(entries)); } catch (e) {}
  }

  // ---- CRUD ----------------------------------------------------------------
  function normalize(e) {
    var qty = +e.qty || 0;
    var unitPrice = +e.unitPrice || 0;
    var amount = (e.amount === "" || e.amount == null) ? qty * unitPrice : (+e.amount || 0);
    return {
      id: e.id || ("vm-" + Date.now() + "-" + Math.random().toString(36).slice(2, 7)),
      name: (e.name || "").trim() || "(không tên)",
      qty: qty,
      type: (e.type || "").trim() || "Khác",
      unitPrice: unitPrice,
      amount: amount,
      buyer: (e.buyer || "").trim() || "(ẩn danh)",
      date: (e.date || "").slice(0, 10)
    };
  }
  function addEntry(e) {
    entries.push(normalize(e));
    entries.sort(function (a, b) { return (a.date < b.date ? -1 : a.date > b.date ? 1 : 0); });
    save(); render();
  }
  function deleteEntry(id) {
    entries = entries.filter(function (e) { return e.id !== id; });
    save(); render();
  }
  function clearAll() {
    if (entries.length && !window.confirm("Xoá toàn bộ giao dịch Vụ Mùa?")) return;
    entries = []; save(); render();
  }

  // ---- Insights (aggregation) ---------------------------------------------
  function computeInsights() {
    var totalRevenue = 0, totalQty = 0;
    var byMonth = {}, byDate = {}, byProduct = {}, byBuyer = {};
    var priceSum = {}, priceCnt = {}; // theo loại
    var buyers = {}, products = {};

    entries.forEach(function (e) {
      totalRevenue += e.amount;
      totalQty += e.qty;
      byMonth[monthKey(e.date)] = (byMonth[monthKey(e.date)] || 0) + e.amount;
      byDate[e.date] = (byDate[e.date] || 0) + e.amount;
      byProduct[e.name] = (byProduct[e.name] || 0) + e.amount;
      byBuyer[e.buyer] = (byBuyer[e.buyer] || 0) + e.amount;
      priceSum[e.type] = (priceSum[e.type] || 0) + e.unitPrice;
      priceCnt[e.type] = (priceCnt[e.type] || 0) + 1;
      buyers[e.buyer] = 1; products[e.name] = 1;
    });

    function pairsSortedByKey(obj) {
      return Object.keys(obj).sort().map(function (k) { return { label: k, value: obj[k] }; });
    }
    function pairsTop(obj, n, labelFn) {
      return Object.keys(obj)
        .map(function (k) { return { label: labelFn ? labelFn(k) : k, value: obj[k] }; })
        .sort(function (a, b) { return b.value - a.value; })
        .slice(0, n || 6);
    }
    var avgPrice = {};
    Object.keys(priceSum).forEach(function (t) { avgPrice[t] = priceSum[t] / priceCnt[t]; });

    return {
      count: entries.length,
      totalRevenue: totalRevenue,
      totalQty: totalQty,
      avgUnit: totalQty ? totalRevenue / totalQty : 0,
      buyerCount: Object.keys(buyers).length,
      productCount: Object.keys(products).length,
      seasonal: pairsSortedByKey(byMonth).map(function (p) { return { label: monthLabel(p.label), value: p.value, raw: p.label }; }),
      trend: Object.keys(byDate).sort().map(function (d) { return { label: fDate(d), value: byDate[d] }; }),
      demand: pairsTop(byProduct, 6),
      buyers: pairsTop(byBuyer, 6),
      price: pairsTop(avgPrice, 8)
    };
  }

  // ---- SVG charts ----------------------------------------------------------
  function emptyChart(msg) {
    return '<p class="vm-chart__empty">' + esc(msg || "Chưa đủ dữ liệu.") + "</p>";
  }

  function vBars(data, fmt) {
    if (!data || !data.length) return emptyChart();
    var H = 190, padB = 46, padT = 22, slot = 54;
    var W = Math.max(data.length * slot, 240);
    var max = Math.max.apply(null, data.map(function (d) { return d.value; })) || 1;
    var bw = slot * 0.6;
    var bars = data.map(function (d, i) {
      var bh = Math.max((d.value / max) * (H - padB - padT), d.value > 0 ? 2 : 0);
      var x = i * slot + (slot - bw) / 2;
      var y = H - padB - bh;
      return (
        '<rect class="vm-bar" x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) +
        '" height="' + bh.toFixed(1) + '" rx="4"></rect>' +
        '<text class="vm-bar-val" x="' + (x + bw / 2).toFixed(1) + '" y="' + (y - 6).toFixed(1) + '">' + esc(fmt(d.value)) + "</text>" +
        '<text class="vm-bar-lbl" x="' + (x + bw / 2).toFixed(1) + '" y="' + (H - padB + 16) + '">' + esc(d.label) + "</text>"
      );
    }).join("");
    return '<svg class="vm-svg" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="xMinYMid meet" role="img">' + bars + "</svg>";
  }

  function hBars(data, fmt) {
    if (!data || !data.length) return emptyChart();
    var max = Math.max.apply(null, data.map(function (d) { return d.value; })) || 1;
    var rowH = 34, W = 300, labelW = 110, valW = 8, barMax = W - labelW - 4;
    var H = data.length * rowH + 6;
    var rows = data.map(function (d, i) {
      var bw = Math.max((d.value / max) * barMax, d.value > 0 ? 3 : 0);
      var y = i * rowH + 6;
      return (
        '<text class="vm-hbar-lbl" x="0" y="' + (y + rowH / 2) + '">' + esc(d.label.length > 16 ? d.label.slice(0, 15) + "…" : d.label) + "</text>" +
        '<rect class="vm-bar" x="' + labelW + '" y="' + (y + 5) + '" width="' + bw.toFixed(1) + '" height="' + (rowH - 14) + '" rx="4"></rect>' +
        '<text class="vm-hbar-val" x="' + (labelW + bw + valW).toFixed(1) + '" y="' + (y + rowH / 2) + '">' + esc(fmt(d.value)) + "</text>"
      );
    }).join("");
    return '<svg class="vm-svg vm-svg--h" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="xMinYMin meet" role="img">' + rows + "</svg>";
  }

  function lineChart(data, fmt) {
    if (!data || data.length < 2) return data && data.length === 1 ? vBars(data, fmt) : emptyChart();
    var H = 190, padB = 46, padT = 22, padL = 6, W = Math.max(data.length * 56, 260);
    var max = Math.max.apply(null, data.map(function (d) { return d.value; })) || 1;
    var n = data.length, span = (W - padL * 2) / (n - 1);
    var pts = data.map(function (d, i) {
      var x = padL + i * span;
      var y = (H - padB) - (d.value / max) * (H - padB - padT);
      return { x: x, y: y, d: d };
    });
    var line = pts.map(function (p, i) { return (i ? "L" : "M") + p.x.toFixed(1) + " " + p.y.toFixed(1); }).join(" ");
    var area = "M" + pts[0].x.toFixed(1) + " " + (H - padB) + " " + line.slice(1) + " L" + pts[n - 1].x.toFixed(1) + " " + (H - padB) + " Z";
    var dots = pts.map(function (p) {
      return (
        '<circle class="vm-dot" cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="3"></circle>' +
        '<text class="vm-bar-lbl" x="' + p.x.toFixed(1) + '" y="' + (H - padB + 16) + '">' + esc(p.d.label) + "</text>"
      );
    }).join("");
    return (
      '<svg class="vm-svg" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="xMinYMid meet" role="img">' +
      '<path class="vm-area" d="' + area + '"></path>' +
      '<path class="vm-line" d="' + line + '" fill="none"></path>' + dots + "</svg>"
    );
  }

  // ---- Render --------------------------------------------------------------
  var tbody = root.querySelector("[data-vm-tbody]");
  var countEl = root.querySelector("[data-vm-count]");
  var insightsEl = root.querySelector("[data-vm-insights]");
  var kpisEl = root.querySelector("[data-vm-kpis]");

  function renderTable() {
    if (!entries.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="vm-table__empty">Chưa có giao dịch — nhập ở trên hoặc nạp dữ liệu mẫu.</td></tr>';
      return;
    }
    tbody.innerHTML = entries.map(function (e) {
      return (
        "<tr>" +
        "<td>" + esc(e.name) + "</td>" +
        '<td class="vm-num">' + fNum(e.qty) + "</td>" +
        "<td>" + esc(e.type) + "</td>" +
        '<td class="vm-num">' + fMoney(e.unitPrice) + "</td>" +
        '<td class="vm-num vm-strong">' + fMoney(e.amount) + "</td>" +
        "<td>" + esc(e.buyer) + "</td>" +
        "<td>" + fDate(e.date) + "</td>" +
        '<td class="vm-num"><button class="vm-del" type="button" data-vm-del="' + e.id + '" aria-label="Xoá giao dịch">✕</button></td>' +
        "</tr>"
      );
    }).join("");
  }

  function kpiCard(label, value, sub) {
    return (
      '<div class="vm-kpi">' +
      '<span class="vm-kpi__label">' + esc(label) + "</span>" +
      '<span class="vm-kpi__value">' + esc(value) + "</span>" +
      (sub ? '<span class="vm-kpi__sub">' + esc(sub) + "</span>" : "") +
      "</div>"
    );
  }

  function setChart(name, html, caption) {
    var box = root.querySelector('[data-vm-chart="' + name + '"]');
    var cap = root.querySelector('[data-vm-cap="' + name + '"]');
    if (box) box.innerHTML = html;
    if (cap) cap.textContent = caption || "";
  }

  function renderInsights() {
    if (!entries.length) { insightsEl.hidden = true; return; }
    insightsEl.hidden = false;
    var s = computeInsights();

    kpisEl.innerHTML =
      kpiCard("Tổng doanh thu", fMoney(s.totalRevenue)) +
      kpiCard("Số giao dịch", fNum(s.count)) +
      kpiCard("Tổng số lượng", fNum(s.totalQty)) +
      kpiCard("Đơn giá TB / đơn vị", fMoney(s.avgUnit)) +
      kpiCard("Người mua", fNum(s.buyerCount)) +
      kpiCard("Mặt hàng", fNum(s.productCount));

    // Seasonal
    var bestMonth = s.seasonal.slice().sort(function (a, b) { return b.value - a.value; })[0];
    setChart("seasonal", vBars(s.seasonal, fMoney),
      bestMonth ? "Mùa vụ cao điểm: " + bestMonth.label + " (" + fMoney(bestMonth.value) + ")." : "");

    // Trend
    setChart("trend", lineChart(s.trend, fMoney),
      s.trend.length ? "Theo dõi doanh thu qua " + s.trend.length + " ngày có giao dịch." : "");

    // Product demand
    var topProd = s.demand[0];
    setChart("demand", hBars(s.demand, fMoney),
      topProd ? "Mặt hàng bán chạy nhất: " + topProd.label + "." : "");

    // Buyers
    var topBuyer = s.buyers[0];
    setChart("buyers", hBars(s.buyers, fMoney),
      topBuyer ? "Khách mua nhiều nhất: " + topBuyer.label + "." : "");

    // Price performance
    var hi = s.price.slice().sort(function (a, b) { return b.value - a.value; })[0];
    setChart("price", vBars(s.price, fMoney),
      hi ? "Loại có đơn giá TB cao nhất: " + hi.label + " (" + fMoney(hi.value) + ")." : "");

    renderAI(s); // hook mở rộng
  }

  function render() {
    renderTable();
    if (countEl) countEl.textContent = entries.length + " giao dịch";
    renderInsights();
  }

  // ---- AI insights hook (placeholder, extensible) --------------------------
  function renderAI(/* stats */) {
    var box = root.querySelector("[data-vm-ai]");
    if (!box) return;
    box.hidden = true; box.innerHTML = "";
    // Tương lai: bơm nhận định AI (gọi backend/LLM) vào đây, set box.hidden=false.
  }

  // ---- Export --------------------------------------------------------------
  function download(filename, text, type) {
    var blob = new Blob([text], { type: type || "text/plain;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
  function exportJSON() {
    download("vu-mua-" + Date.now() + ".json", JSON.stringify(entries, null, 2), "application/json");
  }
  function exportCSV() {
    var head = ["Tên hàng hoá", "Số lượng", "Loại", "Đơn giá", "Thành tiền", "Người mua", "Ngày mua"];
    var rows = entries.map(function (e) {
      return [e.name, e.qty, e.type, e.unitPrice, e.amount, e.buyer, e.date].map(function (v) {
        v = String(v == null ? "" : v);
        return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
      }).join(",");
    });
    download("vu-mua-" + Date.now() + ".csv", "﻿" + head.join(",") + "\n" + rows.join("\n"), "text/csv;charset=utf-8");
  }

  // ---- Sample data ---------------------------------------------------------
  function loadSample() {
    if (entries.length && !window.confirm("Thêm dữ liệu mẫu vào danh sách hiện tại?")) return;
    [
      { name: "Gạo ST25", qty: 50, type: "Gạo", unitPrice: 32000, buyer: "Cô Lan", date: "2026-01-12" },
      { name: "Gạo ST25", qty: 80, type: "Gạo", unitPrice: 32000, buyer: "Anh Hùng", date: "2026-02-03" },
      { name: "Xoài cát", qty: 120, type: "Trái cây", unitPrice: 28000, buyer: "Chị Mai", date: "2026-03-18" },
      { name: "Sầu riêng", qty: 60, type: "Trái cây", unitPrice: 85000, buyer: "Anh Hùng", date: "2026-05-09" },
      { name: "Cà phê nhân", qty: 200, type: "Cà phê", unitPrice: 95000, buyer: "Vựa Tâm", date: "2026-05-22" },
      { name: "Gạo ST25", qty: 100, type: "Gạo", unitPrice: 33000, buyer: "Vựa Tâm", date: "2026-06-02" },
      { name: "Xoài cát", qty: 90, type: "Trái cây", unitPrice: 30000, buyer: "Cô Lan", date: "2026-06-15" }
    ].forEach(function (e) { entries.push(normalize(e)); });
    entries.sort(function (a, b) { return (a.date < b.date ? -1 : a.date > b.date ? 1 : 0); });
    save(); render();
  }

  // ---- Wiring --------------------------------------------------------------
  var form = root.querySelector("[data-vm-form]");
  if (form) {
    var qtyI = form.elements.qty, priceI = form.elements.unitPrice, amountI = form.querySelector("[data-vm-amount]");
    function autoAmount() {
      if (!amountI || amountI.dataset.touched === "1") return;
      var q = +qtyI.value || 0, p = +priceI.value || 0;
      if (q && p) amountI.value = q * p;
    }
    if (qtyI) qtyI.addEventListener("input", autoAmount);
    if (priceI) priceI.addEventListener("input", autoAmount);
    if (amountI) amountI.addEventListener("input", function () { amountI.dataset.touched = "1"; });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var f = form.elements;
      if (!f.name.value.trim() || !(+f.qty.value > 0) || !(+f.unitPrice.value >= 0) || !f.date.value) {
        window.alert("Vui lòng nhập đủ: Tên hàng hoá, Số lượng, Đơn giá, Ngày mua.");
        return;
      }
      addEntry({
        name: f.name.value, qty: f.qty.value, type: f.type.value,
        unitPrice: f.unitPrice.value, amount: f.amount.value,
        buyer: f.buyer.value, date: f.date.value
      });
      form.reset();
      if (amountI) amountI.dataset.touched = "";
      f.name.focus();
    });
  }

  // Table delete (event delegation)
  if (tbody) {
    tbody.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-vm-del]");
      if (btn) deleteEntry(btn.getAttribute("data-vm-del"));
    });
  }

  // Toolbar
  root.querySelectorAll("[data-vm-action]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var a = btn.getAttribute("data-vm-action");
      if (a === "sample") loadSample();
      else if (a === "export-json") exportJSON();
      else if (a === "export-csv") exportCSV();
      else if (a === "clear") clearAll();
    });
  });

  // PDF placeholder (chưa hoạt động)
  var pdf = root.querySelector("[data-vm-pdf]");
  if (pdf) pdf.addEventListener("click", function () {
    window.alert("Tính năng đọc PDF đang được phát triển. Hiện tại vui lòng nhập tay.");
  });

  // ---- Public API ----------------------------------------------------------
  window.VuMua = {
    getEntries: function () { return entries.slice(); },
    addEntry: addEntry,
    deleteEntry: deleteEntry,
    clearAll: clearAll,
    computeInsights: computeInsights,
    exportJSON: exportJSON,
    exportCSV: exportCSV,
    render: render
  };

  load();
  render();
})();
