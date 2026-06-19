/**
 * Header banner carousel — slider/carousel cho .header-rotator (3 banner).
 *
 * Thay "static rotation" cũ bằng slider điều khiển TAY: mũi tên ‹ ›, chấm (dots),
 * vuốt (swipe) trên mobile, phím ← →. Vẫn auto-advance (data-rotate="true") với
 * pause khi hover/focus; mọi thao tác tay reset đồng hồ auto.
 *
 * GHI CHÚ: fetch GitHub API (commit/deploy) đã chuyển build-time (load_data) —
 * file này thuần logic carousel. Banner THEODOI8 LIVE tự refresh ở theodoi8-banner.js.
 */
(function () {
  var rotator = document.querySelector(".header-rotator");
  if (!rotator) return;

  var viewport = rotator.querySelector(".header-rotator__viewport") || rotator;
  var slides = Array.prototype.slice.call(
    rotator.querySelectorAll(".header-rotator__slide")
  );
  if (slides.length < 2) return;

  var autoplay = rotator.dataset.rotate === "true";
  var interval = parseInt(rotator.dataset.interval, 10) || 7000;
  var current = slides.findIndex(function (s) {
    return s.classList.contains("is-active");
  });
  if (current < 0) current = 0;
  var paused = false;
  var timer = null;

  // ----- Dots (sinh động theo số slide) -----
  var dotsWrap = rotator.querySelector("[data-rotator-dots]");
  var dots = [];
  if (dotsWrap) {
    slides.forEach(function (s, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "header-rotator__dot";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-label", "Banner " + (i + 1));
      b.addEventListener("click", function () {
        go(i, true);
      });
      dotsWrap.appendChild(b);
      dots.push(b);
    });
  }

  function render() {
    slides.forEach(function (s, i) {
      var on = i === current;
      s.classList.toggle("is-active", on);
      s.setAttribute("aria-hidden", on ? "false" : "true");
    });
    dots.forEach(function (d, i) {
      var on = i === current;
      d.classList.toggle("is-active", on);
      d.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  function go(i, userInitiated) {
    current = (i + slides.length) % slides.length;
    render();
    if (userInitiated) restart();
  }
  function next(u) {
    go(current + 1, u);
  }
  function prev(u) {
    go(current - 1, u);
  }

  function start() {
    if (!autoplay) return;
    stop();
    timer = setInterval(function () {
      if (!paused) next(false);
    }, interval);
  }
  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }
  function restart() {
    stop();
    start();
  }

  // ----- Mũi tên -----
  var prevBtn = rotator.querySelector("[data-rotator-prev]");
  var nextBtn = rotator.querySelector("[data-rotator-next]");
  if (prevBtn)
    prevBtn.addEventListener("click", function (e) {
      e.preventDefault();
      prev(true);
    });
  if (nextBtn)
    nextBtn.addEventListener("click", function (e) {
      e.preventDefault();
      next(true);
    });

  // ----- Pause on hover / focus -----
  rotator.addEventListener("mouseenter", function () {
    paused = true;
  });
  rotator.addEventListener("mouseleave", function () {
    paused = false;
  });
  rotator.addEventListener("focusin", function () {
    paused = true;
  });
  rotator.addEventListener("focusout", function () {
    paused = false;
  });

  // ----- Phím mũi tên -----
  rotator.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") {
      prev(true);
    } else if (e.key === "ArrowRight") {
      next(true);
    }
  });

  // ----- Vuốt (swipe) trên mobile -----
  var x0 = null;
  var y0 = null;
  var moved = false;
  viewport.addEventListener(
    "touchstart",
    function (e) {
      var t = e.changedTouches[0];
      x0 = t.clientX;
      y0 = t.clientY;
      moved = false;
    },
    { passive: true }
  );
  viewport.addEventListener(
    "touchmove",
    function (e) {
      if (x0 === null) return;
      var t = e.changedTouches[0];
      var dx = Math.abs(t.clientX - x0);
      if (dx > 10 && dx > Math.abs(t.clientY - y0)) moved = true;
    },
    { passive: true }
  );
  viewport.addEventListener("touchend", function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 40) (dx < 0 ? next : prev)(true);
    x0 = y0 = null;
  });
  // Chặn click mở link sau khi vuốt
  slides.forEach(function (s) {
    s.addEventListener(
      "click",
      function (e) {
        if (moved) {
          e.preventDefault();
          moved = false;
        }
      },
      true
    );
  });

  render();
  start();
})();
