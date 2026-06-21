/**
 * Open PR Monitor — footer widget. Fetches /data/open-prs.json (generated at CI
 * time by scripts/build_open_prs.py via `gh pr list`) and renders up to 10 open
 * PRs as small cards. Static site, no backend.
 *
 * Behaviour:
 *   - ≥1 PR        → reveal section, render cards.
 *   - empty array  → reveal section, show a tiny muted "no open PRs".
 *   - missing/error/non-array → stay hidden (no noise, no layout shift).
 * Nodes are built with textContent only (PR titles/branches are never injected as HTML).
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-open-pr-monitor]");
  if (!root) return;

  var listEl = root.querySelector("[data-open-pr-list]");
  var emptyEl = root.querySelector("[data-open-pr-empty]");
  var countEl = root.querySelector("[data-open-pr-count]");
  var url = root.getAttribute("data-open-pr-url") || "/data/open-prs.json";

  var CHECK_ICON = { success: "✓", failure: "✗", pending: "⏳", none: "•" };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function safeUrl(raw) {
    // Only allow absolute http(s) links (PR urls); anything else → no href.
    if (typeof raw !== "string") return null;
    return /^https?:\/\//i.test(raw) ? raw : null;
  }

  function checkState(pr) {
    var c = pr && pr.checks;
    if (c && typeof c === "object") return c;
    return { state: "none", summary: "" };
  }

  function buildCard(pr) {
    var href = safeUrl(pr.url);
    var card = el("li", "open-pr-card");
    var link = el(href ? "a" : "div", "open-pr-card__link");
    if (href) {
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }

    var top = el("div", "open-pr-card__top");
    top.appendChild(el("span", "open-pr-card__num", "#" + pr.number));

    var checks = checkState(pr);
    var state = checks.state || "none";
    var chip = el("span", "open-pr-card__check open-pr-card__check--" + state);
    chip.appendChild(el("span", "open-pr-card__check-icon", CHECK_ICON[state] || "•"));
    if (checks.summary) chip.appendChild(el("span", "open-pr-card__check-text", checks.summary));
    top.appendChild(chip);
    link.appendChild(top);

    link.appendChild(el("p", "open-pr-card__title", pr.title || ("PR #" + pr.number)));

    var meta = el("div", "open-pr-card__meta");
    var branch = el("span", "open-pr-card__branch");
    branch.appendChild(el("span", "open-pr-card__branch-head", pr.head || "?"));
    branch.appendChild(el("span", "open-pr-card__branch-arrow", "→"));
    branch.appendChild(el("span", "open-pr-card__branch-base", pr.base || "main"));
    meta.appendChild(branch);
    if (pr.updated_display) meta.appendChild(el("span", "open-pr-card__time", pr.updated_display));
    link.appendChild(meta);

    card.appendChild(link);
    return card;
  }

  function render(prs) {
    root.hidden = false;
    listEl.textContent = "";

    if (!prs.length) {
      if (emptyEl) emptyEl.hidden = false;
      if (countEl) countEl.hidden = true;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;
    if (countEl) {
      countEl.hidden = false;
      countEl.textContent = prs.length + (prs.length === 1 ? " PR" : " PRs");
    }

    var frag = document.createDocumentFragment();
    prs.slice(0, 10).forEach(function (pr) {
      if (pr && pr.number != null) frag.appendChild(buildCard(pr));
    });
    listEl.appendChild(frag);
  }

  fetch(url + (url.indexOf("?") < 0 ? "?_=" : "&_=") + Date.now(), {
    credentials: "omit",
    cache: "no-store"
  })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      // Stay hidden on missing/error/non-array → footer never shows a broken widget.
      if (!Array.isArray(data)) return;
      render(data);
    })
    .catch(function () { /* offline / blocked → leave section hidden */ });
})();
