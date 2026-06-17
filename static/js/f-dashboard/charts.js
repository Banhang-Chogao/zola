/**
 * Chart.js visualizations for F-Dashboard.
 */
(function (global) {
  "use strict";

  const COLORS = {
    income: "#00a69d",
    expense: "#e30613",
    net: "#003784",
    muted: "#d0d0d0",
    palette: ["#003784", "#00a69d", "#e30613", "#ff9500", "#666666", "#333333"],
  };

  let instances = {};

  function destroyAll() {
    Object.values(instances).forEach((c) => c && c.destroy());
    instances = {};
  }

  function baseFont() {
    return { family: "Ericsson Hilda, Manrope, sans-serif", size: 11 };
  }

  function renderDonut(canvas, data) {
    const ctx = canvas.getContext("2d");
    instances.donut = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [
          {
            data: data.values,
            backgroundColor: [COLORS.income, COLORS.expense],
            borderWidth: 0,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: { position: "bottom", labels: { font: baseFont(), padding: 16 } },
          tooltip: {
            callbacks: {
              label(ctx) {
                const v = ctx.parsed;
                return ` ${ctx.label}: ${FDashboardInsights.formatVnd(v)}`;
              },
            },
          },
        },
      },
    });
  }

  function renderArea(canvas, data) {
    const ctx = canvas.getContext("2d");
    instances.area = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Thu",
            data: data.income,
            borderColor: COLORS.income,
            backgroundColor: "rgba(0,166,157,0.15)",
            fill: true,
            tension: 0.35,
          },
          {
            label: "Chi",
            data: data.expense,
            borderColor: COLORS.expense,
            backgroundColor: "rgba(227,6,19,0.1)",
            fill: true,
            tension: 0.35,
          },
          {
            label: "Ròng",
            data: data.net,
            borderColor: COLORS.net,
            backgroundColor: "rgba(0,55,132,0.08)",
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: {
            ticks: {
              font: baseFont(),
              callback: (v) => (v >= 1e6 ? v / 1e6 + "M" : v >= 1e3 ? v / 1e3 + "K" : v),
            },
          },
          x: { ticks: { font: baseFont() } },
        },
        plugins: { legend: { labels: { font: baseFont() } } },
      },
    });
  }

  function renderTreemap(canvas, data) {
    const ctx = canvas.getContext("2d");
    const labels = data.map((d) => d.label);
    const values = data.map((d) => d.value);

    instances.treemap = new Chart(ctx, {
      type: "treemap",
      data: {
        datasets: [
          {
            tree: data,
            key: "value",
            groups: ["label"],
            spacing: 1,
            borderWidth: 1,
            borderColor: "#fff",
            backgroundColor(ctx) {
              const i = ctx.dataIndex % COLORS.palette.length;
              return COLORS.palette[i];
            },
            labels: {
              display: true,
              formatter(ctx) {
                if (ctx.type !== "data") return "";
                return [ctx.raw.label, FDashboardInsights.formatVnd(ctx.raw.value)];
              },
              color: "#fff",
              font: { size: 10, weight: "bold" },
            },
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderWaterfall(canvas, data) {
    const ctx = canvas.getContext("2d");
    const labels = data.labels;
    const values = data.values;

    const floating = values.map((v, i) => {
      if (i === 0) return [0, v];
      if (i === values.length - 1) return [0, v];
      const prev = values.slice(0, i).reduce((s, x, idx) => (idx === 0 ? x : s + x), 0);
      if (v >= 0) return [prev, prev + v];
      return [prev + v, prev];
    });

    instances.waterfall = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Luồng tiền",
            data: floating,
            backgroundColor: values.map((v, i) => {
              if (i === 0) return COLORS.income;
              if (i === values.length - 1) return v >= 0 ? COLORS.income : COLORS.expense;
              return v >= 0 ? COLORS.income : COLORS.expense;
            }),
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            ticks: {
              font: baseFont(),
              callback: (v) => (Math.abs(v) >= 1e6 ? v / 1e6 + "M" : v),
            },
          },
          x: { ticks: { font: baseFont(), maxRotation: 45 } },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderGauge(canvas, data) {
    const ctx = canvas.getContext("2d");
    const score = data.score;
    const remainder = 100 - score;

    instances.gauge = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Score", "Remainder"],
        datasets: [
          {
            data: [score, remainder],
            backgroundColor: [
              score >= 70 ? COLORS.income : score >= 50 ? "#ff9500" : COLORS.expense,
              COLORS.muted,
            ],
            borderWidth: 0,
            circumference: 180,
            rotation: 270,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "72%",
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false },
        },
      },
      plugins: [
        {
          id: "gaugeLabel",
          afterDraw(chart) {
            const { ctx: c, chartArea } = chart;
            c.save();
            c.font = "bold 28px Ericsson Hilda, Manrope, sans-serif";
            c.fillStyle = "#000";
            c.textAlign = "center";
            c.fillText(String(score), (chartArea.left + chartArea.right) / 2, chartArea.bottom - 18);
            c.font = "12px Ericsson Hilda, Manrope, sans-serif";
            c.fillStyle = "#666";
            c.fillText(data.label, (chartArea.left + chartArea.right) / 2, chartArea.bottom + 4);
            c.restore();
          },
        },
      ],
    });
  }

  function renderAll(charts) {
    destroyAll();
    const donutEl = document.getElementById("fd-chart-donut");
    const areaEl = document.getElementById("fd-chart-area");
    const treemapEl = document.getElementById("fd-chart-treemap");
    const waterfallEl = document.getElementById("fd-chart-waterfall");
    const gaugeEl = document.getElementById("fd-chart-gauge");

    if (donutEl && charts.donut) renderDonut(donutEl, charts.donut);
    if (areaEl && charts.area) renderArea(areaEl, charts.area);
    if (treemapEl && charts.treemap && charts.treemap.length) renderTreemap(treemapEl, charts.treemap);
    if (waterfallEl && charts.waterfall) renderWaterfall(waterfallEl, charts.waterfall);
    if (gaugeEl && charts.gauge) renderGauge(gaugeEl, charts.gauge);
  }

  global.FDashboardCharts = { renderAll, destroyAll };
})(typeof window !== "undefined" ? window : globalThis);