(function () {
  "use strict";

  var CONTAINER = document.querySelector(".deployment-dashboard");
  if (!CONTAINER) return;

  function getStatusCfg(state) {
    if (state === "success")  return { label: "SUCCESS",  cls: "status-success" };
    if (state === "failure")  return { label: "FAILED",   cls: "status-failure" };
    if (state === "pending")  return { label: "PENDING",  cls: "status-pending" };
    return { label: "UNKNOWN", cls: "status-unknown" };
  }

  function refreshDashboard() {
    fetch("/data/deployment-status.json?" + Date.now())
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var cfg = getStatusCfg(data.status);
        var badge = CONTAINER.querySelector("[data-ds-badge]");
        if (badge) {
          badge.textContent = cfg.label;
          badge.className = "status-value " + cfg.cls;
        }

        var timeEl = CONTAINER.querySelector("[data-ds-time]");
        if (timeEl) timeEl.textContent = data.deploy_time || "N/A";

        var shaEl = CONTAINER.querySelector("[data-ds-sha]");
        if (shaEl) shaEl.textContent = data.commit_sha || "N/A";

        var linkEl = CONTAINER.querySelector("[data-ds-sha-link]");
        if (linkEl && data.commit_sha) {
          linkEl.href = "https://github.com/Banhang-Chogao/zola/commit/" + data.commit_sha;
        }

        var msgEl = CONTAINER.querySelector("[data-ds-msg]");
        if (msgEl) {
          msgEl.textContent = (data.commit_message || "N/A").substring(0, 50);
        }

        var runLink = CONTAINER.querySelector("[data-ds-run-link]");
        if (runLink && data.run_url) {
          runLink.href = data.run_url;
        }
      })
      .catch(function (err) {
        console.log("[Dashboard] refresh skipped:", err.message);
      });
  }

  setInterval(refreshDashboard, 300000);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) refreshDashboard();
  });
})();
