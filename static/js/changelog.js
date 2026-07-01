(function () {
  "use strict";

  var list = document.querySelector("[data-changelog-list]");
  var pagination = document.querySelector("[data-changelog-pagination]");
  if (!list || !pagination) return;

  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function getPageSize() {
    var base = Number(list.dataset.pageSize) || 10;
    return window.innerWidth < 480 ? Math.min(base, 5) : base;
  }

  var items = Array.from(list.querySelectorAll("[data-changelog-item]"));
  if (items.length === 0) return;

  var previous = pagination.querySelector("[data-page-prev]");
  var next = pagination.querySelector("[data-page-next]");
  var status = pagination.querySelector("[data-page-status]");
  var numbers = pagination.querySelector("[data-page-numbers]");
  var currentPage = 1;

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function pageFromUrl() {
    var value = Number(new URL(window.location.href).searchParams.get("page"));
    return Number.isInteger(value) && value > 0 ? value : 1;
  }

  function setUrl(page) {
    var url = new URL(window.location.href);
    if (page === 1) url.searchParams.delete("page");
    else url.searchParams.set("page", String(page));
    history.replaceState(null, "", url);
  }

  function renderNumbers() {
    var total = Math.max(1, Math.ceil(items.length / getPageSize()));
    numbers.replaceChildren();
    var start = Math.max(1, currentPage - 2);
    var end = Math.min(total, currentPage + 2);
    for (var page = start; page <= end; page += 1) {
      var button = element("button", "changelog__page-number", String(page));
      button.type = "button";
      button.setAttribute("aria-label", "Trang " + page);
      if (page === currentPage) {
        button.classList.add("is-current");
        button.setAttribute("aria-current", "page");
      }
      button.addEventListener("click", function (p) {
        return function () { showPage(p, true); };
      }(page));
      numbers.appendChild(button);
    }
  }

  function showPage(requestedPage, scroll) {
    var pageSize = getPageSize();
    var total = Math.max(1, Math.ceil(items.length / pageSize));
    currentPage = Math.min(Math.max(1, requestedPage), total);
    var start = (currentPage - 1) * pageSize;

    items.forEach(function (item, index) {
      item.hidden = index < start || index >= start + pageSize;
    });

    previous.disabled = currentPage === 1;
    next.disabled = currentPage === total;
    status.textContent = "Trang " + currentPage + " / " + total + " · " + items.length + " cập nhật";
    renderNumbers();
    pagination.hidden = total <= 1;
    setUrl(currentPage);
    if (scroll) {
      var behavior = prefersReducedMotion ? "instant" : "smooth";
      list.scrollIntoView({ behavior: behavior, block: "start" });
    }
  }

  previous.addEventListener("click", function () { showPage(currentPage - 1, true); });
  next.addEventListener("click", function () { showPage(currentPage + 1, true); });
  window.addEventListener("popstate", function () { showPage(pageFromUrl(), false); });

  showPage(pageFromUrl(), false);
}());
