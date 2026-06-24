(function () {
  const card = document.querySelector("[data-home-heartbeat]");
  if (!card) return;

  const statusEl = card.querySelector("[data-heartbeat-status]");
  const timeEl = card.querySelector("[data-heartbeat-time]");
  const titleEl = card.querySelector("[data-heartbeat-title]");
  const descEl = card.querySelector("[data-heartbeat-desc]");
  const metaEl = card.querySelector("[data-heartbeat-meta]");

  function safeStr(v) {
    if (v == null) return "";
    if (typeof v === "string") return v;
    if (typeof v === "number") return String(v);
    if (typeof v === "boolean") return v ? "true" : "false";
    try { return JSON.stringify(v); } catch (_) { return String(v); }
  }

  function pick(obj, keys) {
    for (const key of keys) {
      if (obj && obj[key] !== undefined && obj[key] !== null && obj[key] !== "") return obj[key];
    }
    return "";
  }

  function setText(el, text) {
    if (el) el.textContent = text;
  }

  function fallback() {
    card.dataset.status = "wait";
    setText(statusEl, "Đang chờ dữ liệu mới");
    setText(titleEl, "Blog Heart Beat đang chờ nhịp mới");
    setText(descEl, "Card đã sẵn sàng. Khi workflow ghi JSON mới, trang chủ sẽ tự đọc và hiển thị trạng thái.");
    setText(timeEl, "");
    setText(metaEl, "Nguồn: /data/blog-heartbeat.json");
  }

  fetch("/data/blog-heartbeat.json", { cache: "no-store" })
    .then(function (res) {
      if (!res.ok) throw new Error("Missing heartbeat JSON");
      return res.json();
    })
    .then(function (data) {
      const status = String(pick(data, ["status", "state", "health", "result"]) || "ok").toLowerCase();
      const generatedAt = safeStr(pick(data, ["generated_at", "updated_at", "last_updated", "timestamp"]));
      const commit = safeStr(pick(data, ["commit", "sha", "short_sha", "head_sha"]));
      const message = safeStr(pick(data, ["message", "title", "description", "name"]));
      const totalPosts = safeStr(pick(data, ["total_posts", "posts_total", "live_posts"]));
      const latestRuns = Array.isArray(data.recent_runs) ? data.recent_runs.length : "";
      const latestItems = Array.isArray(data.items) ? data.items.length : "";

      const ok = (
        status.includes("ok") ||
        status.includes("pass") ||
        status.includes("success") ||
        status.includes("healthy") ||
        status === "live"
      );

      card.dataset.status = ok ? "ok" : "warn";
      setText(statusEl, ok ? "Đang sống khỏe" : "Cần kiểm tra nhẹ");
      setText(titleEl, ok ? "SEOMONEY đang sống khỏe" : "SEOMONEY cần kiểm tra lại");
      setText(descEl, message || "Heartbeat đã đọc dữ liệu kiểm tra mới nhất từ workflow.");

      if (generatedAt) {
        setText(timeEl, "Cập nhật: " + generatedAt);
      }

      const bits = [];
      if (commit) bits.push("Commit " + String(commit).slice(0, 7));
      if (totalPosts) bits.push(totalPosts + " bài live");
      if (latestRuns) bits.push(latestRuns + " run gần đây");
      if (latestItems) bits.push(latestItems + " mục dữ liệu");
      setText(metaEl, bits.length ? bits.join(" · ") : "Nguồn: /data/blog-heartbeat.json");
    })
    .catch(fallback);
})();
