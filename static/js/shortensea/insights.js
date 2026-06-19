(function () {
  "use strict";

  var toast = window.ShortenSEAToast;
  var api = window.ShortenSEAApi;
  var auth = window.ShortenSEAAuth;
  var charts = [];

  function destroyCharts() {
    charts.forEach(function (c) { try { c.destroy(); } catch (e) {} });
    charts = [];
  }

  function makeBar(canvasId, labels, values, label) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") return;
    var c = new Chart(canvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: label,
          data: values,
          backgroundColor: "rgba(0, 167, 160, 0.65)",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
    charts.push(c);
  }

  function makeDoughnut(canvasId, items) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined" || !items.length) return;
    var c = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: items.map(function (i) { return i.name; }),
        datasets: [{
          data: items.map(function (i) { return i.count; }),
          backgroundColor: ["#00A7A0", "#5B9BD5", "#9B8FD4", "#E8A838", "#DCEAF8", "#ECE7FA"]
        }]
      },
      options: { responsive: true, plugins: { legend: { position: "bottom" } } }
    });
    charts.push(c);
  }

  async function loadInsights() {
    try {
      var data = await api.getInsights();
      destroyCharts();

      var totalEl = document.querySelector("[data-sse-total-clicks]");
      if (totalEl) totalEl.textContent = String(data.total_clicks || 0);
      var qrEl = document.querySelector("[data-sse-qr-scans]");
      if (qrEl) qrEl.textContent = String(data.qr_scans || 0);
      var topEl = document.querySelector("[data-sse-top-clicks]");
      if (topEl) {
        var top = (data.top_links && data.top_links[0]) ? data.top_links[0].clicks : 0;
        topEl.textContent = String(top);
      }

      var locked = document.querySelector("[data-sse-insights-locked]");
      var chartGrid = document.querySelector("[data-sse-charts]");
      if (data.locked) {
        if (locked) locked.hidden = false;
        if (chartGrid) chartGrid.hidden = true;
        return;
      }
      if (locked) locked.hidden = true;
      if (chartGrid) chartGrid.hidden = false;

      var byDay = data.clicks_by_day || [];
      makeBar("sse-chart-day", byDay.map(function (d) { return d.date; }), byDay.map(function (d) { return d.clicks; }), "Clicks");

      var byLink = data.clicks_by_link || [];
      makeBar("sse-chart-links", byLink.slice(0, 8).map(function (d) { return d.slug; }), byLink.slice(0, 8).map(function (d) { return d.clicks; }), "Clicks");

      if (data.advanced_insights) {
        document.querySelectorAll("[data-sse-advanced-chart]").forEach(function (el) { el.hidden = false; });
        makeDoughnut("sse-chart-referrer", data.referrers || []);
        makeDoughnut("sse-chart-device", data.devices || []);
        makeDoughnut("sse-chart-browser", data.browsers || []);
      } else {
        document.querySelectorAll("[data-sse-advanced-chart]").forEach(function (el) { el.hidden = true; });
      }
    } catch (e) {
      toast.show(e.message || "Không tải được insights.", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async function () {
    if (!document.querySelector('[data-sse-page="insights"]')) return;
    document.querySelectorAll('[data-sse-action="login"]').forEach(function (btn) {
      btn.addEventListener("click", function () { auth.login(); });
    });
    var user = await auth.init();
    if (!user) return;

    function waitChart() {
      if (typeof Chart !== "undefined") {
        loadInsights();
      } else {
        setTimeout(waitChart, 100);
      }
    }
    waitChart();
  });
})();