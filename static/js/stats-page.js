/**
 * Speed Insights dashboard.
 *
 * Production source: VIPZone RUM field data (GET {API}/rum/web-vitals/summary) —
 * real, cross-visitor Core Web Vitals that survive a browser wipe. localStorage
 * (`zola-vitals`) is used ONLY as a clearly-labelled "Local debug only" fallback
 * when the backend is unreachable. The data source is always shown in the UI.
 *
 * Core Web Vitals: LCP, INP, CLS. Diagnostic (NOT core): FCP, TTFB.
 * A metric with 0 samples shows "Chưa đủ dữ liệu" — never a fake good score.
 */
(function () {
  "use strict";

  var container = document.getElementById("stats-app");
  if (!container) return;

  var API = (container.getAttribute("data-rum-api") || "").replace(/\/+$/, "");

  var CORE = ["LCP", "INP", "CLS"];
  var DIAGNOSTIC = ["FCP", "TTFB"];
  var ALL_METRICS = CORE.concat(DIAGNOSTIC);

  // Google's good / needs-improvement boundaries.
  var THRESHOLDS = {
    LCP: [2500, 4000],
    INP: [200, 500],
    CLS: [0.1, 0.25],
    FCP: [1800, 3000],
    TTFB: [800, 1800],
  };
  var GOOD_TARGET = {
    LCP: "≤ 2,5s",
    INP: "≤ 200ms",
    CLS: "≤ 0,1",
    FCP: "≤ 1,8s",
    TTFB: "≤ 800ms",
  };

  var WINDOWS = [
    { key: "24h", label: "24 giờ" },
    { key: "7d", label: "7 ngày" },
    { key: "30d", label: "30 ngày" },
  ];

  var state = { window: "30d" };

  // ===== util =====
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtMs(v) {
    if (v == null) return "—";
    if (v < 1000) return Math.round(v) + " ms";
    return (v / 1000).toFixed(2).replace(".", ",") + " s";
  }

  function fmtCls(v) {
    if (v == null) return "—";
    return Number(v).toFixed(3).replace(".", ",");
  }

  function fmtVal(name, v) {
    return name === "CLS" ? fmtCls(v) : fmtMs(v);
  }

  function fmtWhen(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("vi-VN", {
        timeZone: "Asia/Ho_Chi_Minh",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return "—";
    }
  }

  function rateValue(name, v) {
    if (v == null || !THRESHOLDS[name]) return "none";
    var t = THRESHOLDS[name];
    if (v <= t[0]) return "good";
    if (v <= t[1]) return "needs-improvement";
    return "poor";
  }

  function rateLabel(r) {
    return (
      {
        good: "Tốt",
        "needs-improvement": "Cần cải thiện",
        poor: "Kém",
        none: "Chưa đủ dữ liệu",
      }[r] || "—"
    );
  }

  // ===== local-debug aggregation (fallback only) =====
  function loadDebug() {
    try {
      var raw = JSON.parse(localStorage.getItem("zola-vitals") || "[]");
      return Array.isArray(raw) ? raw : [];
    } catch (e) {
      return [];
    }
  }

  function windowMs(key) {
    return { "24h": 86400000, "7d": 604800000, "30d": 2592000000 }[key] || 2592000000;
  }

  function percentile(sorted, q) {
    if (!sorted.length) return null;
    if (sorted.length === 1) return sorted[0];
    var idx = Math.min(sorted.length - 1, Math.round(q * (sorted.length - 1)));
    return sorted[idx];
  }

  function median(sorted) {
    if (!sorted.length) return null;
    var mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }

  function aggregate(name, values) {
    var sorted = values.slice().sort(function (a, b) { return a - b; });
    var count = sorted.length;
    if (!count) {
      return { metric: name, count: 0, p75: null, median: null, average: null,
        rating: "none", distribution: { good: 0, "needs-improvement": 0, poor: 0 },
        core: CORE.indexOf(name) >= 0 };
    }
    var p75 = percentile(sorted, 0.75);
    var dist = { good: 0, "needs-improvement": 0, poor: 0 };
    sorted.forEach(function (v) { dist[rateValue(name, v)]++; });
    return {
      metric: name,
      count: count,
      p75: p75,
      median: median(sorted),
      average: sorted.reduce(function (s, v) { return s + v; }, 0) / count,
      rating: rateValue(name, p75),
      distribution: dist,
      core: CORE.indexOf(name) >= 0,
    };
  }

  function buildLocalSummary(win) {
    var cutoff = Date.now() - windowMs(win);
    var samples = loadDebug().filter(function (s) {
      return s && typeof s.value === "number" && (!s.ts || s.ts >= cutoff);
    });
    var byMetric = {};
    var byPageLcp = {};
    var lastTs = 0;
    samples.forEach(function (s) {
      (byMetric[s.name] = byMetric[s.name] || []).push(s.value);
      if (s.ts && s.ts > lastTs) lastTs = s.ts;
      if (s.name === "LCP") (byPageLcp[s.path || "/"] = byPageLcp[s.path || "/"] || []).push(s.value);
    });
    var metrics = {};
    ALL_METRICS.forEach(function (m) { metrics[m] = aggregate(m, byMetric[m] || []); });
    var slow = Object.keys(byPageLcp)
      .map(function (p) {
        var vals = byPageLcp[p].slice().sort(function (a, b) { return a - b; });
        return { path: p, lcp_p75: percentile(vals, 0.75), samples: vals.length };
      })
      .filter(function (r) { return r.samples >= 2; })
      .sort(function (a, b) { return b.lcp_p75 - a.lcp_p75; })
      .slice(0, 5);
    return {
      source: "local-debug",
      window: win,
      total_samples: samples.length,
      metrics: metrics,
      slow_pages: slow,
      last_updated: lastTs ? new Date(lastTs).toISOString() : null,
    };
  }

  // ===== RUM fetch =====
  function fetchSummary(win) {
    if (!API) return Promise.resolve(null);
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, 8000) : null;
    return fetch(API + "/rum/web-vitals/summary?window=" + encodeURIComponent(win), {
      method: "GET",
      mode: "cors",
      credentials: "omit",
      signal: ctrl ? ctrl.signal : undefined,
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (timer) clearTimeout(timer);
        if (!data || data.enabled === false || !data.metrics) return null;
        return data;
      })
      .catch(function () {
        if (timer) clearTimeout(timer);
        return null;
      });
  }

  // ===== renderers =====
  function sourceBadge(source) {
    var map = {
      "vipzone-rum": { cls: "live", label: "VIPZone RUM", note: "Dữ liệu thực tế từ mọi khách truy cập (Real-User-Monitoring), không phụ thuộc trình duyệt này." },
      "local-debug": { cls: "debug", label: "Local debug only", note: "Backend RUM không phản hồi — đang hiển thị dữ liệu cục bộ của trình duyệt này. Xoá dữ liệu duyệt web sẽ mất." },
    };
    var info = map[source] || map["local-debug"];
    return (
      '<div class="stats-source stats-source--' + info.cls + '">' +
      '<span class="stats-source__dot" aria-hidden="true"></span>' +
      '<span class="stats-source__label">Nguồn dữ liệu: <strong>' + escapeHtml(info.label) + "</strong></span>" +
      '<span class="stats-source__note">' + escapeHtml(info.note) + "</span>" +
      "</div>"
    );
  }

  function windowToggle() {
    return (
      '<div class="stats-window" role="group" aria-label="Khoảng thời gian">' +
      WINDOWS.map(function (w) {
        var active = w.key === state.window;
        return (
          '<button type="button" class="stats-window__btn' + (active ? " is-active" : "") +
          '" data-window="' + w.key + '"' + (active ? ' aria-pressed="true"' : ' aria-pressed="false"') +
          ">" + escapeHtml(w.label) + "</button>"
        );
      }).join("") +
      "</div>"
    );
  }

  function distBar(name, dist, count) {
    if (!count) return '<div class="vital-bar vital-bar--empty">Chưa đủ dữ liệu</div>';
    function seg(kind, n, label) {
      return n
        ? '<div class="vital-bar__seg vital-bar__seg--' + kind + '" style="flex:' + n +
            '" title="' + label + ": " + n + '"></div>'
        : "";
    }
    return (
      '<div class="vital-bar" role="img" aria-label="Phân bố ' + name + '">' +
      seg("good", dist.good, "Tốt") +
      seg("ni", dist["needs-improvement"], "Cần cải thiện") +
      seg("poor", dist.poor, "Kém") +
      "</div>"
    );
  }

  function renderVitalCard(name, m) {
    var hasData = m.count > 0;
    var rating = hasData ? m.rating : "none";
    var valueText = hasData ? fmtVal(name, m.p75) : "Chưa đủ dữ liệu";
    var meta = hasData
      ? "P75 từ <strong>" + m.count + "</strong> mẫu<br>Median: " + fmtVal(name, m.median) +
        "<br>Trung bình: " + fmtVal(name, m.average)
      : "Chưa có mẫu nào trong khoảng này.<br>Hãy truy cập vài trang để bắt đầu thu thập.";

    return (
      '<article class="vital-card vital-card--' + rating + (hasData ? "" : " vital-card--empty") + '">' +
      '<div class="vital-card__head">' +
      '<span class="vital-card__name">' + name + "</span>" +
      '<span class="vital-card__target" title="Ngưỡng “tốt” của Google">Mục tiêu ' + GOOD_TARGET[name] + "</span>" +
      "</div>" +
      '<div class="vital-card__value' + (hasData ? "" : " vital-card__value--empty") + '">' + escapeHtml(valueText) + "</div>" +
      '<div class="vital-card__label">' + rateLabel(rating) + "</div>" +
      '<div class="vital-card__meta">' + meta + "</div>" +
      distBar(name, m.distribution, m.count) +
      "</article>"
    );
  }

  function renderMetricGrid(names, metrics) {
    return (
      '<div class="vitals-grid">' +
      names.map(function (n) { return renderVitalCard(n, metrics[n] || aggregate(n, [])); }).join("") +
      "</div>"
    );
  }

  function renderSlowPages(slow) {
    if (!slow || !slow.length) {
      return '<p class="stats-empty">Chưa đủ dữ liệu để xếp hạng trang chậm.</p>';
    }
    return (
      '<div class="stats-table-wrap"><table class="stats-table">' +
      "<thead><tr><th>#</th><th>Đường dẫn</th><th>LCP P75</th><th>Mẫu</th></tr></thead><tbody>" +
      slow
        .map(function (row, i) {
          return (
            "<tr><td>" + (i + 1) + "</td>" +
            '<td><a href="' + escapeHtml(row.path) + '"><code>' + escapeHtml(row.path) + "</code></a></td>" +
            "<td><strong>" + fmtMs(row.lcp_p75) + "</strong></td>" +
            "<td>" + row.samples + "</td></tr>"
          );
        })
        .join("") +
      "</tbody></table></div>"
    );
  }

  function renderLocalActivity() {
    var events;
    try {
      events = JSON.parse(localStorage.getItem("zola-events") || "[]");
      if (!Array.isArray(events)) events = [];
    } catch (e) {
      events = [];
    }
    var cutoff = Date.now() - 2592000000;
    events = events.filter(function (e) { return e && typeof e.ts === "number" && e.ts >= cutoff; });
    var typeCounts = {};
    events.forEach(function (e) { typeCounts[e.type] = (typeCounts[e.type] || 0) + 1; });
    var types = [["view", "Lượt xem"], ["click", "Click"], ["full", "Đọc hết"]];
    return (
      '<div class="event-types">' +
      types
        .map(function (t) {
          return (
            '<div class="event-type event-type--' + t[0] + '">' +
            '<div class="event-type__count">' + (typeCounts[t[0]] || 0) + "</div>" +
            '<div class="event-type__label">' + t[1] + "</div></div>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  // ===== main render =====
  function render(summary) {
    var src = summary.source;
    var metrics = summary.metrics;

    container.innerHTML =
      sourceBadge(src) +
      '<div class="stats-controls">' +
      windowToggle() +
      '<p class="stats-meta">Cập nhật lần cuối: <strong>' + fmtWhen(summary.last_updated) +
      "</strong> · Tổng mẫu: <strong>" + (summary.total_samples || 0) + "</strong></p>" +
      "</div>" +

      '<section class="stats-section">' +
      '<h2 class="stats-heading">Core Web Vitals</h2>' +
      '<p class="stats-help">3 chỉ số xếp hạng chính của Google. Giá trị là <strong>P75</strong> ' +
      "(percentile 75) trên cửa sổ <strong>" + escapeHtml(state.window) + "</strong>. " +
      'Tham chiếu <a href="https://web.dev/articles/vitals" target="_blank" rel="noopener">web.dev</a>.</p>' +
      renderMetricGrid(CORE, metrics) +
      "</section>" +

      '<section class="stats-section">' +
      '<h2 class="stats-heading">Chỉ số chẩn đoán</h2>' +
      '<p class="stats-help">FCP và TTFB giúp chẩn đoán nguyên nhân, <strong>không phải Core Web Vitals chính</strong> ' +
      "và không trực tiếp ảnh hưởng xếp hạng.</p>" +
      renderMetricGrid(DIAGNOSTIC, metrics) +
      "</section>" +

      '<section class="stats-section">' +
      '<h2 class="stats-heading">Top trang chậm nhất (LCP P75)</h2>' +
      renderSlowPages(summary.slow_pages) +
      "</section>" +

      '<section class="stats-section stats-section--local">' +
      '<h2 class="stats-heading">Hoạt động cục bộ <span class="stats-tag">Local debug only</span></h2>' +
      '<p class="stats-help">Lượt xem/đọc ghi ở localStorage của riêng trình duyệt này (không phải số liệu toàn blog).</p>' +
      renderLocalActivity() +
      '<button type="button" class="stats-btn stats-btn--danger" id="clear-stats">Xoá dữ liệu cục bộ (debug)</button>' +
      "</section>";

    // wire window toggle
    Array.prototype.forEach.call(container.querySelectorAll("[data-window]"), function (btn) {
      btn.addEventListener("click", function () {
        var win = btn.getAttribute("data-window");
        if (win === state.window) return;
        state.window = win;
        load();
      });
    });

    var clearBtn = container.querySelector("#clear-stats");
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        if (!confirm("Xoá Web Vitals + events cục bộ khỏi trình duyệt này? (Không ảnh hưởng dữ liệu RUM trên máy chủ)")) return;
        try {
          localStorage.removeItem("zola-vitals");
          localStorage.removeItem("zola-events");
        } catch (e) {}
        load();
      });
    }
  }

  function renderLoading() {
    container.innerHTML = '<p class="stats-loading">Đang tải dữ liệu Speed Insights…</p>';
  }

  function load() {
    renderLoading();
    fetchSummary(state.window).then(function (rum) {
      if (rum) {
        render(rum);
      } else {
        // Backend unreachable → labelled local-debug fallback.
        render(buildLocalSummary(state.window));
      }
    });
  }

  load();
})();
