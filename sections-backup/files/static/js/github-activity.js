/**
 * GitHub Activity heatmap — native tooltips on contribution cells (no API calls).
 */
(function () {
  'use strict';

  var root = document.querySelector('[data-widget="github-activity"]');
  if (!root) return;

  var cells = root.querySelectorAll('.gh-activity__cell[data-date]');
  cells.forEach(function (cell) {
    cell.setAttribute('role', 'img');
    var count = cell.getAttribute('data-count') || '0';
    var date = cell.getAttribute('data-date') || '';
    var label = count + ' contribution' + (count === '1' ? '' : 's') + ' on ' + date;
    cell.setAttribute('aria-label', label);
  });
})();