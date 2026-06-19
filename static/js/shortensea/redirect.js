/**
 * Short URL redirect hook for GitHub Pages 404.html.
 * Matches /zola/s/{slug} → resolve destination → log click → redirect.
 */
(function () {
  "use strict";

  var path = location.pathname;
  var m = path.match(/\/s\/([a-zA-Z0-9_-]+)\/?$/);
  if (!m) return;

  var slug = m[1].toLowerCase();
  var api = (function () {
    var el = document.querySelector('meta[name="zola-shortensea-api"]');
    if (el && el.getAttribute("content")) return el.getAttribute("content").replace(/\/$/, "");
    return "";
  })();

  function parseUa() {
    var ua = navigator.userAgent.toLowerCase();
    var device = /mobile|android|iphone/.test(ua) ? "mobile" : /tablet|ipad/.test(ua) ? "tablet" : "desktop";
    var browser = /edg/.test(ua) ? "Edge" : /chrome/.test(ua) ? "Chrome" : /firefox/.test(ua) ? "Firefox" : /safari/.test(ua) ? "Safari" : "other";
    return { device: device, browser: browser };
  }

  function redirectTo(url) {
    location.replace(url);
  }

  async function run() {
    var isQr = location.search.indexOf("qr=1") >= 0;
    if (api) {
      try {
        var trackUrl = api + "/s/" + encodeURIComponent(slug) + (isQr ? "?qr=1" : "");
        location.replace(trackUrl);
        return;
      } catch (e) {}
    }

    if (window.ShortenSEAApi && window.ShortenSEAApi.usePrototype && window.ShortenSEAApi.usePrototype()) {
      var meta = Object.assign({ referrer: document.referrer, is_qr: isQr }, parseUa());
      var dest = window.ShortenSEAApi.recordClickLocal(slug, meta);
      if (dest) redirectTo(dest);
      return;
    }

    if (api) {
      try {
        var res = await fetch(api + "/api/shortensea/resolve/" + encodeURIComponent(slug), { cache: "no-store" });
        if (res.ok) {
          var data = await res.json();
          fetch(api + "/s/" + encodeURIComponent(slug) + (isQr ? "?qr=1" : ""), { mode: "no-cors" }).catch(function () {});
          redirectTo(data.destination_url);
          return;
        }
      } catch (e) {}
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();