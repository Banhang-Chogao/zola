(function () {
  'use strict';

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

  document.querySelectorAll('[data-home-pager]').forEach(function (pager) {
    var items = Array.prototype.slice.call(pager.querySelectorAll('[data-page-item]'));
    var nav = pager.querySelector('[data-page-nav]');
    var size = Number(pager.getAttribute('data-page-size')) || 6;
    var current = 1;
    var total = Math.max(1, Math.ceil(items.length / size));

    function render() {
      items.forEach(function (item, index) {
        item.hidden = index < (current - 1) * size || index >= current * size;
      });
      if (!nav || total <= 1) {
        if (nav) nav.hidden = true;
        return;
      }
      nav.hidden = false;
      nav.innerHTML = '';
      var previous = document.createElement('button');
      previous.type = 'button';
      previous.textContent = '←';
      previous.disabled = current === 1;
      previous.setAttribute('aria-label', 'Trang trước');
      previous.addEventListener('click', function () { current -= 1; render(); });
      var status = document.createElement('span');
      status.textContent = 'Trang ' + current + '/' + total;
      var next = document.createElement('button');
      next.type = 'button';
      next.textContent = '→';
      next.disabled = current === total;
      next.setAttribute('aria-label', 'Trang sau');
      next.addEventListener('click', function () { current += 1; render(); });
      nav.appendChild(previous);
      nav.appendChild(status);
      nav.appendChild(next);
    }
    render();
  });
})();
