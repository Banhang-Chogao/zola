(function () {
  "use strict";
  if (location.pathname.indexOf("/cms-") === 0 || navigator.webdriver) return;
  var meta = document.querySelector('meta[name="zola-cms-auth-api"]');
  if (!meta || !meta.content) return;
  var endpoint = meta.content.replace(/\/$/, "") + "/api/cms-v5/analytics";
  var path = location.pathname;

  function send(metric) {
    fetch(endpoint, {
      method: "POST",
      mode: "cors",
      credentials: "omit",
      keepalive: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path, metric: metric }),
    }).catch(function () {});
  }

  var viewKey = "cms5-view:" + path;
  try {
    if (!sessionStorage.getItem(viewKey)) {
      sessionStorage.setItem(viewKey, "1");
      send("view");
    }
  } catch (_) {
    send("view");
  }

  var interacted = false;
  document.addEventListener("click", function (event) {
    if (interacted || !event.target.closest(".post-single a, .post-single button, [data-comments] button")) return;
    interacted = true;
    send("interaction");
  }, { passive: true });
})();
