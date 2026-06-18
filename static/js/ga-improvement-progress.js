/**
 * GA Improvement Progress — poll /data/ga-improvement-progress.json (from static/data/)
 * and refresh the footer checklist when updated_at changes.
 * Informational only; does not touch GA4 collection.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-ga-improve]");
  if (!root) return;

  var POLL_MS = 5 * 60 * 1000;
  var CACHE_KEY = "zola-ga-improve-cache";

  var base = (function () {
    var m = document.querySelector('meta[name="zola-base-url"]');
    return m && m.content ? m.content.replace(/\/$/, "") : "";
  })();

  var listEl = root.querySelector("[data-ga-improve-list]");
  var updatedEl = root.querySelector("[data-ga-improve-updated]");
  var countsEl = root.querySelector("[data-ga-improve-counts]");
  var bakedUpdated = root.getAttribute("data-baked-updated") || "";

  var STATUS_LABEL = {
    pending: "Pending",
    running: "Running",
    done: "Done",
  };

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatTime(iso) {
    if (!iso) return "—";
    if (window.ZolaDateTime && window.ZolaDateTime.formatDisplayDateTime) {
      return window.ZolaDateTime.formatDisplayDateTime(iso);
    }
    try {
      return new Date(iso).toLocaleString("vi-VN");
    } catch (e) {
      return iso;
    }
  }

  function renderCounts(summary) {
    if (!countsEl || !summary) return;
    countsEl.textContent =
      (summary.done || 0) + " done · " +
      (summary.running || 0) + " running · " +
      (summary.pending || 0) + " pending";
  }

  function renderTasks(tasks) {
    if (!listEl || !Array.isArray(tasks)) return;
    listEl.innerHTML = tasks.map(function (t, idx) {
      var st = t.status || "pending";
      var isLast = idx === tasks.length - 1;
      return (
        '<li class="ga-improve__item ga-improve__item--' + escapeHtml(st) + '">' +
          '<span class="ga-improve__track" aria-hidden="true">' +
            '<span class="ga-improve__dot"></span>' +
            (isLast ? "" : '<span class="ga-improve__line"></span>') +
          "</span>" +
          '<div class="ga-improve__body">' +
            '<div class="ga-improve__row">' +
              '<span class="ga-improve__icon" aria-hidden="true">' + escapeHtml(t.icon || "•") + "</span>" +
              '<span class="ga-improve__label">' + escapeHtml(t.label || "") + "</span>" +
              '<span class="ga-improve__badge ga-improve__badge--' + escapeHtml(st) + '">' +
                escapeHtml(STATUS_LABEL[st] || st) +
              "</span>" +
            "</div>" +
            '<p class="ga-improve__detail">' + escapeHtml(t.detail || "") + "</p>" +
          "</div>" +
        "</li>"
      );
    }).join("");
  }

  function applyPayload(payload) {
    if (!payload) return;
    renderTasks(payload.tasks);
    renderCounts(payload.summary);
    if (updatedEl && payload.updated_at) {
      updatedEl.innerHTML =
        'Cập nhật: <time datetime="' + escapeHtml(payload.updated_at) + '">' +
        escapeHtml(formatTime(payload.updated_at)) +
        "</time> — từ QA/SEO/PERF jobs";
    }
    root.setAttribute("data-baked-updated", payload.updated_at || "");
  }

  function fetchFresh() {
    var url = base + "/data/ga-improvement-progress.json?t=" + Date.now();
    return fetch(url, { credentials: "omit", cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.updated_at) return;
        if (data.updated_at === bakedUpdated) {
          try {
            sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: data }));
          } catch (e) { /* quota */ }
          return;
        }
        bakedUpdated = data.updated_at;
        applyPayload(data);
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: data }));
        } catch (e) { /* quota */ }
      })
      .catch(function () { /* keep baked HTML */ });
  }

  try {
    var cached = sessionStorage.getItem(CACHE_KEY);
    if (cached) {
      var parsed = JSON.parse(cached);
      if (parsed && parsed.data && parsed.data.updated_at &&
          parsed.data.updated_at !== bakedUpdated) {
        applyPayload(parsed.data);
        bakedUpdated = parsed.data.updated_at;
      }
    }
  } catch (e) { /* ignore */ }

  fetchFresh();
  setInterval(fetchFresh, POLL_MS);
})();