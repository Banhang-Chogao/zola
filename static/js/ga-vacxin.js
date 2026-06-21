/**
 * GA Vacxin client — refresh the footer GA module's health state from
 * static/data/ga-vacxin-report.json (committed hourly by the GA Vacxin bot).
 *
 * Hardening / guarantees:
 *  - No-op when the module is absent (every access is guarded).
 *  - CACHE ISOLATION: a fetched report is applied ONLY when its property_id
 *    matches the property the page was built for (data-ga-property). A report
 *    from a different/old property is ignored — old numbers never leak.
 *  - sessionStorage cache key is NAMESPACED by property id.
 *  - Everything is wrapped so a malformed payload can never throw (no JS crash).
 *  - Never touches GA collection and never touches the server-rendered KPI numbers.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-ga-module]");
  if (!root) return;

  var expectedProperty = root.getAttribute("data-ga-property") || "";
  var CACHE_KEY = "zola-ga-vacxin::" + expectedProperty;
  var POLL_MS = 10 * 60 * 1000;

  var base = (function () {
    try {
      var m = document.querySelector('meta[name="zola-base-url"]');
      return m && m.content ? m.content.replace(/\/$/, "") : "";
    } catch (e) {
      return "";
    }
  })();

  var HEALTH_TEXT = {
    healthy: "Hoạt động tốt",
    error: "Mất kết nối",
    degraded: "Cảnh báo",
    pending: "Chờ kiểm tra",
  };
  var KNOWN = { healthy: 1, error: 1, degraded: 1, pending: 1 };

  function $(sel) {
    try { return root.querySelector(sel); } catch (e) { return null; }
  }

  function formatTime(iso) {
    if (!iso) return "";
    try {
      if (window.ZolaDateTime && window.ZolaDateTime.formatDisplayDateTime) {
        return window.ZolaDateTime.formatDisplayDateTime(iso);
      }
      return new Date(iso).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
    } catch (e) {
      return String(iso);
    }
  }

  function setModuleStatus(status) {
    try {
      ["healthy", "error", "degraded", "pending"].forEach(function (s) {
        root.classList.remove("ga-module--" + s);
      });
      root.classList.add("ga-module--" + status);
      root.setAttribute("data-ga-health", status);
    } catch (e) { /* ignore */ }
  }

  function updatePill(report) {
    var pill = $("[data-ga-health-pill]");
    if (!pill) return;
    var status = report.status;
    try {
      ["healthy", "error", "degraded", "pending"].forEach(function (s) {
        pill.classList.remove("ga-module__health--" + s);
      });
      pill.classList.add("ga-module__health--" + status);
      var txt = pill.querySelector("[data-ga-health-text]");
      if (txt) txt.textContent = HEALTH_TEXT[status] || HEALTH_TEXT.pending;
      if (report.checked_at) {
        pill.setAttribute("title", "GA Vacxin · kiểm tra " + formatTime(report.checked_at));
      }
    } catch (e) { /* ignore */ }
  }

  function updateBanner(report) {
    var status = report.status;
    var banner = $("[data-ga-banner]");
    var isProblem = status === "error" || status === "degraded";
    if (!isProblem) {
      // Health recovered — remove any stale banner so the module stays calm.
      if (banner && banner.parentNode) {
        try { banner.parentNode.removeChild(banner); } catch (e) { /* ignore */ }
      }
      return;
    }
    if (!banner) return; // server didn't render one; avoid building DOM from scratch
    try {
      banner.classList.remove("ga-module__banner--error", "ga-module__banner--degraded");
      banner.classList.add("ga-module__banner--" + status);
      var title = banner.querySelector("[data-ga-banner-title]");
      if (title) {
        title.textContent = status === "error"
          ? "Google Analytics đang mất kết nối"
          : "Cảnh báo theo dõi Google Analytics";
      }
      var detail = banner.querySelector("[data-ga-banner-detail]");
      if (detail && report.summary) detail.textContent = report.summary;
      var fix = banner.querySelector("[data-ga-banner-fix]");
      if (fix && report.fix_url) fix.setAttribute("href", report.fix_url);
    } catch (e) { /* ignore */ }
  }

  function updateHealthUpdatedLine(report) {
    // Only update the "Kiểm tra: …" line when the module is in health mode
    // (no live KPI cards present). Never overwrite the live "Cập nhật … fetch
    // hourly từ GA4 Data API" message, which is bound to the real fetch time.
    if ($("[data-ga-kpis]")) return;
    var line = $("[data-ga-updated]");
    if (!line || !report.checked_at) return;
    try {
      line.innerHTML =
        'Kiểm tra: <time datetime="' + report.checked_at + '" data-ga-updated-time>' +
        formatTime(report.checked_at) + "</time> — GA Vacxin chạy mỗi giờ";
    } catch (e) { /* ignore */ }
  }

  function applyReport(report) {
    if (!report || typeof report !== "object") return;
    // CACHE ISOLATION: ignore reports for a different property.
    if (report.property_id && expectedProperty && report.property_id !== expectedProperty) {
      return;
    }
    var status = KNOWN[report.status] ? report.status : "pending";
    report.status = status;
    setModuleStatus(status);
    updatePill(report);
    updateBanner(report);
    updateHealthUpdatedLine(report);
  }

  function readCache() {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      return parsed && parsed.data ? parsed.data : null;
    } catch (e) {
      return null;
    }
  }

  function writeCache(data) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: data }));
    } catch (e) { /* quota / disabled */ }
  }

  function fetchFresh() {
    var url = base + "/data/ga-vacxin-report.json?t=" + Date.now();
    return fetch(url, { credentials: "omit", cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.status) return;
        if (data.property_id && expectedProperty && data.property_id !== expectedProperty) {
          return; // never cache/apply a foreign property's report
        }
        applyReport(data);
        writeCache(data);
      })
      .catch(function () { /* keep server-rendered state */ });
  }

  // Warm from namespaced cache first (instant), then refresh.
  try {
    var cached = readCache();
    if (cached) applyReport(cached);
  } catch (e) { /* ignore */ }

  fetchFresh();
  try { setInterval(fetchFresh, POLL_MS); } catch (e) { /* ignore */ }
})();
