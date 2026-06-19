/**
 * THEODOI8 LIVE header banner — auto-refresh trạng thái CI/CD từ static JSON.
 *
 * Build-time HTML (load_data) là nguồn sự thật ban đầu; file này chỉ CẬP NHẬT khi
 * /data/theodoi8-report.json đổi (so sánh generated_at). Poll mỗi 60s, chỉ khi tab
 * đang hiển thị. Mọi lỗi network → bỏ qua im lặng (không vỡ UI).
 */
(function () {
  var P = window.Theodoi8Parser;
  if (!P) return;

  var el = document.querySelector("[data-theodoi8]");
  if (!el) return;

  var url = el.getAttribute("data-theodoi8-url") || P.reportUrl();
  var TTL = 60000;
  var lastStamp = el.getAttribute("data-theodoi8-stamp") || null;
  var STATUS = P.STATUS;

  function set(sel, text) {
    var n = el.querySelector(sel);
    if (n && text != null) n.textContent = text;
  }

  function apply(d) {
    if (!d || typeof d !== "object") return;
    if (d.generated_at && d.generated_at === lastStamp) return; // không đổi
    lastStamp = d.generated_at || null;

    var st = STATUS[d.status] || STATUS.idle;
    Object.keys(STATUS).forEach(function (k) {
      el.classList.remove(STATUS[k].cls);
    });
    el.classList.add(st.cls);

    set("[data-theodoi8-icon]", d.status_icon || st.icon);
    set("[data-theodoi8-summary]", d.summary || "");
    set("[data-theodoi8-time]", d.generated_at_display || "");
    if (d.cta) set("[data-theodoi8-cta]", d.cta + " →");
    if (d.url) el.setAttribute("href", d.url);
  }

  function poll() {
    fetch(url + (url.indexOf("?") < 0 ? "?_=" : "&_=") + Date.now(), {
      credentials: "omit",
      cache: "no-store"
    })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(apply)
      .catch(function () {});
  }

  poll();
  setInterval(function () {
    if (document.visibilityState === "visible") poll();
  }, TTL);
})();
