/* Bảng Vàng SEO — sắp xếp client-side + đánh số thứ hạng.
   Dữ liệu render sẵn từ data/seo-qa-scores.json; JS chỉ sắp xếp lại tbody
   và cập nhật cột #. Mặc định: điểm cao → thấp. */
(function () {
  "use strict";

  var table = document.querySelector("[data-seo-table]");
  var tbody = document.querySelector("[data-seo-tbody]");
  var sortSel = document.querySelector("[data-seo-sort]");
  if (!table || !tbody) return;

  function rows() {
    return Array.prototype.slice.call(tbody.querySelectorAll("tr"));
  }

  function renumber() {
    rows().forEach(function (tr, i) {
      var cell = tr.querySelector(".seo-board__td--rank");
      if (cell) cell.textContent = i + 1;
    });
  }

  function sortBy(mode) {
    var sorted = rows().sort(function (a, b) {
      switch (mode) {
        case "score-asc":
          return parseFloat(a.dataset.score) - parseFloat(b.dataset.score);
        case "title-asc":
          return (a.dataset.title || "").localeCompare(b.dataset.title || "", "vi");
        case "score-desc":
        default:
          return parseFloat(b.dataset.score) - parseFloat(a.dataset.score);
      }
    });
    sorted.forEach(function (tr) { tbody.appendChild(tr); });
    renumber();
  }

  if (sortSel) {
    sortSel.addEventListener("change", function () { sortBy(sortSel.value); });
  }

  // Sắp xếp mặc định khi tải trang.
  sortBy(sortSel ? sortSel.value : "score-desc");
})();
