(function () {
  var card = document.querySelector("[data-home-heartbeat]");
  if (!card) return;

  var statusEl = card.querySelector("[data-heartbeat-status]");
  var timeEl = card.querySelector("[data-heartbeat-time]");
  var titleEl = card.querySelector("[data-heartbeat-title]");
  var descEl = card.querySelector("[data-heartbeat-desc]");
  var metaEl = card.querySelector("[data-heartbeat-meta]");

  function pick(obj, keys) {
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
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
      var status = String(pick(data, ["status", "state", "health", "result"]) || "ok").toLowerCase();
      var lastCheck = pick(data, ["last_check", "generated_at", "updated_at", "last_updated", "timestamp"]);
      var message = pick(data, ["message", "title", "description", "name"]) || "Blog đang hoạt động bình thường";
      var totalPosts = pick(data, ["total_posts", "posts_total", "live_posts"]);

      var ok = (
        status.indexOf("ok") !== -1 ||
        status.indexOf("pass") !== -1 ||
        status.indexOf("success") !== -1 ||
        status.indexOf("healthy") !== -1 ||
        status === "live"
      );

      card.dataset.status = ok ? "ok" : "warn";
      setText(statusEl, ok ? "Đang sống khỏe" : "Cần kiểm tra nhẹ");
      setText(titleEl, ok ? "SEOMONEY đang sống khỏe" : "SEOMONEY cần kiểm tra lại");
      setText(descEl, message);

      if (lastCheck) {
        setText(timeEl, "Cập nhật: " + lastCheck);
      }

      var bits = [];
      if (totalPosts) bits.push(totalPosts + " bài live");
      setText(metaEl, bits.length ? bits.join(" · ") : "Nguồn: /data/blog-heartbeat.json");
    })
    .catch(fallback);
})();
