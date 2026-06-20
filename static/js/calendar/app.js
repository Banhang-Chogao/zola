/**
 * Calendar — client-side calendar for the Zola static blog.
 * Microsoft 365-style UX (Day/Week/Month, drag-drop, side agenda, keyboard)
 * with S-DNA visual language. Events persist in localStorage only —
 * nothing is sent to a server.
 */
(function () {
  "use strict";

  /* ============================ constants ============================ */
  const LS_KEY = "zola_calendar_events_v1";
  const LS_SEEDED = "zola_calendar_seeded_v1";
  const HOUR_H = 48;   // px per hour in the time grid
  const BAR_H = 22;    // px per all-day/multi-day bar row in month view
  const SNAP = 15;     // minutes — drag snap
  const MONTH_CHIP_CAP = 3;

  const WD_LONG = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"];
  const WD_SHORT = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  const COLORS = [
    { key: "teal", label: "Teal" },
    { key: "blue", label: "Xanh dương" },
    { key: "purple", label: "Tím" },
    { key: "amber", label: "Hổ phách" },
    { key: "green", label: "Xanh lá" },
    { key: "red", label: "Đỏ" },
    { key: "pink", label: "Hồng" },
  ];
  const COLOR_KEYS = COLORS.map(function (c) { return c.key; });

  const $ = function (sel, root) { return (root || document).querySelector(sel); };
  const $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* ============================== state ============================== */
  const today0 = startOfDay(new Date());
  const state = {
    view: "month",
    anchor: today0,        // any day in the focused period
    selected: today0,      // selected day (drives agenda + mini)
    miniMonth: startOfMonth(today0),
    sideOpen: true,
    events: [],
  };

  let drag = null;     // active drag descriptor
  let nowTimer = null;

  /* ============================ date utils ========================== */
  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function startOfDay(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  function startOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
  function addDays(d, n) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
  function addMonths(d, n) { return new Date(d.getFullYear(), d.getMonth() + n, 1); }
  function ymd(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function parseYmd(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }
  function startOfWeek(d) { var x = startOfDay(d); return addDays(x, -((x.getDay() + 6) % 7)); }
  function minutesOf(d) { return d.getHours() * 60 + d.getMinutes(); }
  function atMinutes(day, mins) { var x = startOfDay(day); x.setMinutes(mins); return x; }
  function daysBetween(a, b) { return Math.round((startOfDay(b) - startOfDay(a)) / 86400000); }
  function dmy(d) { return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear(); }
  function hm(d) { return pad(d.getHours()) + ":" + pad(d.getMinutes()); }
  function wdLong(d) { return WD_LONG[(d.getDay() + 6) % 7]; }

  function toLocalIso(d) {
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) +
      "T" + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }
  function fromLocalIso(s) {
    if (!s) return null;
    var m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
    if (!m) return null;
    return new Date(+m[1], +m[2] - 1, +m[3], m[4] ? +m[4] : 0, m[5] ? +m[5] : 0);
  }

  function uid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "e" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  /* ============================== storage =========================== */
  function load() {
    try { var raw = JSON.parse(localStorage.getItem(LS_KEY) || "[]"); return Array.isArray(raw) ? raw : []; }
    catch (_) { return []; }
  }
  function save() {
    try { localStorage.setItem(LS_KEY, JSON.stringify(state.events)); } catch (_) { /* quota */ }
  }

  function seedIfFirstRun() {
    if (localStorage.getItem(LS_SEEDED)) return;
    localStorage.setItem(LS_SEEDED, "1");
    if (state.events.length) return;
    var d = today0;
    state.events = [
      mkEvent({ title: "Họp kế hoạch tuần", color: "teal",
        start: toLocalIso(atMinutes(d, 9 * 60)), end: toLocalIso(atMinutes(d, 10 * 60)), location: "Phòng họp A" }),
      mkEvent({ title: "Viết bài blog", color: "purple",
        start: toLocalIso(atMinutes(d, 14 * 60)), end: toLocalIso(atMinutes(d, 15 * 60 + 30)) }),
      mkEvent({ title: "Nghỉ lễ", color: "amber", allDay: true,
        start: toLocalIso(addDays(d, 2)), end: toLocalIso(addDays(d, 3)) }),
      mkEvent({ title: "Deadline dự án", color: "red",
        start: toLocalIso(atMinutes(addDays(d, 1), 17 * 60)), end: toLocalIso(atMinutes(addDays(d, 1), 18 * 60)) }),
    ];
    save();
  }

  function mkEvent(o) {
    var now = new Date().toISOString();
    return {
      id: o.id || uid(),
      title: (o.title || "").trim() || "(Không tiêu đề)",
      start: o.start, end: o.end,
      allDay: !!o.allDay,
      color: COLOR_KEYS.indexOf(o.color) >= 0 ? o.color : "teal",
      location: (o.location || "").trim(),
      notes: (o.notes || "").trim(),
      createdAt: o.createdAt || now,
      updatedAt: now,
    };
  }

  function getEvent(id) { return state.events.find(function (e) { return e.id === id; }); }
  function upsert(ev) {
    var i = state.events.findIndex(function (e) { return e.id === ev.id; });
    if (i >= 0) state.events[i] = ev; else state.events.push(ev);
    save();
  }
  function removeEvent(id) {
    state.events = state.events.filter(function (e) { return e.id !== id; });
    save();
  }

  /* ====================== event geometry helpers ==================== */
  function evStart(ev) { return fromLocalIso(ev.start); }
  function evEnd(ev) {
    var e = fromLocalIso(ev.end) || fromLocalIso(ev.start);
    var s = evStart(ev);
    if (!ev.allDay && e <= s) e = new Date(s.getTime() + 30 * 60000);
    return e;
  }
  function isBar(ev) { return ev.allDay || daysBetween(evStart(ev), evEnd(ev)) > 0; }

  function coversDay(ev, day) {
    var s = startOfDay(evStart(ev));
    var e = startOfDay(evEnd(ev));
    var d = startOfDay(day);
    return d >= s && d <= e;
  }
  function eventsForDay(day) {
    return state.events.filter(function (ev) { return coversDay(ev, day); });
  }
  function sortByStart(a, b) {
    if (a.allDay !== b.allDay) return a.allDay ? -1 : 1;
    return evStart(a) - evStart(b) || (a.title || "").localeCompare(b.title || "");
  }

  /* ============================ overlap layout ====================== */
  function layoutOverlap(items) {
    items.sort(function (a, b) { return a.s - b.s || a.e - b.e; });
    var res = [], cluster = [], clusterEnd = -1;
    function flush() {
      var cols = [];
      cluster.forEach(function (it) {
        var placed = false;
        for (var c = 0; c < cols.length; c++) {
          if (it.s >= cols[c]) { cols[c] = it.e; it.col = c; placed = true; break; }
        }
        if (!placed) { it.col = cols.length; cols.push(it.e); }
      });
      cluster.forEach(function (it) { it.cols = cols.length; res.push(it); });
      cluster = [];
    }
    items.forEach(function (it) {
      if (cluster.length === 0) { cluster.push(it); clusterEnd = it.e; return; }
      if (it.s >= clusterEnd) { flush(); cluster.push(it); clusterEnd = it.e; }
      else { cluster.push(it); clusterEnd = Math.max(clusterEnd, it.e); }
    });
    if (cluster.length) flush();
    return res;
  }

  function layoutBars(bars) {
    bars.sort(function (a, b) { return a.c0 - b.c0 || (b.c1 - b.c0) - (a.c1 - a.c0); });
    var lanes = [];
    bars.forEach(function (b) {
      var placed = false;
      for (var l = 0; l < lanes.length; l++) {
        var free = lanes[l].every(function (seg) { return b.c1 < seg[0] || b.c0 > seg[1]; });
        if (free) { lanes[l].push([b.c0, b.c1]); b.lane = l; placed = true; break; }
      }
      if (!placed) { b.lane = lanes.length; lanes.push([[b.c0, b.c1]]); }
    });
    return lanes.length;
  }

  /* ============================== chrome ============================ */
  function setPeriodLabel() {
    var el = $("[data-cal-period]");
    if (!el) return;
    if (state.view === "month") {
      el.textContent = "Tháng " + (state.anchor.getMonth() + 1) + " " + state.anchor.getFullYear();
    } else if (state.view === "week") {
      var s = startOfWeek(state.anchor), e = addDays(s, 6);
      el.textContent = pad(s.getDate()) + "/" + pad(s.getMonth() + 1) + " – " + dmy(e);
    } else {
      el.textContent = wdLong(state.anchor) + ", " + dmy(state.anchor);
    }
  }
  function setViewTabs() {
    $$("[data-cal-view-btn]").forEach(function (b) {
      var on = b.getAttribute("data-cal-view-btn") === state.view;
      b.classList.toggle("cal__view-tab--active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  /* ============================ mini calendar ======================= */
  function renderMini() {
    var host = $("[data-cal-mini]");
    if (!host) return;
    var m = state.miniMonth;
    var first = startOfMonth(m);
    var gridStart = startOfWeek(first);
    var head = '<div class="cal-mini__head">' +
      '<button type="button" class="cal-mini__nav" data-cal-mini-prev aria-label="Tháng trước">' +
      '<svg class="cal__ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg></button>' +
      '<span class="cal-mini__title">Tháng ' + (m.getMonth() + 1) + " " + m.getFullYear() + "</span>" +
      '<button type="button" class="cal-mini__nav" data-cal-mini-next aria-label="Tháng sau">' +
      '<svg class="cal__ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg></button></div>';

    var dow = '<div class="cal-mini__dow">' + WD_SHORT.map(function (w) {
      return "<span>" + w + "</span>";
    }).join("") + "</div>";

    var cells = "";
    for (var i = 0; i < 42; i++) {
      var d = addDays(gridStart, i);
      var cls = "cal-mini__day";
      if (d.getMonth() !== m.getMonth()) cls += " cal-mini__day--mute";
      if (sameDay(d, today0)) cls += " cal-mini__day--today";
      if (sameDay(d, state.selected)) cls += " cal-mini__day--sel";
      var has = eventsForDay(d).length > 0;
      cells += '<button type="button" class="' + cls + '" data-cal-mini-day="' + ymd(d) + '">' +
        d.getDate() + (has ? '<i class="cal-mini__dot" aria-hidden="true"></i>' : "") + "</button>";
    }
    host.innerHTML = head + dow + '<div class="cal-mini__grid">' + cells + "</div>";
  }

  /* ============================== agenda =========================== */
  function renderAgenda() {
    var host = $("[data-cal-agenda]");
    var title = $("[data-cal-agenda-title]");
    var count = $("[data-cal-agenda-count]");
    if (!host) return;
    if (title) {
      title.textContent = sameDay(state.selected, today0)
        ? "Hôm nay · " + dmy(state.selected)
        : wdLong(state.selected) + " · " + dmy(state.selected);
    }
    var list = eventsForDay(state.selected).slice().sort(sortByStart);
    if (count) count.textContent = list.length ? list.length + " sự kiện" : "";
    if (!list.length) {
      host.innerHTML = '<div class="cal__empty"><svg class="cal__empty-ico" viewBox="0 0 24 24" aria-hidden="true">' +
        '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/></svg>' +
        "<p>Không có sự kiện</p><span>Bấm “Sự kiện mới” để thêm.</span></div>";
      return;
    }
    host.innerHTML = list.map(function (ev) {
      var time = ev.allDay ? "Cả ngày" : hm(evStart(ev)) + "–" + hm(evEnd(ev));
      return '<button type="button" class="cal-ag" data-color="' + ev.color + '" data-cal-open="' + ev.id + '">' +
        '<span class="cal-ag__bar" aria-hidden="true"></span>' +
        '<span class="cal-ag__body"><span class="cal-ag__title">' + esc(ev.title) + "</span>" +
        '<span class="cal-ag__meta">' + time + (ev.location ? " · " + esc(ev.location) : "") + "</span></span></button>";
    }).join("");
  }

  /* ============================== month view ======================= */
  function renderMonth() {
    var view = $("[data-cal-view]");
    var first = startOfMonth(state.anchor);
    var gridStart = startOfWeek(first);

    var head = '<div class="cal-month__dow">' + WD_LONG.map(function (w, i) {
      return '<span>' + w + '<i>' + WD_SHORT[i] + "</i></span>";
    }).join("") + "</div>";

    var weeks = "";
    for (var w = 0; w < 6; w++) {
      var weekStart = addDays(gridStart, w * 7);
      weeks += renderMonthWeek(weekStart, first.getMonth());
    }
    view.className = "cal__view cal__view--month";
    view.innerHTML = head + '<div class="cal-month__grid">' + weeks + "</div>";
    bindMonthInteractions(view);
  }

  function renderMonthWeek(weekStart, focusMonth) {
    var weekEnd = addDays(weekStart, 6);
    // spanning bars (all-day / multi-day) intersecting this week
    var bars = [];
    state.events.forEach(function (ev) {
      if (!isBar(ev)) return;
      var s = startOfDay(evStart(ev)), e = startOfDay(evEnd(ev));
      if (e < weekStart || s > weekEnd) return;
      bars.push({
        ev: ev,
        c0: Math.max(0, daysBetween(weekStart, s)),
        c1: Math.min(6, daysBetween(weekStart, e)),
        contStart: s < weekStart,
        contEnd: e > weekEnd,
      });
    });
    var laneCount = layoutBars(bars);
    var barsH = laneCount * BAR_H;

    var barsHtml = bars.map(function (b) {
      var left = (b.c0 / 7 * 100), width = ((b.c1 - b.c0 + 1) / 7 * 100);
      var rounded = (b.contStart ? " cal-month__bar--cont-l" : "") + (b.contEnd ? " cal-month__bar--cont-r" : "");
      var label = b.ev.allDay ? esc(b.ev.title) : hm(evStart(b.ev)) + " " + esc(b.ev.title);
      return '<div class="cal-month__bar' + rounded + '" data-color="' + b.ev.color + '" data-cal-drag="' + b.ev.id + '" ' +
        'role="button" tabindex="0" style="left:' + left + "%;width:" + width + "%;top:" + (b.lane * BAR_H) + 'px">' +
        '<span>' + label + "</span></div>";
    }).join("");

    var cells = "";
    for (var i = 0; i < 7; i++) {
      var d = addDays(weekStart, i);
      var inMonth = d.getMonth() === focusMonth;
      var cls = "cal-month__cell" + (inMonth ? "" : " cal-month__cell--mute") + (sameDay(d, today0) ? " cal-month__cell--today" : "");
      // timed single-day events for this cell
      var timed = state.events.filter(function (ev) {
        return !isBar(ev) && sameDay(evStart(ev), d);
      }).sort(sortByStart);
      var shown = timed.slice(0, MONTH_CHIP_CAP);
      var chips = shown.map(function (ev) {
        return '<div class="cal-month__chip" data-color="' + ev.color + '" data-cal-drag="' + ev.id + '" role="button" tabindex="0">' +
          '<i class="cal-month__chip-dot" aria-hidden="true"></i>' +
          '<span class="cal-month__chip-time">' + hm(evStart(ev)) + "</span>" +
          '<span class="cal-month__chip-title">' + esc(ev.title) + "</span></div>";
      }).join("");
      var more = timed.length > MONTH_CHIP_CAP
        ? '<button type="button" class="cal-month__more" data-cal-more="' + ymd(d) + '">+' + (timed.length - MONTH_CHIP_CAP) + " mục</button>"
        : "";
      cells += '<div class="' + cls + '" data-date="' + ymd(d) + '">' +
        '<div class="cal-month__date"><span>' + d.getDate() + (d.getDate() === 1 ? "/" + (d.getMonth() + 1) : "") + "</span></div>" +
        '<div class="cal-month__cell-body" style="padding-top:' + (barsH + 2) + 'px">' + chips + more + "</div></div>";
    }

    return '<div class="cal-month__week"><div class="cal-month__bars" style="height:' + barsH + 'px">' +
      barsHtml + '</div><div class="cal-month__row">' + cells + "</div></div>";
  }

  /* ============================ time grid view ===================== */
  function renderTime(days) {
    var view = $("[data-cal-view]");
    var nDays = days.length;

    var headCells = days.map(function (d) {
      var on = sameDay(d, today0);
      return '<button type="button" class="cal-time__dayhead' + (on ? " cal-time__dayhead--today" : "") +
        '" data-cal-mini-day="' + ymd(d) + '"><span class="cal-time__dayhead-wd">' + WD_SHORT[(d.getDay() + 6) % 7] +
        '</span><span class="cal-time__dayhead-num">' + d.getDate() + "</span></button>";
    }).join("");

    var alldayCells = days.map(function (d) {
      var evs = state.events.filter(function (ev) { return isBar(ev) && coversDay(ev, d); }).sort(sortByStart);
      var chips = evs.map(function (ev) {
        return '<div class="cal-time__allday-chip" data-color="' + ev.color + '" data-cal-open="' + ev.id + '" role="button" tabindex="0">' +
          esc(ev.title) + "</div>";
      }).join("");
      return '<div class="cal-time__allday-cell" data-date="' + ymd(d) + '">' + chips + "</div>";
    }).join("");

    var hours = "";
    for (var h = 0; h < 24; h++) {
      hours += '<div class="cal-time__hour" style="height:' + HOUR_H + 'px"><span>' + pad(h) + ":00</span></div>";
    }

    var cols = days.map(function (d) {
      var slots = "";
      for (var h = 0; h < 24; h++) {
        slots += '<div class="cal-time__slot" data-date="' + ymd(d) + '" data-min="' + (h * 60) + '" style="height:' + HOUR_H + 'px"></div>';
      }
      var blocks = renderDayBlocks(d);
      var nowLine = sameDay(d, new Date())
        ? '<div class="cal-time__now" style="top:' + (minutesOf(new Date()) / 60 * HOUR_H) + 'px"><i></i></div>'
        : "";
      return '<div class="cal-time__col" data-date="' + ymd(d) + '">' + slots + blocks + nowLine + "</div>";
    }).join("");

    view.className = "cal__view cal__view--time" + (nDays === 1 ? " cal__view--day" : " cal__view--week");
    view.innerHTML =
      '<div class="cal-time" style="--cal-cols:' + nDays + '">' +
        '<div class="cal-time__head"><div class="cal-time__corner"></div>' +
          '<div class="cal-time__headcols">' + headCells + "</div></div>" +
        '<div class="cal-time__allday"><div class="cal-time__allday-label">Cả ngày</div>' +
          '<div class="cal-time__allday-cols">' + alldayCells + "</div></div>" +
        '<div class="cal-time__scroll" data-cal-scroll>' +
          '<div class="cal-time__grid">' +
            '<div class="cal-time__gutter">' + hours + "</div>" +
            '<div class="cal-time__cols">' + cols + "</div>" +
          "</div></div></div>";

    bindTimeInteractions(view);
    // scroll to ~07:00 on first paint
    var sc = $("[data-cal-scroll]", view);
    if (sc) sc.scrollTop = 7 * HOUR_H;
  }

  function renderDayBlocks(day) {
    var items = state.events.filter(function (ev) {
      return !isBar(ev) && sameDay(evStart(ev), day);
    }).map(function (ev) {
      return { ev: ev, s: minutesOf(evStart(ev)), e: Math.max(minutesOf(evStart(ev)) + 15, clampEnd(ev, day)) };
    });
    layoutOverlap(items);
    return items.map(function (it) {
      var ev = it.ev;
      var top = it.s / 60 * HOUR_H;
      var height = Math.max(22, (it.e - it.s) / 60 * HOUR_H);
      var w = 100 / it.cols, left = it.col * w;
      return '<div class="cal-time__event" data-color="' + ev.color + '" data-cal-drag="' + ev.id + '" role="button" tabindex="0" ' +
        'style="top:' + top + "px;height:" + height + "px;left:calc(" + left + "% + 2px);width:calc(" + w + '% - 4px)">' +
        '<span class="cal-time__event-time">' + hm(evStart(ev)) + "–" + hm(evEnd(ev)) + "</span>" +
        '<span class="cal-time__event-title">' + esc(ev.title) + "</span>" +
        (ev.location ? '<span class="cal-time__event-loc">' + esc(ev.location) + "</span>" : "") +
        '<span class="cal-time__resize" data-cal-resize="' + ev.id + '" aria-hidden="true"></span></div>';
    }).join("");
  }
  function clampEnd(ev, day) {
    var e = evEnd(ev);
    return sameDay(e, day) ? minutesOf(e) : 1440;
  }

  /* ============================== render ============================ */
  function render() {
    setPeriodLabel();
    setViewTabs();
    renderMini();
    renderAgenda();
    if (state.view === "month") renderMonth();
    else if (state.view === "week") renderTime(weekDays(state.anchor));
    else renderTime([startOfDay(state.anchor)]);
    var root = $("[data-cal-root]");
    if (root) root.classList.toggle("cal--side-collapsed", !state.sideOpen);
  }
  function weekDays(anchor) {
    var s = startOfWeek(anchor), out = [];
    for (var i = 0; i < 7; i++) out.push(addDays(s, i));
    return out;
  }

  /* ====================== month interactions ======================= */
  function bindMonthInteractions(view) {
    $$(".cal-month__cell", view).forEach(function (cell) {
      cell.addEventListener("click", function (e) {
        if (e.target.closest("[data-cal-drag],[data-cal-more]")) return;
        openEditorNew(parseYmd(cell.getAttribute("data-date")), false);
      });
    });
    $$("[data-cal-more]", view).forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        gotoDay(parseYmd(btn.getAttribute("data-cal-more")));
      });
    });
    $$("[data-cal-drag]", view).forEach(function (el) {
      attachDraggable(el, "month");
    });
  }

  /* ======================= time interactions ======================= */
  function bindTimeInteractions(view) {
    $$(".cal-time__slot", view).forEach(function (slot) {
      slot.addEventListener("click", function () {
        var d = parseYmd(slot.getAttribute("data-date"));
        openEditorNew(atMinutes(d, +slot.getAttribute("data-min")), false);
      });
    });
    $$(".cal-time__allday-cell", view).forEach(function (cell) {
      cell.addEventListener("click", function (e) {
        if (e.target.closest("[data-cal-open]")) return;
        openEditorNew(parseYmd(cell.getAttribute("data-date")), true);
      });
    });
    $$("[data-cal-open]", view).forEach(function (el) {
      el.addEventListener("click", function () { var ev = getEvent(el.getAttribute("data-cal-open")); if (ev) openEditor(ev); });
      keyActivate(el);
    });
    $$(".cal-time__dayhead", view).forEach(function (el) {
      el.addEventListener("click", function () { gotoDay(parseYmd(el.getAttribute("data-cal-mini-day"))); });
    });
    $$(".cal-time__event", view).forEach(function (el) { attachDraggable(el, "time"); });
    $$("[data-cal-resize]", view).forEach(function (h) { attachResize(h); });
  }

  /* ============================ drag & drop ======================== */
  function attachDraggable(el, mode) {
    el.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        var ev = getEvent(el.getAttribute("data-cal-drag"));
        if (ev) openEditor(ev);
      }
    });
    el.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      if (e.target.closest("[data-cal-resize]")) return;
      var id = el.getAttribute("data-cal-drag");
      var ev = getEvent(id);
      if (!ev) return;
      startDrag(e, el, ev, mode === "month" ? "move-month" : "move-time");
    });
  }
  function attachResize(handle) {
    handle.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      e.stopPropagation();
      var ev = getEvent(handle.getAttribute("data-cal-resize"));
      if (!ev) return;
      startDrag(e, handle.parentNode, ev, "resize-time");
    });
  }

  function startDrag(e, el, ev, kind) {
    drag = {
      kind: kind, el: el, ev: ev,
      startX: e.clientX, startY: e.clientY, moved: false,
      origStartMin: minutesOf(evStart(ev)),
      origDurMin: Math.max(SNAP, Math.round((evEnd(ev) - evStart(ev)) / 60000)),
      origDay: startOfDay(evStart(ev)),
      pointerId: e.pointerId,
    };
    try { el.setPointerCapture(e.pointerId); } catch (_) { /* noop */ }
    window.addEventListener("pointermove", onDragMove);
    window.addEventListener("pointerup", onDragUp);
  }

  function onDragMove(e) {
    if (!drag) return;
    var dx = e.clientX - drag.startX, dy = e.clientY - drag.startY;
    if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 5) return;
    if (!drag.moved) {
      drag.moved = true;
      drag.el.classList.add("is-dragging");
      document.body.classList.add("cal-dragging");
    }
    if (drag.kind === "move-time" || drag.kind === "resize-time") {
      drag.el.style.pointerEvents = "none";
      var target = document.elementFromPoint(e.clientX, e.clientY);
      var col = target && target.closest(".cal-time__col");
      var deltaMin = Math.round((dy / HOUR_H * 60) / SNAP) * SNAP;
      if (drag.kind === "move-time") {
        var newStart = clampMin(drag.origStartMin + deltaMin, drag.origDurMin);
        drag.el.style.top = (newStart / 60 * HOUR_H) + "px";
        drag.previewStart = newStart;
        drag.previewDay = col ? parseYmd(col.getAttribute("data-date")) : drag.origDay;
        if (col) {
          $$(".cal-time__col").forEach(function (c) { c.classList.toggle("is-drop", c === col); });
        }
      } else {
        var newDur = Math.max(SNAP, drag.origDurMin + deltaMin);
        newDur = Math.min(newDur, 1440 - drag.origStartMin);
        drag.el.style.height = Math.max(22, newDur / 60 * HOUR_H) + "px";
        drag.previewDur = newDur;
      }
    } else if (drag.kind === "move-month") {
      ensureGhost(e);
      var t = document.elementFromPoint(e.clientX, e.clientY);
      var cell = t && t.closest(".cal-month__cell");
      $$(".cal-month__cell").forEach(function (c) { c.classList.toggle("is-drop", c === cell); });
      drag.previewCellDate = cell ? cell.getAttribute("data-date") : null;
    }
  }

  function onDragUp() {
    window.removeEventListener("pointermove", onDragMove);
    window.removeEventListener("pointerup", onDragUp);
    document.body.classList.remove("cal-dragging");
    removeGhost();
    $$(".is-drop").forEach(function (c) { c.classList.remove("is-drop"); });
    var d = drag;
    drag = null;
    if (!d) return;
    if (!d.moved) { openEditor(d.ev); return; }   // treated as a click
    var ev = getEvent(d.ev.id);
    if (!ev) { render(); return; }

    if (d.kind === "move-time") {
      var day = d.previewDay || d.origDay;
      var startMin = typeof d.previewStart === "number" ? d.previewStart : d.origStartMin;
      var ns = atMinutes(day, startMin);
      ev.start = toLocalIso(ns);
      ev.end = toLocalIso(new Date(ns.getTime() + d.origDurMin * 60000));
      ev.allDay = false;
      ev.updatedAt = new Date().toISOString();
      upsert(ev);
    } else if (d.kind === "resize-time") {
      var dur = d.previewDur || d.origDurMin;
      var s = evStart(ev);
      ev.end = toLocalIso(new Date(s.getTime() + dur * 60000));
      ev.updatedAt = new Date().toISOString();
      upsert(ev);
    } else if (d.kind === "move-month" && d.previewCellDate) {
      var targetDay = parseYmd(d.previewCellDate);
      var delta = daysBetween(d.origDay, targetDay);
      if (delta !== 0) {
        ev.start = toLocalIso(addDays(evStart(ev), delta));
        ev.end = toLocalIso(addDays(evEnd(ev), delta));
        ev.updatedAt = new Date().toISOString();
        upsert(ev);
      }
    }
    render();
  }
  function clampMin(start, dur) { return Math.max(0, Math.min(start, 1440 - dur)); }

  function ensureGhost(e) {
    if (!drag.ghost) {
      var g = document.createElement("div");
      g.className = "cal-ghost";
      g.setAttribute("data-color", drag.ev.color);
      g.textContent = drag.ev.title;
      document.body.appendChild(g);
      drag.ghost = g;
    }
    drag.ghost.style.left = (e.clientX + 12) + "px";
    drag.ghost.style.top = (e.clientY + 12) + "px";
  }
  function removeGhost() { if (drag && drag.ghost) { drag.ghost.remove(); drag.ghost = null; } }

  /* ============================== editor =========================== */
  var modal = null, formRefs = null, editingId = null;

  function cacheModal() {
    modal = $("[data-cal-modal]");
    formRefs = {
      form: $("[data-cal-form]"),
      title: $("[data-cal-dialog-title]"),
      id: $("[data-cal-f-id]"),
      titleIn: $("[data-cal-f-title]"),
      allday: $("[data-cal-f-allday]"),
      sdate: $("[data-cal-f-sdate]"),
      stime: $("[data-cal-f-stime]"),
      stimeWrap: $("[data-cal-f-stime-wrap]"),
      edate: $("[data-cal-f-edate]"),
      etime: $("[data-cal-f-etime]"),
      etimeWrap: $("[data-cal-f-etime-wrap]"),
      colors: $("[data-cal-f-colors]"),
      loc: $("[data-cal-f-loc]"),
      notes: $("[data-cal-f-notes]"),
      del: $("[data-cal-delete]"),
    };
    formRefs.colors.innerHTML = COLORS.map(function (c, i) {
      return '<button type="button" class="cal-swatch" data-color="' + c.key + '" data-cal-color="' + c.key +
        '" role="radio" aria-checked="' + (i === 0 ? "true" : "false") + '" aria-label="' + c.label + '" title="' + c.label + '"></button>';
    }).join("");
    $$("[data-cal-color]", formRefs.colors).forEach(function (b) {
      b.addEventListener("click", function () { selectColor(b.getAttribute("data-cal-color")); });
    });
    formRefs.allday.addEventListener("change", syncAllDay);
    formRefs.form.addEventListener("submit", onSubmit);
    formRefs.del.addEventListener("click", onDelete);
    $$("[data-cal-modal-close]").forEach(function (b) { b.addEventListener("click", closeEditor); });
  }

  function selectColor(key) {
    formRefs._color = key;
    $$("[data-cal-color]", formRefs.colors).forEach(function (b) {
      var on = b.getAttribute("data-cal-color") === key;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-checked", on ? "true" : "false");
    });
  }
  function syncAllDay() {
    var on = formRefs.allday.checked;
    formRefs.stimeWrap.style.display = on ? "none" : "";
    formRefs.etimeWrap.style.display = on ? "none" : "";
  }

  function openEditorNew(when, allDay) {
    var start = when || atMinutes(state.selected, nextHourMin());
    var end;
    if (allDay) { start = startOfDay(start); end = start; }
    else { end = new Date(start.getTime() + 60 * 60000); }
    openEditor(mkEvent({
      title: "", color: "teal", allDay: !!allDay,
      start: toLocalIso(start), end: toLocalIso(end),
    }), true);
  }
  function nextHourMin() {
    var now = new Date();
    if (!sameDay(state.selected, today0)) return 9 * 60;
    return Math.min(23 * 60, (now.getHours() + 1) * 60);
  }

  function openEditor(ev, isNew) {
    editingId = isNew ? null : ev.id;
    formRefs.title.textContent = isNew ? "Sự kiện mới" : "Sửa sự kiện";
    formRefs.id.value = ev.id;
    formRefs.titleIn.value = isNew ? "" : ev.title;
    formRefs.allday.checked = !!ev.allDay;
    var s = evStart(ev), e = evEnd(ev);
    formRefs.sdate.value = ymd(s);
    formRefs.stime.value = hm(s);
    formRefs.edate.value = ymd(ev.allDay ? e : s);
    formRefs.etime.value = hm(e);
    formRefs.loc.value = ev.location || "";
    formRefs.notes.value = ev.notes || "";
    selectColor(ev.color || "teal");
    syncAllDay();
    formRefs.del.hidden = !!isNew;
    modal.hidden = false;
    document.body.classList.add("cal-modal-open");
    setTimeout(function () { formRefs.titleIn.focus(); }, 20);
  }

  function closeEditor() {
    if (!modal) return;
    modal.hidden = true;
    editingId = null;
    document.body.classList.remove("cal-modal-open");
  }

  function onSubmit(e) {
    e.preventDefault();
    var allDay = formRefs.allday.checked;
    var sdate = formRefs.sdate.value, edate = formRefs.edate.value;
    if (!sdate) { toast("Chọn ngày bắt đầu", "error"); return; }
    var start, end;
    if (allDay) {
      start = parseYmd(sdate);
      end = edate ? parseYmd(edate) : start;
      if (end < start) end = start;
    } else {
      start = combine(sdate, formRefs.stime.value || "09:00");
      var ed = edate || sdate;
      end = combine(ed, formRefs.etime.value || formRefs.stime.value || "10:00");
      if (end <= start) end = new Date(start.getTime() + 30 * 60000);
    }
    var existing = editingId ? getEvent(editingId) : null;
    var ev = mkEvent({
      id: existing ? existing.id : (formRefs.id.value || uid()),
      title: formRefs.titleIn.value,
      color: formRefs._color || "teal",
      allDay: allDay,
      start: toLocalIso(start),
      end: toLocalIso(end),
      location: formRefs.loc.value,
      notes: formRefs.notes.value,
      createdAt: existing ? existing.createdAt : undefined,
    });
    upsert(ev);
    closeEditor();
    state.selected = startOfDay(start);
    state.anchor = state.selected;
    render();
    toast(editingId ? "Đã cập nhật" : "Đã thêm sự kiện");
  }
  function combine(dateStr, timeStr) {
    var d = parseYmd(dateStr);
    var t = (timeStr || "00:00").split(":");
    return atMinutes(d, (+t[0]) * 60 + (+t[1] || 0));
  }
  function onDelete() {
    if (!editingId) { closeEditor(); return; }
    removeEvent(editingId);
    closeEditor();
    render();
    toast("Đã xoá sự kiện");
  }

  /* ============================ navigation ========================= */
  function gotoToday() { state.anchor = today0; state.selected = today0; state.miniMonth = startOfMonth(today0); render(); }
  function gotoDay(d) {
    state.selected = startOfDay(d);
    state.anchor = state.selected;
    state.miniMonth = startOfMonth(state.selected);
    render();
  }
  function step(dir) {
    if (state.view === "month") state.anchor = addMonths(state.anchor, dir);
    else if (state.view === "week") state.anchor = addDays(state.anchor, dir * 7);
    else { state.anchor = addDays(state.anchor, dir); state.selected = state.anchor; }
    render();
  }
  function setView(v) {
    state.view = v;
    if (v === "day") state.selected = state.anchor;
    render();
  }

  /* ============================== misc ============================= */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function keyActivate(el) {
    el.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); el.click(); }
    });
  }
  function toast(msg, type) {
    var el = $("[data-cal-toast]");
    if (!el) return;
    el.textContent = msg;
    el.className = "cal__toast cal__toast--" + (type || "ok") + " cal__toast--show";
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.classList.remove("cal__toast--show"); }, 2600);
  }
  function updateNowLine() {
    if (state.view === "month") return;
    $$(".cal-time__now").forEach(function (line) {
      line.style.top = (minutesOf(new Date()) / 60 * HOUR_H) + "px";
    });
  }

  /* ============================== keyboard ========================= */
  function onKeydown(e) {
    var open = modal && !modal.hidden;
    if (open) { if (e.key === "Escape") { e.preventDefault(); closeEditor(); } return; }
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    switch (e.key) {
      case "n": case "N": e.preventDefault(); openEditorNew(null, false); break;
      case "t": case "T": e.preventDefault(); gotoToday(); break;
      case "d": case "D": e.preventDefault(); setView("day"); break;
      case "w": case "W": e.preventDefault(); setView("week"); break;
      case "m": case "M": e.preventDefault(); setView("month"); break;
      case "ArrowLeft": e.preventDefault(); step(-1); break;
      case "ArrowRight": e.preventDefault(); step(1); break;
    }
  }

  /* ============================== wiring =========================== */
  function bindChrome() {
    $("[data-cal-new]").addEventListener("click", function () { openEditorNew(null, false); });
    $("[data-cal-today]").addEventListener("click", gotoToday);
    $("[data-cal-prev]").addEventListener("click", function () { step(-1); });
    $("[data-cal-next]").addEventListener("click", function () { step(1); });
    $$("[data-cal-view-btn]").forEach(function (b) {
      b.addEventListener("click", function () { setView(b.getAttribute("data-cal-view-btn")); });
    });
    var sideToggle = $("[data-cal-side-toggle]");
    if (sideToggle) sideToggle.addEventListener("click", function () {
      state.sideOpen = !state.sideOpen;
      sideToggle.setAttribute("aria-pressed", state.sideOpen ? "true" : "false");
      render();
    });
    // delegated mini-cal + agenda interactions (re-rendered html)
    document.addEventListener("click", function (e) {
      var miniDay = e.target.closest("[data-cal-mini-day]");
      if (miniDay && miniDay.closest("[data-cal-mini]")) { gotoDay(parseYmd(miniDay.getAttribute("data-cal-mini-day"))); return; }
      if (e.target.closest("[data-cal-mini-prev]")) { state.miniMonth = addMonths(state.miniMonth, -1); renderMini(); return; }
      if (e.target.closest("[data-cal-mini-next]")) { state.miniMonth = addMonths(state.miniMonth, 1); renderMini(); return; }
      var ag = e.target.closest("[data-cal-open]");
      if (ag && ag.closest("[data-cal-agenda]")) { var ev = getEvent(ag.getAttribute("data-cal-open")); if (ev) openEditor(ev); }
    });
    document.addEventListener("keydown", onKeydown);
  }

  function init() {
    state.events = load();
    seedIfFirstRun();
    cacheModal();
    bindChrome();
    render();
    nowTimer = setInterval(updateNowLine, 60000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
