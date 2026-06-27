/**
 * RUM — Real User Monitoring qua web-vitals.
 *
 * Gửi Core Web Vitals đo trên trình duyệt THẬT của người đọc về backend VIPZone
 * (POST {endpoint}/rum/web-vitals). Đo: LCP, INP, CLS, FCP, TTFB.
 *
 * Nguyên tắc (BẮT BUỘC):
 *   - Privacy-first: tôn trọng Do Not Track / Global Privacy Control; KHÔNG gửi
 *     PII; KHÔNG gửi query string (chỉ pathname); UA rút gọn.
 *   - Sampling: mặc định 10% production, 100% khi có ?rum_debug=1.
 *   - Fail-soft: bọc try/catch toàn bộ — không bao giờ ném lỗi, không chặn render,
 *     không đụng UI/layout. Backend lỗi/không có → im lặng bỏ qua.
 *   - Chống spam: mỗi metric gửi đúng 1 lần theo callback của thư viện (không loop).
 *
 * Tái dùng global `webVitals` (IIFE build web-vitals@4) đã được nạp ở <head>.
 * Config đọc từ data-* trên chính thẻ <script> (base.html bake từ config.toml):
 *   data-endpoint   URL ingest đầy đủ (vd https://blog-vipzone-api.onrender.com/rum/web-vitals)
 *   data-sample     tỉ lệ lấy mẫu production 0..1 (mặc định 0.1)
 *   data-page-type  nhãn loại trang (home|article|category|tag|listing|tool|...)
 *   data-env        "production" | "dev"
 */
(function () {
  "use strict";

  // currentScript có sẵn trong lúc thực thi đồng bộ của script (kể cả khi defer).
  var SELF = document.currentScript ||
    document.querySelector('script[data-rum-web-vitals]');

  function attr(name, fallback) {
    try {
      var v = SELF && SELF.getAttribute(name);
      return v === null || v === undefined || v === "" ? fallback : v;
    } catch (e) {
      return fallback;
    }
  }

  // ---- Config ----------------------------------------------------------------
  var ENDPOINT = attr("data-endpoint", "");
  var PAGE_TYPE = attr("data-page-type", "other");
  var ENV = attr("data-env", "production");
  var SAMPLE_RATE = parseFloat(attr("data-sample", "0.1"));
  if (!(SAMPLE_RATE >= 0 && SAMPLE_RATE <= 1)) SAMPLE_RATE = 0.1;

  // Không có endpoint → không có gì để gửi (vd backend chưa cấu hình). Im lặng.
  if (!ENDPOINT) return;

  // ---- Privacy gates ---------------------------------------------------------
  // Do Not Track (legacy) + Global Privacy Control. Bất kỳ tín hiệu nào bật → thoát.
  function privacyOptOut() {
    try {
      var dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
      if (dnt === "1" || dnt === "yes" || dnt === true) return true;
      if (navigator.globalPrivacyControl === true) return true;
    } catch (e) {}
    return false;
  }

  // Bỏ qua trình duyệt tự động (Playwright/Puppeteer của chính repo) để tránh nhiễu.
  function isAutomated() {
    try {
      return navigator.webdriver === true;
    } catch (e) {
      return false;
    }
  }

  // Defense-in-depth: dù base.html đã KHÔNG nhúng script ở route admin/editor,
  // vẫn tự chặn nếu vô tình chạy ở các path riêng tư.
  var PRIVATE_PREFIXES = [
    "/editor", "/admin-author", "/admin-countdown", "/admin/",
    "/worldcup-content-manager", "/bao-cao-tong-ket",
  ];
  function isPrivatePath() {
    try {
      var p = location.pathname || "/";
      for (var i = 0; i < PRIVATE_PREFIXES.length; i++) {
        if (p === PRIVATE_PREFIXES[i] || p.indexOf(PRIVATE_PREFIXES[i]) === 0) return true;
      }
    } catch (e) {}
    return false;
  }

  if (privacyOptOut() || isAutomated() || isPrivatePath()) return;

  // ---- Sampling --------------------------------------------------------------
  // ?rum_debug=1 → luôn lấy mẫu 100% + log ra console để debug thủ công.
  var DEBUG = false;
  try {
    DEBUG = new URLSearchParams(location.search).get("rum_debug") === "1";
  } catch (e) {}

  var SAMPLED = DEBUG || (ENV !== "production") || (Math.random() < SAMPLE_RATE);
  if (!SAMPLED) return;

  // ---- Payload tĩnh (tính 1 lần / page load) --------------------------------
  function navType() {
    try {
      var nav = performance.getEntriesByType("navigation")[0];
      if (nav && nav.type) return String(nav.type);
    } catch (e) {}
    return "";
  }

  function connInfo() {
    try {
      var c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (c) {
        return {
          effective_type: c.effectiveType || "",
          save_data: !!c.saveData,
        };
      }
    } catch (e) {}
    return { effective_type: "", save_data: false };
  }

  var CONN = connInfo();
  var BASE = {
    v: 1,
    // Chỉ pathname — KHÔNG gửi query string (có thể chứa thông tin nhạy cảm).
    page_path: (location.pathname || "/").slice(0, 300),
    page_type: PAGE_TYPE,
    nav_type: navType(),
    viewport_w: Math.max(0, window.innerWidth || 0) | 0,
    viewport_h: Math.max(0, window.innerHeight || 0) | 0,
    connection: CONN.effective_type,
    save_data: CONN.save_data,
    // UA rút gọn (không phải PII định danh; cắt ngắn để chống fingerprint nặng).
    ua: (navigator.userAgent || "").slice(0, 180),
  };

  // ---- Gửi dữ liệu (sendBeacon → fetch keepalive) ---------------------------
  function send(payload) {
    var body;
    try {
      body = JSON.stringify(payload);
    } catch (e) {
      return;
    }
    if (DEBUG) {
      try { console.info("[RUM]", payload.metric, payload.value, payload.rating); } catch (e) {}
    }
    // 1) navigator.sendBeacon — bền vững khi trang đang ẩn/đóng.
    try {
      if (navigator.sendBeacon) {
        var blob = new Blob([body], { type: "application/json" });
        if (navigator.sendBeacon(ENDPOINT, blob)) return;
      }
    } catch (e) {}
    // 2) fallback fetch keepalive.
    try {
      fetch(ENDPOINT, {
        method: "POST",
        body: body,
        keepalive: true,
        mode: "cors",
        credentials: "omit",
        headers: { "Content-Type": "application/json" },
      }).catch(function () {});
    } catch (e) {}
  }

  // Tóm tắt attribution (chỉ khi dùng attribution build — standard build bỏ qua).
  function attributionSummary(metric) {
    var a = metric && metric.attribution;
    if (!a || typeof a !== "object") return undefined;
    var out = {};
    var keys = [
      "element", "url", "largestShiftTarget", "eventTarget", "eventType",
      "loadState", "navigationEntry",
    ];
    for (var i = 0; i < keys.length; i++) {
      var val = a[keys[i]];
      if (typeof val === "string" && val) out[keys[i]] = val.slice(0, 200);
    }
    return Object.keys(out).length ? out : undefined;
  }

  function report(metric) {
    try {
      var payload = {};
      for (var k in BASE) if (BASE.hasOwnProperty(k)) payload[k] = BASE[k];
      payload.metric = metric.name;                       // LCP | INP | CLS | FCP | TTFB
      // CLS là tỉ số (≈0..) — giữ 4 chữ số; còn lại là ms → làm tròn nhẹ.
      payload.value = Math.round(metric.value * 10000) / 10000;
      payload.rating = metric.rating || "";               // good | needs-improvement | poor
      payload.delta = Math.round((metric.delta || 0) * 10000) / 10000;
      payload.id = String(metric.id || "").slice(0, 80);
      if (metric.navigationType) payload.metric_nav = String(metric.navigationType).slice(0, 40);
      var attr = attributionSummary(metric);
      if (attr) payload.attribution = attr;
      send(payload);
    } catch (e) {}
  }

  // ---- Đăng ký callback (đợi web-vitals global nạp xong) --------------------
  var tries = 0;
  function init() {
    var wv = window.webVitals;
    if (!wv || typeof wv.onLCP !== "function") {
      if (tries++ < 20) { setTimeout(init, 250); }       // CDN defer chưa nạp xong → thử lại tối đa ~5s
      return;
    }
    // Mỗi hàm onX gọi callback đúng 1 lần với giá trị cuối (mặc định
    // reportAllChanges=false) → không loop, không spam.
    try { wv.onLCP(report); } catch (e) {}
    try { wv.onINP(report); } catch (e) {}
    try { wv.onCLS(report); } catch (e) {}
    try { wv.onFCP(report); } catch (e) {}
    try { wv.onTTFB(report); } catch (e) {}
  }

  init();
})();
