/**
 * VIPZone — VIP gate, MoMo activation, session restore.
 * API: meta zola-vipzone-api. Fallback: localStorage prototype (TODO backend).
 */
(function (global) {
  "use strict";

  var SESSION_KEY = "zola-vipzone-vip";
  var STORE_KEY = "zola-vipzone-store";
  var CMS_KEY = "zola-cms-session-id";

  var SUPER_USERNAMES = ["banhang-chogao"];
  var SUPER_EMAILS = ["292648126+banhang-chogao@users.noreply.github.com"];

  var PLANS = {
    monthly: { label: "Gói Tháng — 250.000 VND", days: 30, price: 250000 },
    semiannual: { label: "Gói 6 Tháng — 500.000 VND", days: 180, price: 500000 },
  };

  var TOOL_PREFIXES = [
    "/editor", "/tools/", "/seo-bang-vang", "/converter", "/insights",
    "/ad-report", "/ad-report-v2", "/authority-report", "/scoring",
    "/prompt-support", "/changelog", "/shortensea/",
  ];
  var UPLOAD_TOOLS = [
    "/tools/f-dashboard", "/tools/l-dashboard", "/tools/o-dashboard", "/tools/h-dashboard",
  ];
  var EXEMPT = ["/tools/vipzone", "/tools/vipzone-admin", "/tools/s-dna", "/vipzone"];

  var API = (function () {
    var m = document.querySelector('meta[name="zola-vipzone-api"]');
    return m && m.getAttribute("content") ? m.getAttribute("content").replace(/\/$/, "") : "";
  })();

  var AUTH_API = (function () {
    var m = document.querySelector('meta[name="zola-cms-auth-api"]');
    return m && m.getAttribute("content") ? m.getAttribute("content").replace(/\/$/, "") : "";
  })();

  var BASE = (function () {
    var m = document.querySelector('meta[name="zola-base-url"]');
    return m && m.getAttribute("content") ? m.getAttribute("content").replace(/\/$/, "") : "/zola";
  })();

  function momoLink(plan) {
    var meta = plan === "monthly" ? "vipzone-momo-monthly" : "vipzone-momo-semiannual";
    var el = document.querySelector('meta[name="' + meta + '"]');
    return el ? el.getAttribute("content") : "#";
  }

  function toast(msg, type) {
    var host = document.querySelector("[data-vz-toast-host]");
    if (!host) return;
    var el = document.createElement("div");
    el.className = "vipzone__toast vipzone__toast--" + (type || "info");
    el.textContent = msg;
    host.appendChild(el);
    setTimeout(function () { el.remove(); }, 4200);
  }

  function readStore() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return { codes: [], payments: [], vips: [], picks: [], revenue: 0 };
  }

  function writeStore(data) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch (e) {}
    updateSidebarCount();
  }

  function genCode16() {
    var arr = new Uint32Array(4);
    crypto.getRandomValues(arr);
    var s = "";
    for (var i = 0; i < 4; i++) s += (arr[i] % 100000000).toString().padStart(8, "0");
    return s.slice(0, 16);
  }

  function getVipSession() {
    try {
      var raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      var s = JSON.parse(raw);
      if (!s.expires_at) return null;
      if (new Date(s.expires_at) <= new Date()) {
        localStorage.removeItem(SESSION_KEY);
        return null;
      }
      return s;
    } catch (e) { return null; }
  }

  function setVipSession(session) {
    try { localStorage.setItem(SESSION_KEY, JSON.stringify(session)); } catch (e) {}
    updateSidebarCount();
  }

  function isVipActive() { return !!getVipSession(); }

  function getCmsSid() {
    try { return sessionStorage.getItem(CMS_KEY) || ""; } catch (e) { return ""; }
  }

  async function fetchSuperuser() {
    if (!AUTH_API || !getCmsSid()) return false;
    try {
      var res = await fetch(AUTH_API + "/auth/me", {
        headers: { Authorization: "Bearer " + getCmsSid() },
        credentials: "omit",
        cache: "no-store",
      });
      if (!res.ok) return false;
      var p = await res.json();
      var u = (p.username || "").toLowerCase();
      var e = (p.email || "").toLowerCase();
      return p.is_super || SUPER_USERNAMES.indexOf(u) >= 0 || SUPER_EMAILS.indexOf(e) >= 0;
    } catch (e) { return false; }
  }

  var superCache = null;
  async function isSuperuser() {
    if (superCache !== null) return superCache;
    superCache = await fetchSuperuser();
    return superCache;
  }

  function normPath(path) {
    var p = path || location.pathname;
    if (BASE && p.indexOf(BASE) === 0) p = p.slice(BASE.length) || "/";
    return p.replace(/\/$/, "") || "/";
  }

  function pathNeedsGate(p) {
    for (var i = 0; i < EXEMPT.length; i++) {
      if (p === EXEMPT[i] || p.indexOf(EXEMPT[i] + "/") === 0) return false;
    }
    for (var j = 0; j < TOOL_PREFIXES.length; j++) {
      if (p === TOOL_PREFIXES[j] || p.indexOf(TOOL_PREFIXES[j]) === 0) return true;
    }
    return document.documentElement.getAttribute("data-vipzone-premium") === "true" ||
      (document.body && document.body.getAttribute("data-vipzone-premium") === "true");
  }

  function isUploadTool(p) {
    for (var i = 0; i < UPLOAD_TOOLS.length; i++) {
      if (p === UPLOAD_TOOLS[i] || p.indexOf(UPLOAD_TOOLS[i]) === 0) return true;
    }
    return false;
  }

  function activeVipCount() {
    var store = readStore();
    var n = 0;
    var now = Date.now();
    (store.vips || []).forEach(function (v) {
      if (v.active !== false && v.expires_at && new Date(v.expires_at).getTime() > now) n++;
    });
    var cur = getVipSession();
    if (cur && cur.email) {
      var found = (store.vips || []).some(function (v) {
        return v.email === cur.email && v.expires_at === cur.expires_at;
      });
      if (!found) n++;
    }
    return Math.max(n, (store.vips || []).filter(function (v) { return v.active !== false; }).length);
  }

  function updateSidebarCount() {
    var el = document.querySelector("[data-vipzone-count]");
    if (el) el.textContent = String(activeVipCount());
  }

  function showGateOverlay(kind) {
    if (document.getElementById("vz-gate-overlay")) return;
    var ov = document.createElement("div");
    ov.id = "vz-gate-overlay";
    ov.className = "vipzone__gate";
    ov.setAttribute("role", "dialog");
    ov.innerHTML =
      '<div class="vipzone__gate-card">' +
      '<p class="vipzone__gate-eyebrow">VIPZone · S-DNA</p>' +
      '<h2 class="vipzone__gate-title">' + (kind === "super" ? "Chỉ Superuser" : "Cần VIP") + '</h2>' +
      '<p class="vipzone__gate-desc">' + (kind === "super"
        ? "Công cụ upload sao kê chỉ dành cho superuser (GitHub whitelist)."
        : "Khu vực này dành cho thành viên VIP. Thanh toán MoMo và kích hoạt mã 16 số.") + '</p>' +
      '<a class="vipzone__btn vipzone__btn--momo" href="' + BASE + '/tools/vipzone/">' +
      (kind === "super" ? "Đăng nhập GitHub Admin" : "Kích hoạt VIPZone") + '</a>' +
      '</div>';
    document.body.appendChild(ov);
    document.documentElement.classList.add("vz-gated");
  }

  async function initGate() {
    var p = normPath();
    if (!pathNeedsGate(p)) return;
    if (await isSuperuser()) return;
    if (isUploadTool(p)) { showGateOverlay("super"); return; }
    if (!isVipActive()) showGateOverlay("vip");
    else if (document.documentElement.getAttribute("data-vipzone-premium") === "true") {
      var box = document.getElementById("paywall-box");
      if (box) {
        box.innerHTML = '<p class="vipzone__gate-desc">VIPZone đã kích hoạt — nội dung premium đang đồng bộ (TODO backend).</p>';
      }
    }
  }

  async function apiFetch(path, opts) {
    opts = opts || {};
    if (!API) throw new Error("VIPZone API chưa cấu hình — dùng local prototype.");
    var headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    var sid = getCmsSid();
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
    if (!res.ok) throw new Error((data && data.detail) || res.statusText);
    return data;
  }

  function redeemLocal(code, email) {
    var store = readStore();
    var found = null;
    (store.codes || []).forEach(function (c) {
      if (c.code === code && !c.used) found = c;
    });
    if (!found) throw new Error("Mã không hợp lệ hoặc đã dùng.");
    found.used = true;
    found.used_at = new Date().toISOString();
    var plan = PLANS[found.plan] || PLANS.monthly;
    var exp = new Date();
    exp.setDate(exp.getDate() + plan.days);
    var session = {
      email: email || found.email,
      plan: found.plan,
      activated_at: new Date().toISOString(),
      expires_at: exp.toISOString(),
    };
    store.vips = store.vips || [];
    store.vips.push({ email: session.email, plan: found.plan, expires_at: session.expires_at, active: true });
    store.revenue = (store.revenue || 0) + plan.price;
    writeStore(store);
    setVipSession(session);
    return session;
  }

  function submitPaymentLocal(body) {
    var store = readStore();
    store.payments = store.payments || [];
    store.payments.push({
      id: "pay_" + Date.now(),
      email: body.email,
      plan: body.plan,
      note: body.payment_note || "",
      status: "pending",
      created_at: new Date().toISOString(),
    });
    writeStore(store);
    return { message: "Đã gửi yêu cầu (local prototype)." };
  }

  function initLanding() {
    var root = document.querySelector('[data-vz-page="landing"]');
    if (!root) return;

    if (!API) {
      var note = document.querySelector("[data-vz-proto-note]");
      if (note) note.hidden = false;
    }

    var planInput = document.getElementById("vz-selected-plan");
    var planLabel = document.querySelector("[data-vz-plan-label]");
    var momoA = document.querySelector("[data-vz-momo-link]");

    function setPlan(plan) {
      if (planInput) planInput.value = plan;
      if (planLabel && PLANS[plan]) planLabel.textContent = PLANS[plan].label;
      if (momoA) momoA.href = momoLink(plan);
      document.querySelectorAll("[data-vz-plan-card]").forEach(function (c) {
        c.classList.toggle("vipzone__price-card--featured", c.getAttribute("data-vz-plan-card") === plan);
      });
    }

    var sess = getVipSession();
    if (sess) {
      var st = document.querySelector("[data-vz-vip-status]");
      var flow = document.getElementById("vz-paywall-flow");
      var pricing = document.querySelector("[data-vz-pricing]");
      if (st) {
        st.hidden = false;
        var em = document.querySelector("[data-vz-status-email]");
        var ex = document.querySelector("[data-vz-status-expiry]");
        if (em) em.textContent = sess.email;
        if (ex) ex.textContent = "Hết hạn: " + new Date(sess.expires_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
        startCountdown(sess.expires_at, document.querySelector("[data-vz-countdown]"));
      }
      if (flow) flow.hidden = true;
      if (pricing) pricing.hidden = true;
    } else {
      setPlan("semiannual");
    }

    document.querySelectorAll("[data-vz-select-plan]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setPlan(btn.getAttribute("data-vz-select-plan"));
      });
    });

    var payForm = document.getElementById("vz-payment-form");
    if (payForm) {
      payForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        var email = document.getElementById("vz-pay-email").value.trim();
        var note = document.getElementById("vz-pay-note").value.trim();
        var plan = planInput ? planInput.value : "semiannual";
        if (!email) { toast("Nhập email.", "error"); return; }
        try {
          if (API) {
            await apiFetch("/api/vipzone/payment-request", { method: "POST", body: { email: email, plan: plan, payment_note: note } });
          } else {
            submitPaymentLocal({ email: email, plan: plan, payment_note: note });
          }
          toast("Đã gửi yêu cầu kích hoạt.", "success");
        } catch (err) { toast(err.message || "Lỗi.", "error"); }
      });
    }

    var redeemBtn = document.querySelector('[data-vz-action="redeem"]');
    if (redeemBtn) {
      redeemBtn.addEventListener("click", async function () {
        var code = (document.getElementById("vz-approve-code").value || "").replace(/\D/g, "");
        var email = (document.getElementById("vz-pay-email") || {}).value;
        if (code.length !== 16) { toast("Mã phải đủ 16 chữ số.", "error"); return; }
        try {
          var session;
          if (API) {
            session = await apiFetch("/api/vipzone/redeem", { method: "POST", body: { code: code, email: email } });
          } else {
            session = redeemLocal(code, email);
          }
          var ok = document.getElementById("vz-success");
          var flow = document.getElementById("vz-paywall-flow");
          var msg = document.querySelector("[data-vz-success-msg]");
          if (msg) msg.textContent = "Gói " + (PLANS[session.plan] ? PLANS[session.plan].label : session.plan) + " — hết hạn " + new Date(session.expires_at).toLocaleDateString("vi-VN");
          if (flow) flow.hidden = true;
          if (ok) ok.hidden = false;
          toast("Kích hoạt VIP thành công!", "success");
        } catch (err) { toast(err.message || "Mã không hợp lệ.", "error"); }
      });
    }
  }

  function startCountdown(expiresAt, el) {
    if (!el || !expiresAt) return;
    function tick() {
      var diff = new Date(expiresAt) - new Date();
      if (diff <= 0) { el.textContent = "Đã hết hạn"; return; }
      var d = Math.floor(diff / 86400000);
      var h = Math.floor((diff % 86400000) / 3600000);
      var m = Math.floor((diff % 3600000) / 60000);
      el.textContent = "Còn " + d + " ngày " + h + " giờ " + m + " phút";
      requestAnimationFrame(function () { setTimeout(tick, 60000); });
    }
    tick();
  }

  global.VIPZone = {
    isVipActive: isVipActive,
    isSuperuser: isSuperuser,
    getVipSession: getVipSession,
    readStore: readStore,
    writeStore: writeStore,
    genCode16: genCode16,
    PLANS: PLANS,
    BASE: BASE,
    API: API,
    apiFetch: apiFetch,
    redeemLocal: redeemLocal,
    toast: toast,
    startCountdown: startCountdown,
    activeVipCount: activeVipCount,
    momoLink: momoLink,
  };

  document.addEventListener("DOMContentLoaded", function () {
    updateSidebarCount();
    initLanding();
    initGate();
  });
})(window);