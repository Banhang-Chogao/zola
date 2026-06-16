(function () {
  var dialog = document.querySelector("[data-site-search]");
  var openers = document.querySelectorAll("[data-search-open]");
  if (!dialog || !openers.length) return;

  var input = dialog.querySelector("[data-search-input]");
  var resultBox = dialog.querySelector("[data-local-search-results]");
  var searchDataEl = document.getElementById("site-search-data");
  var posts = [];
  var lastFocus = null;

  try {
    posts = JSON.parse(searchDataEl ? searchDataEl.textContent : "[]");
  } catch (e) {
    posts = [];
  }

  function syncGoogleInput() {
    input = dialog.querySelector("[data-search-input]") || input;
  }

  function normalize(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[đĐ]/g, "d")
      .toLowerCase()
      .trim();
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function compact(value, max) {
    var text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length <= max) return text;
    return text.slice(0, max - 1).trim() + "…";
  }

  function scorePost(post, terms) {
    var title = normalize(post.title);
    var keyword = normalize(post.keyword);
    var tags = normalize(post.tags);
    var desc = normalize(post.description + " " + post.summary);
    var body = normalize(post.body);
    var score = 0;

    terms.forEach(function (term) {
      if (!term) return;
      if (title === term) score += 80;
      if (title.indexOf(term) !== -1) score += 45;
      if (keyword.indexOf(term) !== -1) score += 35;
      if (tags.indexOf(term) !== -1) score += 28;
      if (desc.indexOf(term) !== -1) score += 18;
      if (body.indexOf(term) !== -1) score += 8;
    });

    return score;
  }

  function renderResults(query) {
    if (!resultBox) return;

    var normalized = normalize(query);
    var terms = normalized.split(/\s+/).filter(Boolean);
    if (!terms.length) {
      resultBox.innerHTML = '<p class="site-search__note">Nhập từ khóa để tìm trực tiếp trong bài viết của blog.</p>';
      return;
    }

    var results = posts
      .map(function (post) {
        return { post: post, score: scorePost(post, terms) };
      })
      .filter(function (item) { return item.score > 0; })
      .sort(function (a, b) {
        return b.score - a.score || String(b.post.date).localeCompare(String(a.post.date));
      })
      .slice(0, 8);

    if (!results.length) {
      resultBox.innerHTML =
        '<p class="site-search__note">Chưa thấy kết quả local. Bấm Google để tìm trong chỉ mục Google.</p>';
      return;
    }

    resultBox.innerHTML =
      '<div class="site-search__count">' + results.length + ' kết quả trong blog</div>' +
      '<ol class="site-search__results">' +
      results.map(function (item) {
        var post = item.post;
        var snippet = post.description || post.summary || post.body;
        return '' +
          '<li class="site-search__result">' +
            '<a class="site-search__result-title" href="' + escapeHtml(post.url) + '">' + escapeHtml(post.title) + '</a>' +
            '<div class="site-search__result-meta">' +
              escapeHtml(post.category || "Bài viết") + ' · ' + escapeHtml(post.date || "") +
            '</div>' +
            '<p class="site-search__result-snippet">' + escapeHtml(compact(snippet, 180)) + '</p>' +
          '</li>';
      }).join("") +
      '</ol>';
  }

  function openSearch() {
    lastFocus = document.activeElement;
    dialog.hidden = false;
    document.body.classList.add("search-open");
    window.setTimeout(function () {
      syncGoogleInput();
      if (input) input.focus();
      if (input && input.value) renderResults(input.value);
    }, 80);
  }

  function closeSearch() {
    dialog.hidden = true;
    document.body.classList.remove("search-open");
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  openers.forEach(function (btn) {
    btn.addEventListener("click", openSearch);
  });

  dialog.querySelectorAll("[data-search-close]").forEach(function (btn) {
    btn.addEventListener("click", closeSearch);
  });

  if (input) {
    input.addEventListener("input", function () {
      renderResults(input.value);
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !dialog.hidden) closeSearch();
  });
})();
