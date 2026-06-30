(function () {
  'use strict';

  /* ── Category chip filter ── */
  var chips = document.querySelectorAll('#explore-chips .home-magazine__chip');
  var exploreCards = document.querySelectorAll('#explore-grid .explore-card');

  if (chips.length && exploreCards.length) {
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        chips.forEach(function (c) { c.classList.remove('is-active'); });
        chip.classList.add('is-active');

        var slug = chip.getAttribute('data-chip');

        exploreCards.forEach(function (card) {
          if (slug === 'all' || card.getAttribute('data-category') === slug) {
            card.style.display = '';
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }

  /* ── Per-section pagination ── */
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('[data-home-pager]').forEach(function (pager) {
    var items = Array.prototype.slice.call(pager.querySelectorAll('[data-page-item]'));
    var nav = pager.querySelector('[data-page-nav]');
    var size = Number(pager.getAttribute('data-page-size')) || 6;
    var current = 1;
    var total = Math.max(1, Math.ceil(items.length / size));

    /* Preserve container min-height to prevent layout shift */
    var grid = pager.querySelector('.home-editorial__topic-card-grid');
    var knownHeight = null;

    function measureMinHeight() {
      if (!grid) return;
      /* Show first page items to measure, others hidden */
      items.forEach(function (item, index) {
        item.hidden = index >= size;
      });
      var rect = grid.getBoundingClientRect();
      if (rect.height > 0) {
        knownHeight = rect.height;
        grid.style.minHeight = knownHeight + 'px';
      }
    }

    function render() {
      var isFirst = current === 1;
      var isLast = current === total;

      /* Fade out then swap then fade in */
      if (grid && !prefersReducedMotion) {
        grid.style.opacity = '0';
        grid.style.transition = 'opacity 0.15s ease';
      }

      window.setTimeout(function () {
        items.forEach(function (item, index) {
          item.hidden = index < (current - 1) * size || index >= current * size;
        });

        if (grid && !prefersReducedMotion) {
          grid.style.opacity = '1';
        }

        if (!nav || total <= 1) {
          if (nav) { nav.hidden = true; }
          return;
        }
        nav.hidden = false;
        updateNavUI(nav, current, total, isFirst, isLast);
      }, prefersReducedMotion ? 0 : 80);
    }

    function updateNavUI(nav, cur, tot, isFirst, isLast) {
      nav.innerHTML = '';

      var prevBtn = document.createElement('button');
      prevBtn.type = 'button';
      prevBtn.className = 'home-editorial__topic-pager-btn home-editorial__topic-pager-btn--prev';
      prevBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"></polyline></svg>';
      prevBtn.disabled = isFirst;
      prevBtn.setAttribute('aria-label', 'Trang trước');
      if (isFirst) { prevBtn.setAttribute('aria-disabled', 'true'); }

      var info = document.createElement('span');
      info.className = 'home-editorial__topic-pager-info';
      info.textContent = cur + '/' + tot;

      var nextBtn = document.createElement('button');
      nextBtn.type = 'button';
      nextBtn.className = 'home-editorial__topic-pager-btn home-editorial__topic-pager-btn--next';
      nextBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 18 15 12 9 6"></polyline></svg>';
      nextBtn.disabled = isLast;
      nextBtn.setAttribute('aria-label', 'Trang sau');
      if (isLast) { nextBtn.setAttribute('aria-disabled', 'true'); }

      prevBtn.addEventListener('click', function () {
        if (current > 1) { current -= 1; render(); }
      });
      nextBtn.addEventListener('click', function () {
        if (current < total) { current += 1; render(); }
      });

      nav.appendChild(prevBtn);
      nav.appendChild(info);
      nav.appendChild(nextBtn);
    }

    /* Init: measure height, render first page, hide nav if ≤1 page */
    measureMinHeight();
    render();
    if (nav && total <= 1) {
      nav.hidden = true;
    }
  });
})();
