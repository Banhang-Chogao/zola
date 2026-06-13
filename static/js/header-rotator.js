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

    fetch("https://api.github.com/repos/" + repo + "/commits?per_page=1", {
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then((data) => {
        const c = Array.isArray(data) && data[0];
        if (!c) throw new Error("no commits");
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
