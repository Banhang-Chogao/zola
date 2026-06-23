(function () {
  const root = document.querySelector("[data-bhb-strip]");
  if (!root) return;

  const summaryEl = root.querySelector("[data-bhb-strip-summary]");
  const metaEl = root.querySelector("[data-bhb-strip-meta]");
  const DATA_URL = "/data/blog-heartbeat.json";
  const REFRESH_MS = 15000;

  function parseDate(value) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function age(value) {
    const d = parseDate(value);
    if (!d) return "unknown";
    const seconds = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `about ${minutes} minutes ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `about ${hours} hours ago`;
    return `about ${Math.floor(hours / 24)} days ago`;
  }

  function latestDeployText(deploys) {
    if (!Array.isArray(deploys) || deploys.length === 0) return "deploy unknown";
    const latest = deploys[0];
    const ok = latest.conclusion === "success" ? "deployed" : (latest.status || latest.conclusion || "pending");
    return `${ok} ${age(latest.created_at)}`;
  }

  async function load() {
    const res = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function render() {
    try {
      const data = await load();
      const s = data.summary || {};
      const running = s.in_progress || 0;
      const queued = s.queued || 0;
      const success = s.success || 0;
      const failure = s.failure || 0;

      let state = "healthy";
      if (failure > 0) state = "attention";
      else if (running > 0 || queued > 0) state = "running";

      root.dataset.state = state;
      root.hidden = false;

      summaryEl.textContent =
        `CI/CD live · ${running} running · ${queued} queued · ${success} pass · ${failure} fail · ${latestDeployText(data.deploy_runs)}`;

      metaEl.textContent = `updated ${age(data.generated_at)} →`;
    } catch (err) {
      root.dataset.state = "attention";
      root.hidden = false;
      summaryEl.textContent = `Blog Heart Beat offline · ${err.message}`;
      metaEl.textContent = "open dashboard →";
    }
  }

  render();
  window.setInterval(render, REFRESH_MS);
})();
