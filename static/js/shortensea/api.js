/**
 * ShortenSEA API client — production backend only (no fake login state).
 */
(function (global) {
  "use strict";

  var API = (function () {
    var m = document.querySelector('meta[name="zola-shortensea-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "";
  })();

  var BASE = (function () {
    var m = document.querySelector('meta[name="zola-base-url"]');
    return (m && m.getAttribute("content")) ? m.getAttribute("content").replace(/\/$/, "") : "";
  })();

  async function apiFetch(path, opts) {
    opts = opts || {};
    if (!API) throw new Error("ShortenSEA API chưa cấu hình.");
    var sid = global.ShortenSEAAuth ? global.ShortenSEAAuth.getSid() : "";
    var headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (sid) headers.Authorization = "Bearer " + sid;
    var res = await fetch(API + path, {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      credentials: "omit",
      cache: "no-store",
    });
    var data = null;
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) {
      var detail = data && data.detail;
      if (Array.isArray(detail)) detail = detail.map(function (d) { return d.msg || d; }).join(", ");
      var err = new Error(detail || res.statusText || "request_failed");
      err.status = res.status;
      throw err;
    }
    return data;
  }

  global.ShortenSEAApi = {
    getApiUrl: function () { return API; },
    getBaseUrl: function () { return BASE; },
    isConfigured: function () { return !!API; },

    getAccount: function () { return apiFetch("/api/shortensea/account"); },
    listLinks: function () { return apiFetch("/api/shortensea/links"); },
    createLink: function (body) { return apiFetch("/api/shortensea/links", { method: "POST", body: body }); },
    updateLink: function (linkId, body) {
      return apiFetch("/api/shortensea/links/" + encodeURIComponent(linkId), { method: "PUT", body: body });
    },
    deleteLink: function (linkId) {
      return apiFetch("/api/shortensea/links/" + encodeURIComponent(linkId), { method: "DELETE" });
    },
    redeemCode: function (code) {
      return apiFetch("/api/shortensea/redeem-code", { method: "POST", body: { approve_code: code } });
    },
    getInsights: function () { return apiFetch("/api/shortensea/insights"); },
    submitPaymentRequest: function (body) {
      return apiFetch("/api/shortensea/payment-request", { method: "POST", body: body });
    },

    adminCreateCode: function (body) {
      return apiFetch("/api/shortensea/admin/codes", { method: "POST", body: body });
    },
    adminListCodes: function () { return apiFetch("/api/shortensea/admin/codes"); },
    adminListUsers: function () { return apiFetch("/api/shortensea/admin/users"); },
    adminOverrideUser: function (userId, body) {
      return apiFetch("/api/shortensea/admin/users/" + encodeURIComponent(userId), { method: "PUT", body: body });
    },
    adminListPaymentRequests: function (status) {
      var q = status ? "?status=" + encodeURIComponent(status) : "";
      return apiFetch("/api/shortensea/admin/payment-requests" + q);
    },
    adminResolvePaymentRequest: function (requestId) {
      return apiFetch("/api/shortensea/admin/payment-requests/" + encodeURIComponent(requestId) + "/resolve", { method: "POST" });
    },

    resolveSlug: async function (slug) {
      var res = await fetch(API + "/api/shortensea/resolve/" + encodeURIComponent(slug), { cache: "no-store" });
      if (!res.ok) throw new Error("not_found");
      return res.json();
    },
  };
})(window);