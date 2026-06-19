/**
 * ShortenSEA API client.
 * Uses backend when configured; falls back to localStorage prototype.
 * TODO(production): Remove localStorage fallback once ShortenSEA API is deployed.
 */
(function (global) {
  "use strict";

  var LS_KEY = "zola-shortensea-data";
  var LS_USER_KEY = "zola-shortensea-user";

  var API = (function () {
    var m = document.querySelector('meta[name="zola-shortensea-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "";
  })();

  var BASE = (function () {
    var m = document.querySelector('meta[name="zola-base-url"]');
    return (m && m.getAttribute("content")) ? m.getAttribute("content").replace(/\/$/, "") : "/zola";
  })();

  var MOMO = (function () {
    return "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/YQdJ8k98OO4vaOG";
  })();

  var PLAN_LIMITS = {
    free: { links_per_month: 10, custom_halves: 0, qr: false, tags: false, utm: false, expiration: false, basic_insights: true, advanced_insights: false, label: "Miễn phí" },
    locked_premium: { links_per_month: 10, custom_halves: 0, qr: false, tags: false, utm: false, expiration: false, basic_insights: true, advanced_insights: false, label: "Premium đã hết hạn" },
    monthly: { links_per_month: 100, custom_halves: 10, qr: true, tags: true, utm: false, expiration: false, basic_insights: true, advanced_insights: false, label: "Gói Tháng" },
    yearly: { links_per_month: 1000, custom_halves: 50, qr: true, tags: true, utm: true, expiration: true, basic_insights: true, advanced_insights: true, label: "Gói Năm" },
    super: { links_per_month: 999999, custom_halves: 999999, qr: true, tags: true, utm: true, expiration: true, basic_insights: true, advanced_insights: true, label: "Super VIP" }
  };

  var SUPER_USERNAMES = ["banhang-chogao"];
  var SUPER_EMAILS = ["292648126+banhang-chogao@users.noreply.github.com"];

  function usePrototype() {
    return !API || localStorage.getItem("zola-shortensea-prototype") === "1";
  }

  function lsGet() {
    try {
      return JSON.parse(localStorage.getItem(LS_KEY) || '{"links":[],"clicks":[],"codes":[]}');
    } catch (e) {
      return { links: [], clicks: [], codes: [] };
    }
  }

  function lsSet(data) {
    try { localStorage.setItem(LS_KEY, JSON.stringify(data)); } catch (e) {}
  }

  function isSuper(user) {
    if (!user) return false;
    if (user.is_super) return true;
    var u = (user.username || "").toLowerCase();
    var e = (user.email || "").toLowerCase();
    return SUPER_USERNAMES.indexOf(u) >= 0 || SUPER_EMAILS.indexOf(e) >= 0;
  }

  function effectivePlan(user) {
    if (isSuper(user)) return "super";
    return user.plan || "free";
  }

  function buildAccount(user) {
    var plan = effectivePlan(user);
    var limits = PLAN_LIMITS[plan] || PLAN_LIMITS.free;
    var monthKey = new Date().toISOString().slice(0, 7);
    if (user.links_month_key !== monthKey) {
      user.links_month_key = monthKey;
      user.links_month_count = 0;
    }
    return {
      user_id: user.user_id,
      email: user.email,
      username: user.username,
      name: user.name,
      avatar: user.avatar,
      plan: plan,
      plan_label: limits.label,
      is_super: isSuper(user),
      plan_expires_at: user.plan_expires_at || null,
      locked_until: user.locked_until || null,
      remaining_links: Math.max(0, limits.links_per_month - (user.links_month_count || 0)),
      remaining_custom_halves: Math.max(0, limits.custom_halves - (user.custom_halves_used || 0)),
      limits: limits,
      momo_payment_link: MOMO,
      short_domain: "banhang-chogao.github.io/zola"
    };
  }

  function applyExpiryLogic(user) {
    if (isSuper(user) || user.plan === "free" || user.plan === "super") return user;
    var now = Date.now();
    if (user.plan_expires_at) {
      var exp = new Date(user.plan_expires_at).getTime();
      if (now > exp) {
        if (!user.locked_until) {
          user.plan = "locked_premium";
          user.locked_until = new Date(exp + 86400000).toISOString().replace(/\.\d{3}Z$/, "Z");
        } else if (now > new Date(user.locked_until).getTime()) {
          user.plan = "free";
          user.locked_until = null;
          user.plan_expires_at = null;
        }
      }
    }
    return user;
  }

  function randomSlug() {
    return Math.random().toString(36).slice(2, 10);
  }

  function hashCode(code) {
    return code.toUpperCase();
  }

  async function apiFetch(path, opts) {
    opts = opts || {};
    var sid = global.ShortenSEAAuth ? global.ShortenSEAAuth.getSid() : "";
    var headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (sid) headers.Authorization = "Bearer " + sid;
    var res = await fetch(API + path, {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      credentials: "omit",
      cache: "no-store"
    });
    var data = null;
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) {
      var err = new Error((data && data.detail) || res.statusText || "request_failed");
      err.status = res.status;
      throw err;
    }
    return data;
  }

  var proto = {
    getAccount: function (user) {
      user = applyExpiryLogic(user);
      try { localStorage.setItem(LS_USER_KEY, JSON.stringify(user)); } catch (e) {}
      return Promise.resolve(buildAccount(user));
    },

    listLinks: function (user) {
      var data = lsGet();
      return Promise.resolve(
        data.links
          .filter(function (l) { return l.user_id === user.user_id; })
          .map(function (l) {
            return {
              link_id: l.link_id,
              slug: l.slug,
              short_url: BASE + "/s/" + l.slug,
              destination_url: l.destination_url,
              title: l.title || "",
              tags: l.tags || [],
              click_count: l.click_count || 0,
              status: l.status || "active",
              created_at: l.created_at,
              qr_enabled: !!l.qr_enabled
            };
          })
          .sort(function (a, b) { return (b.created_at || "").localeCompare(a.created_at || ""); })
      );
    },

    createLink: function (user, body) {
      user = applyExpiryLogic(user);
      var account = buildAccount(user);
      var limits = account.limits;
      if (account.remaining_links <= 0) return Promise.reject(new Error("Đã hết quota link tháng này."));
      if (body.slug && account.remaining_custom_halves <= 0) return Promise.reject(new Error("Gói hiện tại không hỗ trợ custom back-half."));
      if (body.qr_enabled && !limits.qr) return Promise.reject(new Error("QR code chỉ có ở gói trả phí."));
      if (body.tags && body.tags.length && !limits.tags) return Promise.reject(new Error("Tags chỉ có ở gói trả phí."));
      if ((body.utm_source || body.utm_medium) && !limits.utm) return Promise.reject(new Error("UTM chỉ có ở Gói Năm."));
      if (body.expires_at && !limits.expiration) return Promise.reject(new Error("Hết hạn link chỉ có ở Gói Năm."));

      var slug = (body.slug || "").trim().toLowerCase() || randomSlug();
      var data = lsGet();
      if (data.links.some(function (l) { return l.slug === slug; })) {
        return Promise.reject(new Error("Slug đã tồn tại — chọn back-half khác."));
      }

      var link = {
        link_id: "ls-" + Date.now(),
        user_id: user.user_id,
        slug: slug,
        destination_url: body.destination_url,
        title: body.title || "",
        tags: body.tags || [],
        qr_enabled: !!body.qr_enabled,
        status: "active",
        click_count: 0,
        created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z")
      };
      data.links.push(link);
      user.links_month_count = (user.links_month_count || 0) + 1;
      if (body.slug) user.custom_halves_used = (user.custom_halves_used || 0) + 1;
      lsSet(data);
      try { localStorage.setItem(LS_USER_KEY, JSON.stringify(user)); } catch (e) {}
      return Promise.resolve({
        link_id: link.link_id,
        slug: link.slug,
        short_url: BASE + "/s/" + link.slug,
        destination_url: link.destination_url,
        title: link.title,
        tags: link.tags,
        click_count: 0,
        status: "active",
        created_at: link.created_at,
        qr_enabled: link.qr_enabled
      });
    },

    updateLink: function (user, linkId, body) {
      var data = lsGet();
      var link = data.links.find(function (l) { return l.link_id === linkId && l.user_id === user.user_id; });
      if (!link) return Promise.reject(new Error("Không tìm thấy link."));
      if (body.destination_url) link.destination_url = body.destination_url;
      if (body.title !== undefined) link.title = body.title;
      if (body.status) link.status = body.status;
      lsSet(data);
      return Promise.resolve({ ok: true });
    },

    deleteLink: function (user, linkId) {
      var data = lsGet();
      data.links = data.links.filter(function (l) { return !(l.link_id === linkId && l.user_id === user.user_id); });
      data.clicks = data.clicks.filter(function (c) {
        var link = data.links.find(function (l) { return l.link_id === c.link_id; });
        return link;
      });
      lsSet(data);
      return Promise.resolve({ ok: true });
    },

    redeemCode: function (user, code) {
      var data = lsGet();
      var plain = code.trim().toUpperCase();
      var row = data.codes.find(function (c) {
        return c.code === plain && !c.used && (!c.email || c.email === user.email);
      });
      if (!row) return Promise.reject(new Error("Mã không hợp lệ hoặc đã dùng."));
      row.used = true;
      row.redeemed_at = new Date().toISOString();
      var days = row.plan_type === "yearly" ? 365 : 30;
      user.plan = row.plan_type;
      user.plan_expires_at = new Date(Date.now() + days * 86400000).toISOString().replace(/\.\d{3}Z$/, "Z");
      user.locked_until = null;
      user.custom_halves_used = 0;
      lsSet(data);
      try { localStorage.setItem(LS_USER_KEY, JSON.stringify(user)); } catch (e) {}
      return Promise.resolve({ ok: true, account: buildAccount(user) });
    },

    getInsights: function (user) {
      var account = buildAccount(user);
      var data = lsGet();
      var links = data.links.filter(function (l) { return l.user_id === user.user_id; });
      var linkIds = links.map(function (l) { return l.link_id; });
      var clicks = data.clicks.filter(function (c) { return linkIds.indexOf(c.link_id) >= 0; });
      var total = links.reduce(function (s, l) { return s + (l.click_count || 0); }, 0);
      var byDay = {};
      var referrers = {};
      var devices = {};
      var browsers = {};
      var qrScans = 0;
      clicks.forEach(function (c) {
        var day = (c.ts || "").slice(0, 10);
        byDay[day] = (byDay[day] || 0) + 1;
        var ref = c.referrer || "(direct)";
        referrers[ref] = (referrers[ref] || 0) + 1;
        devices[c.device || "unknown"] = (devices[c.device || "unknown"] || 0) + 1;
        browsers[c.browser || "unknown"] = (browsers[c.browser || "unknown"] || 0) + 1;
        if (c.is_qr) qrScans++;
      });
      function top(d, n) {
        return Object.keys(d).map(function (k) { return { name: k, count: d[k] }; })
          .sort(function (a, b) { return b.count - a.count; }).slice(0, n || 10);
      }
      var byLink = links.map(function (l) {
        return { slug: l.slug, title: l.title, clicks: l.click_count || 0 };
      }).sort(function (a, b) { return b.clicks - a.clicks; });

      var result = {
        total_clicks: total,
        clicks_by_link: byLink,
        clicks_by_day: Object.keys(byDay).sort().map(function (k) { return { date: k, clicks: byDay[k] }; }),
        referrers: top(referrers),
        devices: top(devices, 5),
        browsers: top(browsers, 5),
        countries: [],
        top_links: byLink.slice(0, 10),
        qr_scans: qrScans,
        plan: account.plan,
        basic_insights: account.limits.basic_insights,
        advanced_insights: account.limits.advanced_insights
      };
      if (!account.limits.advanced_insights) {
        result.locked_advanced = true;
        result.countries = [];
      }
      return Promise.resolve(result);
    },

    adminCreateCode: function (user, body) {
      if (!isSuper(user)) return Promise.reject(new Error("Chỉ admin mới tạo được mã."));
      var code = (body.code || Math.random().toString(36).slice(2, 10)).toUpperCase();
      var data = lsGet();
      data.codes.push({
        code: code,
        plan_type: body.plan_type,
        email: body.email || "",
        used: false,
        created_at: new Date().toISOString()
      });
      lsSet(data);
      return Promise.resolve({ approve_code: code, plan_type: body.plan_type });
    },

    recordClick: function (slug, meta) {
      var data = lsGet();
      var link = data.links.find(function (l) { return l.slug === slug && l.status === "active"; });
      if (!link) return null;
      link.click_count = (link.click_count || 0) + 1;
      data.clicks.push({
        link_id: link.link_id,
        ts: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
        referrer: meta.referrer || "",
        device: meta.device || "desktop",
        browser: meta.browser || "other",
        is_qr: !!meta.is_qr
      });
      lsSet(data);
      return link.destination_url;
    }
  };

  global.ShortenSEAApi = {
    getApiUrl: function () { return API; },
    getBaseUrl: function () { return BASE; },
    usePrototype: usePrototype,

    getAccount: async function () {
      if (usePrototype()) {
        var user = global.ShortenSEAAuth.getUser();
        if (!user) throw new Error("not_authenticated");
        return proto.getAccount(user);
      }
      return apiFetch("/api/shortensea/account");
    },

    listLinks: async function () {
      if (usePrototype()) {
        return proto.listLinks(global.ShortenSEAAuth.getUser());
      }
      return apiFetch("/api/shortensea/links");
    },

    createLink: async function (body) {
      if (usePrototype()) {
        return proto.createLink(global.ShortenSEAAuth.getUser(), body);
      }
      return apiFetch("/api/shortensea/links", { method: "POST", body: body });
    },

    updateLink: async function (linkId, body) {
      if (usePrototype()) {
        return proto.updateLink(global.ShortenSEAAuth.getUser(), linkId, body);
      }
      return apiFetch("/api/shortensea/links/" + encodeURIComponent(linkId), { method: "PUT", body: body });
    },

    deleteLink: async function (linkId) {
      if (usePrototype()) {
        return proto.deleteLink(global.ShortenSEAAuth.getUser(), linkId);
      }
      return apiFetch("/api/shortensea/links/" + encodeURIComponent(linkId), { method: "DELETE" });
    },

    redeemCode: async function (code) {
      if (usePrototype()) {
        return proto.redeemCode(global.ShortenSEAAuth.getUser(), code);
      }
      return apiFetch("/api/shortensea/redeem-code", { method: "POST", body: { approve_code: code } });
    },

    getInsights: async function () {
      if (usePrototype()) {
        return proto.getInsights(global.ShortenSEAAuth.getUser());
      }
      return apiFetch("/api/shortensea/insights");
    },

    adminCreateCode: async function (body) {
      if (usePrototype()) {
        return proto.adminCreateCode(global.ShortenSEAAuth.getUser(), body);
      }
      return apiFetch("/api/shortensea/admin/codes", { method: "POST", body: body });
    },

    resolveSlug: async function (slug) {
      if (usePrototype()) {
        var data = lsGet();
        var link = data.links.find(function (l) { return l.slug === slug && l.status === "active"; });
        if (!link) throw new Error("not_found");
        return { destination_url: link.destination_url };
      }
      var res = await fetch(API + "/api/shortensea/resolve/" + encodeURIComponent(slug), { cache: "no-store" });
      if (!res.ok) throw new Error("not_found");
      return res.json();
    },

    recordClickLocal: proto.recordClick
  };
})(window);