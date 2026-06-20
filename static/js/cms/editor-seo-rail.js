/* ============================================================================
   cms/editor-seo-rail.js — live SEO companion for /editor/ (CMS V2, section 5).

   Reads the existing editor form (title / slug / body / tags / category) and the
   page's #posts-metadata island. Renders an SEO checklist, canonical preview,
   content-quality badge, AI internal-link suggestions and keyword clusters.

   Strictly additive & read-only toward editor.js: it never calls editor.js
   functions. The only write it performs is appending a markdown link to the body
   textarea (on user click) and dispatching an 'input' event so the existing
   autosave/counter stay in sync.
   ============================================================================ */
(function () {
  "use strict";

  var app = document.getElementById("editor-app");
  var rail = document.querySelector("[data-seo-rail]");
  var form = app && app.querySelector("[data-form='post']");
  if (!app || !rail || !form) return;

  var BASE = "";
  var m = document.querySelector('meta[name="zola-base-url"]');
  if (m) BASE = (m.getAttribute("content") || "").replace(/\/$/, "");

  function $(s) { return rail.querySelector(s); }
  function fld(n) { return form.querySelector("[name='" + n + "']"); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var POSTS = [];
  try { POSTS = JSON.parse(document.getElementById("posts-metadata").textContent) || []; } catch (e) {}

  /* ---- Vietnamese-aware slugify (mirrors the usual blog slug rules) ---- */
  function slugify(s) {
    s = (s || "").toLowerCase();
    s = s.replace(/đ/g, "d");
    try { s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); } catch (e) {}
    return s.replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-").replace(/-+/g, "-");
  }

  var STOP = { "va": 1, "la": 1, "cua": 1, "cho": 1, "mot": 1, "cac": 1, "nhung": 1, "voi": 1, "tu": 1, "khi": 1, "the": 1, "the0": 1, "co": 1, "khong": 1, "nhu": 1, "de": 1, "trong": 1, "tai": 1 };

  function analyze() {
    var title = (fld("title").value || "").trim();
    var slug = (fld("slug").value || "").trim() || slugify(title);
    var body = (fld("body") ? fld("body").value : "") || "";
    var tags = (fld("tags") ? fld("tags").value : "") || "";
    var cat = fld("category") ? fld("category").value : "";

    var words = (body.trim().match(/\S+/g) || []).length;
    var h2 = (body.match(/^##\s+/gm) || []).length;
    var images = (body.match(/!\[[^\]]*\]\(/g) || []).length;
    var hasFaq = /(^|\n)#+\s*(faq|câu hỏi)/i.test(body) || /\bfaq\b/i.test(body);

    // links
    var linkRe = /\]\(([^)\s]+)/g, lm, internal = 0, external = 0;
    while ((lm = linkRe.exec(body))) {
      var u = lm[1];
      if (/^https?:\/\//i.test(u)) {
        if (BASE && u.indexOf(BASE) === 0) internal++; else external++;
      } else if (u.charAt(0) === "/" || u.charAt(0) === "#" && u.length > 1 || /^@\//.test(u) || /^\.\.?\//.test(u)) {
        internal++;
      }
    }

    var kw = title.split(/\s+/).slice(0, 3).join(" ").toLowerCase();
    var firstPara = body.split(/\n\n/)[0].toLowerCase();

    var checks = [
      { ok: title.length >= 20 && title.length <= 65, label: "Tiêu đề 20–65 ký tự (" + title.length + ")" },
      { ok: !!slug, label: "Có slug / URL" },
      { ok: words >= 800, label: "Độ dài ≥ 800 từ (" + words + ")" },
      { ok: h2 >= 2, label: "≥ 2 tiêu đề H2 (" + h2 + ")" },
      { ok: internal >= 3, label: "≥ 3 liên kết nội bộ (" + internal + ")" },
      { ok: external >= 1, label: "≥ 1 liên kết ngoài (" + external + ")" },
      { ok: hasFaq, label: "Có khối FAQ" },
      { ok: firstPara.indexOf(kw) !== -1 && kw.length > 0, label: "Từ khóa ở đoạn mở đầu" }
    ];
    var pass = checks.filter(function (c) { return c.ok; }).length;
    var score = Math.round((pass / checks.length) * 100);

    // render checks
    $("[data-esr-checks]").innerHTML = checks.map(function (c) {
      return '<li class="esr-check ' + (c.ok ? "is-pass" : "is-fail") + '">' + esc(c.label) + "</li>";
    }).join("");

    // badge
    var grade = score >= 90 ? "A+" : score >= 80 ? "A" : score >= 65 ? "B" : score >= 50 ? "C" : "D";
    var badge = $("[data-esr-badge]");
    badge.textContent = grade;
    badge.setAttribute("data-grade", grade);

    // canonical
    $("[data-esr-canonical]").textContent = (BASE || "") + "/" + (slug || "…") + "/";

    // quality cells
    $("[data-esr-words]").textContent = words;
    $("[data-esr-h2]").textContent = h2;
    $("[data-esr-int]").textContent = internal;

    renderSuggestions(title, cat, body);
    renderClusters(tags, cat);
  }

  function renderSuggestions(title, cat, body) {
    var box = $("[data-esr-suggest]");
    var titleWords = title.toLowerCase().split(/\s+/).filter(function (w) { return w.length > 3 && !STOP[w]; });
    var scored = POSTS.map(function (p) {
      if (!p.permalink || (body.indexOf(p.permalink) !== -1)) return null; // already linked
      var s = 0;
      var pt = (p.title || "").toLowerCase();
      titleWords.forEach(function (w) { if (pt.indexOf(w) !== -1) s += 2; });
      if (cat && p.category && p.category === cat) s += 3;
      return s > 0 ? { p: p, s: s } : null;
    }).filter(Boolean).sort(function (a, b) { return b.s - a.s; }).slice(0, 6);

    if (!scored.length) { box.innerHTML = '<span class="cms-muted">Chưa có gợi ý phù hợp.</span>'; return; }
    box.innerHTML = scored.map(function (x) {
      return '<button type="button" class="esr-chip" data-insert="' + esc(x.p.permalink) + '" data-title="' + esc(x.p.title) + '">+ ' + esc(trunc(x.p.title)) + "</button>";
    }).join("");
    Array.prototype.forEach.call(box.querySelectorAll("[data-insert]"), function (btn) {
      btn.addEventListener("click", function () {
        insertLink(btn.getAttribute("data-title"), btn.getAttribute("data-insert"));
        btn.disabled = true; btn.textContent = "✓ đã chèn";
      });
    });
  }

  function renderClusters(tags, cat) {
    var box = $("[data-esr-clusters]");
    var chips = [];
    if (cat) chips.push('<span class="esr-cluster esr-cluster--cat">' + esc(cat) + "</span>");
    (tags ? tags.split(",") : []).forEach(function (t) {
      t = t.trim(); if (t) chips.push('<span class="esr-cluster">' + esc(t) + "</span>");
    });
    // same-category siblings as a topic cluster hint
    var sib = POSTS.filter(function (p) { return cat && p.category === cat; }).slice(0, 4);
    box.innerHTML = (chips.length ? chips.join("") : '<span class="cms-muted">Thêm tag để tạo cụm.</span>') +
      (sib.length ? '<p class="esr-cluster-note">Cùng cụm: ' + sib.map(function (p) { return esc(trunc(p.title, 24)); }).join(" · ") + "</p>" : "");
  }

  function insertLink(title, url) {
    var body = fld("body");
    if (!body) return;
    var snippet = (body.value && !/\n$/.test(body.value) ? "\n\n" : "") + "[" + title + "](" + url + ")\n";
    body.value += snippet;
    body.dispatchEvent(new Event("input", { bubbles: true })); // keep editor.js counter/autosave in sync
    analyze();
  }

  function trunc(s, n) { s = String(s || ""); n = n || 40; return s.length > n ? s.slice(0, n - 1) + "…" : s; }

  /* ---- wire live updates ---- */
  ["title", "slug", "body", "tags"].forEach(function (n) {
    var f = fld(n); if (f) f.addEventListener("input", analyze);
  });
  var catF = fld("category"); if (catF) catF.addEventListener("change", analyze);

  // Re-run when the edit view is revealed / a post is loaded (editor.js toggles [hidden]).
  var editView = app.querySelector("[data-view='edit']");
  if (editView && window.MutationObserver) {
    new MutationObserver(function () { if (!editView.hidden) setTimeout(analyze, 30); })
      .observe(editView, { attributes: true, attributeFilter: ["hidden"] });
  }

  analyze();
})();
