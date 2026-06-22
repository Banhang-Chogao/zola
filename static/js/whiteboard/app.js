/**
 * whiteboard/app.js — "3M Whiteboard": yellow post-it sticky notes pinned beside
 * the Calendar. Personal & private — every note is read/written through the
 * VIPZone API behind the shared GitHub-OAuth guard (window.PrivateAuth), stored
 * server-side keyed by the owner email. Nothing lives in localStorage, so clearing
 * cookies only ends the session: re-login brings the board back.
 *
 * Boots only after `private-auth:authed`; until then the page renders no note data.
 */
(function () {
  "use strict";

  var COLORS = [
    { key: "yellow", label: "Vàng" },
    { key: "green", label: "Xanh lá" },
    { key: "blue", label: "Xanh dương" },
    { key: "pink", label: "Hồng" },
    { key: "purple", label: "Tím" },
    { key: "orange", label: "Cam" },
    { key: "white", label: "Trắng" },
  ];
  var COLOR_KEYS = COLORS.map(function (c) { return c.key; });

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var root, board, emptyEl;
  var notes = [];
  var booted = false;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function toast(msg, type) {
    var el = $("[data-wb-toast]");
    if (!el) return;
    el.textContent = msg;
    el.className = "wb__toast wb__toast--" + (type || "ok") + " wb__toast--show";
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.classList.remove("wb__toast--show"); }, 2400);
  }

  function fmtTime(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return "";
    function p(n) { return n < 10 ? "0" + n : "" + n; }
    return p(d.getDate()) + "/" + p(d.getMonth() + 1) + " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }

  /* ============================== API ============================== */
  async function loadNotes() {
    var data = await window.PrivateAuth.api("/whiteboard/notes");
    notes = Array.isArray(data.notes) ? data.notes : [];
  }
  async function apiCreate(payload) {
    return (await window.PrivateAuth.api("/whiteboard/notes", { method: "POST", body: payload })).note;
  }
  async function apiUpdate(id, patch) {
    return (await window.PrivateAuth.api("/whiteboard/notes/" + encodeURIComponent(id), { method: "PATCH", body: patch })).note;
  }
  async function apiDelete(id) {
    await window.PrivateAuth.api("/whiteboard/notes/" + encodeURIComponent(id), { method: "DELETE" });
  }

  function getNote(id) { return notes.find(function (n) { return n.id === id; }); }

  /* ============================ rendering ========================== */
  function render() {
    if (!board) return;
    notes.sort(function (a, b) { return (a.order - b.order) || (a.createdAt || "").localeCompare(b.createdAt || ""); });
    if (emptyEl) emptyEl.hidden = notes.length > 0;
    board.innerHTML = notes.map(noteHtml).join("");
    bindNotes();
  }

  function noteHtml(n) {
    var swatches = COLORS.map(function (c) {
      var on = c.key === n.color;
      return '<button type="button" class="wb-note__swatch' + (on ? " is-active" : "") +
        '" data-color="' + c.key + '" data-wb-color="' + c.key + '" title="' + c.label +
        '" aria-label="' + c.label + '"' + (on ? ' aria-pressed="true"' : "") + "></button>";
    }).join("");
    return '<article class="wb-note" data-color="' + esc(n.color) + '" data-wb-note="' + esc(n.id) + '">' +
      '<header class="wb-note__top">' +
        '<div class="wb-note__swatches" role="group" aria-label="Màu ghi chú">' + swatches + "</div>" +
        '<button type="button" class="wb-note__del" data-wb-del aria-label="Xoá ghi chú">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><path d="M18 6L6 18M6 6l12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>' +
        "</button>" +
      "</header>" +
      '<textarea class="wb-note__text" data-wb-text rows="5" placeholder="Viết ghi chú…" maxlength="5000">' + esc(n.text) + "</textarea>" +
      '<footer class="wb-note__foot">' +
        '<div class="wb-note__order">' +
          '<button type="button" class="wb-note__move" data-wb-up aria-label="Lên trên">↑</button>' +
          '<button type="button" class="wb-note__move" data-wb-down aria-label="Xuống dưới">↓</button>' +
        "</div>" +
        '<span class="wb-note__time">' + esc(fmtTime(n.updatedAt || n.createdAt)) + "</span>" +
      "</footer>" +
    "</article>";
  }

  function bindNotes() {
    $$(".wb-note", board).forEach(function (el) {
      var id = el.getAttribute("data-wb-note");

      // colour change
      $$("[data-wb-color]", el).forEach(function (b) {
        b.addEventListener("click", function () {
          var color = b.getAttribute("data-wb-color");
          if (COLOR_KEYS.indexOf(color) < 0) return;
          var n = getNote(id);
          if (!n || n.color === color) return;
          n.color = color;            // optimistic
          el.setAttribute("data-color", color);
          $$("[data-wb-color]", el).forEach(function (s) {
            var on = s.getAttribute("data-wb-color") === color;
            s.classList.toggle("is-active", on);
          });
          apiUpdate(id, { color: color }).then(function (saved) {
            if (saved) replaceNote(saved);
          }).catch(function () { toast("Đổi màu thất bại", "error"); reload(); });
        });
      });

      // text edit on blur (save only when changed)
      var ta = $("[data-wb-text]", el);
      if (ta) {
        ta.addEventListener("blur", function () {
          var n = getNote(id);
          if (!n) return;
          var val = ta.value;
          if (val === n.text) return;
          n.text = val;               // optimistic
          apiUpdate(id, { text: val }).then(function (saved) {
            if (saved) { replaceNote(saved); updateTime(el, saved); }
          }).catch(function () { toast("Lưu ghi chú thất bại", "error"); reload(); });
        });
      }

      // delete
      var del = $("[data-wb-del]", el);
      if (del) del.addEventListener("click", function () {
        if (!confirm("Xoá ghi chú này?")) return;
        apiDelete(id).then(function () {
          notes = notes.filter(function (n) { return n.id !== id; });
          render();
          toast("Đã xoá");
        }).catch(function () { toast("Xoá thất bại", "error"); });
      });

      // reorder
      var up = $("[data-wb-up]", el), down = $("[data-wb-down]", el);
      if (up) up.addEventListener("click", function () { move(id, -1); });
      if (down) down.addEventListener("click", function () { move(id, 1); });
    });
  }

  function updateTime(el, n) {
    var t = $(".wb-note__time", el);
    if (t) t.textContent = fmtTime(n.updatedAt || n.createdAt);
  }
  function replaceNote(saved) {
    var i = notes.findIndex(function (n) { return n.id === saved.id; });
    if (i >= 0) notes[i] = saved;
  }

  /* swap order with the neighbour and persist both */
  function move(id, dir) {
    notes.sort(function (a, b) { return (a.order - b.order) || (a.createdAt || "").localeCompare(b.createdAt || ""); });
    var i = notes.findIndex(function (n) { return n.id === id; });
    var j = i + dir;
    if (i < 0 || j < 0 || j >= notes.length) return;
    var a = notes[i], b = notes[j];
    var ao = a.order, bo = b.order;
    if (ao === bo) { ao = i; bo = j; } // normalise if equal
    a.order = bo; b.order = ao;
    render();
    Promise.all([
      apiUpdate(a.id, { order: a.order }),
      apiUpdate(b.id, { order: b.order }),
    ]).then(function (res) {
      res.forEach(function (n) { if (n) replaceNote(n); });
    }).catch(function () { toast("Sắp xếp thất bại", "error"); reload(); });
  }

  async function addNote() {
    try {
      var saved = await apiCreate({ text: "", color: "yellow" });
      notes.push(saved);
      render();
      // focus the new note's textarea
      var el = $('[data-wb-note="' + (window.CSS && CSS.escape ? CSS.escape(saved.id) : saved.id) + '"]', board);
      var ta = el && $("[data-wb-text]", el);
      if (ta) ta.focus();
    } catch (e) {
      toast("Không tạo được ghi chú", "error");
    }
  }

  async function reload() {
    try { await loadNotes(); } catch (e) {}
    render();
  }

  /* ============================== boot ============================= */
  function cacheDom() {
    root = $("[data-wb-root]");
    board = $("[data-wb-board]");
    emptyEl = $("[data-wb-empty]");
    var add = $("[data-wb-add]");
    if (add) add.addEventListener("click", addNote);
  }

  async function start() {
    if (booted) return;
    booted = true;
    cacheDom();
    if (!board) return;
    try {
      await loadNotes();
      render();
    } catch (e) {
      if (e && e.status === 401) return; // gate handles re-login
      toast("Không tải được bảng ghi chú", "error");
    }
  }

  document.addEventListener("private-auth:authed", start);
})();
