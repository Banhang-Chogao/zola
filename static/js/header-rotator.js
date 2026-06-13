/**
 * Header banner rotator — luân phiên giữa Ad banner và GitHub status.
 *
 * Tắt rotation:  thêm data-rotate="false" vào .header-rotator (slide đầu hiển thị mãi).
 * Đổi thời gian: sửa data-interval (ms).
 * Tắt hoàn toàn: bỏ <script src="js/header-rotator.js"> trong base.html
 *                hoặc xoá slide B trong template.
 */
(function () {
  const rotator = document.querySelector(".header-rotator");
  if (!rotator) return;

  // ===== GitHub fetcher =====
  const ghSlide = rotator.querySelector("[data-repo]");
  if (ghSlide) {
    const repo = ghSlide.dataset.repo;
    const msgEl = ghSlide.querySelector("[data-commit-msg]");
    const hashEl = ghSlide.querySelector("[data-commit-hash]");
    const noteEl = ghSlide.querySelector("[data-commit-note]");
    const clockEl = ghSlide.querySelector(".header-github__clock");

    const pad = (n) => (n < 10 ? "0" + n : "" + n);
    const formatDateTime = (d) =>
      pad(d.getHours()) + ":" + pad(d.getMinutes()) + " " +
      pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();

    // Đợi data về thì hiển thị thời điểm commit (KHÔNG còn realtime current time)
    clockEl.textContent = "đang tải…";

    // Fetch 100 commit gần nhất để vừa lấy commit cuối, vừa đếm cho version
    fetch("https://api.github.com/repos/" + repo + "/commits?per_page=100", {
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then((commits) => {
        if (!Array.isArray(commits) || !commits.length) throw new Error("no commits");
        const c = commits[0];
        const sha = c.sha.substring(0, 7);
        const title = (c.commit.message || "").split("\n")[0];
        msgEl.textContent = title;
        hashEl.textContent = sha;
        noteEl.textContent = "Code mới nhất đã được GitHub ghi nhận.";

        // Thời điểm commit (committer.date ưu tiên, fallback author.date)
        const isoDate =
          (c.commit.committer && c.commit.committer.date) ||
          (c.commit.author && c.commit.author.date);
        if (isoDate) {
          const commitDate = new Date(isoDate);
          clockEl.textContent = formatDateTime(commitDate);
          clockEl.setAttribute("title", "Commit lúc " + commitDate.toString());
        } else {
          clockEl.textContent = "--:-- --/--/----";
        }

        // ===== Tính phiên bản blog =====
        updateBlogVersion(commits);
      })
      .catch((err) => {
        msgEl.textContent = "Không tải được commit";
        hashEl.textContent = "ERROR";
        noteEl.textContent = err.message;
        clockEl.textContent = "--:-- --/--/----";
        const tags = ghSlide.querySelector(".header-github__tags");
        const active = tags && tags.querySelector(".tag--active");
        if (active) {
          active.textContent = "KHÔNG TẢI ĐƯỢC";
          active.classList.remove("tag--active");
          active.classList.add("tag--error");
        }
      });
  }

  /**
   * Tính phiên bản blog từ danh sách commits.
   * Format: MAJOR.MINOR.PATCH v{6-digit-id}
   *   MAJOR = 1 (cố định)
   *   MINOR = số commit trong tuần hiện tại (từ thứ 2 đầu tuần đến hiện tại)
   *   PATCH = số commit trong ngày hôm nay
   *   ID    = SHA của commit cuối → parse 6 ký tự hex đầu → decimal mod 1,000,000
   *           → cho con số duy nhất ổn định cho mỗi commit
   */
  function updateBlogVersion(commits) {
    const verEl = document.querySelector("[data-blog-version]");
    const idEl = document.querySelector("[data-blog-id]");
    if (!verEl || !idEl) return;

    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const day = now.getDay(); // 0=Sun..6=Sat
    const daysSinceMonday = (day + 6) % 7;
    const startOfWeek = new Date(startOfDay);
    startOfWeek.setDate(startOfWeek.getDate() - daysSinceMonday);

    const dateOf = (c) =>
      new Date((c.commit.committer && c.commit.committer.date) || c.commit.author.date);

    const todayCount = commits.filter((c) => dateOf(c) >= startOfDay).length;
    const weekCount = commits.filter((c) => dateOf(c) >= startOfWeek).length;

    const major = 1;
    const minor = weekCount;
    const patch = todayCount;

    // SHA → 6 digit numeric id
    const latest = commits[0];
    const hex = latest.sha.substring(0, 8);
    const decimal = parseInt(hex, 16);
    const numericId = String(decimal % 1000000).padStart(6, "0");

    verEl.textContent = major + "." + minor + "." + patch;
    idEl.textContent = "v" + numericId;

    const root = document.querySelector("[data-blog-version-root]");
    if (root) {
      root.setAttribute(
        "title",
        "Tuần này có " + weekCount + " commit, hôm nay có " + patch + " commit. " +
        "ID dựa trên SHA " + latest.sha.substring(0, 7)
      );
    }
  }

  // ===== Deploy queue (GitHub Actions runs) =====
  loadDeployQueue();
  setInterval(loadDeployQueue, 30000);

  function loadDeployQueue() {
    const queueEl = document.querySelector("[data-deploy-queue]");
    if (!queueEl) return;
    const repo = queueEl.dataset.repo;
    const target = queueEl.querySelector("[data-queue-target]");
    const badge = queueEl.querySelector("[data-queue-badge]");

    fetch("https://api.github.com/repos/" + repo + "/actions/runs?per_page=20", {
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then((data) => {
        const runs = (data.workflow_runs || []).filter(
          (r) => r.status === "queued" || r.status === "in_progress" || r.status === "waiting"
        );
        renderQueue(runs, target, badge);
      })
      .catch((err) => {
        badge.textContent = "QUEUE ERROR";
        target.innerHTML = '<span class="deploy-queue__msg">' + escapeHtml(err.message) + "</span>";
      });
  }

  function renderQueue(runs, target, badge) {
    if (runs.length === 0) {
      badge.textContent = "✓ DEPLOYED";
      badge.classList.add("deploy-queue__badge--success");
      target.innerHTML =
        '<span class="deploy-queue__msg">' +
        '<span class="status-dot status-dot--success"></span>' +
        " Hàng đợi trống — mọi commit đã deploy xong</span>";
      return;
    }
    badge.textContent = "PENDING QUEUE (" + runs.length + ")";
    badge.classList.remove("deploy-queue__badge--success");

    target.innerHTML = runs
      .map((r) => {
        const sha = r.head_sha.substring(0, 7);
        const isRunning = r.status === "in_progress";
        const statusClass = isRunning ? "running" : "queued";
        const label = isRunning ? "đang deploy" : "chờ";
        const msg = (r.head_commit && r.head_commit.message) || "";
        const firstLine = msg.split("\n")[0];
        return (
          '<a class="deploy-queue__item deploy-queue__item--' + statusClass + '" ' +
          'href="' + escapeAttr(r.html_url) + '" target="_blank" rel="noopener" ' +
          'title="' + escapeAttr(firstLine) + '">' +
          '<span class="status-dot status-dot--' + statusClass + '"></span>' +
          '<code>' + escapeHtml(sha) + '</code>' +
          '<span>' + escapeHtml(label) + '</span>' +
          '</a>'
        );
      })
      .join("");
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) =>
      ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c])
    );
  }
  function escapeAttr(s) { return escapeHtml(s); }

  // ===== Rotation =====
  if (rotator.dataset.rotate !== "true") return;
  const slides = rotator.querySelectorAll(".header-rotator__slide");
  if (slides.length < 2) return;

  const interval = parseInt(rotator.dataset.interval, 10) || 3000;
  let current = 0;

  // Pause on hover for UX
  let paused = false;
  rotator.addEventListener("mouseenter", () => (paused = true));
  rotator.addEventListener("mouseleave", () => (paused = false));

  setInterval(() => {
    if (paused) return;
    slides[current].classList.remove("is-active");
    current = (current + 1) % slides.length;
    slides[current].classList.add("is-active");
  }, interval);
})();
