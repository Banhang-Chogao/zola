/**
 * Vụ Mùa — Chart.js rendering (theme-aware, calm enterprise palette).
 *
 * Reads neutral colors (ink/muted/grid) from the site's CSS tokens so charts
 * follow light/dark, with safe fallbacks. Data colors use a calm harvest
 * palette. Every renderer guards for "no Chart.js" and "no data".
 */
(function (global) {
  "use strict";

  // Calm harvest palette for data series (kept consistent light/dark).
  const PALETTE = {
    green: "#2f9e44",
    greenFill: "rgba(47, 158, 68, 0.12)",
    amber: "#e8a33d",
    amberFill: "rgba(232, 163, 61, 0.16)",
    teal: "#1098ad",
    tealSoft: "rgba(16, 152, 173, 0.55)",
    clay: "rgba(199, 122, 88, 0.6)",
  };

  let instances = {};

  function token(name, fallback) {
    try {
      const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fallback;
    } catch (_) {
      return fallback;
    }
  }

  function neutrals() {
    return {
      ink: token("--c-text-heading", "#1f2933"),
      muted: token("--c-text-muted", "#7b8794"),
      grid: token("--c-border", "#e4e7eb"),
    };
  }

  function font(size, weight) {
    return { family: "Manrope, system-ui, sans-serif", size: size || 11, weight: weight || "500" };
  }

  function tickCompact(v) {
    const n = Math.abs(Number(v)) || 0;
    if (n >= 1e9) return (v / 1e9).toFixed(1).replace(/\.0$/, "") + "B";
    if (n >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return Math.round(v / 1e3) + "K";
    return String(Math.round(v));
  }

  function hasChart() {
    return typeof global.Chart === "function";
  }

  function destroyAll() {
    Object.keys(instances).forEach((k) => {
      try {
        instances[k] && instances[k].destroy();
      } catch (_) {
        /* ignore */
      }
    });
    instances = {};
  }

  function baseOptions(yFmt) {
    const c = neutrals();
    return {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 16, right: 12, bottom: 4, left: 4 } },
      animation: { duration: 600, easing: "easeOutQuart" },
      interaction: { mode: "index", intersect: false },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: c.muted, font: font(10), maxRotation: 0, maxTicksLimit: 12 },
          border: { display: false },
        },
        y: {
          grid: { color: c.grid, lineWidth: 0.5 },
          ticks: { color: c.muted, font: font(10), callback: yFmt || tickCompact, maxTicksLimit: 6 },
          border: { display: false },
        },
      },
      plugins: {
        legend: {
          position: "top",
          align: "end",
          labels: { color: c.muted, font: font(10), boxWidth: 12, padding: 10 },
        },
        tooltip: {
          backgroundColor: c.ink,
          titleColor: "#fff",
          bodyColor: "#e6e6e6",
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
        },
      },
    };
  }

  function ctxOf(id) {
    const canvas = document.getElementById(id);
    if (!canvas) return null;
    return canvas.getContext("2d");
  }

  function renderRevenue(trend) {
    const ctx = ctxOf("vm-chart-revenue");
    if (!ctx || !trend || !trend.labels.length) return;
    instances.revenue = new global.Chart(ctx, {
      type: "line",
      data: {
        labels: trend.labels.map((k) => global.VuMuaInsights.fmtMonth(k)),
        datasets: [
          {
            label: "Doanh thu",
            data: trend.revenue,
            borderColor: PALETTE.green,
            backgroundColor: PALETTE.greenFill,
            fill: true,
            tension: 0.32,
            borderWidth: 2.5,
            pointRadius: trend.labels.length <= 24 ? 3 : 0,
          },
        ],
      },
      options: baseOptions(tickCompact),
    });
  }

  function renderSeason(seasonal) {
    const ctx = ctxOf("vm-chart-season");
    if (!ctx || !seasonal || !seasonal.length) return;
    instances.season = new global.Chart(ctx, {
      type: "bar",
      data: {
        labels: seasonal.map((s) => s.label),
        datasets: [
          {
            label: "Doanh thu",
            data: seasonal.map((s) => s.revenue),
            backgroundColor: PALETTE.green,
            borderRadius: 6,
            barPercentage: 0.6,
          },
          {
            label: "Sản lượng",
            data: seasonal.map((s) => s.quantity),
            backgroundColor: PALETTE.amber,
            borderRadius: 6,
            barPercentage: 0.6,
            yAxisID: "y1",
          },
        ],
      },
      options: (function () {
        const c = neutrals();
        const o = baseOptions(tickCompact);
        o.scales.y1 = {
          position: "right",
          grid: { display: false },
          ticks: { color: c.muted, font: font(10), callback: tickCompact, maxTicksLimit: 6 },
          border: { display: false },
        };
        return o;
      })(),
    });
  }

  function renderProductDemand(products) {
    const ctx = ctxOf("vm-chart-product");
    if (!ctx || !products || !products.length) return;
    const top = products.slice(0, 8);
    instances.product = new global.Chart(ctx, {
      type: "bar",
      data: {
        labels: top.map((p) => p.label),
        datasets: [
          {
            label: "Doanh thu",
            data: top.map((p) => p.revenue),
            backgroundColor: PALETTE.green,
            borderRadius: 5,
            barPercentage: 0.7,
          },
          {
            label: "Sản lượng",
            data: top.map((p) => p.quantity),
            backgroundColor: PALETTE.tealSoft,
            borderRadius: 5,
            barPercentage: 0.7,
          },
        ],
      },
      options: (function () {
        const o = baseOptions(tickCompact);
        o.indexAxis = "y";
        o.layout = { padding: { top: 8, right: 40, bottom: 4, left: 4 } };
        return o;
      })(),
    });
  }

  function renderBuyers(buyers) {
    const ctx = ctxOf("vm-chart-buyer");
    if (!ctx || !buyers || !buyers.length) return;
    const top = buyers.slice(0, 8);
    instances.buyer = new global.Chart(ctx, {
      type: "bar",
      data: {
        labels: top.map((b) => b.label),
        datasets: [
          {
            label: "Doanh thu",
            data: top.map((b) => b.revenue),
            backgroundColor: PALETTE.amber,
            borderRadius: 5,
            barPercentage: 0.7,
          },
          {
            label: "Số đơn",
            data: top.map((b) => b.orders),
            backgroundColor: PALETTE.clay,
            borderRadius: 5,
            barPercentage: 0.7,
            yAxisID: "x1",
          },
        ],
      },
      options: (function () {
        const c = neutrals();
        const o = baseOptions(tickCompact);
        o.indexAxis = "y";
        o.layout = { padding: { top: 8, right: 40, bottom: 4, left: 4 } };
        o.scales.x1 = {
          position: "top",
          grid: { display: false },
          ticks: { color: c.muted, font: font(10), maxTicksLimit: 6 },
          border: { display: false },
        };
        return o;
      })(),
    });
  }

  function renderAll(payload) {
    destroyAll();
    if (!hasChart() || !payload) return;
    renderRevenue(payload.revenueTrend);
    renderSeason(payload.seasonal);
    renderProductDemand(payload.productDemand);
    renderBuyers(payload.buyerPatterns);
  }

  global.VuMuaCharts = { renderAll, destroyAll, hasChart, PALETTE };
})(typeof window !== "undefined" ? window : globalThis);
