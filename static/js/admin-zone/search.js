/**
 * Search functionality for Operation Guidelines
 */

(function () {
  window.AdminZoneSearch = window.AdminZoneSearch || {};

  const searchInput = document.getElementById("guideline-search");
  const resultsContainer = document.getElementById("search-results");
  const emptyContainer = document.getElementById("search-empty");

  if (!searchInput) return;

  function renderResults(results) {
    const list = resultsContainer.querySelector(".admin-search-results__list");
    if (!list) return;

    list.innerHTML = "";

    if (results.length === 0) {
      resultsContainer.hidden = true;
      emptyContainer.hidden = false;
      return;
    }

    results.forEach(g => {
      const item = document.createElement("div");
      item.className = "admin-search-result-item";
      item.innerHTML = `
        <div class="admin-search-result-item__header">
          <strong class="admin-search-result-item__code">${sanitize(g.code)}</strong>
          <h3 class="admin-search-result-item__name">${sanitize(g.name)}</h3>
        </div>
        <p class="admin-search-result-item__purpose">${sanitize(g.purpose)}</p>
        <p class="admin-search-result-item__template">
          <strong>Tiêu biểu:</strong> ${sanitize(g.template)}
        </p>
      `;
      list.appendChild(item);
    });

    resultsContainer.hidden = false;
    emptyContainer.hidden = true;
  }

  function sanitize(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function handleSearch() {
    const query = searchInput.value || "";
    const results = window.AdminZoneData.searchGuidelines(query);
    renderResults(results);
  }

  function clearSearch() {
    searchInput.value = "";
    resultsContainer.hidden = true;
    emptyContainer.hidden = true;
    searchInput.focus();
  }

  // Event listeners
  searchInput.addEventListener("input", handleSearch);
  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch();
    }
  });

  const clearBtn = document.querySelector("[data-action='search-clear']");
  if (clearBtn) {
    clearBtn.addEventListener("click", clearSearch);
  }

  Object.assign(window.AdminZoneSearch, {
    search: handleSearch,
    clear: clearSearch,
  });
})();
