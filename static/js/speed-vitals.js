/**
 * Speed Insights — Real-User-Monitoring (RUM) collector for Core Web Vitals.
 *
 * Sends every page's field measurements to durable, cross-visitor sinks instead
 * of treating per-browser localStorage as the source of truth:
 *
 *   1. GA4   — one `web_vital` event per metric (Google's web-vitals → GA4 recipe).
 *   2. VIPZone RUM backend — batched POST /rum/web-vitals via sendBeacon, so the
 *      Speed Insights dashboard reflects the WHOLE blog and survives a browser wipe.
 *   3. localStorage (`zola-vitals`) — a small LOCAL-DEBUG-ONLY mirror, never the
 *      production source. The dashboard labels it "Local debug only".
 *
 * Metrics (Core Web Vitals: LCP, INP, CLS · Diagnostic: FCP, TTFB).
 * API base + GA id are injected from config.toml via data-* on the script tag.
 */
(function () {
  "use strict";

  var script =
    document.getElementById("speed-vitals-js") || document.currentScript || {};
  var getAttr = script.getAttribute ? script.getAttribute.bind(script) : function () { return ""; };
  var API = (getAttr("data-rum-api") || "").replace(/\/+$/, "");
  var GA_ID = getAttr("data-ga-id") || "";

  var DEBUG_KEY = "zola-vitals"; // local debug mirror only — NOT the prod source
  var MAX_DEBUG = 200;

  function noTrack() {
    try {
      return sessionStorage.getItem("zola-no-track") === "1";
    } catch (e) {
      return false;
    }
  }

  // Coarse device class (no fingerprinting) for the dashboard's device filter.
  function deviceType() {
    var ua = navigator.userAgent || "";
    if (/\b(iPad|Tablet)\b/i.test(ua)) return "tablet";
    if (/Mobi|Android|iPhone|iPod/i.test(ua)) return "mobile";
    try {
      if (window.matchMedia && window.matchMedia("(max-width: 768px)").matches) return "mobile";
    } catch (e) {}
    return "desktop";
  }

  function navType() {
    try {
      var nav = performance.getEntriesByType("navigation")[0];
      return nav && nav.type ? String(nav.type) : "";
    } catch (e) {
      return "";
    }
  }

  var DEVICE = deviceType();
  var NAV = navType();
  var queue = [];
  var flushTimer = null;

  function round3(n) {
    return Math.round((Number(n) || 0) * 1000) / 1000;
  }

  function toEvent(metric) {
    return {
      metric_name: metric.name,
      metric_value: round3(metric.value),
      metric_rating: metric.rating, // "good" | "needs-improvement" | "poor"
      metric_delta: round3(metric.delta),
      metric_id: metric.id,
      page_path: location.pathname,
      page_url: location.href,
      device_type: DEVICE,
      navigation_type: NAV,
      timestamp: Date.now(),
    };
  }

  // 1. GA4 — emit one `web_vital` event as each metric finalises.
  function sendGA(ev) {
    if (!GA_ID || typeof window.gtag !== "function") return;
    try {
      window.gtag("event", "web_vital", {
        metric_name: ev.metric_name,
        metric_value: ev.metric_value,
        metric_rating: ev.metric_rating,
        metric_delta: ev.metric_delta,
        metric_id: ev.metric_id,
        page_path: ev.page_path,
        page_url: ev.page_url,
        device_type: ev.device_type,
        navigation_type: ev.navigation_type,
        timestamp: ev.timestamp,
        // GA4 reporting value: CLS scaled ×1000 (so 0.1 → 100), others rounded ms.
        value:
          ev.metric_name === "CLS"
            ? Math.round(ev.metric_value * 1000)
            : Math.round(ev.metric_value),
        non_interaction: true,
      });
    } catch (e) {}
  }

  // 2. localStorage debug mirror (clearly local-only, capped small).
  function mirrorDebug(ev) {
    try {
      var arr = JSON.parse(localStorage.getItem(DEBUG_KEY) || "[]");
      if (!Array.isArray(arr)) arr = [];
      arr.push({
        name: ev.metric_name,
        value: ev.metric_value,
        rating: ev.metric_rating,
        path: ev.page_path,
        ts: ev.timestamp,
      });
      if (arr.length > MAX_DEBUG) arr = arr.slice(-MAX_DEBUG);
      localStorage.setItem(DEBUG_KEY, JSON.stringify(arr));
    } catch (e) {}
  }

  // 3. VIPZone RUM backend — batch the buffered metrics into one beacon.
  function flush() {
    if (flushTimer) {
      clearTimeout(flushTimer);
      flushTimer = null;
    }
    if (!API || !queue.length) return;
    var batch = queue.splice(0, queue.length);
    var url = API + "/rum/web-vitals";
    var payload = JSON.stringify({ events: batch });
    try {
      if (navigator.sendBeacon) {
        var blob = new Blob([payload], { type: "application/json" });
        if (navigator.sendBeacon(url, blob)) return;
      }
    } catch (e) {}
    // Fallback: keepalive fetch (survives the unload that sendBeacon would handle).
    try {
      fetch(url, {
        method: "POST",
        body: payload,
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        mode: "cors",
        credentials: "omit",
      })["catch"](function () {});
    } catch (e) {}
  }

  function scheduleFlush() {
    if (flushTimer || !API) return;
    // Early metrics (TTFB/FCP/LCP) finalise long before the page hides — flush
    // them shortly after they arrive so nothing is lost if the visitor stays.
    flushTimer = setTimeout(function () {
      flushTimer = null;
      flush();
    }, 1500);
  }

  function record(metric) {
    if (noTrack()) return;
    var ev = toEvent(metric);
    sendGA(ev);
    mirrorDebug(ev);
    if (API) {
      queue.push(ev);
      scheduleFlush();
    }
  }

  function init() {
    if (typeof webVitals === "undefined") {
      setTimeout(init, 300);
      return;
    }
    // Default reportAllChanges=false → each callback fires once with the final
    // value (CLS/INP finalise at page hide), which is exactly the RUM model.
    webVitals.onCLS(record);
    webVitals.onLCP(record);
    webVitals.onFCP(record);
    webVitals.onINP(record);
    webVitals.onTTFB(record);
  }

  // Flush on lifecycle transitions. Both handlers run so that even if the
  // visibilitychange flush fires before web-vitals records the final CLS/INP,
  // pagehide still drains the stragglers.
  addEventListener(
    "visibilitychange",
    function () {
      if (document.visibilityState === "hidden") flush();
    },
    { capture: true }
  );
  addEventListener("pagehide", flush, { capture: true });

  init();
})();
