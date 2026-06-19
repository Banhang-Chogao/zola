/**
 * Header banner rotator — luân phiên giữa các slide trong .header-rotator.
 *
 * GHI CHÚ QUAN TRỌNG (2026-06):
 *   Toàn bộ fetch GitHub API (commit info + deploy queue) đã được CHUYỂN sang
 *   build-time qua `load_data()` trong templates/base.html. Lý do: GitHub API
 *   unauthenticated chỉ cho 60 req/h/IP → user refresh vài chục lần là hết quota.
 *   Build-time fetch (có token) có 5000 req/h → đủ vô tận, user visit = 0 API call.
 *
 *   File này giờ chỉ còn logic rotation thuần tuý (Welcome ⇄ GitHub status).
 *   Mặc định 3 phút (180000ms) — cấu hình qua data-interval trên .header-rotator.
 */
(function () {
  const rotator = document.querySelector(".header-rotator");
  if (!rotator) return;
  if (rotator.dataset.rotate !== "true") return;

  const slides = rotator.querySelectorAll(".header-rotator__slide");
  if (slides.length < 2) return;

  const interval = parseInt(rotator.dataset.interval, 10) || 180000;
  let current = 0;
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
