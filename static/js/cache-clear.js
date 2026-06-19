(function () {
  var button = document.querySelector("[data-clear-cache]");
  if (!button) return;

  var label = button.querySelector("[data-clear-cache-label]");
  var defaultLabel = label ? label.textContent : "Xoá cache";

  function setLabel(text) {
    if (label) label.textContent = text;
  }

  function clearStorage() {
    // Giữ lại phiên đăng nhập super-admin/CMS để xoá cache KHÔNG bắt login GitHub lại.
    var CMS_KEY = "zola-cms-session-id";
    var sid = "";
    try { sid = localStorage.getItem(CMS_KEY) || sessionStorage.getItem(CMS_KEY) || ""; } catch (e) {}
    try { localStorage.clear(); } catch (e) {}
    try { sessionStorage.clear(); } catch (e) {}
    if (sid) {
      try { localStorage.setItem(CMS_KEY, sid); } catch (e) {}
      try { sessionStorage.setItem(CMS_KEY, sid); } catch (e) {}
    }
  }

  async function clearCacheStorage() {
    if (!("caches" in window)) return;
    try {
      var names = await caches.keys();
      await Promise.all(names.map(function (name) { return caches.delete(name); }));
    } catch (e) {}
  }

  async function unregisterWorkers() {
    if (!("serviceWorker" in navigator)) return;
    try {
      var regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map(function (reg) { return reg.unregister(); }));
    } catch (e) {}
  }

  async function clearIndexedDb() {
    if (!("indexedDB" in window) || typeof indexedDB.databases !== "function") return;
    try {
      var dbs = await indexedDB.databases();
      await Promise.all(dbs.map(function (db) {
        return new Promise(function (resolve) {
          if (!db.name) return resolve();
          var req = indexedDB.deleteDatabase(db.name);
          req.onsuccess = req.onerror = req.onblocked = function () { resolve(); };
        });
      }));
    } catch (e) {}
  }

  function reloadFresh() {
    var url = new URL(window.location.href);
    url.searchParams.set("_fresh", Date.now().toString());
    window.location.replace(url.toString());
  }

  button.addEventListener("click", async function () {
    button.disabled = true;
    setLabel("Đang xoá...");
    clearStorage();
    await Promise.all([
      clearCacheStorage(),
      unregisterWorkers(),
      clearIndexedDb()
    ]);
    setLabel("Đã xoá");
    window.setTimeout(reloadFresh, 250);
    window.setTimeout(function () {
      button.disabled = false;
      setLabel(defaultLabel);
    }, 3000);
  });
})();
