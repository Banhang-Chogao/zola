/**
 * World Cup 2026 News Hub — playful pastel-neon edition
 * Pure front-end interactivity: filtering, search, dark toggle,
 * count-up, scroll reveal, confetti, like/save, toast, live ticks.
 * All scoped to #wc-root so it never touches the global site.
 */
(function () {
  'use strict';

  var root = document.getElementById('wc-root');
  if (!root) return;

  var $ = function (sel, ctx) { return (ctx || root).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || root).querySelectorAll(sel)); };

  /* ---------- Toast ---------- */
  var toastEl = $('#wc-toast');
  var toastTimer;
  function toast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('wc__toast--show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('wc__toast--show'); }, 2200);
  }

  /* ---------- Confetti ---------- */
  var COLORS = ['#ff8a9b', '#c084fc', '#fcd34d', '#b5e6c3', '#b8d9ff', '#ff4d6d'];
  function confetti(n) {
    n = n || 24;
    for (var i = 0; i < n; i++) {
      (function (i) {
        var c = document.createElement('div');
        c.className = 'wc-confetti';
        c.style.background = COLORS[i % COLORS.length];
        c.style.left = Math.random() * 100 + 'vw';
        c.style.top = '-20px';
        c.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
        document.body.appendChild(c);
        var x = (Math.random() - 0.5) * 260;
        var dur = 1600 + Math.random() * 1400;
        c.animate([
          { transform: 'translate(0,0) rotate(0)', opacity: 1 },
          { transform: 'translate(' + x + 'px,' + (window.innerHeight + 60) + 'px) rotate(' + (720 * Math.random()) + 'deg)', opacity: 0 }
        ], { duration: dur, easing: 'cubic-bezier(.2,.6,.4,1)' }).onfinish = function () { c.remove(); };
      })(i);
    }
  }

  /* ---------- Generic [data-toast] elements ---------- */
  $$('[data-toast]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (el.tagName === 'A' && el.getAttribute('href') === '#') e.preventDefault();
      toast(el.getAttribute('data-toast'));
      if (el.hasAttribute('data-confetti')) confetti(20);
    });
  });

  /* ---------- Match items ---------- */
  $$('.wc__match').forEach(function (m) {
    m.addEventListener('click', function () { toast('⚽ ' + m.getAttribute('data-match')); });
  });

  /* ---------- Video items ---------- */
  $$('.wc__video').forEach(function (v) {
    v.addEventListener('click', function () { toast('▶️ Đang phát: ' + v.getAttribute('data-video')); });
  });

  /* ---------- Standings tabs ---------- */
  var standTabs = $$('#wc-stand-tabs .wc__tab');
  standTabs.forEach(function (btn) {
    btn.addEventListener('click', function () {
      standTabs.forEach(function (b) { b.classList.remove('wc__tab--active'); });
      btn.classList.add('wc__tab--active');
      var group = btn.getAttribute('data-group');
      $$('[data-group-table]').forEach(function (t) {
        t.hidden = t.getAttribute('data-group-table') !== group;
      });
    });
  });

  /* ---------- Menu filter ---------- */
  var menuLinks = $$('.wc__menu-link');
  var articles = $$('.wc__article');
  var emptyEl = $('#wc-empty');

  function applyFilter(category) {
    var shown = 0;
    articles.forEach(function (a) {
      var show = category === 'all' || a.getAttribute('data-category') === category;
      a.style.display = show ? '' : 'none';
      if (show) shown++;
    });
    if (emptyEl) emptyEl.hidden = shown !== 0;
  }

  menuLinks.forEach(function (link) {
    link.addEventListener('click', function () {
      var filter = link.getAttribute('data-filter');
      if (filter) {
        menuLinks.forEach(function (l) { l.classList.remove('wc__menu-link--active'); });
        link.classList.add('wc__menu-link--active');
        applyFilter(filter);
      }
    });
  });

  /* ---------- Search ---------- */
  var searchBtn = $('#wc-search-btn');
  var searchWrap = $('#wc-searchwrap');
  var searchInput = $('#wc-search-input');
  if (searchBtn && searchWrap) {
    searchBtn.addEventListener('click', function () {
      searchWrap.classList.toggle('wc__searchwrap--open');
      if (searchWrap.classList.contains('wc__searchwrap--open') && searchInput) searchInput.focus();
    });
  }
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      var q = searchInput.value.trim().toLowerCase();
      var shown = 0;
      articles.forEach(function (a) {
        var hay = (a.getAttribute('data-search') || '').toLowerCase();
        var show = !q || hay.indexOf(q) !== -1;
        a.style.display = show ? '' : 'none';
        if (show) shown++;
      });
      if (emptyEl) emptyEl.hidden = shown !== 0;
    });
  }

  /* ---------- Dark toggle (page-local) ---------- */
  var themeBtn = $('#wc-theme-btn');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var dark = root.classList.toggle('wc--dark');
      themeBtn.textContent = dark ? '☀️' : '🌙';
      toast(dark ? 'Chế độ Tối 🌙' : 'Chế độ Sáng ☀️');
    });
  }

  /* ---------- Bell ---------- */
  var bellBtn = $('#wc-bell-btn');
  if (bellBtn) {
    bellBtn.addEventListener('click', function () {
      var badge = $('.wc__badge', bellBtn);
      if (badge) badge.remove();
      toast('🔔 3 thông báo: Iran bất bại, Messi tin vui, Mbappe hat-trick!');
    });
  }

  /* ---------- Mini actions: like / save / share ---------- */
  $$('.wc__mini').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var act = btn.getAttribute('data-act');
      if (act === 'like') {
        var liked = btn.classList.toggle('wc__mini--liked');
        btn.textContent = liked ? '❤' : '♡';
        if (liked) { toast('Đã thích bài viết ❤️'); confetti(8); }
      } else if (act === 'save') {
        var saved = btn.classList.toggle('wc__mini--saved');
        toast(saved ? 'Đã lưu bài viết 🔖' : 'Đã bỏ lưu');
      } else if (act === 'share') {
        toast('Đã sao chép liên kết 🔗');
      }
    });
  });

  /* ---------- Featured "Đọc tiếp" button ---------- */
  $$('.wc__featured .wc__btn').forEach(function (b) {
    b.addEventListener('click', function (e) { e.stopPropagation(); toast('Đang mở bài viết 📖'); confetti(16); });
  });

  /* ---------- Count-up stats ---------- */
  function countUp() {
    $$('[data-count]').forEach(function (el) {
      var target = parseInt(el.getAttribute('data-count'), 10) || 0;
      var cur = 0;
      var step = Math.max(1, target / 40);
      var iv = setInterval(function () {
        cur += step;
        if (cur >= target) { cur = target; clearInterval(iv); }
        el.textContent = Math.floor(cur);
      }, 28);
    });
  }

  /* ---------- Scroll reveal ---------- */
  var revealEls = $$('.wc-reveal');
  if ('IntersectionObserver' in window) {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('wc-in'); obs.unobserve(en.target); }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { obs.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('wc-in'); });
  }

  /* ---------- Back to top ---------- */
  var toTop = $('#wc-to-top');
  if (toTop) {
    window.addEventListener('scroll', function () {
      toTop.classList.toggle('wc__to-top--show', window.scrollY > 500);
    });
    toTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
  }

  /* ---------- Live score tick (fun, every 9s) ---------- */
  var liveMatch = null;
  $$('.wc__match').forEach(function (m) {
    if ($('.wc__chip--live', m)) liveMatch = m;
  });
  if (liveMatch) {
    setInterval(function () {
      if (Math.random() > 0.6) {
        var scoreEl = $('.wc__match-score', liveMatch);
        var parts = scoreEl.textContent.split('-').map(function (s) { return parseInt(s, 10) || 0; });
        if (Math.random() > 0.5) parts[0]++; else parts[1]++;
        scoreEl.textContent = parts[0] + ' - ' + parts[1];
        var name = liveMatch.getAttribute('data-match');
        toast('⚽ VÀOOO! ' + name + ' → ' + parts[0] + ' - ' + parts[1]);
        confetti(14);
      }
    }, 9000);
  }

  /* ---------- Init ---------- */
  setTimeout(countUp, 400);
  setTimeout(function () { toast('🎉 Chào mừng đến World Cup 2026!'); confetti(20); }, 900);
})();
