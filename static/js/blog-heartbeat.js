(function () {
  const root = document.querySelector("[data-blog-heartbeat]");
  if (!root) return;

  const DATA_URL = "/data/blog-heartbeat.json";
  const REFRESH_MS = 15000;

  const qs = (sel) => root.querySelector(sel);

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
    const diff = Math.max(0, Date.now() - d.getTime());
    const s = Math.floor(diff / 1000);
    if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `about ${m} minutes ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `about ${h} hours ago`;
    return `about ${Math.floor(h / 24)} days ago`;
  }

  function elapsed(run) {
    const start = parseDate(run.created_at || run.started_at);
    if (!start) return "-";
    const live = run.status === "in_progress" || run.status === "queued" || run.status === "waiting";
    const end = live ? new Date() : parseDate(run.updated_at);
    if (!end) return "-";
    return duration(end.getTime() - start.getTime());
  }

  function icon(item) {
    const status = item.status || item.state || "";
    const conclusion = item.conclusion || "";
    if (conclusion === "success" || status === "success") return "✓";
    if (["failure", "cancelled", "timed_out"].includes(conclusion) || status === "failure") return "×";
    if (status === "in_progress") return "↻";
    if (status === "queued" || status === "waiting") return "…";
    return "•";
  }

  function renderTable(data) {
    const runs = Array.isArray(data.runs) ? data.runs.slice(0, 10) : [];
    const header = [
      pad("STATUS", 10),
      pad("TITLE", 32),
      pad("WORKFLOW", 24),
      pad("BRANCH", 24),
      pad("EVENT", 12),
      pad("ELAPSED", 9),
      pad("AGE", 22)
    ].join(" ");

    const line = "-".repeat(header.length);

    const body = runs.map((run) => [
      pad(`${icon(run)} ${run.conclusion || run.status || "-"}`, 10),
      pad(run.title || run.display_title || "-", 32),
      pad(run.workflow || run.workflow_name || "-", 24),
      pad(run.branch || "-", 24),
      pad(run.event || "-", 12),
      pad(elapsed(run), 9),
      pad(age(run.created_at), 22)
    ].join(" "));

    return [header, line, ...body].join("\n");
  }

  function htmlEscape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function renderCards(items, emptyText) {
    if (!Array.isArray(items) || items.length === 0) {
      return `<p class="bhb-muted">${htmlEscape(emptyText)}</p>`;
    }

    return `<div class="bhb-list">` + items.slice(0, 6).map((item) => {
      const title = htmlEscape(item.title || item.workflow || item.workflow_name || item.head || item.branch || "Untitled");
      const url = htmlEscape(item.url || "#");
      const meta = htmlEscape([
        item.head || item.branch || "",
        item.status || item.state || "",
        item.conclusion || item.merge_state || "",
        age(item.created_at)
      ].filter(Boolean).join(" · "));

      return `
        <div class="bhb-item">
          <a href="${url}" target="_blank" rel="noopener">${icon(item)} ${title}</a>
          <div class="bhb-muted">${meta}</div>
        </div>
      `;
    }).join("") + `</div>`;
  }

  async function fetchData() {
    const res = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function updateClock() {
    const el = qs("[data-bhb-clock]");
    if (el) {
      el.textContent = new Date().toLocaleString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        day: "2-digit",
        month: "2-digit",
        year: "numeric"
      });
    }
  }

  async function render() {
    updateClock();

    try {
      const data = await fetchData();
      const s = data.summary || {};
      const running = s.in_progress || 0;
      const queued = s.queued || 0;
      const success = s.success || 0;
      const failure = s.failure || 0;

      qs("[data-bhb-state]").textContent =
        failure > 0 ? "attention" : running > 0 || queued > 0 ? "in_progress" : "healthy";

      qs("[data-bhb-main-title]").textContent =
        failure > 0
          ? "GitHub đang báo lỗi cần xem"
          : running > 0 || queued > 0
            ? "CI/CD đang có workflow chạy"
            : "GitHub pipeline đang ổn định";

      qs("[data-bhb-main-desc]").textContent =
        `↻ ${running} running · … ${queued} queued · ✓ ${success} pass · × ${failure} fail · updated ${age(data.generated_at)}`;

      qs("[data-bhb-table]").textContent = renderTable(data);
      qs("[data-bhb-prs]").innerHTML = renderCards(data.pull_requests, "Không có PR đang mở.");
      qs("[data-bhb-deploys]").innerHTML = renderCards(data.deploy_runs, "Chưa có deploy run.");
      qs("[data-bhb-updated]").textContent = `Auto-refresh 15s · ${age(data.generated_at)}`;
    } catch (err) {
      qs("[data-bhb-state]").textContent = "offline";
      qs("[data-bhb-main-title]").textContent = "Blog Heart Beat chưa lấy được dữ liệu";
      qs("[data-bhb-main-desc]").textContent = err.message;
      qs("[data-bhb-table]").textContent = "Data unavailable.";
    }
  }

  updateClock();
  render();
  window.setInterval(updateClock, 1000);
  window.setInterval(render, REFRESH_MS);
})();
