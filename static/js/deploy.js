(function () {
  const card = document.querySelector(".deploy-card");
  if (!card) return;

  const repo = card.dataset.repo;
  const headlineEl = card.querySelector("[data-headline]");
  const commitEl = card.querySelector("[data-commit]");
  const statusTag = card.querySelector("[data-status]");
  const banner = card.querySelector("[data-banner]");
  const bannerTitle = card.querySelector("[data-banner-title]");
  const bannerMsg = card.querySelector("[data-banner-msg]");
  const divider = card.querySelector("[data-divider]");
  const clockEl = card.querySelector(".deploy-card__clock");

  function pad(n) { return n < 10 ? "0" + n : "" + n; }

  function formatTime(d) {
    return pad(d.getHours()) + ":" + pad(d.getMinutes()) + " " +
           pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();
  }

  function tick() { clockEl.textContent = formatTime(new Date()); }
  tick();
  setInterval(tick, 30000);

  function setState(state) {
    banner.classList.remove("deploy-banner--success", "deploy-banner--running", "deploy-banner--failed");
    divider.classList.remove("deploy-card__divider--success", "deploy-card__divider--running", "deploy-card__divider--failed");
    statusTag.classList.remove("tag--active", "tag--code", "tag--error", "tag--warn");

    if (state === "success") {
      banner.classList.add("deploy-banner--success");
      divider.classList.add("deploy-card__divider--success");
      statusTag.classList.add("tag--active");
      statusTag.textContent = "HOẠT ĐỘNG";
      headlineEl.textContent = "GitHub main đang truy cập được";
      bannerTitle.textContent = "Đã sẵn sàng";
      bannerMsg.textContent = "GitHub cập nhật ngay khi commit được đẩy lên nhánh main.";
    } else if (state === "running") {
      banner.classList.add("deploy-banner--running");
      divider.classList.add("deploy-card__divider--running");
      statusTag.classList.add("tag--warn");
      statusTag.textContent = "ĐANG DEPLOY";
      headlineEl.textContent = "GitHub Actions đang chạy";
      bannerTitle.textContent = "Đang triển khai";
      bannerMsg.textContent = "Workflow build & deploy đang chạy, đợi vài giây site sẽ cập nhật.";
    } else if (state === "failed") {
      banner.classList.add("deploy-banner--failed");
      divider.classList.add("deploy-card__divider--failed");
      statusTag.classList.add("tag--error");
      statusTag.textContent = "LỖI";
      headlineEl.textContent = "Deploy thất bại";
      bannerTitle.textContent = "Cần khắc phục";
      bannerMsg.textContent = "Workflow gần nhất thất bại — xem log Actions để biết chi tiết.";
    }
  }

  async function loadDeploy() {
    try {
      const res = await fetch("https://api.github.com/repos/" + repo + "/actions/runs?per_page=1", {
        headers: { "Accept": "application/vnd.github+json" }
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      const run = (data.workflow_runs || [])[0];
      if (!run) throw new Error("không có workflow run nào");

      const sha = run.head_sha.substring(0, 7);
      const msg = (run.head_commit && run.head_commit.message || "").split("\n")[0];
      commitEl.textContent = sha + " - " + msg;

      if (run.status === "completed" && run.conclusion === "success") {
        setState("success");
      } else if (run.status === "completed" && run.conclusion !== "success") {
        setState("failed");
      } else {
        setState("running");
      }
    } catch (err) {
      banner.classList.add("deploy-banner--failed");
      divider.classList.add("deploy-card__divider--failed");
      statusTag.classList.remove("tag--active");
      statusTag.classList.add("tag--error");
      statusTag.textContent = "KHÔNG TẢI ĐƯỢC";
      headlineEl.textContent = "Không lấy được trạng thái";
      commitEl.textContent = "ERROR - " + err.message;
      bannerTitle.textContent = "API lỗi";
      bannerMsg.textContent = err.message;
    }
  }

  loadDeploy();
  setInterval(loadDeploy, 60000);
})();
