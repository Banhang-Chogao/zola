/**
 * GA Health — refresh the GA stats module's health banner from GA Vacxin.
 *
 * Polls /data/ga-health.json (committed hourly by the GA Vacxin workflow) and
 * keeps the inline warning banner, the "healthy" pulse, the dashboard/fix links
 * and the last-checked time in sync between deploys. Purely presentational — it
 * never touches GA4 collection and never throws (a missing node or a bad fetch
 * just leaves the server-rendered banner untouched).
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-ga-health]");
  if (!root) return;

  var POLL_MS = 5 * 60 * 1000;
  var CACHE_KEY = "zola-ga-health-cache";

  var base = (function () {
    try {
      var m = document.querySelector('meta[name="zola-base-url"]');
      return m && m.content ? m.content.replace(/\/$/, "") : "";
    } catch (e) { return ""; }
  })();

  var banner = root.querySelector("[data-ga-banner]");
  var bannerIcon = root.querySelector("[data-ga-banner-icon]");
  var bannerTitle = root.querySelector("[data-ga-banner-title]");
  var bannerMsg = root.querySelector("[data-ga-banner-msg]");
  var bannerBtn = root.querySelector("[data-ga-banner-btn]");
  var pulse = root.querySelector("[data-ga-pulse]");
  var dashLink = root.querySelector("[data-ga-dashboard]");
  var checkedTime = root.querySelector("[data-ga-checked-time]");
  var bakedChecked = root.getAttribute("data-baked-checked") || "";

  var TITLES = {
    disconnected: "Mất kết nối Google Analytics",
    error: "Cần kiểm tra Google Analytics",
    pending: "Đang chờ GA Vacxin",
  };

  function formatTime(iso) {
    if (!iso) return "—";
    try {
      if (window.ZolaDateTime && window.ZolaDateTime.formatDisplayDateTime) {
        return window.ZolaDateTime.formatDisplayDateTime(iso);
      }
      return new Date(iso).toLocaleString("vi-VN");
    } catch (e) { return iso; }
  }

  function setHidden(el, hidden) {
    if (!el) return;
    if (hidden) { el.setAttribute("hidden", ""); }
    else { el.removeAttribute("hidden"); }
  }

  function apply(data) {
    if (!data || !data.status) return;
    var status = String(data.status);
    var ok = status === "ok";

    // Healthy pulse vs warning banner are mutually exclusive.
    setHidden(pulse, !ok);
    setHidden(banner, ok);

    if (!ok && banner) {
      banner.className = "ga-stats__health ga-stats__health--" + status;
      if (bannerIcon) bannerIcon.textContent = status === "pending" ? "⏳" : "⚠";
      if (bannerTitle) bannerTitle.textContent = TITLES[status] || TITLES.error;
      if (bannerMsg && data.message) bannerMsg.textContent = data.message;
      if (bannerBtn && data.fix_url) bannerBtn.setAttribute("href", data.fix_url);
    }

    if (dashLink && data.dashboard_url) dashLink.setAttribute("href", data.dashboard_url);

    if (checkedTime && data.last_checked) {
      checkedTime.setAttribute("datetime", data.last_checked);
      checkedTime.textContent = formatTime(data.last_checked);
    }
    root.setAttribute("data-ga-status", status);
    root.setAttribute("data-baked-checked", data.last_checked || "");
  }

  function fetchFresh() {
    var url = base + "/data/ga-health.json?t=" + Date.now();
    return fetch(url, { credentials: "omit", cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.last_checked) return;
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: data }));
        } catch (e) { /* quota */ }
        if (data.last_checked === bakedChecked) return;
        bakedChecked = data.last_checked;
        apply(data);
      })
      .catch(function () { /* keep server-rendered banner */ });
  }

  try {
    var cached = sessionStorage.getItem(CACHE_KEY);
    if (cached) {
      var parsed = JSON.parse(cached);
      if (parsed && parsed.data && parsed.data.last_checked &&
          parsed.data.last_checked !== bakedChecked) {
        apply(parsed.data);
        bakedChecked = parsed.data.last_checked;
      }
    }
  } catch (e) { /* ignore */ }

  fetchFresh();
  setInterval(fetchFresh, POLL_MS);
})();
