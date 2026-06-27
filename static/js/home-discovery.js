(function () {
  var root = document.querySelector("[data-home-discovery]");
  if (!root) return;
  var feed = root.querySelector("[data-home-feed]");
  var filterEmpty = root.querySelector("[data-filter-empty]");
  var searchForm = root.querySelector("[data-home-search-form]");
  var searchInput = root.querySelector("[data-home-search-input]");
  var searchResults = root.querySelector("[data-home-search-results]");
  var filterPanel = root.querySelector("[data-home-filter-panel]");
  var filterToggle = root.querySelector("[data-home-filter-toggle]");
  var searchDataEl = document.getElementById("site-search-data");
  var posts = [], searchIndex = [], activeCategory = "", activeQuick = "latest";
  function norm(v) { return String(v || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[đĐ]/g, "d").toLowerCase().replace(/[^a-z0-9\s:/._-]+/g, " ").replace(/\s+/g, " ").trim(); }
  function esc(v) { return String(v || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function cards() { return feed ? Array.prototype.slice.call(feed.querySelectorAll(".home-discovery__card")) : []; }
  function applyFilters() {
    var n = 0;
    cards().forEach(function (card) {
      var show = true, cat = card.getAttribute("data-category") || "", tags = (card.getAttribute("data-tags") || "").toLowerCase();
      if (activeCategory) {
        var cats = (card.getAttribute("data-categories") || cat || "").toLowerCase();
        if (activeCategory === "case-study") show = tags.indexOf("case") !== -1;
        else if (activeCategory === "Ngân hàng") show = cats.indexOf("ngân hàng") !== -1 || cats.indexOf("banking") !== -1 || cats.indexOf("bảo hiểm") !== -1;
        else if (activeCategory === "AI WebOps") show = tags.indexOf("webops") !== -1 || tags.indexOf("ai webops") !== -1 || cats.indexOf("ai webops") !== -1;
        else if (activeCategory === "Tài chính cá nhân") show = cats.indexOf("tài chính cá nhân") !== -1 || cats.indexOf("ngân hàng") !== -1 || tags.indexOf("fintech") !== -1 || tags.indexOf("tài chính") !== -1;
        else show = cats.indexOf(activeCategory.toLowerCase()) !== -1;
      }
      if (show && activeQuick === "featured") show = card.getAttribute("data-featured") === "true";
      if (show && activeQuick === "sticky") show = card.getAttribute("data-sticky") === "true";
      if (show && activeQuick === "series") show = !!card.getAttribute("data-series");
      if (show && activeQuick === "faq") show = card.getAttribute("data-faq") === "true";
      card.hidden = !show; if (show) n++;
    });
    if (filterEmpty) filterEmpty.hidden = n > 0;
  }
  try { posts = JSON.parse(searchDataEl ? searchDataEl.textContent : "[]"); } catch (e) { posts = []; }
  searchIndex = posts.map(function (p) { return { post: p, all: norm([p.title, p.category, p.tags, p.keyword, p.description, p.summary, p.body].join(" ")) }; });
  root.querySelectorAll("[data-filter-category]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      root.querySelectorAll("[data-filter-category]").forEach(function (el) { el.classList.toggle("is-active", el === btn); });
      activeCategory = btn.getAttribute("data-filter-category") || "";
      // Reset quick filter when clicking category (primary filter)
      activeQuick = "latest";
      root.querySelectorAll("[data-filter-quick]").forEach(function (el) { el.classList.toggle("is-active", el.getAttribute("data-filter-quick") === "latest"); });
      applyFilters();
    });
  });
  root.querySelectorAll("[data-filter-quick]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      root.querySelectorAll("[data-filter-quick]").forEach(function (el) { el.classList.toggle("is-active", el === btn); });
      activeQuick = btn.getAttribute("data-filter-quick") || "latest"; applyFilters();
    });
  });
  if (filterToggle && filterPanel) filterToggle.addEventListener("click", function () {
    var open = filterPanel.classList.toggle("is-open"); filterToggle.setAttribute("aria-expanded", open ? "true" : "false");
  });
  if (searchForm && searchInput) searchForm.addEventListener("submit", function (e) {
    e.preventDefault(); var q = searchInput.value.trim(); if (!q) return;
    var dlg = document.querySelector("[data-site-search]"), inp = dlg ? dlg.querySelector("[data-search-input]") : null, op = document.querySelector("[data-search-open]");
    if (dlg && inp && op) { inp.value = q; op.click(); return; }
    if (!searchResults) return;
    var terms = norm(q).split(/\s+/).filter(function (t) { return t.length >= 2; });
    if (!terms.length) { searchResults.hidden = true; searchResults.innerHTML = ""; return; }
    var hits = searchIndex.map(function (it) {
      var s = 0; terms.forEach(function (t) { if (it.all.indexOf(t) !== -1) s += 10; if (norm(it.post.title).indexOf(t) !== -1) s += 30; });
      return { post: it.post, score: s };
    }).filter(function (it) { return it.score > 0; }).sort(function (a, b) { return b.score - a.score; }).slice(0, 8);
    if (!hits.length) { searchResults.hidden = false; searchResults.innerHTML = '<p style="margin:0;font-size:.88rem;color:#6b7280;">Không tìm thấy bài phù hợp.</p>'; return; }
    searchResults.hidden = false;
    searchResults.innerHTML = hits.map(function (it) {
      return '<a class="home-discovery__search-hit" href="' + esc(it.post.url) + '"><strong>' + esc(it.post.title) + '</strong><span>' + esc(it.post.category || "Bài viết") + " · " + esc(it.post.date || "") + '</span></a>';
    }).join("");
  });
})();