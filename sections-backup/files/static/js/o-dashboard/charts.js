/**
 * Chart.js visualizations for O-Dashboard.
 */
(function (global) {
  "use strict";

  const COLORS = {
    income: "#00a69d",
    expense: "#e30613",
    net: "#003784",
    amber: "#ff9500",
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
                return ` ${ctx.label}: ${ODashboardInsights.formatVnd(v)}`;
              },
            },
          },
        },
      },
    });
  }

  function tickMK(v) {
    const n = Math.abs(v);
    if (n >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return Math.round(v / 1e3) + "K";
    return v;
  }

  function renderBalanceTimeline(canvas, data) {
    const ctx = canvas.getContext("2d");
    const labels = data.labels || [];
    const n = labels.length;
    const avgLine = new Array(n).fill(data.avg);
    const minLine = new Array(n).fill(data.min);

    instances.balanceTimeline = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Số dư",
            data: data.balance || [],
            borderColor: COLORS.net,
            backgroundColor: "rgba(0,55,132,0.10)",
            fill: true,
            tension: 0.3,
            pointRadius: n > 40 ? 0 : 2,
            pointHoverRadius: 4,
            borderWidth: 2,
            order: 1,
          },
          {
            label: "Trung bình",
            data: avgLine,
            borderColor: COLORS.income,
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0,
            order: 0,
          },
          {
            label: "Thấp nhất",
            data: minLine,
            borderColor: COLORS.amber,
            borderDash: [3, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0,
            order: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: { ticks: { font: baseFont(), callback: tickMK } },
          x: { ticks: { font: baseFont(), maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
        },
        plugins: {
          legend: { labels: { font: baseFont(), boxWidth: 12 } },
          tooltip: {
            callbacks: {
              label(c) {
                return ` ${c.dataset.label}: ${ODashboardInsights.formatVnd(c.parsed.y)}`;
              },
            },
          },
        },
      },
    });
  }

  function renderDailyNet(canvas, data) {
    const ctx = canvas.getContext("2d");
    const net = data.net || [];

    instances.dailyNet = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels || [],
        datasets: [
          {
            type: "bar",
            label: "Ròng/ngày",
            data: net,
            backgroundColor: net.map((v) => (v >= 0 ? COLORS.income : COLORS.expense)),
            borderRadius: 3,
            order: 1,
          },
          {
            type: "line",
            label: "Trung bình 7 ngày",
            data: data.rolling || [],
            borderColor: COLORS.net,
            backgroundColor: "rgba(0,55,132,0.05)",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
            fill: false,
            order: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: { ticks: { font: baseFont(), callback: tickMK } },
          x: { ticks: { font: baseFont(), maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
        },
        plugins: {
          legend: { labels: { font: baseFont(), boxWidth: 12 } },
          tooltip: {
            callbacks: {
              label(c) {
                return ` ${c.dataset.label}: ${ODashboardInsights.formatVnd(c.parsed.y)}`;
              },
            },
          },
        },
      },
    });
  }

  function renderTopTxns(canvas, data) {
    const ctx = canvas.getContext("2d");
    const items = (data && data.items) || [];

    instances.topTxns = new Chart(ctx, {
      type: "bar",
      data: {
        labels: items.map((it) => it.label),
        datasets: [
          {
            label: "Giao dịch",
            data: items.map((it) => it.value),
            backgroundColor: items.map((it) => (it.value >= 0 ? COLORS.income : COLORS.expense)),
            borderRadius: 3,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { font: baseFont(), callback: tickMK } },
          y: { ticks: { font: baseFont(), autoSkip: false } },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(c) {
                const it = items[c.dataIndex] || {};
                return ` ${it.date || ""} · ${ODashboardInsights.formatVnd(c.parsed.x)}`;
              },
            },
          },
        },
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
    // Canvas ids reused as-is: area→balanceTimeline, waterfall→dailyNet,
    // treemap→topTxns. Donut + gauge unchanged.
    const donutEl = document.getElementById("od-chart-donut");
    const balanceEl = document.getElementById("od-chart-area");
    const topTxnsEl = document.getElementById("od-chart-treemap");
    const dailyNetEl = document.getElementById("od-chart-waterfall");
    const gaugeEl = document.getElementById("od-chart-gauge");

    if (donutEl && charts.donut) renderDonut(donutEl, charts.donut);
    if (balanceEl && charts.balanceTimeline) renderBalanceTimeline(balanceEl, charts.balanceTimeline);
    if (topTxnsEl && charts.topTxns && charts.topTxns.items && charts.topTxns.items.length) {
      renderTopTxns(topTxnsEl, charts.topTxns);
    }
    if (dailyNetEl && charts.dailyNet) renderDailyNet(dailyNetEl, charts.dailyNet);
    if (gaugeEl && charts.gauge) renderGauge(gaugeEl, charts.gauge);
  }

  global.ODashboardCharts = { renderAll, destroyAll };
})(typeof window !== "undefined" ? window : globalThis);
