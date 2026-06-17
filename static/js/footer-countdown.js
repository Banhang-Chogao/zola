/**
 * Footer countdown — dual format:
 * CÒN X NGÀY | CÒN Y GIỜ Z PHÚT NỮA LÀ TỚI: EVENT_NAME
 * Updates every minute. No external APIs.
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
  };

  var timerId = null;
  var TICK_MS = 60000;

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

  function remainingParts(nowMs, endMs) {
    var left = Math.max(0, endMs - nowMs);
    var sec = Math.floor(left / 1000);
    return {
      days: Math.floor(sec / 86400),
      totalHours: Math.floor(sec / 3600),
      minutes: Math.floor((sec % 3600) / 60),
      past: endMs <= nowMs,
    };
  }

  function digit(value) {
    return '<span class="footer-countdown__digit">' + value + "</span>";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function buildMessage(parts) {
    if (parts.past) {
      return (
        '<span class="footer-countdown__past">SỰ KIỆN ĐÃ DIỄN RA: ' +
        '<strong class="footer-countdown__title">' + escapeHtml(cfg.title) + "</strong></span>"
      );
    }

    return (
      '<span class="footer-countdown__dual">' +
        '<span class="footer-countdown__segment footer-countdown__segment--days">' +
          '<span class="footer-countdown__word">CÒN</span> ' +
          digit(parts.days) + ' ' +
          '<span class="footer-countdown__word">NGÀY</span>' +
        "</span>" +
        '<span class="footer-countdown__sep" aria-hidden="true">|</span>' +
        '<span class="footer-countdown__segment footer-countdown__segment--rest">' +
          '<span class="footer-countdown__word">CÒN</span> ' +
          digit(parts.totalHours) + ' ' +
          '<span class="footer-countdown__word">GIỜ</span> ' +
          digit(parts.minutes) + ' ' +
          '<span class="footer-countdown__word">PHÚT NỮA LÀ TỚI:</span> ' +
          '<strong class="footer-countdown__title">' + escapeHtml(cfg.title) + "</strong>" +
        "</span>" +
      "</span>"
    );
  }

  function ariaLabel(parts) {
    if (parts.past) return "Sự kiện đã diễn ra: " + cfg.title;
    return (
      "Còn " + parts.days + " ngày, còn " + parts.totalHours +
      " giờ " + parts.minutes + " phút nữa là tới: " + cfg.title
    );
  }

  function tick() {
    if (!cfg.targetDate || !cfg.title) {
      root.hidden = true;
      return;
    }
    var end = targetMs(cfg.targetDate, cfg.targetTime, cfg.timezone);
    var parts = remainingParts(Date.now(), end);
    if (loadingEl) loadingEl.remove();
    textEl.innerHTML = buildMessage(parts);
    root.setAttribute("aria-label", ariaLabel(parts));
  }

  function start() {
    tick();
    if (timerId) clearInterval(timerId);
    timerId = setInterval(tick, TICK_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();