(function () {
  var dialog = document.querySelector("[data-site-search]");
  var openers = document.querySelectorAll("[data-search-open]");
  if (!dialog || !openers.length) return;

  var input = dialog.querySelector("[data-search-input]");
  var form = dialog.querySelector("[data-local-search-form]");
  var resultBox = dialog.querySelector("[data-local-search-results]");
  var posts = [];
  var index = [];
  var lastFocus = null;
  var dataLoaded = false;
  var dataLoading = false;

  // Search data is no longer inlined into every page (it used to embed the full
  // body of every post = ~2.5MB per page). It now lives at /search-index/
  // (templates/search-index.html) and is fetched lazily the first time the user
  // opens the search dialog, then cached in-memory for the rest of the session.
  function searchIndexUrl() {
    var meta = document.querySelector('meta[name="zola-base-url"]');
    var base = meta && meta.content ? meta.content.replace(/\/+$/, "") : "";
    return base + "/search-index/";
  }

  function ensureData() {
    if (dataLoaded || dataLoading) return;
    dataLoading = true;
    fetch(searchIndexUrl(), { credentials: "omit" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        posts = Array.isArray(data) ? data : [];
        buildIndex();
        dataLoaded = true;
        dataLoading = false;
        refresh();
      })
      .catch(function () {
        dataLoading = false;
        if (input && tokenize(input.value).length) renderError();
      });
  }

  function normalize(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[đĐ]/g, "d")
      .toLowerCase()
      .replace(/[^a-z0-9\s:/._-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function tokenize(value) {
    return normalize(value).split(/\s+/).filter(function (term) {
      return term.length >= 2;
    });
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

  function buildIndex() {
    index = posts.map(function (post, id) {
      var title = normalize(post.title);
      var url = normalize(post.url);
      var meta = normalize([
        post.category,
        post.tags,
        post.keyword,
        post.description,
        post.summary,
      ].join(" "));
      var body = normalize(post.body);
      return {
        id: id,
        post: post,
        title: title,
        url: url,
        meta: meta,
        body: body,
        all: [title, url, meta, body].join(" "),
      };
    });
  }

  function termCount(text, term) {
    if (!term) return 0;
    var count = 0;
    var pos = text.indexOf(term);
    while (pos !== -1) {
      count += 1;
      pos = text.indexOf(term, pos + term.length);
    }
    return count;
  }

  function scoreItem(item, terms, phrase) {
    var score = 0;
    var matchedTerms = 0;

    terms.forEach(function (term) {
      var termScore = 0;
      if (item.title === term) termScore += 120;
      if (item.title.indexOf(term) !== -1) termScore += 70 + termCount(item.title, term) * 8;
      if (item.url.indexOf(term) !== -1) termScore += 44;
      if (item.meta.indexOf(term) !== -1) termScore += 32 + termCount(item.meta, term) * 4;
      if (item.body.indexOf(term) !== -1) termScore += 12 + Math.min(termCount(item.body, term), 8);
      if (termScore > 0) matchedTerms += 1;
      score += termScore;
    });

    if (phrase && phrase.length > 2) {
      if (item.title.indexOf(phrase) !== -1) score += 90;
      if (item.meta.indexOf(phrase) !== -1) score += 46;
      if (item.body.indexOf(phrase) !== -1) score += 24;
    }

    return matchedTerms === terms.length ? score : 0;
  }

  function makeSnippet(post, terms) {
    var source = String(post.description || post.summary || post.body || "");
    var normalizedSource = normalize(source);
    var hit = -1;

    terms.some(function (term) {
      hit = normalizedSource.indexOf(term);
      return hit !== -1;
    });

    if (hit === -1) return compact(source, 190);

    var start = Math.max(0, hit - 72);
    var end = Math.min(source.length, start + 220);
    return (start > 0 ? "…" : "") + compact(source.slice(start, end), 210);
  }

  function renderEmpty() {
    if (!resultBox) return;
    resultBox.innerHTML =
      '<p class="site-search__note">Nhập từ khóa để tìm trực tiếp trong nội dung blog. Search chạy nội bộ, không dùng Google index.</p>';
  }

  function renderLoading() {
    if (!resultBox) return;
    resultBox.innerHTML =
      '<p class="site-search__note">Đang tải dữ liệu tìm kiếm…</p>';
  }

  function renderError() {
    if (!resultBox) return;
    resultBox.innerHTML =
      '<p class="site-search__note">Không tải được dữ liệu tìm kiếm. Kiểm tra kết nối rồi thử lại.</p>';
  }

  // Render the right state depending on whether the index has loaded yet.
  function refresh() {
    if (!dataLoaded) {
      if (input && tokenize(input.value).length) renderLoading();
      else renderEmpty();
      return;
    }
    if (input) renderResults(input.value);
    else renderEmpty();
  }

  function renderNoResults(query) {
    resultBox.innerHTML =
      '<div class="site-search__summary" role="status">' +
        '<div><span>Từ khóa</span><strong>' + escapeHtml(query) + '</strong></div>' +
        '<div><span>Tổng số kết quả</span><strong>0</strong></div>' +
        '<div><span>Số lượng link</span><strong>0</strong></div>' +
      '</div>' +
      '<p class="site-search__note">Không tìm thấy URL nào trong blog chứa từ khóa này.</p>';
  }

  function renderResults(query) {
    if (!resultBox) return;

    var terms = tokenize(query);
    if (!terms.length) {
      renderEmpty();
      return;
    }

    var phrase = normalize(query);
    var results = index
      .map(function (item) {
        return { post: item.post, score: scoreItem(item, terms, phrase) };
      })
      .filter(function (item) { return item.score > 0; })
      .sort(function (a, b) {
        return b.score - a.score || String(b.post.date).localeCompare(String(a.post.date));
      });

    if (!results.length) {
      renderNoResults(query);
      return;
    }

    var uniqueLinks = {};
    results.forEach(function (item) {
      uniqueLinks[item.post.url] = true;
    });
    var linkCount = Object.keys(uniqueLinks).length;

    resultBox.innerHTML =
      '<div class="site-search__summary" role="status">' +
        '<div><span>Từ khóa</span><strong>' + escapeHtml(query) + '</strong></div>' +
        '<div><span>Tổng số kết quả</span><strong>' + results.length + '</strong></div>' +
        '<div><span>Số lượng link</span><strong>' + linkCount + '</strong></div>' +
      '</div>' +
      '<div class="site-search__count">Danh sách URL chứa từ khóa</div>' +
      '<ol class="site-search__results">' +
      results.map(function (item) {
        var post = item.post;
        return '' +
          '<li class="site-search__result">' +
            '<a class="site-search__result-title" href="' + escapeHtml(post.url) + '">' + escapeHtml(post.title) + '</a>' +
            '<a class="site-search__result-url" href="' + escapeHtml(post.url) + '">' + escapeHtml(post.url) + '</a>' +
            '<div class="site-search__result-meta">' +
              escapeHtml(post.category || "Bài viết") + ' · ' + escapeHtml(post.date || "") +
            '</div>' +
            '<p class="site-search__result-snippet">' + escapeHtml(makeSnippet(post, terms)) + '</p>' +
          '</li>';
      }).join("") +
      '</ol>';
  }

  function openSearch() {
    lastFocus = document.activeElement;
    dialog.hidden = false;
    document.body.classList.add("search-open");
    ensureData();
    window.setTimeout(function () {
      if (input) input.focus();
      refresh();
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

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      ensureData();
      refresh();
    });
  }

  if (input) {
    input.addEventListener("input", function () {
      ensureData();
      refresh();
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !dialog.hidden) closeSearch();
  });
})();
