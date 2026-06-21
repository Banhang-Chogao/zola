/**
 * Admin countdown preview — allows editing footer-countdown.json config
 * and previewing the countdown display in real-time.
 */
(function () {
  "use strict";

  var previewRoot = document.querySelector("[data-preview-countdown]");
  if (!previewRoot) return;

  var titleInput = document.getElementById("countdown-title");
  var dateInput = document.getElementById("countdown-date");
  var timeInput = document.getElementById("countdown-time");
  var timezoneInput = document.getElementById("countdown-timezone");
  var displayModeSelect = document.getElementById("countdown-display-mode");
  var previewText = document.querySelector("[data-preview-text]");

  if (!titleInput || !previewText) return;

  function showsSeconds() {
    return displayModeSelect.value === "full";
  }

  function previewTickMs() {
    return showsSeconds() ? 1000 : 60000;
  }

  function digit(value) {
    return '<span class="countdown-preview__digit">' + value + "</span>";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function targetMs(dateStr, timeStr, timeZone) {
    if (!dateStr || !timeStr) return Date.now();
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
      seconds: sec % 60,
      past: endMs <= nowMs,
    };
  }

  function buildRestSegment(parts) {
    var html =
      '<span class="countdown-preview__word">CÒN</span> ' +
      digit(parts.totalHours) + ' ' +
      '<span class="countdown-preview__word">GIỜ</span> ' +
      digit(parts.minutes) + ' ' +
      '<span class="countdown-preview__word">PHÚT</span> ';

    if (showsSeconds()) {
      html +=
        digit(parts.seconds) + ' ' +
        '<span class="countdown-preview__word">GIÂY</span> ';
    }

    html +=
      '<span class="countdown-preview__word">NỮA LÀ TỚI:</span> ' +
      '<span class="countdown-preview__title">' +
      escapeHtml(titleInput.value || "Event") +
      "</span>";

    return html;
  }

  function buildMessage(parts) {
    if (parts.past) {
      return (
        '<span class="countdown-preview__past">SỰ KIỆN ĐÃ DIỄN RA: ' +
        '<span class="countdown-preview__title">' +
        escapeHtml(titleInput.value || "Event") +
        "</span></span>"
      );
    }

    if (displayModeSelect.value === "days") {
      return (
        '<span class="countdown-preview__dual">' +
          '<span class="countdown-preview__segment countdown-preview__segment--days">' +
            '<span class="countdown-preview__word">CÒN</span> ' +
            digit(parts.days) + ' ' +
            '<span class="countdown-preview__word">NGÀY</span> ' +
            '<span class="countdown-preview__word">NỮA LÀ TỚI:</span> ' +
            '<span class="countdown-preview__title">' +
            escapeHtml(titleInput.value || "Event") +
            "</span>" +
          "</span>" +
        "</span>"
      );
    }

    return (
      '<span class="countdown-preview__dual">' +
        '<span class="countdown-preview__segment countdown-preview__segment--days">' +
          '<span class="countdown-preview__word">CÒN</span> ' +
          digit(parts.days) + ' ' +
          '<span class="countdown-preview__word">NGÀY</span>' +
        "</span>" +
        '<span class="countdown-preview__sep" aria-hidden="true">|</span>' +
        '<span class="countdown-preview__segment countdown-preview__segment--rest">' +
          buildRestSegment(parts) +
        "</span>" +
      "</span>"
    );
  }

  var timerId = null;

  function tick() {
    var title = titleInput.value || "Event";
    var date = dateInput.value;
    var time = timeInput.value || "00:00";
    var tz = timezoneInput.value || "Asia/Ho_Chi_Minh";

    if (!date) {
      previewText.innerHTML =
        '<span class="countdown-preview__placeholder">Chọn ngày để xem preview</span>';
      return;
    }

    var end = targetMs(date, time, tz);
    var parts = remainingParts(Date.now(), end);
    previewText.innerHTML = buildMessage(parts);
  }

  function start() {
    tick();
    if (timerId) clearInterval(timerId);
    timerId = setInterval(tick, previewTickMs());
  }

  function handleChange() {
    start();
  }

  if (titleInput) titleInput.addEventListener("input", handleChange);
  if (dateInput) dateInput.addEventListener("change", handleChange);
  if (timeInput) timeInput.addEventListener("change", handleChange);
  if (timezoneInput) timezoneInput.addEventListener("change", handleChange);
  if (displayModeSelect) displayModeSelect.addEventListener("change", handleChange);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
