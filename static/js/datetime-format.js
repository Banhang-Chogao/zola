/**
 * Shared display datetime formatters for the Zola blog UI.
 * Date: DD-MM-YYYY · Datetime: HH:mm:ss DD-MM-YYYY · TZ: Asia/Ho_Chi_Minh
 * Stored/raw ISO values are unchanged — use these only for visible text.
 */
(function (global) {
  "use strict";

  var TZ = "Asia/Ho_Chi_Minh";

  function partsInTz(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    var fmt = new Intl.DateTimeFormat("en-GB", {
      timeZone: TZ,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    var map = {};
    fmt.formatToParts(d).forEach(function (p) {
      if (p.type !== "literal") map[p.type] = p.value;
    });
    return map;
  }

  function formatDisplayDate(iso) {
    var p = partsInTz(iso);
    if (!p) {
      var s = String(iso || "");
      if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
        return s.slice(8, 10) + "-" + s.slice(5, 7) + "-" + s.slice(0, 4);
      }
      return s;
    }
    return p.day + "-" + p.month + "-" + p.year;
  }

  function formatDisplayTime(iso) {
    var p = partsInTz(iso);
    if (!p) return "";
    return p.hour + ":" + p.minute + ":" + p.second;
  }

  function formatDisplayDateTime(iso) {
    var p = partsInTz(iso);
    if (!p) return String(iso || "");
    return p.hour + ":" + p.minute + ":" + p.second + " " + p.day + "-" + p.month + "-" + p.year;
  }

  /** Compact chart axis label: DD-MM */
  function formatChartDayMonth(dateStr) {
    var s = String(dateStr || "");
    if (s.length >= 10 && s[4] === "-") {
      return s.slice(8, 10) + "-" + s.slice(5, 7);
    }
    var p = partsInTz(s);
    if (!p) return s.slice(0, 10);
    return p.day + "-" + p.month;
  }

  /** Table cell: show time when ISO carries a clock component. */
  function formatTxnDate(iso) {
    var s = String(iso || "");
    if (!s) return "—";
    if (s.length > 10 || /T\d{2}:\d{2}/.test(s)) {
      return formatDisplayDateTime(s);
    }
    return formatDisplayDate(s);
  }

  global.ZolaDateTime = {
    TZ: TZ,
    formatDisplayDate: formatDisplayDate,
    formatDisplayTime: formatDisplayTime,
    formatDisplayDateTime: formatDisplayDateTime,
    formatChartDayMonth: formatChartDayMonth,
    formatTxnDate: formatTxnDate,
  };
})(typeof window !== "undefined" ? window : globalThis);