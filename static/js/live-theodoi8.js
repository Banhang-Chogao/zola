/**
 * Live TheoDoi8 — footer terminal panel. Poll /data/theodoi8-report.json
 * (cùng nguồn shortcut theodoi8), hiển thị 1 vòng terminal, auto-refresh 30–35s.
 */
(function () {
  "use strict";

  var P = window.Theodoi8Parser;
  if (!P) return;

  var root = document.querySelector("[data-live-theodoi8]");
  if (!root) return;

  var viewport = root.querySelector("[data-live-t8-viewport]");
  var badgeEl = root.querySelector("[data-live-t8-badge]");
  var pollTimer = null;
  var frozen = false;
  var roundNum = 0;
  var lastStamp = null;
  var prevCommits = null;
  var lastCommitsSnapshot = null;

  var url =
    root.getAttribute("data-live-t8-url") ||
    P.reportUrl(root.getAttribute("data-live-t8-base") || "");

  function jitterMs() {
    return 30000 + Math.floor(Math.random() * 5001);
  }

  function setBadge(data) {
    if (!badgeEl) return;
    var b = P.overallBadge(data);
    badgeEl.textContent = b.icon + " " + b.label;
    badgeEl.className = "live-t8__badge live-t8__badge--" + (b.label || "idle").replace(/_/g, "-");
    if (frozen) badgeEl.classList.add("live-t8__badge--frozen");
    else badgeEl.classList.remove("live-t8__badge--frozen");
  }

  function buildRoundEl(text) {
    var wrap = document.createElement("div");
    wrap.className = "live-t8__round is-entering";
    var pre = document.createElement("pre");
    pre.className = "live-t8__terminal";
    pre.setAttribute("aria-live", "polite");
    pre.textContent = text;
    wrap.appendChild(pre);
    return wrap;
  }

  function removeAfterTransition(node, cb) {
    if (!node) {
      if (cb) cb();
      return;
    }
    var done = false;
    function finish() {
      if (done) return;
      done = true;
      if (node.parentNode) node.parentNode.removeChild(node);
      if (cb) cb();
    }
    node.classList.add("is-exiting");
    node.addEventListener("transitionend", finish, { once: true });
    setTimeout(finish, 450);
  }

  function showRound(data, animate) {
    if (!viewport || !data) return;
    var loading = viewport.querySelector(".live-t8__loading");
    if (loading) loading.remove();
    viewport.setAttribute("aria-busy", "false");
    roundNum += 1;
    var text = P.formatTerminalRound(data, roundNum, prevCommits);
    prevCommits = (data.commits || []).map(function (c) {
      return { sha: c.sha, status: c.status, run_status: c.run_status };
    });
    lastCommitsSnapshot = data.generated_at;
    setBadge(data);

    var current = viewport.querySelector(".live-t8__round:not(.is-exiting)");
    var next = buildRoundEl(text);
    viewport.appendChild(next);

    requestAnimationFrame(function () {
      next.classList.remove("is-entering");
    });

    if (animate && current) {
      removeAfterTransition(current);
    } else if (current && current !== next) {
      current.parentNode.removeChild(current);
    }
  }

  function applyData(data, animate) {
    if (!data || typeof data !== "object") return;
    if (data.generated_at && data.generated_at === lastStamp) return;
    lastStamp = data.generated_at || null;
    showRound(data, animate);
  }

  function stopPolling() {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    frozen = true;
    if (badgeEl) badgeEl.classList.add("live-t8__badge--frozen");
  }

  function schedulePoll() {
    if (pollTimer) clearTimeout(pollTimer);
    pollTimer = setTimeout(function () {
      pollTimer = null;
      if (document.visibilityState === "visible") poll(true);
      else schedulePoll();
    }, jitterMs());
  }

  function startPolling() {
    frozen = false;
    if (badgeEl) badgeEl.classList.remove("live-t8__badge--frozen");
    schedulePoll();
  }

  function poll(animate) {
    fetch(url + (url.indexOf("?") < 0 ? "?_=" : "&_=") + Date.now(), {
      credentials: "omit",
      cache: "no-store"
    })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (data) {
        if (!data) {
          if (!frozen) schedulePoll();
          return;
        }

        var active = P.hasActiveRuns(data);
        if (frozen && active) startPolling();

        var changed = !lastStamp || data.generated_at !== lastStamp;
        if (changed) applyData(data, animate !== false);

        if (active) {
          frozen = false;
          schedulePoll();
        } else {
          stopPolling();
        }
      })
      .catch(function () {
        if (!frozen) schedulePoll();
      });
  }

  function seed() {
    var node = document.getElementById("live-t8-seed");
    if (!node || !node.textContent) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (e) {
      return null;
    }
  }

  var initial = seed();
  if (initial) {
    lastStamp = initial.generated_at || null;
    roundNum = 0;
    showRound(initial, false);
    if (P.hasActiveRuns(initial)) startPolling();
    else stopPolling();
  } else {
    poll(false);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && !frozen) poll(true);
  });
})();