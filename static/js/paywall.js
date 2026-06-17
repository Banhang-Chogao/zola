/**
 * Paywall client — request access, unlock, fetch premium content.
 * Full content KHÔNG có trong static HTML; chỉ load sau khi token hợp lệ.
 */
(function () {
  "use strict";

  var box = document.getElementById("paywall-box");
  var premium = document.getElementById("paywall-premium");
  if (!box || !premium) return;

  var API = (function () {
    var m = document.querySelector('meta[name="zola-paywall-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "";
  })();

  var postId = box.dataset.postId || "";
  var postTitle = box.dataset.postTitle || "";
  var postUrl = box.dataset.postUrl || location.pathname;
  var blogName = box.dataset.blogName || "Blog";

  var SESSION_PREFIX = "paywall-token-";
  var sessionKey = SESSION_PREFIX + postId;

  function storageGet(key) {
    try { return sessionStorage.getItem(key) || ""; } catch (e) { return ""; }
  }
  function storageSet(key, val) {
    try { sessionStorage.setItem(key, val); } catch (e) {}
  }
  function storageRemove(key) {
    try { sessionStorage.removeItem(key); } catch (e) {}
  }

  function getToken() {
    var raw = storageGet(sessionKey);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (e) { return null; }
  }
  function setToken(data) {
    storageSet(sessionKey, JSON.stringify(data));
  }

  function statusEl() {
    return box.querySelector("[data-paywall-status]");
  }
  function showStatus(msg, type) {
    var el = statusEl();
    if (!el) return;
    el.textContent = msg;
    el.className = "paywall-status paywall-status--" + (type || "info");
    el.hidden = false;
  }
  function hideStatus() {
    var el = statusEl();
    if (el) el.hidden = true;
  }

  function apiUrl(path) {
    if (!API) return "";
    return API + path;
  }

  async function postJson(path, body, token) {
    var headers = { "Content-Type": "application/json" };
    if (token) headers.Authorization = "Bearer " + token;
    var res = await fetch(apiUrl(path), {
      method: "POST",
      headers: headers,
      credentials: "omit",
      cache: "no-store",
      body: JSON.stringify(body),
    });
    var data = null;
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) {
      var detail = (data && data.detail) ? data.detail : ("HTTP " + res.status);
      throw new Error(detail);
    }
    return data;
  }

  async function getJson(path, token) {
    var res = await fetch(apiUrl(path), {
      headers: { Authorization: "Bearer " + token },
      credentials: "omit",
      cache: "no-store",
    });
    var data = null;
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) {
      var detail = (data && data.detail) ? data.detail : ("HTTP " + res.status);
      throw new Error(detail);
    }
    return data;
  }

  function formatPriceVnd(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + "đ";
  }

  function applyWatermark(trace, emailHash) {
    var wm = premium.querySelector("[data-paywall-watermark]");
    if (wm) {
      wm.textContent = blogName + " • " + emailHash + " • " + postId + " • " + trace;
    }
    var printWm = document.querySelector("[data-paywall-print-wm]");
    if (printWm) {
      printWm.textContent = trace + "_" + (location.hostname || "blog");
    }
  }

  function enableReadOnlyProtection(container) {
    container.addEventListener("contextmenu", function (e) { e.preventDefault(); });
    container.addEventListener("copy", function (e) { e.preventDefault(); });
    container.addEventListener("cut", function (e) { e.preventDefault(); });
    container.addEventListener("dragstart", function (e) { e.preventDefault(); });
    document.addEventListener("keydown", function (e) {
      if (!premium || premium.hidden) return;
      var mod = e.ctrlKey || e.metaKey;
      if (!mod) return;
      var k = e.key.toLowerCase();
      if (k === "c" || k === "x" || k === "a" || k === "s" || k === "p") {
        if (k === "p") return;
        e.preventDefault();
      }
    });
  }

  async function loadPremiumContent(tokenData) {
    if (!API) {
      showStatus("Paywall API chưa cấu hình. Liên hệ admin.", "error");
      return;
    }
    var data = await getJson("/api/paywall/content/" + encodeURIComponent(postId), tokenData.access_token);
    var body = premium.querySelector("[data-paywall-body]");
    if (!body) return;
    body.innerHTML = data.html;
    applyWatermark(data.trace_code, data.reader_email_hash);
    premium.hidden = false;
    box.hidden = true;
    enableReadOnlyProtection(premium);
  }

  async function tryRestoreSession() {
    var tok = getToken();
    if (!tok || !tok.access_token) return;
    try {
      await loadPremiumContent(tok);
    } catch (e) {
      storageRemove(sessionKey);
    }
  }

  box.querySelector('[data-form="request"]').addEventListener("submit", async function (e) {
    e.preventDefault();
    hideStatus();
    if (!API) {
      showStatus("Paywall API chưa cấu hình.", "error");
      return;
    }
    var fd = new FormData(e.target);
    var email = (fd.get("email") || "").toString().trim();
    var note = (fd.get("payment_note") || "").toString().trim();
    if (!email) {
      showStatus("Vui lòng nhập email.", "error");
      return;
    }
    var btn = e.target.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    try {
      await postJson("/api/paywall/request-access", {
        post_id: postId,
        post_title: postTitle,
        post_url: postUrl,
        email: email,
        payment_note: note,
      });
      showStatus(
        "Đã gửi yêu cầu! Admin sẽ xác nhận thanh toán Momo và gửi approve code qua email trong thời gian sớm nhất.",
        "success"
      );
      e.target.reset();
    } catch (err) {
      showStatus(err.message || "Gửi yêu cầu thất bại.", "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  box.querySelector('[data-form="unlock"]').addEventListener("submit", async function (e) {
    e.preventDefault();
    hideStatus();
    if (!API) {
      showStatus("Paywall API chưa cấu hình.", "error");
      return;
    }
    var fd = new FormData(e.target);
    var email = (fd.get("email") || "").toString().trim();
    var code = (fd.get("approve_code") || "").toString().trim();
    if (!email || !code) {
      showStatus("Vui lòng nhập email và approve code.", "error");
      return;
    }
    var btn = e.target.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    try {
      var out = await postJson("/api/paywall/unlock", {
        post_id: postId,
        email: email,
        approve_code: code,
      });
      setToken(out);
      await loadPremiumContent(out);
      showStatus("Đã mở khóa bài viết!", "success");
    } catch (err) {
      showStatus(err.message || "Mở khóa thất bại.", "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  window.addEventListener("beforeprint", function () {
    var tok = getToken();
    if (!tok || !tok.access_token || premium.hidden) return;
    fetch(apiUrl("/api/paywall/log-print?post_id=" + encodeURIComponent(postId)), {
      method: "POST",
      headers: { Authorization: "Bearer " + tok.access_token },
      credentials: "omit",
    }).catch(function () {});
  });

  (function formatPrice() {
    var el = box.querySelector("[data-paywall-price]");
    if (!el) return;
    var n = parseInt(el.getAttribute("data-paywall-price"), 10);
    if (!isNaN(n)) el.textContent = n.toLocaleString("vi-VN") + "đ";
  })();

  tryRestoreSession();
})();