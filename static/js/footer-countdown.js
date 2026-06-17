/**
 * Footer countdown — lightweight client update from data/footer-countdown.json
 * baked into data-* attributes at build time. No external APIs.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-countdown-root]");
  if (!root) return;

  var textEl = root.querySelector("[data-countdown-text]");
  var loadingEl = root.querySelector("[data-countdown-loading]");
  if (!textEl) return;

  var cfgEl = document.getElementById("footer-countdown-config");
  var parsed = {};
  try {
    parsed = JSON.parse((cfgEl && cfgEl.textContent) || "{}");
  } catch (e) {
    parsed = {};
  }

  var cfg = {
    title: parsed.title || "",
    targetDate: parsed.targetDate || "",
    targetTime: parsed.targetTime || "00:00",
    timezone: parsed.timezone || "Asia/Ho_Chi_Minh",
    displayMode: parsed.displayMode || "days",
    prefix: parsed.footerTextPrefix || "Còn",
    suffix: parsed.footerTextSuffix || "nữa là tới",
  };

  var timerId = null;

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  /** Parse local date+time in IANA timezone → UTC ms (no external libs). */
  function targetMs(dateStr, timeStr, timeZone) {
    var parts = dateStr.split("-").map(Number);
    var tparts = timeStr.split(":").map(Number);
    var y = parts[0];
    var mo = parts[1];
    var d = parts[2];
    var hh = tparts[0] || 0;
    var mm = tparts[1] || 0;

    var utc = Date.UTC(y, mo - 1, d, hh, mm, 0);
    for (var i = 0; i < 4; i++) {
      var fmt = new Intl.DateTimeFormat("en-US", {
        timeZone: timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
      var map = {};
      fmt.formatToParts(new Date(utc)).forEach(function (p) {
        if (p.type !== "literal") map[p.type] = p.value;
      });
      var asUtc = Date.UTC(
        +map.year,
        +map.month - 1,
        +map.day,
        +map.hour,
        +map.minute,
        +map.second
      );
      var diff = Date.UTC(y, mo - 1, d, hh, mm, 0) - asUtc;
      utc += diff;
    }
    return utc;
  }

  function diffParts(nowMs, endMs) {
    var left = Math.max(0, endMs - nowMs);
    var sec = Math.floor(left / 1000);
    return {
      days: Math.floor(sec / 86400),
      hours: Math.floor((sec % 86400) / 3600),
      minutes: Math.floor((sec % 3600) / 60),
      seconds: sec % 60,
      past: endMs <= nowMs,
    };
  }

  function digitSpan(value, unit) {
    return (
      '<span class="footer-countdown__unit" aria-hidden="true">' +
      '<span class="footer-countdown__digit">' + value + "</span> " +
      unit +
      "</span>"
    );
  }

  function buildMessage(parts) {
    if (parts.past) {
      return (
        '<span class="footer-countdown__past">Sự kiện đã diễn ra: ' +
        '<strong class="footer-countdown__title">' + escapeHtml(cfg.title) + "</strong></span>"
      );
    }

    var mode = cfg.displayMode;
    var body = "";

    if (mode === "full") {
      body =
        digitSpan(parts.days, "ngày") + " " +
        digitSpan(pad2(parts.hours), "giờ") + " " +
        digitSpan(pad2(parts.minutes), "phút") + " " +
        digitSpan(pad2(parts.seconds), "giây");
    } else if (mode === "days_hours_minutes") {
      body =
        digitSpan(parts.days, "ngày") + " " +
        digitSpan(pad2(parts.hours), "giờ") + " " +
        digitSpan(pad2(parts.minutes), "phút");
    } else {
      body = digitSpan(parts.days, "ngày");
    }

    return (
      '<span class="footer-countdown__prefix">' + escapeHtml(cfg.prefix) + "</span> " +
      body + " " +
      '<span class="footer-countdown__suffix">' + escapeHtml(cfg.suffix) + ":</span> " +
      '<strong class="footer-countdown__title">' + escapeHtml(cfg.title) + "</strong>"
    );
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function tick() {
    if (!cfg.targetDate || !cfg.title) {
      root.hidden = true;
      return;
    }
    var end = targetMs(cfg.targetDate, cfg.targetTime, cfg.timezone);
    var parts = diffParts(Date.now(), end);
    if (loadingEl) loadingEl.remove();
    textEl.innerHTML = buildMessage(parts);
    root.setAttribute(
      "aria-label",
      parts.past
        ? "Sự kiện đã diễn ra: " + cfg.title
        : cfg.prefix + " " + parts.days + " ngày " + cfg.suffix + ": " + cfg.title
    );
  }

  function intervalMs() {
    return cfg.displayMode === "full" ? 1000 : 60000;
  }

  function start() {
    tick();
    if (timerId) clearInterval(timerId);
    timerId = setInterval(tick, intervalMs());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();