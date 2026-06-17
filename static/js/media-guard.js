/**
 * media-guard — casual download/copy friction for images & attachments.
 * Deterrent only (not absolute; static URLs remain fetchable). Skips CMS/editor.
 * Hotlink blocking cần CDN (Cloudflare Hotlink Protection) — xem SECURITY-GUIDE.md.
 * Page text keeps right-click; protected media blocks drag/select/context menu.
 */
(function () {
  'use strict';

  if (/\/(editor|admin-author)(\/|$)/.test(location.pathname)) return;
  if (document.getElementById('editor-app')) return;

  var ATTACH_RE = /\.(pdf|zip|rar|7z|tar|gz|docx?|xlsx?|pptx?|epub|mp3|mp4|webm|avi|mov)(\?|#|$)/i;

  var MEDIA_ROOTS = [
    '.post-single__content',
    '.post-single__hero',
    '.post-card__image',
    '.home-hero__image',
    '.home-card__image',
    '.featured-card__image',
    '.random-item__image',
    '.related-card__image',
    '.ad-banner__image',
    '.header-ad',
  ];

  var SKIP_ANCESTORS = '.site-header, .site-footer, .navbar, .post-meta, .post-stat, ' +
    '.post-author, .editor-user-bar, [data-media-guard-skip]';

  function inSkipZone(el) {
    return !!(el && el.closest && el.closest(SKIP_ANCESTORS));
  }

  function inMediaRoot(el) {
    if (!el || !el.closest) return false;
    for (var i = 0; i < MEDIA_ROOTS.length; i++) {
      if (el.closest(MEDIA_ROOTS[i])) return true;
    }
    return false;
  }

  function markImages(root) {
    var scope = root.querySelectorAll ? root : document;
    scope.querySelectorAll('img').forEach(function (img) {
      if (!inMediaRoot(img) || inSkipZone(img)) return;
      img.classList.add('media-guard');
      img.setAttribute('draggable', 'false');
      img.setAttribute('data-media-guard', 'img');
    });
    scope.querySelectorAll('picture').forEach(function (pic) {
      var img = pic.querySelector('img');
      if (!img || !inMediaRoot(pic) || inSkipZone(pic)) return;
      pic.classList.add('media-guard');
      pic.setAttribute('draggable', 'false');
      pic.setAttribute('data-media-guard', 'picture');
      img.classList.add('media-guard');
      img.setAttribute('draggable', 'false');
    });
  }

  function markAttachments(root) {
    var scope = root.querySelectorAll ? root : document;
    scope.querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute('href') || '';
      if (!ATTACH_RE.test(href) || !inMediaRoot(a) || inSkipZone(a)) return;
      a.classList.add('media-guard', 'media-guard--attach');
      a.setAttribute('data-media-guard', 'attach');
      a.removeAttribute('download');
    });
  }

  function markAll(root) {
    markImages(root || document);
    markAttachments(root || document);
  }

  function isProtectedTarget(el) {
    return !!(el && el.closest && el.closest('[data-media-guard]'));
  }

  function isProtectedImageTarget(el) {
    var node = el && el.closest && el.closest('[data-media-guard]');
    return node && node.getAttribute('data-media-guard') !== 'attach';
  }

  document.addEventListener('dragstart', function (e) {
    if (isProtectedTarget(e.target)) e.preventDefault();
  }, true);

  document.addEventListener('selectstart', function (e) {
    if (isProtectedImageTarget(e.target)) e.preventDefault();
  }, true);

  /* Block image/attachment context menu only — page text keeps right-click. */
  document.addEventListener('contextmenu', function (e) {
    if (isProtectedTarget(e.target)) e.preventDefault();
  }, true);

  document.addEventListener('keydown', function (e) {
    if (e.target && (e.target.closest('input, textarea, select, [contenteditable="true"]'))) return;
    var key = (e.key || '').toLowerCase();
    var mod = e.ctrlKey || e.metaKey;
    if (!mod) return;
    /* Ctrl/Cmd+S on protected focus — nudge only, does not block page save globally */
    if (key === 's' && document.activeElement && isProtectedImageTarget(document.activeElement)) {
      e.preventDefault();
    }
  }, true);

  function init() {
    markAll(document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  if (typeof MutationObserver !== 'undefined' && document.body) {
    var pending = false;
    var observer = new MutationObserver(function (records) {
      if (pending) return;
      pending = true;
      requestAnimationFrame(function () {
        pending = false;
        records.forEach(function (rec) {
          rec.addedNodes.forEach(function (node) {
            if (node.nodeType === 1) markAll(node);
          });
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();