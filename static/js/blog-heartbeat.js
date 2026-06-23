(function () {
  const DATA_URL = "/data/blog-heartbeat.json";
  const REFRESH_MS = 15000;

  const $ = (id) => document.getElementById(id);

  function escapeText(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function clip(value, size) {
    const text = String(value ?? "");
    return text.length > size ? text.slice(0, Math.max(0, size - 1)) + "…" : text;
  }

  function pad(value, size) {
    const text = clip(value, size);
    return text + " ".repeat(Math.max(0, size - text.length));
  }

  function parseDate(value) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function duration(ms) {
    if (!Number.isFinite(ms) || ms < 0) return "-";
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rs = s % 60;
    if (m < 60) return `${m}m${rs ? `${rs}s` : ""}`;
    const h = Math.floor(m / 60);
    const rm = m % 60;
    return `${h}h${rm ? `${rm}m` : ""}`;
  }

  function age(value) {
    const d = parseDate(value);
    if (!d) return "-";
    const diff = Date.now() - d.getTime();
    const s = Math.max(0, Math.floor(diff / 1000));
    if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `about ${m} minutes ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `about ${h} hours ago`;
    const day = Math.floor(h / 24);
    return `about ${day} days ago`;
  }

  function elapsed(run) {
    const start = parseDate(run.created_at || run.started_at);
    if (!start) return "-";

    if (run.status === "in_progress" || run.status === "queued" || run.status === "waiting") {
      return duration(Date.now() - start.getTime());
    }

    const end = parseDate(run.updated_at);
    if (!end) return "-";
    return duration(end.getTime() - start.getTime());
  }

  function statusIcon(item) {
    const status = item.status || item.state || "";
    const conclusion = item.conclusion || "";

    if (conclusion === "success" || status === "success") return "✅";
    if (conclusion === "failure" || conclusion === "cancelled" || status === "failure") return "❌";
    if (status === "in_progress") return "🔄";
    if (status === "queued" || status === "waiting") return "⏳";
    return "•";
  }

  function renderTable(data) {
    const runs = Array.isArray(data.runs) ? data.runs.slice(0, 8) : [];

    const header =
      `${pad("Status", 8)} | ${pad("Message", 30)} | ${pad("Workflow", 24)} | ${pad("Branch", 22)} | ${pad("Elapsed", 8)} | ${pad("Age", 22)}`;

    const line = "-".repeat(header.length);

    const body = runs.map((run) => {
      return [
        pad(statusIcon(run) + " " + (run.conclusion || run.status || "-"), 8),
        pad(run.title || run.display_title || "-", 30),
        pad(run.workflow || run.workflow_name || "-", 24),
        pad(run.branch || "-", 22),
        pad(elapsed(run), 8),
        pad(age(run.created_at), 22)
      ].join(" | ");
    });

    return [header, line, ...body].join("\n");
  }

  function renderList(items, emptyText) {
    if (!Array.isArray(items) || items.length === 0) {
      return `<p class="bhb-muted">${escapeText(emptyText)}</p>`;
    }

    return `<div class="bhb-list">` + items.slice(0, 6).map((item) => {
      const title = escapeText(item.title || item.workflow || item.workflow_name || item.branch || "Untitled");
      const url = escapeText(item.url || "#");
      const meta = escapeText([
        item.branch || item.head || item.head_ref || "",
        item.status || item.state || "",
        item.conclusion || "",
        age(item.created_at)
      ].filter(Boolean).join(" · "));

      return `
        <div class="bhb-item">
          <a href="${url}" target="_blank" rel="noopener">${statusIcon(item)} ${title}</a>
          <div class="bhb-muted">${meta}</div>
        </div>
      `;
    }).join("") + `</div>`;
  }

  async function loadHeartbeat() {
    const res = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function render() {
    try {
      const data = await loadHeartbeat();
      const summary = data.summary || {};
      const updated = data.generated_at ? age(data.generated_at) : "unknown";

      const running = summary.in_progress || 0;
      const success = summary.success || 0;
      const failure = summary.failure || 0;
      const queued = summary.queued || 0;

      $("bhb-status-pill").textContent =
        failure > 0 ? "attention" : running > 0 || queued > 0 ? "in_progress" : "healthy";

      $("bhb-summary").textContent =
        `blog heartbeat: 🔄 ${running} đang chạy · ⏳ ${queued} chờ · ✅ ${success} pass · ❌ ${failure} fail · updated ${updated}`;

      $("bhb-table").textContent = renderTable(data);
      $("bhb-prs").innerHTML = renderList(data.pull_requests, "Không có PR mở.");
      $("bhb-deploys").innerHTML = renderList(data.deploy_runs, "Chưa có deploy run.");
      $("bhb-refresh-note").textContent =
        `Auto-refresh 15s · browser ${new Date().toLocaleTimeString("vi-VN")}`;
    } catch (err) {
      $("bhb-status-pill").textContent = "offline";
      $("bhb-summary").textContent = `Không tải được Blog Heart Beat: ${err.message}`;
      $("bhb-table").textContent = "Data unavailable.";
    }
  }

  render();
  window.setInterval(render, REFRESH_MS);
})();
