/* toc-rail.js — "On This Page" scroll-spy for the sticky article TOC rail.
 *
 *  Highlights the active heading in the right rail (.toc-rail) as the reader
 *  scrolls, using IntersectionObserver. Smooth scroll on click is CSS-native
 *  (html { scroll-behavior: smooth; scroll-padding-top } in _reset.scss), so
 *  this only manages the active-state class.
 *
 *  Vanilla, defer-safe, no dependencies. Safe no-op when: there is no rail on
 *  the page, the article has few/no headings, or the browser lacks
 *  IntersectionObserver (the rail still works as plain anchor links).
 */
(function () {
  "use strict";

  var rail = document.querySelector("[data-toc-rail]");
  if (!rail) return;

  var links = Array.prototype.slice.call(rail.querySelectorAll("[data-toc-link]"));
  if (!links.length) return;

  // Map heading id -> rail link; collect the heading elements in document order.
  var linkById = Object.create(null);
  var ids = [];
  var headings = [];
  links.forEach(function (link) {
    var href = link.getAttribute("href") || "";
    var id = href.charAt(0) === "#" ? href.slice(1) : "";
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    linkById[id] = link;
    ids.push(id);
    headings.push(el);
  });
  if (!headings.length) return;

  var current = null;
  function setActive(id) {
    if (id === current || !linkById[id]) return;
    if (current && linkById[current]) {
      linkById[current].classList.remove("is-active");
      linkById[current].removeAttribute("aria-current");
    }
    current = id;
    linkById[id].classList.add("is-active");
    linkById[id].setAttribute("aria-current", "true");
  }

  // Click → activate immediately for snappy feedback (scroll handled by CSS).
  links.forEach(function (link) {
    link.addEventListener("click", function () {
      var href = link.getAttribute("href") || "";
      if (href.charAt(0) === "#") setActive(href.slice(1));
    });
  });

  // Graceful fallback: no observer support → keep the first item highlighted.
  if (!("IntersectionObserver" in window)) {
    setActive(ids[0]);
    return;
  }

  var visible = Object.create(null);
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) visible[entry.target.id] = true;
      else delete visible[entry.target.id];
    });
    // Highlight the first visible heading in document order; if nothing is in
    // the active band (between sections), keep the last active one.
    for (var i = 0; i < ids.length; i++) {
      if (visible[ids[i]]) { setActive(ids[i]); return; }
    }
  }, { rootMargin: "-15% 0px -70% 0px", threshold: 0 });

  headings.forEach(function (h) { observer.observe(h); });
  setActive(ids[0]);
})();
