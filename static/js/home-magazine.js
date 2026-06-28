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
})();
