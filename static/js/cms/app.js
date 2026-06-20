/* ============================================================================
   cms/app.js — CMS V2 Control Center logic (vanilla, no deps).

   Drives the single-page shell: hash routing, the persistent sidebar, and all
   six modules. Uses REAL baked data (#cms-nodes / #cms-edges / #cms-seo /
   #cms-404) + REAL runtime KPIs (static/data/*.json). AI Writer uses a local
   mock generator (no backend) — human approval is always required.

   Everything is defensive: a missing data source degrades to a calm placeholder,
   never an error. No destructive action happens here — publishing always hands
   off to the existing authenticated /editor/.
   ============================================================================ */
(function () {
  "use strict";

  var shell = document.getElementById("cms-shell");
  if (!shell) return;
  var BASE = (shell.dataset.cmsBase || "").replace(/\/$/, "");

  /* ---------- tiny helpers ---------- */
  function $(s, p) { return (p || document).querySelector(s); }
  function $$(s, p) { return Array.prototype.slice.call((p || document).querySelectorAll(s)); }
  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function readJSON(id, fallback) {
    var n = document.getElementById(id);
    if (!n) return fallback;
    try { return JSON.parse(n.textContent || "null") || fallback; }
    catch (e) { return fallback; }
  }
  function fmtNum(n) {
    if (n == null || isNaN(n)) return "—";
    return Number(n).toLocaleString("vi-VN");
  }
  function slugFromUrl(u) {
    return String(u || "").replace(/\/+$/, "").split("/").pop();
  }

  /* ---------- data ---------- */
  var NODES = readJSON("cms-nodes", []);
  var EDGES_RAW = readJSON("cms-edges", []);
  var SEO = readJSON("cms-seo", {});
  var REPORT404 = readJSON("cms-404", { broken: 0, status: "ok" });

  // Per-panel renderers (populated below). Declared here so strict mode is happy.
  var RENDER = {};

  // Index nodes by slug; build degree maps from edges that connect known nodes.
  var bySlug = {};
  NODES.forEach(function (n) { bySlug[n.slug] = n; n.inDeg = 0; n.outDeg = 0; });
  var EDGES = [];
  EDGES_RAW.forEach(function (e) {
    if (bySlug[e.s] && bySlug[e.t] && e.s !== e.t) {
      EDGES.push(e);
      bySlug[e.s].outDeg++;
      bySlug[e.t].inDeg++;
    }
  });

  /* ============================================================
     ROUTER + SIDEBAR
     ============================================================ */
  var PANELS = ["insights", "posts", "ai-writer", "links", "alerts", "settings"];
  var rendered = {};

  function activate(name) {
    if (PANELS.indexOf(name) === -1) name = "insights";
    $$("[data-cms-panel]").forEach(function (p) {
      var on = p.getAttribute("data-cms-panel") === name;
      p.hidden = !on;
      p.classList.toggle("is-active", on);
    });
    $$("[data-cms-link]").forEach(function (a) {
      a.classList.toggle("is-active", a.getAttribute("data-cms-link") === name);
    });
    if (!rendered[name] && RENDER[name]) { try { RENDER[name](); } catch (e) {} rendered[name] = true; }
    if (window.innerWidth <= 960) shell.classList.remove("is-navopen");
  }

  function routeFromHash() {
    var h = (location.hash || "").replace(/^#/, "");
    activate(h || "insights");
  }
  window.addEventListener("hashchange", routeFromHash);

  // Nav toggle: off-canvas on mobile, collapse-to-icons on desktop.
  var burger = $("[data-cms-nav-toggle]");
  if (burger) {
    burger.addEventListener("click", function () {
      if (window.innerWidth <= 960) {
        shell.classList.toggle("is-navopen");
        burger.setAttribute("aria-expanded", shell.classList.contains("is-navopen"));
      } else {
        shell.classList.toggle("is-collapsed");
        burger.setAttribute("aria-expanded", !shell.classList.contains("is-collapsed"));
      }
    });
  }
  shell.addEventListener("click", function (e) {
    // tap the backdrop (::after) area closes mobile nav
    if (window.innerWidth <= 960 && shell.classList.contains("is-navopen") && e.target === shell) {
      shell.classList.remove("is-navopen");
    }
  });

  /* ---------- topbar: clock + auth chip ---------- */
  function tickClock() {
    var n = $("[data-cms-clock]");
    if (!n) return;
    try {
      n.textContent = new Date().toLocaleString("vi-VN", {
        timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit",
        day: "2-digit", month: "2-digit", year: "numeric"
      });
    } catch (e) {}
  }
  tickClock(); setInterval(tickClock, 30000);

  (function authChip() {
    var chip = $("[data-cms-auth]");
    if (!chip) return;
    var sid = null;
    try { sid = localStorage.getItem("zola-cms-session-id") || sessionStorage.getItem("zola-cms-session-id"); } catch (e) {}
    if (sid) {
      chip.classList.add("is-auth");
      $(".cms-authchip__text", chip).textContent = "Phiên CMS";
    } else {
      $(".cms-authchip__text", chip).textContent = "Khách";
    }
  })();

  /* ============================================================
     INSIGHTS
     ============================================================ */
  function setKpi(key, value, note, status) {
    var card = $('[data-kpi="' + key + '"]');
    if (!card) return;
    $("[data-kpi-value]", card).innerHTML = value;
    $("[data-kpi-note]", card).textContent = note || "";
    card.setAttribute("data-status", status || "neutral");
  }

  function computeContentDecay() {
    // Proxy: share of published posts older than 180 days without a top SEO grade.
    var now = Date.now(), DAY = 86400000, total = 0, stale = 0;
    NODES.forEach(function (n) {
      var rec = SEO[n.slug];
      if (rec && rec.published === false) return;
      total++;
      var age = (now - new Date(n.date).getTime()) / DAY;
      var weak = rec ? rec.score < 80 : true;
      if (age > 180 && weak) stale++;
    });
    if (!total) return null;
    return Math.round((1 - stale / total) * 100); // higher = fresher
  }

  function computeLinkStrength() {
    if (!NODES.length) return null;
    var linked = NODES.filter(function (n) { return n.inDeg > 0; }).length;
    return Math.round((linked / NODES.length) * 100);
  }

  RENDER.insights = function () {
    // Decay + link strength come from baked data (always available).
    var decay = computeContentDecay();
    if (decay != null) {
      setKpi("decay", decay + "<small>/100</small>",
        decay >= 75 ? "Nội dung còn tươi" : "Một số bài cần làm mới",
        decay >= 75 ? "good" : (decay >= 55 ? "optimize" : "risk"));
    } else { setKpi("decay", "—", "Chưa đủ dữ liệu", "neutral"); }

    var ls = computeLinkStrength();
    if (ls != null) {
      var orphans = NODES.length - NODES.filter(function (n) { return n.inDeg > 0; }).length;
      setKpi("linkstrength", ls + "<small>%</small>",
        orphans + " bài mồ côi · " + EDGES.length + " liên kết",
        ls >= 80 ? "good" : (ls >= 60 ? "optimize" : "risk"));
    } else { setKpi("linkstrength", "—", "Chưa có dữ liệu liên kết", "neutral"); }

    // Live KPIs from static/data (best-effort).
    fetchJSON(BASE + "/data/gsc-metrics.json").then(function (g) {
      if (g && g.connected) {
        setKpi("ctr", (g.ctr != null ? (g.ctr * 100).toFixed(1) : "—") + "<small>%</small>", "28 ngày qua", "good");
        setKpi("impressions", fmtNum(g.impressions), "28 ngày qua", "good");
        setKpi("position", g.avg_position != null ? Number(g.avg_position).toFixed(1) : "—", "vị trí TB", g.avg_position <= 10 ? "good" : "optimize");
      } else {
        setKpi("ctr", "—", "Chưa kết nối GSC", "neutral");
        setKpi("impressions", "—", "Chưa kết nối GSC", "neutral");
        setKpi("position", "—", "Chưa kết nối GSC", "neutral");
      }
      renderGsc(g);
    });

    fetchJSON(BASE + "/data/google-rank.json").then(renderHealth);
  };

  function renderHealth(rank) {
    var scoreEl = $("[data-health-score]"), barsEl = $("[data-health-bars]");
    if (!rank || !scoreEl) { return; }
    scoreEl.textContent = rank.score != null ? Math.round(rank.score) : "—";
    var labels = {
      seo_audit: "SEO audit", compliance: "Compliance", lighthouse_seo: "Lighthouse",
      content_volume: "Khối lượng", category_diversity: "Đa dạng mục", topical_authority: "Authority chủ đề",
      schema_coverage: "Schema", internal_links: "Liên kết nội bộ"
    };
    var comp = rank.components || {};
    barsEl.innerHTML = "";
    Object.keys(comp).forEach(function (k) {
      var v = Math.round(comp[k]);
      var row = el("li", "cms-health__row",
        '<span>' + esc(labels[k] || k) + '</span>' +
        '<span class="cms-health__track"><span class="cms-health__fill" style="width:' + Math.min(100, v) + '%"></span></span>' +
        '<span class="cms-health__val">' + v + '</span>');
      barsEl.appendChild(row);
    });
  }

  function renderGsc(g) {
    var box = $("[data-cms-gsc]");
    if (!box) return;
    if (g && g.connected) {
      box.innerHTML =
        row("Trạng thái", "✓ Đã kết nối") +
        row("Trang đã index", fmtNum(g.indexed_pages)) +
        row("Clicks (28d)", fmtNum(g.clicks)) +
        row("Sitemap", esc(g.sitemap_status || "—"));
    } else {
      box.innerHTML =
        '<p class="cms-muted">Google Search Console <strong>chưa kết nối</strong>. Các chỉ số CTR / Impressions / vị trí sẽ tự xuất hiện khi kết nối — đây không phải lỗi.</p>' +
        row("Trang sitemap", "223") + row("Technical SEO", "91/100 · A+");
    }
    function row(k, v) {
      return '<div class="cms-gsc__row"><span>' + esc(k) + '</span><strong>' + v + '</strong></div>';
    }
  }

  function fetchJSON(url) {
    return fetch(url, { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  /* ============================================================
     POSTS
     ============================================================ */
  function scoreClass(s) { return s >= 80 ? "is-good" : (s >= 60 ? "is-mid" : "is-low"); }

  RENDER.posts = function () {
    var listEl = $("[data-cms-postlist]"), searchEl = $("[data-cms-post-search]"),
        sortEl = $("[data-cms-post-sort]"), countEl = $("[data-cms-post-count]");

    function draw() {
      var q = (searchEl.value || "").toLowerCase().trim();
      var items = NODES.filter(function (n) {
        if (!q) return true;
        return (n.title + " " + n.slug + " " + n.cat).toLowerCase().indexOf(q) !== -1;
      });
      var sort = sortEl.value;
      items.sort(function (a, b) {
        var sa = (SEO[a.slug] || {}).score || 0, sb = (SEO[b.slug] || {}).score || 0;
        if (sort === "score") return sb - sa;
        if (sort === "score-asc") return sa - sb;
        if (sort === "title") return a.title.localeCompare(b.title, "vi");
        return new Date(b.date) - new Date(a.date);
      });
      countEl.textContent = items.length + "/" + NODES.length;
      if (!items.length) { listEl.innerHTML = '<p class="cms-muted">Không có bài khớp.</p>'; return; }
      listEl.innerHTML = items.slice(0, 200).map(function (n) {
        var rec = SEO[n.slug] || {};
        var sc = rec.score != null ? Math.round(rec.score) : null;
        var scHtml = sc != null
          ? '<span class="cms-postrow__score ' + scoreClass(sc) + '" title="Điểm SEO">' + sc + '</span>'
          : '<span class="cms-postrow__score" title="Chưa chấm">–</span>';
        var d = "";
        try { d = new Date(n.date).toLocaleDateString("vi-VN"); } catch (e) {}
        return '<div class="cms-postrow">' +
          '<div class="cms-postrow__main">' +
            '<a class="cms-postrow__title" href="' + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.title) + '</a>' +
            '<div class="cms-postrow__meta"><span>' + esc(n.cat) + '</span><span>·</span><span>' + d + '</span>' +
              (rec.words ? '<span>·</span><span>' + fmtNum(rec.words) + ' từ</span>' : '') + '</div>' +
          '</div>' +
          scHtml +
          '<a class="cms-postrow__edit" href="' + BASE + '/editor/" title="Sửa trong trình soạn thảo">✎ Sửa</a>' +
        '</div>';
      }).join("");
    }
    searchEl.addEventListener("input", draw);
    sortEl.addEventListener("change", draw);
    draw();
  };

  /* ============================================================
     AI WRITER (mock generator · human-gated)
     ============================================================ */
  RENDER["ai-writer"] = function () {
    var pillar = "ai", mode = "idea";
    bindSeg("[data-aiw-pillar]", function (v) { pillar = v; });
    bindSeg("[data-aiw-mode]", function (v) { mode = v; });

    var promptEl = $("[data-aiw-prompt]"), kwEl = $("[data-aiw-keyword]"),
        previewEl = $("[data-aiw-preview]"), outEl = $("[data-aiw-output]"),
        spin = $("[data-aiw-spin]"), genBtn = $("[data-aiw-generate]");

    function bindSeg(sel, cb) {
      var grp = $(sel);
      if (!grp) return;
      $$(".cms-seg__btn", grp).forEach(function (b) {
        b.addEventListener("click", function () {
          $$(".cms-seg__btn", grp).forEach(function (x) { x.classList.remove("is-active"); x.setAttribute("aria-checked", "false"); });
          b.classList.add("is-active"); b.setAttribute("aria-checked", "true");
          cb(b.getAttribute("data-val"));
        });
      });
    }

    $("[data-aiw-reset]").addEventListener("click", function () {
      promptEl.value = ""; kwEl.value = ""; previewEl.hidden = true;
    });

    genBtn.addEventListener("click", function () {
      var topic = (promptEl.value || "").trim();
      if (!topic) { promptEl.focus(); return; }
      spin.hidden = false; genBtn.disabled = true;
      // Mock "AI" latency, then build a template draft from the inputs.
      setTimeout(function () {
        var kw = (kwEl.value || "").trim() || topic;
        var md = mockDraft(pillar, mode, topic, kw);
        outEl.value = md;
        $("[data-aiw-out-pillar]").textContent = "Pillar: " + pillar.toUpperCase();
        $("[data-aiw-out-mode]").textContent = "Mode: " + mode;
        updateGate();
        previewEl.hidden = false;
        spin.hidden = true; genBtn.disabled = false;
        previewEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 480);
    });

    outEl.addEventListener("input", updateGate);

    function updateGate() {
      var md = outEl.value, kw = ((kwEl.value || "").trim() || (promptEl.value || "").trim()).toLowerCase();
      var words = (md.trim().match(/\S+/g) || []).length;
      var h2 = (md.match(/^##\s+/gm) || []).length;
      var links = (md.match(/\]\(/g) || []).length;
      var hasFaq = /faq|câu hỏi/i.test(md);
      var hasKwTitle = md.split("\n")[0].toLowerCase().indexOf(kw) !== -1;
      var checks = [
        { ok: words >= (mode === "idea" ? 120 : (mode === "draft" ? 600 : 1200)), label: "Độ dài đạt chuẩn (" + words + " từ)" },
        { ok: h2 >= 2, label: "≥ 2 tiêu đề H2 (" + h2 + ")" },
        { ok: links >= 3, label: "≥ 3 liên kết (" + links + ")" },
        { ok: hasKwTitle, label: "Từ khóa trong tiêu đề" },
        { ok: hasFaq, label: "Có khối FAQ" }
      ];
      var passed = checks.filter(function (c) { return c.ok; }).length;
      var score = Math.round((passed / checks.length) * 100);
      $("[data-aiw-words]").textContent = words + " từ";
      $("[data-aiw-score]").textContent = score;
      var g = $("[data-aiw-gauge]");
      g.setAttribute("pathLength", "100");
      g.setAttribute("stroke-dasharray", score + " 100");
      g.style.stroke = score >= 80 ? "var(--cms-ok)" : (score >= 60 ? "var(--cms-warn)" : "var(--cms-risk)");
      $("[data-aiw-checks]").innerHTML = checks.map(function (c) {
        return '<li class="cms-gate__check ' + (c.ok ? "is-pass" : "is-fail") + '">' + esc(c.label) + '</li>';
      }).join("");
      previewEl.dataset.score = score;
    }

    $("[data-aiw-copy]").addEventListener("click", function () {
      copyText(outEl.value, $("[data-aiw-copy]"), "⧉ Copy markdown");
    });

    $("[data-aiw-approve]").addEventListener("click", function () {
      var score = Number(previewEl.dataset.score || 0);
      var note = $("[data-aiw-decide-note]");
      try { localStorage.setItem("cms-aiw-approved-draft", outEl.value); } catch (e) {}
      copyText(outEl.value, null, null);
      note.hidden = false;
      if (score < 60) {
        note.classList.add("is-warn");
        note.innerHTML = "⚠ Điểm cổng chất lượng thấp (" + score + "/100). Đã copy nháp + mở Editor — hãy bổ sung trước khi xuất bản.";
      } else {
        note.classList.remove("is-warn");
        note.innerHTML = "✓ Đã duyệt (điểm " + score + "/100). Nháp đã được copy — mở Editor để hoàn thiện &amp; xuất bản.";
      }
      window.open(BASE + "/editor/", "_blank", "noopener");
    });

    $("[data-aiw-reject]").addEventListener("click", function () {
      previewEl.hidden = true;
      var note = $("[data-aiw-decide-note]"); note.hidden = true;
      outEl.value = "";
    });
  };

  function mockDraft(pillar, mode, topic, kw) {
    var pillarName = { ai: "AI & Công nghệ", travel: "Du lịch", life: "Đời sống" }[pillar] || pillar;
    var title = topic.charAt(0).toUpperCase() + topic.slice(1);
    var hubs = { ai: "/categories/cong-nghe/", travel: "/categories/du-lich/", life: "/categories/tat-ca/" };
    var hub = BASE + (hubs[pillar] || "/categories/tat-ca/");
    var rel = NODES.slice(0, 3);

    if (mode === "idea") {
      return "# " + title + "\n\n" +
        "_Pillar: " + pillarName + " · ý tưởng nháp (cần con người phát triển)._\n\n" +
        "## Góc tiếp cận đề xuất\n" +
        "- Search intent: thông tin (informational)\n" +
        "- Từ khóa chính: **" + kw + "**\n" +
        "- 3 ý chính cần triển khai cho \"" + esc(topic) + "\"\n\n" +
        "## Dàn ý\n" +
        "1. Mở đầu trả lời nhanh câu hỏi chính\n2. Phân tích / so sánh\n3. Hướng dẫn từng bước\n\n" +
        "## Liên kết gợi ý\n" +
        "- [Chuyên mục " + pillarName + "](" + hub + ")\n" +
        rel.map(function (n) { return "- [" + n.title + "](" + n.url + ")"; }).join("\n") + "\n";
    }

    var intro = "Bài viết này tổng hợp về **" + esc(topic) + "** dưới góc nhìn " + pillarName +
      ". Mình đi thẳng vào trọng tâm để bạn nắm nhanh, sau đó đào sâu từng phần.\n\n";
    var body = "## " + title + " là gì?\n\n" +
      "Theo tìm hiểu của mình, " + esc(kw) + " là chủ đề đáng quan tâm. " +
      "Dưới đây là những điểm cốt lõi.\n\n" +
      "## Vì sao quan trọng\n\n- Lý do 1\n- Lý do 2\n- Lý do 3\n\n" +
      "## Hướng dẫn thực tế\n\n1. Bước một\n2. Bước hai\n3. Bước ba\n\n";
    var links = "## Đọc thêm\n\n- [Chuyên mục " + pillarName + "](" + hub + ")\n" +
      rel.map(function (n) { return "- [" + n.title + "](" + n.url + ")"; }).join("\n") + "\n\n";
    var faq = "## FAQ\n\n**" + esc(topic) + " có khó không?**\nKhông — nếu làm theo các bước trên.\n\n" +
      "**Mình nên bắt đầu từ đâu?**\nBắt đầu từ phần hướng dẫn thực tế ở trên.\n\n";
    var cta = "## Bước tiếp theo\n\nNếu thấy hữu ích, hãy xem thêm [chuyên mục " + pillarName + "](" + hub + ").\n";

    if (mode === "draft") return "# " + title + "\n\n" + intro + body + links + faq;
    // full
    return "# " + title + "\n\n" + intro + body +
      "## Phân tích chuyên sâu\n\nPhần này mở rộng bối cảnh, dữ liệu và ví dụ thực tế cho **" + esc(kw) + "**. " +
      "Hãy thay nội dung mẫu bằng trải nghiệm/nghiên cứu thật trước khi xuất bản.\n\n" +
      links + faq + cta;
  }

  function copyText(text, btn, original) {
    function done() { if (btn) { var t = btn.textContent; btn.textContent = "✓ Đã copy"; setTimeout(function () { btn.textContent = original || t; }, 1500); } }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(fallback);
    } else { fallback(); }
    function fallback() {
      try {
        var ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta);
        ta.select(); document.execCommand("copy"); document.body.removeChild(ta); done();
      } catch (e) {}
    }
  }

  /* ============================================================
     INTERNAL LINK GRAPH
     ============================================================ */
  RENDER.links = function () {
    // Display top N nodes by total degree for readability.
    var disp = NODES.slice().sort(function (a, b) {
      return (b.inDeg + b.outDeg) - (a.inDeg + a.outDeg);
    }).slice(0, 56);
    var dispSet = {};
    disp.forEach(function (n) { dispSet[n.slug] = n; });

    var W = 800, H = 520, cx = W / 2, cy = H / 2;
    // Ring layout: higher inbound degree = closer to center (more authority).
    var maxIn = disp.reduce(function (m, n) { return Math.max(m, n.inDeg); }, 0) || 1;
    disp.forEach(function (n, i) {
      var auth = n.inDeg / maxIn;            // 0..1
      var radius = 60 + (1 - auth) * 200;     // center = high authority
      var ang = (i / disp.length) * Math.PI * 2 + (n.inDeg * 0.6);
      n.x = cx + radius * Math.cos(ang);
      n.y = cy + radius * Math.sin(ang);
      n.r = 4 + Math.min(11, n.inDeg * 1.6);
    });

    var orphans = disp.filter(function (n) { return n.inDeg === 0; });
    var weak = disp.filter(function (n) { return n.inDeg > 0 && n.inDeg <= 1; });

    var edgesG = $("[data-graph-edges]"), nodesG = $("[data-graph-nodes]");
    var SVGNS = "http://www.w3.org/2000/svg";
    edgesG.innerHTML = ""; nodesG.innerHTML = "";

    EDGES.forEach(function (e) {
      var a = dispSet[e.s], b = dispSet[e.t];
      if (!a || !b) return;
      var ln = document.createElementNS(SVGNS, "line");
      ln.setAttribute("x1", a.x.toFixed(1)); ln.setAttribute("y1", a.y.toFixed(1));
      ln.setAttribute("x2", b.x.toFixed(1)); ln.setAttribute("y2", b.y.toFixed(1));
      ln.setAttribute("class", "cms-graph__edge");
      edgesG.appendChild(ln);
    });

    var showOrphan = $("[data-graph-orphans]"), showWeak = $("[data-graph-weak]");
    var tip = $("[data-graph-tip]");
    disp.forEach(function (n) {
      var c = document.createElementNS(SVGNS, "circle");
      c.setAttribute("cx", n.x.toFixed(1)); c.setAttribute("cy", n.y.toFixed(1));
      c.setAttribute("r", n.r.toFixed(1));
      var cls = "cms-graph__node";
      if (n.inDeg === 0) n._kind = "orphan"; else if (n.inDeg <= 1) n._kind = "weak"; else n._kind = "ok";
      c.setAttribute("class", cls);
      c._node = n;
      c.addEventListener("mouseenter", function () {
        tip.hidden = false;
        tip.innerHTML = esc(n.title) + "<br>← " + n.inDeg + " trỏ đến · → " + n.outDeg + " trỏ đi";
        tip.style.left = Math.min(W - 160, n.x + 10) + "px";
        tip.style.top = (n.y + 10) + "px";
      });
      c.addEventListener("mouseleave", function () { tip.hidden = true; });
      c.addEventListener("click", function () { window.open(n.url, "_blank", "noopener"); });
      nodesG.appendChild(c);
      n._circle = c;
    });

    function paint() {
      var so = showOrphan.checked, sw = showWeak.checked;
      disp.forEach(function (n) {
        var c = n._circle; if (!c) return;
        c.classList.remove("is-orphan", "is-weak");
        if (n._kind === "orphan" && so) c.classList.add("is-orphan");
        else if (n._kind === "weak" && sw) c.classList.add("is-weak");
      });
    }
    showOrphan.addEventListener("change", paint);
    showWeak.addEventListener("change", paint);
    paint();

    // Stats + lists
    $('[data-gs="nodes"]').textContent = NODES.length;
    $('[data-gs="edges"]').textContent = EDGES.length;
    $('[data-gs="orphans"]').textContent = NODES.filter(function (n) { return n.inDeg === 0; }).length;
    setBadge("[data-cms-alert-count]"); // updated later via alerts too

    fillList("[data-graph-orphan-list]", NODES.filter(function (n) { return n.inDeg === 0; }), "Không có node mồ côi 🎉");
    fillList("[data-graph-weak-list]", NODES.filter(function (n) { return n.inDeg > 0 && n.inDeg <= 1; }), "Không có authority yếu");
    // AI suggestion: same-category posts not yet linked together (sample).
    var sugg = suggestLinks();
    var sl = $("[data-graph-suggest-list]");
    sl.innerHTML = sugg.length
      ? sugg.map(function (s) { return '<li><a href="' + esc(s.from.url) + '" target="_blank" rel="noopener">' + esc(trunc(s.from.title)) + '</a> → <a href="' + esc(s.to.url) + '" target="_blank" rel="noopener">' + esc(trunc(s.to.title)) + '</a></li>'; }).join("")
      : '<li class="cms-muted">Không có gợi ý nổi bật</li>';

    function fillList(sel, arr, empty) {
      var n = $(sel);
      n.innerHTML = arr.length
        ? arr.slice(0, 30).map(function (p) { return '<li><a href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(trunc(p.title)) + '</a></li>'; }).join("")
        : '<li class="cms-muted">' + esc(empty) + '</li>';
    }
  };

  function trunc(s) { s = String(s || ""); return s.length > 42 ? s.slice(0, 41) + "…" : s; }

  function suggestLinks() {
    var linkSet = {};
    EDGES.forEach(function (e) { linkSet[e.s + ">" + e.t] = 1; });
    var byCat = {};
    NODES.forEach(function (n) { (byCat[n.cat] = byCat[n.cat] || []).push(n); });
    var out = [];
    Object.keys(byCat).forEach(function (cat) {
      var arr = byCat[cat];
      for (var i = 0; i < arr.length && out.length < 8; i++) {
        for (var j = 0; j < arr.length; j++) {
          if (i === j) continue;
          var from = arr[i], to = arr[j];
          if (to.inDeg === 0 && !linkSet[from.slug + ">" + to.slug]) {
            out.push({ from: from, to: to });
            break;
          }
        }
      }
    });
    return out.slice(0, 6);
  }

  function setBadge(sel) {} // placeholder; alert count is owned by alerts module

  /* ============================================================
     SEO ALERTS
     ============================================================ */
  function buildAlerts(gsc) {
    var a = [];
    var orphans = NODES.filter(function (n) { return n.inDeg === 0; });
    var weak = NODES.filter(function (n) { return n.inDeg > 0 && n.inDeg <= 1; });
    var lowScore = NODES.filter(function (n) {
      var r = SEO[n.slug]; return r && r.published !== false && r.score < 70;
    });

    if (orphans.length) a.push({
      sev: "risk", icon: "🚨", title: "Bài mồ côi (" + orphans.length + ")",
      desc: "Không có liên kết nội bộ nào trỏ đến — Google khó khám phá, dễ rớt index.",
      meta: orphans.slice(0, 3).map(function (n) { return n.title; }).join(" · "),
      action: { label: "Xem Link Graph", href: "#links" }
    });
    if (weak.length) a.push({
      sev: "optimize", icon: "⚠", title: "Authority yếu (" + weak.length + ")",
      desc: "Chỉ có 1 liên kết trỏ đến. Thêm liên kết nội bộ từ bài cùng cụm để tăng sức mạnh.",
      meta: weak.slice(0, 3).map(function (n) { return n.title; }).join(" · "),
      action: { label: "Xem gợi ý liên kết", href: "#links" }
    });
    if (lowScore.length) a.push({
      sev: "optimize", icon: "📉", title: "Điểm SEO thấp (" + lowScore.length + ")",
      desc: "Các bài dưới 70 điểm SEO — bổ sung từ khóa, internal link, FAQ, độ dài.",
      meta: lowScore.slice(0, 3).map(function (n) { return n.title + " (" + Math.round(SEO[n.slug].score) + ")"; }).join(" · "),
      action: { label: "Mở trình soạn thảo", href: BASE + "/editor/", ext: true }
    });
    if (REPORT404 && REPORT404.broken > 0) a.push({
      sev: "risk", icon: "🔗", title: "Liên kết hỏng (" + REPORT404.broken + ")",
      desc: "Có liên kết nội bộ 404 — chặn cổng QA và ảnh hưởng trải nghiệm.",
      meta: "Chạy qa-404-checker.py --fix để sửa tự động.",
      action: null
    });
    // GSC-derived
    if (gsc && gsc.connected) {
      // (placeholders for when GSC connected — CTR drop / not indexed would be computed from trend)
      if (gsc.non_indexed_pages > 0) a.push({
        sev: "risk", icon: "🛑", title: "Trang chưa index (" + gsc.non_indexed_pages + ")",
        desc: "Một số trang chưa được Google index. Kiểm tra Coverage trong GSC.",
        meta: "", action: null
      });
    } else {
      a.push({
        sev: "optimize", icon: "🔌", title: "Kết nối Google Search Console",
        desc: "Chưa kết nối GSC nên không thể theo dõi CTR drop, impressions hay trang chưa index.",
        meta: "Kết nối để mở khóa cảnh báo theo dữ liệu thực.",
        action: null
      });
    }
    if (!a.length) a.push({
      sev: "good", icon: "✓", title: "Không có cảnh báo",
      desc: "Liên kết nội bộ khỏe mạnh, không có bài mồ côi hay điểm SEO thấp.",
      meta: "", action: null
    });
    return a;
  }

  RENDER.alerts = function () {
    fetchJSON(BASE + "/data/gsc-metrics.json").then(function (gsc) {
      var alerts = buildAlerts(gsc);
      var wrap = $("[data-cms-alerts]");
      var current = "all";

      function draw() {
        var list = alerts.filter(function (x) { return current === "all" || x.sev === current; });
        wrap.innerHTML = list.map(function (x) {
          var act = "";
          if (x.action) {
            act = '<a class="cms-btn cms-btn--ghost cms-alert__action" href="' + esc(x.action.href) + '"' +
              (x.action.ext ? ' target="_blank" rel="noopener"' : "") + '>' + esc(x.action.label) + ' →</a>';
          }
          var sevLabel = { risk: "Rủi ro", optimize: "Tối ưu", good: "Tốt" }[x.sev] || x.sev;
          return '<article class="cms-alert" data-sev="' + x.sev + '">' +
            '<div class="cms-alert__head"><span class="cms-alert__icon">' + x.icon + '</span>' +
              '<span class="cms-alert__title">' + esc(x.title) + '</span>' +
              '<span class="cms-alert__sev">' + sevLabel + '</span></div>' +
            '<p class="cms-alert__desc">' + esc(x.desc) + '</p>' +
            (x.meta ? '<p class="cms-alert__meta">' + esc(x.meta) + '</p>' : "") +
            act +
          '</article>';
        }).join("");
        // re-bind hash links inside alerts
        $$(".cms-alert__action", wrap).forEach(function (link) {
          if (link.getAttribute("href").charAt(0) === "#") {
            link.addEventListener("click", function () { setTimeout(routeFromHash, 0); });
          }
        });
      }

      $$("[data-cms-alert-filters] [data-sev]").forEach(function (b) {
        b.addEventListener("click", function () {
          $$("[data-cms-alert-filters] [data-sev]").forEach(function (x) { x.classList.remove("is-active"); });
          b.classList.add("is-active");
          current = b.getAttribute("data-sev");
          draw();
        });
      });
      draw();

      // sidebar count = actionable (risk + optimize)
      var actionable = alerts.filter(function (x) { return x.sev === "risk" || x.sev === "optimize"; }).length;
      var badge = $("[data-cms-alert-count]");
      if (badge && actionable > 0) { badge.hidden = false; badge.textContent = actionable; }
    });
  };

  /* ---------- boot ---------- */
  routeFromHash();
  // Pre-compute alert badge even if user hasn't opened the alerts panel.
  if (!rendered.alerts) { try { RENDER.alerts(); rendered.alerts = true; } catch (e) {} }

})();
