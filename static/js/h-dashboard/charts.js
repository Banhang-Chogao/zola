/**
 * H-Dashboard V2 — Coffee Life Analytics charts (S-DNA).
 * Trend lines, horizontal bars, area — no donuts, gauges, or financial waterfalls.
 */
(function (global) {
  "use strict";

  const THEME = {
    ink: "#111111",
    muted: "#888888",
    grid: "#E6E6E6",
    teal: "#00A7A0",
    tealFill: "rgba(0, 167, 160, 0.12)",
    blue: "#DCEAF8",
    blueLine: "#5B8DB8",
    purple: "#ECE7FA",
    purpleLine: "#8B7EC8",
  };

  let instances = {};

  function fmt(n) {
    return global.HDashboardCoffee
      ? global.HDashboardCoffee.formatVnd(n)
      : String(n);
  }

  function destroyAll() {
    Object.values(instances).forEach((c) => c && c.destroy());
    instances = {};
  }

  function sciFont(size, weight) {
    return { family: "Manrope, system-ui, sans-serif", size: size || 11, weight: weight || "500" };
  }

  function tickCompact(v) {
    const n = Math.abs(Number(v)) || 0;
    if (n >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return Math.round(v / 1e3) + "K";
    return String(Math.round(v));
  }

  function baseOptions(yFmt) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 16, right: 8, bottom: 4, left: 4 } },
      animation: { duration: 700, easing: "easeOutQuart" },
      interaction: { mode: "index", intersect: false },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: THEME.muted, font: sciFont(10), maxRotation: 0, maxTicksLimit: 12 },
          border: { display: false },
        },
        y: {
          grid: { color: THEME.grid, lineWidth: 0.5 },
          ticks: { color: THEME.muted, font: sciFont(10), callback: yFmt || tickCompact, maxTicksLimit: 6 },
          border: { display: false },
        },
      },
      plugins: {
        legend: {
          position: "top",
          align: "end",
          labels: { color: THEME.muted, font: sciFont(10), boxWidth: 12, padding: 10 },
        },
        tooltip: {
          backgroundColor: THEME.ink,
          titleColor: "#fff",
          bodyColor: "#ddd",
          padding: 10,
          cornerRadius: 6,
          displayColors: false,
        },
      },
    };
  }

  function renderTimeline(canvas, data, mode) {
    if (!canvas || !data) return;
    const ctx = canvas.getContext("2d");
    const key = mode || "daily";
    const series = data[key] || data.daily;
    if (!series?.labels?.length) return;

    instances["timeline-" + key] = new Chart(ctx, {
      type: "line",
      data: {
        labels: series.labels.map((l) => l.length > 10 ? l.slice(5) : l),
        datasets: [
          {
            label: "Lần ghé",
            data: series.values,
            borderColor: THEME.teal,
            backgroundColor: THEME.tealFill,
            fill: true,
            tension: 0.35,
            pointRadius: series.values.length <= 30 ? 3 : 0,
            borderWidth: 2.5,
          },
          {
            label: "TB trượt",
            data: series.rolling,
            borderColor: THEME.blueLine,
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.35,
            fill: false,
          },
        ],
      },
      options: baseOptions((v) => String(Math.round(v))),
    });
  }

  function renderCategoryBars(canvas, categories) {
    if (!canvas || !categories?.length) return;
    const ctx = canvas.getContext("2d");
    const top = categories.slice(0, 8);
    instances.categories = new Chart(ctx, {
      type: "bar",
      data: {
        labels: top.map((c) => c.category),
        datasets: [
          {
            label: "Số lần",
            data: top.map((c) => c.count),
            backgroundColor: THEME.teal,
            borderRadius: 4,
            barPercentage: 0.65,
          },
          {
            label: "Chi tiêu",
            data: top.map((c) => c.spend),
            backgroundColor: "rgba(91, 141, 184, 0.55)",
            borderRadius: 4,
            barPercentage: 0.65,
          },
        ],
      },
      options: {
        indexAxis: "y",
        ...baseOptions(tickCompact),
        layout: { padding: { top: 8, right: 40, bottom: 4, left: 4 } },
      },
    });
  }

  function renderSeasonTrend(canvas, seasonality) {
    if (!canvas || !seasonality) return;
    const ctx = canvas.getContext("2d");
    const labels = ["Mùa khô", "Mùa nóng", "Mùa mưa"];
    const ids = ["dry", "hot", "rainy"];
    instances.season = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Lần ghé",
            data: ids.map((id) => seasonality.seasonVisits[id] || 0),
            backgroundColor: THEME.teal,
            borderRadius: 4,
          },
          {
            label: "Chi tiêu",
            data: ids.map((id) => seasonality.seasonSpend[id] || 0),
            backgroundColor: "rgba(139, 126, 200, 0.5)",
            borderRadius: 4,
          },
        ],
      },
      options: baseOptions(tickCompact),
    });
  }

  function renderMonthlyArea(canvas, monthlyReports) {
    if (!canvas || !monthlyReports?.length) return;
    const ctx = canvas.getContext("2d");
    instances.monthly = new Chart(ctx, {
      type: "line",
      data: {
        labels: monthlyReports.map((m) => m.monthLabel || m.month),
        datasets: [
          {
            label: "Lần ghé",
            data: monthlyReports.map((m) => m.visits),
            borderColor: THEME.teal,
            backgroundColor: THEME.tealFill,
            fill: true,
            tension: 0.3,
            yAxisID: "y",
          },
          {
            label: "Chi tiêu",
            data: monthlyReports.map((m) => m.spend),
            borderColor: THEME.purpleLine,
            backgroundColor: "rgba(139, 126, 200, 0.1)",
            fill: true,
            tension: 0.3,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        ...baseOptions(),
        scales: {
          x: { grid: { display: false }, ticks: { color: THEME.muted, font: sciFont(10) }, border: { display: false } },
          y: { position: "left", grid: { color: THEME.grid }, ticks: { color: THEME.muted, callback: (v) => String(v) }, border: { display: false } },
          y1: { position: "right", grid: { display: false }, ticks: { color: THEME.muted, callback: tickCompact }, border: { display: false } },
        },
      },
    });
  }

  function bindTimelineTabs(payload) {
    const tabs = document.querySelectorAll("[data-hd-timeline]");
    if (!tabs.length) return;
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.classList.remove("hd-tab--active"));
        tab.classList.add("hd-tab--active");
        const mode = tab.dataset.hdTimeline;
        const canvas = document.getElementById("hd-chart-timeline");
        Object.keys(instances).forEach((k) => {
          if (k.startsWith("timeline-") && instances[k]) {
            instances[k].destroy();
            delete instances[k];
          }
        });
        renderTimeline(canvas, payload.timeline, mode);
      });
    });
  }

  function renderAll(coffeePayload) {
    destroyAll();
    if (!coffeePayload) return;
    const timeline = coffeePayload.timeline;
    const drinks = coffeePayload.drinks;
    const seasonality = coffeePayload.seasonality;
    const monthly = coffeePayload.monthlyReports;

    renderTimeline(document.getElementById("hd-chart-timeline"), timeline, "daily");
    renderCategoryBars(document.getElementById("hd-chart-categories"), drinks?.topCategories);
    renderSeasonTrend(document.getElementById("hd-chart-season"), seasonality);
    renderMonthlyArea(document.getElementById("hd-chart-monthly"), monthly);
    bindTimelineTabs(coffeePayload);
  }

  const api = { renderAll, destroyAll, THEME };
  global.HDashboardCharts = api;
  if (typeof window !== "undefined") window.HDashboardCharts = api;
})(typeof window !== "undefined" ? window : globalThis);