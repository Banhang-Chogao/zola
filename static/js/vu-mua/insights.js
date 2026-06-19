/**
 * Vụ Mùa — insights engine (rule-based, H-Dashboard style).
 *
 * Pure functions: `compute(records)` returns the full analytics payload used by
 * the KPI cards, charts and narrative. No DOM, no network — easy to unit test
 * and a clean seam for a future AI insights engine (extend `buildNarrative`).
 */
(function (global) {
  "use strict";

  // Mùa vụ nông nghiệp Việt Nam (xấp xỉ theo tháng dương lịch). Mọi tháng đều
  // thuộc đúng một mùa để gom doanh thu theo mùa vụ.
  const SEASONS = [
    { id: "dong-xuan", label: "Đông Xuân", months: [12, 1, 2, 3, 4] },
    { id: "he-thu", label: "Hè Thu", months: [5, 6, 7, 8] },
    { id: "mua", label: "Vụ Mùa", months: [9, 10, 11] },
  ];

  function seasonOfMonth(month) {
    for (const s of SEASONS) {
      if (s.months.indexOf(month) !== -1) return s;
    }
    return SEASONS[0];
  }

  function num(v) {
    const n = Number(v);
    return isFinite(n) ? n : 0;
  }

  function norm(s) {
    return String(s == null ? "" : s).trim().toLowerCase();
  }

  function monthOf(dateStr) {
    // dateStr ISO yyyy-mm-dd → month number 1..12 (0 if unknown).
    const m = /^\d{4}-(\d{2})/.exec(dateStr || "");
    return m ? parseInt(m[1], 10) : 0;
  }

  function monthKey(dateStr) {
    return (dateStr || "").slice(0, 7); // yyyy-mm
  }

  function computeSummary(records) {
    let revenue = 0;
    let quantity = 0;
    const products = new Set();
    const buyers = new Set();
    const types = new Set();
    let dateFrom = "";
    let dateTo = "";

    records.forEach((r) => {
      revenue += num(r.total);
      quantity += num(r.quantity);
      if (norm(r.product)) products.add(norm(r.product));
      if (norm(r.buyer)) buyers.add(norm(r.buyer));
      if (norm(r.type)) types.add(norm(r.type));
      const d = (r.date || "").slice(0, 10);
      if (d) {
        if (!dateFrom || d < dateFrom) dateFrom = d;
        if (!dateTo || d > dateTo) dateTo = d;
      }
    });

    return {
      revenue,
      quantity,
      orders: records.length,
      products: products.size,
      buyers: buyers.size,
      types: types.size,
      avgOrder: records.length ? revenue / records.length : 0,
      avgUnitPrice: quantity ? revenue / quantity : 0,
      dateFrom,
      dateTo,
    };
  }

  function revenueTrend(records) {
    const map = new Map(); // yyyy-mm → { revenue, quantity, orders }
    records.forEach((r) => {
      const key = monthKey(r.date);
      if (!key) return;
      if (!map.has(key)) map.set(key, { revenue: 0, quantity: 0, orders: 0 });
      const bucket = map.get(key);
      bucket.revenue += num(r.total);
      bucket.quantity += num(r.quantity);
      bucket.orders += 1;
    });
    const labels = Array.from(map.keys()).sort();
    return {
      labels,
      revenue: labels.map((k) => map.get(k).revenue),
      quantity: labels.map((k) => map.get(k).quantity),
      orders: labels.map((k) => map.get(k).orders),
    };
  }

  function seasonalAnalysis(records) {
    const acc = {};
    SEASONS.forEach((s) => {
      acc[s.id] = { id: s.id, label: s.label, revenue: 0, quantity: 0, orders: 0 };
    });
    records.forEach((r) => {
      const m = monthOf(r.date);
      if (!m) return;
      const s = seasonOfMonth(m);
      acc[s.id].revenue += num(r.total);
      acc[s.id].quantity += num(r.quantity);
      acc[s.id].orders += 1;
    });
    return SEASONS.map((s) => acc[s.id]);
  }

  // Group records by a normalized key, keeping the first-seen original label.
  function groupBy(records, field) {
    const map = new Map();
    records.forEach((r) => {
      const key = norm(r[field]);
      if (!key) return;
      if (!map.has(key)) {
        map.set(key, {
          label: String(r[field]).trim(),
          revenue: 0,
          quantity: 0,
          orders: 0,
          unitPrices: [],
        });
      }
      const g = map.get(key);
      g.revenue += num(r.total);
      g.quantity += num(r.quantity);
      g.orders += 1;
      const up = num(r.unitPrice);
      if (up > 0) g.unitPrices.push(up);
    });
    return map;
  }

  function productDemand(records) {
    const map = groupBy(records, "product");
    return Array.from(map.values())
      .map((g) => ({
        label: g.label,
        revenue: g.revenue,
        quantity: g.quantity,
        orders: g.orders,
      }))
      .sort((a, b) => b.revenue - a.revenue);
  }

  function buyerPatterns(records) {
    const map = groupBy(records, "buyer");
    return Array.from(map.values())
      .map((g) => ({
        label: g.label,
        revenue: g.revenue,
        quantity: g.quantity,
        orders: g.orders,
        avgOrder: g.orders ? g.revenue / g.orders : 0,
      }))
      .sort((a, b) => b.revenue - a.revenue);
  }

  function pricePerformance(records) {
    const map = groupBy(records, "product");
    return Array.from(map.values())
      .map((g) => {
        const prices = g.unitPrices;
        const avg = g.quantity ? g.revenue / g.quantity : 0; // weighted avg
        return {
          label: g.label,
          avg,
          min: prices.length ? Math.min.apply(null, prices) : 0,
          max: prices.length ? Math.max.apply(null, prices) : 0,
          revenue: g.revenue,
          quantity: g.quantity,
        };
      })
      .sort((a, b) => b.revenue - a.revenue);
  }

  function fmtMonth(key) {
    const m = /^(\d{4})-(\d{2})/.exec(key || "");
    return m ? m[2] + "/" + m[1] : key;
  }

  // Rule-based narrative. This is the extension point for a future AI engine:
  // swap/append richer sentences here without touching the UI.
  function buildNarrative(payload) {
    const out = [];
    const { summary, seasonal, productDemand: prod, buyerPatterns: buyers, revenueTrend: trend, pricePerformance: price } = payload;
    if (!summary.orders) return out;

    if (prod.length) {
      out.push(
        "Sản phẩm chủ lực: <strong>" + prod[0].label + "</strong> đóng góp lớn nhất vào doanh thu (" +
          Math.round((prod[0].revenue / (summary.revenue || 1)) * 100) + "% tổng thu)."
      );
    }

    const topSeason = seasonal.slice().sort((a, b) => b.revenue - a.revenue)[0];
    if (topSeason && topSeason.revenue > 0) {
      out.push("Mùa vụ cao điểm: <strong>" + topSeason.label + "</strong> mang lại doanh thu cao nhất trong năm.");
    }

    if (buyers.length) {
      out.push(
        "Khách hàng lớn nhất: <strong>" + buyers[0].label + "</strong> với " + buyers[0].orders +
          " giao dịch."
      );
      const repeat = buyers.filter((b) => b.orders > 1).length;
      if (repeat > 0) {
        out.push("Có <strong>" + repeat + "</strong> khách mua lặp lại — dấu hiệu tệp khách trung thành.");
      }
    }

    if (price.length) {
      const topPrice = price.slice().sort((a, b) => b.avg - a.avg)[0];
      if (topPrice && topPrice.avg > 0) {
        out.push("Giá trị cao nhất theo đơn vị: <strong>" + topPrice.label + "</strong>, hiệu suất giá tốt nhất danh mục.");
      }
    }

    if (trend.labels.length >= 2) {
      let bestIdx = 0;
      trend.revenue.forEach((v, i) => {
        if (v > trend.revenue[bestIdx]) bestIdx = i;
      });
      out.push("Tháng bán tốt nhất: <strong>" + fmtMonth(trend.labels[bestIdx]) + "</strong>.");
    }

    return out;
  }

  function compute(records) {
    const rows = Array.isArray(records) ? records : [];
    const payload = {
      summary: computeSummary(rows),
      revenueTrend: revenueTrend(rows),
      seasonal: seasonalAnalysis(rows),
      productDemand: productDemand(rows),
      buyerPatterns: buyerPatterns(rows),
      pricePerformance: pricePerformance(rows),
    };
    payload.narrative = buildNarrative(payload);
    return payload;
  }

  global.VuMuaInsights = { compute, SEASONS, seasonOfMonth, fmtMonth };
})(typeof window !== "undefined" ? window : globalThis);
