(function () {
  "use strict";

  const list = document.querySelector("[data-changelog-list]");
  const pagination = document.querySelector("[data-changelog-pagination]");
  if (!list || !pagination) return;

  const pageSize = Number(list.dataset.pageSize) || 15;
  const items = Array.from(list.querySelectorAll("[data-changelog-item]"));
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const previous = pagination.querySelector("[data-page-prev]");
  const next = pagination.querySelector("[data-page-next]");
  const status = pagination.querySelector("[data-page-status]");
  const numbers = pagination.querySelector("[data-page-numbers]");
  let currentPage = 1;

  if (items.length === 0) return;

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
    numbers.replaceChildren();
    var start = Math.max(1, currentPage - 2);
    var end = Math.min(totalPages, currentPage + 2);
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
    currentPage = Math.min(Math.max(1, requestedPage), totalPages);
    var start = (currentPage - 1) * pageSize;

    items.forEach(function (item, index) {
      item.hidden = index < start || index >= start + pageSize;
    });

    previous.disabled = currentPage === 1;
    next.disabled = currentPage === totalPages;
    status.textContent = "Trang " + currentPage + " / " + totalPages + " · " + items.length + " cập nhật";
    renderNumbers();
    pagination.hidden = totalPages <= 1;
    setUrl(currentPage);
    if (scroll) list.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  previous.addEventListener("click", function () { showPage(currentPage - 1, true); });
  next.addEventListener("click", function () { showPage(currentPage + 1, true); });
  window.addEventListener("popstate", function () { showPage(pageFromUrl(), false); });

  showPage(pageFromUrl(), false);
}());
