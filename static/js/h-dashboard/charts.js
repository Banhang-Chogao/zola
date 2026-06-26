/**
 * Sembcorp-style investor-slide charts for H-Dashboard.
 * Premium annual-report look: teal palette, floating waterfall bars,
 * large value labels, thin gridlines — not default Chart.js chrome.
 */
(function (global) {
  "use strict";

  const THEME = {
    ink: "#0f1b2d",
    muted: "#5b6573",
    grid: "#e8ecef",
    teal: "#00a69d",
    tealDark: "#007d76",
    tealLight: "#7fd3cb",
    tealPale: "#b8e8e4",
    tealFill: "rgba(0, 166, 157, 0.14)",
    positive: "#00a69d",
    negative: "#e30613",
    negativePale: "#f9d0d3",
    blue: "#003784",
    amber: "#c87d00",
    track: "#eef3f6",
    white: "#ffffff",
  };

  let instances = {};

  function fmt() {
    return global.HDashboardInsights && global.HDashboardInsights.formatVnd
      ? global.HDashboardInsights.formatVnd.bind(global.HDashboardInsights)
      : (v) => String(v);
  }

  function destroyAll() {
    Object.values(instances).forEach((c) => c && c.destroy());
    instances = {};
  }

  function sciFont(size, weight) {
    return {
      family: "Ericsson Hilda, Manrope, sans-serif",
      size: size || 11,
      weight: weight || "500",
    };
  }

  function tickCompact(v) {
    const n = Math.abs(Number(v)) || 0;
    if (n >= 1e9) return (v / 1e9).toFixed(1).replace(/\.0$/, "") + "B";
    if (n >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return Math.round(v / 1e3) + "K";
    return String(Math.round(v));
  }

  function sciAnim() {
    return { duration: 900, easing: "easeOutQuart" };
  }

  function sciLayout() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 28, right: 8, bottom: 4, left: 4 } },
      animation: sciAnim(),
    };
  }

  function sciCartesianScales(yFmt) {
    return {
      x: {
        grid: { display: false, drawBorder: false },
        ticks: {
          color: THEME.muted,
          font: sciFont(10),
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 14,
        },
        border: { display: false },
      },
      y: {
        grid: { color: THEME.grid, lineWidth: 0.5, drawBorder: false },
        ticks: {
          color: THEME.muted,
          font: sciFont(10),
          callback: yFmt || tickCompact,
          maxTicksLimit: 6,
        },
        border: { display: false },
      },
    };
  }

  function sciTooltip() {
    return {
      backgroundColor: THEME.ink,
      titleColor: THEME.white,
      bodyColor: THEME.tealPale,
      borderColor: THEME.teal,
      borderWidth: 1,
      padding: 10,
      cornerRadius: 6,
      titleFont: sciFont(11, "700"),
      bodyFont: sciFont(10),
      displayColors: false,
    };
  }

  /** Build [min, max] pairs for floating waterfall bars. */
  function waterfallPairs(deltas) {
    let cum = 0;
    return deltas.map((v) => {
      const start = cum;
      cum += v;
      return v >= 0 ? [start, cum] : [cum, start];
    });
  }

  function deltaColor(v) {
    return v >= 0 ? THEME.positive : THEME.negative;
  }

  /** Large value labels above bars (Sembcorp slide style). */
  const valueLabelsPlugin = {
    id: "sciValueLabels",
    afterDatasetsDraw(chart, _args, opts) {
      const { ctx } = chart;
      const dataset = chart.data.datasets[opts.datasetIndex || 0];
      if (!dataset) return;
      const meta = chart.getDatasetMeta(opts.datasetIndex || 0);
      const raw = dataset._sciRaw || dataset.data;
      const formatter = opts.formatter || tickCompact;

      const horizontal = chart.options.indexAxis === "y";
      meta.data.forEach((bar, i) => {
        const val = raw[i];
        if (val == null || (Array.isArray(val) && val[0] === val[1])) return;
        const display = Array.isArray(val)
          ? formatter(val[1] - val[0])
          : formatter(val);
        const props = bar.getProps(["x", "y", "base"], true);
        ctx.save();
        ctx.font = "700 10px Ericsson Hilda, Manrope, sans-serif";
        ctx.fillStyle = THEME.ink;
        if (horizontal) {
          const edge = val >= 0 ? Math.max(props.x, props.base) : Math.min(props.x, props.base);
          ctx.textAlign = val >= 0 ? "left" : "right";
          ctx.textBaseline = "middle";
          ctx.fillText(display, edge + (val >= 0 ? 6 : -6), props.y);
        } else {
          const top = Math.min(props.y, props.base) - 6;
          ctx.textAlign = "center";
          ctx.textBaseline = "bottom";
          ctx.fillText(display, props.x, top);
        }
        ctx.restore();
      });
    },
  };

  /** Numbered circles inside waterfall bars. */
  const barNumbersPlugin = {
    id: "sciBarNumbers",
    afterDatasetsDraw(chart, _args, opts) {
      const meta = chart.getDatasetMeta(opts.datasetIndex || 0);
      if (!meta || !meta.data.length) return;
      const { ctx } = chart;
      const horizontal = chart.options.indexAxis === "y";
      meta.data.forEach((bar, i) => {
        const props = bar.getProps(["x", "y", "base", "height", "width"], true);
        const span = horizontal ? Math.abs(props.width || 0) : Math.abs(props.height || 0);
        if (span < 14) return;
        const cx = horizontal ? (props.x + props.base) / 2 : props.x;
        const cy = horizontal ? props.y : (props.y + props.base) / 2;
        const r = 9;
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle = THEME.white;
        ctx.globalAlpha = 0.92;
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = THEME.tealDark;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.font = "700 9px Ericsson Hilda, Manrope, sans-serif";
        ctx.fillStyle = THEME.tealDark;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(i + 1), cx, cy);
        ctx.restore();
      });
    },
  };

  /** Thin connector lines between floating waterfall steps. */
  const waterfallConnectorsPlugin = {
    id: "sciWaterfallConnectors",
    afterDatasetsDraw(chart, _args, opts) {
      const meta = chart.getDatasetMeta(opts.datasetIndex || 0);
      if (!meta || meta.data.length < 2) return;
      const { ctx } = chart;
      ctx.save();
      ctx.strokeStyle = THEME.muted;
      ctx.lineWidth = 0.75;
      ctx.setLineDash([3, 3]);
      for (let i = 0; i < meta.data.length - 1; i += 1) {
        const a = meta.data[i].getProps(["x", "y", "base"], true);
        const b = meta.data[i + 1].getProps(["x", "y", "base"], true);
        const yA = a.y;
        const yB = b.base;
        ctx.beginPath();
        ctx.moveTo(a.x, yA);
        ctx.lineTo(b.x, yB);
        ctx.stroke();
      }
      ctx.restore();
    },
  };

  /** Center label for donut / gauge. */
  function centerTextPlugin(lines) {
    return {
      id: "sciCenterText",
      afterDraw(chart) {
        const { ctx, chartArea } = chart;
        if (!chartArea) return;
        const cx = (chartArea.left + chartArea.right) / 2;
        const cy = (chartArea.top + chartArea.bottom) / 2;
        ctx.save();
        ctx.textAlign = "center";
        lines.forEach((line, i) => {
          ctx.font = line.font || "600 12px Ericsson Hilda, Manrope, sans-serif";
          ctx.fillStyle = line.color || THEME.ink;
          ctx.fillText(line.text, cx, cy + (line.offsetY || 0) + i * (line.lineHeight || 16));
        });
        ctx.restore();
      },
    };
  }

  function renderDonut(canvas, data) {
    const ctx = canvas.getContext("2d");
    const values = data.values || [];
    const total = values.reduce((s, v) => s + (Number(v) || 0), 0) || 1;
    const incomePct = Math.round(((values[0] || 0) / total) * 100);

    instances.donut = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [
          {
            data: values,
            backgroundColor: [THEME.teal, THEME.negative],
            borderWidth: 3,
            borderColor: THEME.white,
            hoverOffset: 4,
            spacing: 2,
          },
        ],
      },
      options: {
        ...sciLayout(),
        cutout: "74%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: THEME.ink,
              font: sciFont(11, "600"),
              padding: 18,
              usePointStyle: true,
              pointStyle: "circle",
              boxWidth: 8,
            },
          },
          tooltip: {
            ...sciTooltip(),
            callbacks: {
              label(c) {
                return ` ${c.label}: ${fmt()(c.parsed)}`;
              },
            },
          },
        },
      },
      plugins: [
        centerTextPlugin([
          { text: incomePct + "%", font: "800 26px Ericsson Hilda, Manrope, sans-serif", offsetY: -6 },
          { text: "Thu / tổng", font: "500 11px Ericsson Hilda, Manrope, sans-serif", color: THEME.muted, offsetY: 8 },
        ]),
      ],
    });
  }

  function renderBalanceTimeline(canvas, data) {
    const ctx = canvas.getContext("2d");
    const labels = data.labels || [];
    const balance = data.balance || [];
    if (balance.length < 2) {
      renderSparseLine(canvas, labels, balance, "Số dư");
      return;
    }

    const deltas = balance.map((v, i) => (i === 0 ? v : v - balance[i - 1]));
    const pairs = waterfallPairs(deltas);

    instances.balanceTimeline = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Biến động số dư",
            data: pairs,
            backgroundColor: deltas.map(deltaColor),
            borderRadius: 2,
            borderSkipped: false,
            barPercentage: 0.72,
            _sciRaw: deltas,
          },
        ],
      },
      options: {
        ...sciLayout(),
        interaction: { mode: "index", intersect: false },
        scales: sciCartesianScales(tickCompact),
        plugins: {
          legend: { display: false },
          tooltip: {
            ...sciTooltip(),
            callbacks: {
              label(c) {
                const d = deltas[c.dataIndex];
                return ` Δ: ${fmt()(d)} · Cuối: ${fmt()(balance[c.dataIndex])}`;
              },
            },
          },
          sciValueLabels: { datasetIndex: 0, formatter: (v) => tickCompact(v) },
          sciBarNumbers: { datasetIndex: 0 },
          sciWaterfallConnectors: { datasetIndex: 0 },
        },
      },
      plugins: [valueLabelsPlugin, barNumbersPlugin, waterfallConnectorsPlugin],
    });
  }

  function renderSparseLine(canvas, labels, series, label) {
    const ctx = canvas.getContext("2d");
    instances.balanceTimeline = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label,
            data: series,
            borderColor: THEME.teal,
            backgroundColor: THEME.tealFill,
            fill: true,
            tension: 0.35,
            pointRadius: series.length <= 24 ? 3 : 0,
            pointBackgroundColor: THEME.teal,
            borderWidth: 2.5,
          },
        ],
      },
      options: {
        ...sciLayout(),
        scales: sciCartesianScales((v) => fmt()(v)),
        plugins: {
          legend: { display: false },
          tooltip: {
            ...sciTooltip(),
            callbacks: { label(c) { return ` ${label}: ${fmt()(c.parsed.y)}`; } },
          },
        },
      },
    });
  }

  function renderDailyNet(canvas, data) {
    const ctx = canvas.getContext("2d");
    const net = data.net || [];
    const labels = data.labels || [];
    const pairs = waterfallPairs(net);

    instances.dailyNet = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Ròng/ngày",
            data: pairs,
            backgroundColor: net.map(deltaColor),
            borderRadius: 2,
            borderSkipped: false,
            barPercentage: 0.68,
            _sciRaw: net,
          },
          {
            type: "line",
            label: "TB 7 ngày",
            data: data.rolling || [],
            borderColor: THEME.blue,
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.35,
            fill: false,
          },
        ],
      },
      options: {
        ...sciLayout(),
        interaction: { mode: "index", intersect: false },
        scales: sciCartesianScales(tickCompact),
        plugins: {
          legend: {
            position: "top",
            align: "end",
            labels: {
              color: THEME.muted,
              font: sciFont(10),
              boxWidth: 14,
              padding: 12,
            },
          },
          tooltip: {
            ...sciTooltip(),
            callbacks: {
              label(c) {
                if (c.datasetIndex === 0) return ` Ròng: ${fmt()(net[c.dataIndex])}`;
                return ` TB 7 ngày: ${fmt()(c.parsed.y)}`;
              },
            },
          },
          sciValueLabels: { datasetIndex: 0, formatter: (v) => tickCompact(v) },
          sciBarNumbers: { datasetIndex: 0 },
          sciWaterfallConnectors: { datasetIndex: 0 },
        },
      },
      plugins: [valueLabelsPlugin, barNumbersPlugin, waterfallConnectorsPlugin],
    });
  }

  function renderTopTxns(canvas, data) {
    const ctx = canvas.getContext("2d");
    const items = (data && data.items) || [];
    if (!items.length) return;

    const values = items.map((it) => it.value);
    const pairs = waterfallPairs(values);

    instances.topTxns = new Chart(ctx, {
      type: "bar",
      data: {
        labels: items.map((it) => it.label),
        datasets: [
          {
            label: "Giao dịch",
            data: pairs,
            backgroundColor: values.map(deltaColor),
            borderRadius: 2,
            borderSkipped: false,
            barPercentage: 0.7,
            _sciRaw: values,
          },
        ],
      },
      options: {
        indexAxis: "y",
        ...sciLayout(),
        layout: { padding: { top: 8, right: 48, bottom: 4, left: 4 } },
        scales: {
          x: {
            grid: { color: THEME.grid, lineWidth: 0.5, drawBorder: false },
            ticks: { color: THEME.muted, font: sciFont(10), callback: tickCompact },
            border: { display: false },
          },
          y: {
            grid: { display: false, drawBorder: false },
            ticks: { color: THEME.ink, font: sciFont(10, "600"), autoSkip: false },
            border: { display: false },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...sciTooltip(),
            callbacks: {
              label(c) {
                const it = items[c.dataIndex] || {};
                return ` ${it.date || ""} · ${fmt()(values[c.dataIndex])}`;
              },
            },
          },
          sciValueLabels: { datasetIndex: 0, formatter: (v) => tickCompact(v) },
          sciBarNumbers: { datasetIndex: 0 },
        },
      },
      plugins: [valueLabelsPlugin, barNumbersPlugin],
    });
  }

  function renderGauge(canvas, data) {
    const ctx = canvas.getContext("2d");
    const score = data.score;
    const arcColor = score >= 70 ? THEME.teal : score >= 50 ? THEME.amber : THEME.negative;

    instances.gauge = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Score", "Track"],
        datasets: [
          {
            data: [score, 100 - score],
            backgroundColor: [arcColor, THEME.track],
            borderWidth: 0,
            circumference: 200,
            rotation: 250,
            spacing: 0,
          },
        ],
      },
      options: {
        ...sciLayout(),
        cutout: "78%",
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false },
        },
      },
      plugins: [
        centerTextPlugin([
          { text: String(score), font: "800 34px Ericsson Hilda, Manrope, sans-serif", offsetY: -4 },
          { text: data.label || "Score", font: "600 12px Ericsson Hilda, Manrope, sans-serif", color: THEME.muted, offsetY: 14 },
          { text: "/ 100", font: "500 10px Ericsson Hilda, Manrope, sans-serif", color: THEME.muted, offsetY: 30 },
        ]),
      ],
    });
  }

  function renderAll(charts) {
    destroyAll();
    const donutEl = document.getElementById("hd-chart-donut");
    const balanceEl = document.getElementById("hd-chart-area");
    const topTxnsEl = document.getElementById("hd-chart-treemap");
    const dailyNetEl = document.getElementById("hd-chart-waterfall");
    const gaugeEl = document.getElementById("hd-chart-gauge");

    if (donutEl && charts.donut) renderDonut(donutEl, charts.donut);
    if (balanceEl && charts.balanceTimeline) renderBalanceTimeline(balanceEl, charts.balanceTimeline);
    if (topTxnsEl && charts.topTxns && charts.topTxns.items && charts.topTxns.items.length) {
      renderTopTxns(topTxnsEl, charts.topTxns);
    }
    if (dailyNetEl && charts.dailyNet) renderDailyNet(dailyNetEl, charts.dailyNet);
    if (gaugeEl && charts.gauge) renderGauge(gaugeEl, charts.gauge);
  }

  global.HDashboardCharts = { renderAll, destroyAll, THEME };
})(typeof window !== "undefined" ? window : globalThis);