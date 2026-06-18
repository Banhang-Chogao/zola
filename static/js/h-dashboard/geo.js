/**
 * Geographic transactions map for F-Dashboard.
 *
 * Reads each transaction description, detects a Vietnamese location (province,
 * city or a well-known district such as "Bàu Bàng"). When no location can be
 * found the transaction defaults to TP. Hồ Chí Minh. Renders a brand-styled
 * map: a teal Việt Nam silhouette on a light background with labelled dots
 * sized by transaction value, plus a ranked legend + per-region summary.
 *
 * Matching is WHOLE-WORD on a diacritic-stripped description (e.g. "TIEN THUE
 * NHA" must NOT match "Huế"). The silhouette and every dot share ONE lon/lat
 * projection, so markers always land in the correct spot relative to the
 * outline even though the outline itself is a stylised approximation.
 *
 * Engine is identical across f/l/h-dashboard — only the global export name
 * differs. CSS uses the shared `dash-geo__*` namespace.
 */
(function (global) {
  "use strict";

  const DEFAULT_PLACE_NAME = "TP. Hồ Chí Minh";

  // name · region (Bắc | Trung | Nam) · lon · lat · alias keywords.
  const PLACES = [
    // ---- Miền Nam ----
    { name: "TP. Hồ Chí Minh", region: "Nam", lon: 106.70, lat: 10.78, aliases: ["ho chi minh", "tp ho chi minh", "tphcm", "tp hcm", "hcm", "sai gon", "saigon"] },
    { name: "Bình Dương", region: "Nam", lon: 106.65, lat: 11.00, aliases: ["binh duong", "thu dau mot", "di an", "thuan an"] },
    { name: "Bàu Bàng", region: "Nam", lon: 106.62, lat: 11.27, specific: true, aliases: ["bau bang"] },
    { name: "Đồng Nai", region: "Nam", lon: 106.84, lat: 10.95, aliases: ["dong nai", "bien hoa", "long khanh"] },
    { name: "Bà Rịa - Vũng Tàu", region: "Nam", lon: 107.08, lat: 10.41, aliases: ["ba ria vung tau", "vung tau", "ba ria", "brvt"] },
    { name: "Tây Ninh", region: "Nam", lon: 106.10, lat: 11.31, aliases: ["tay ninh"] },
    { name: "Bình Phước", region: "Nam", lon: 106.91, lat: 11.53, aliases: ["binh phuoc", "dong xoai"] },
    { name: "Long An", region: "Nam", lon: 106.41, lat: 10.53, aliases: ["long an", "tan an"] },
    { name: "Tiền Giang", region: "Nam", lon: 106.36, lat: 10.36, aliases: ["tien giang", "my tho"] },
    { name: "Bến Tre", region: "Nam", lon: 106.38, lat: 10.24, aliases: ["ben tre"] },
    { name: "Vĩnh Long", region: "Nam", lon: 105.97, lat: 10.25, aliases: ["vinh long"] },
    { name: "Trà Vinh", region: "Nam", lon: 106.34, lat: 9.93, aliases: ["tra vinh"] },
    { name: "Đồng Tháp", region: "Nam", lon: 105.63, lat: 10.46, aliases: ["dong thap", "cao lanh", "sa dec"] },
    { name: "An Giang", region: "Nam", lon: 105.44, lat: 10.39, aliases: ["an giang", "long xuyen", "chau doc"] },
    { name: "Kiên Giang", region: "Nam", lon: 105.08, lat: 10.01, aliases: ["kien giang", "rach gia", "ha tien"] },
    { name: "Phú Quốc", region: "Nam", lon: 103.96, lat: 10.23, specific: true, aliases: ["phu quoc"] },
    { name: "Cần Thơ", region: "Nam", lon: 105.78, lat: 10.03, aliases: ["can tho", "ninh kieu"] },
    { name: "Hậu Giang", region: "Nam", lon: 105.47, lat: 9.78, aliases: ["hau giang", "vi thanh"] },
    { name: "Sóc Trăng", region: "Nam", lon: 105.97, lat: 9.60, aliases: ["soc trang"] },
    { name: "Bạc Liêu", region: "Nam", lon: 105.72, lat: 9.29, aliases: ["bac lieu"] },
    { name: "Cà Mau", region: "Nam", lon: 105.15, lat: 9.18, aliases: ["ca mau"] },
    { name: "Lâm Đồng", region: "Nam", lon: 108.44, lat: 11.94, aliases: ["lam dong", "da lat", "dalat", "bao loc"] },
    // ---- Miền Trung ----
    { name: "Đà Nẵng", region: "Trung", lon: 108.22, lat: 16.05, aliases: ["da nang", "danang"] },
    { name: "Thừa Thiên Huế", region: "Trung", lon: 107.58, lat: 16.46, aliases: ["thua thien hue", "thua thien", "hue"] },
    { name: "Quảng Nam", region: "Trung", lon: 108.30, lat: 15.57, aliases: ["quang nam", "tam ky", "hoi an"] },
    { name: "Quảng Ngãi", region: "Trung", lon: 108.80, lat: 15.12, aliases: ["quang ngai"] },
    { name: "Bình Định", region: "Trung", lon: 109.22, lat: 13.78, aliases: ["binh dinh", "quy nhon"] },
    { name: "Phú Yên", region: "Trung", lon: 109.30, lat: 13.10, aliases: ["phu yen", "tuy hoa"] },
    { name: "Khánh Hòa", region: "Trung", lon: 109.19, lat: 12.24, aliases: ["khanh hoa", "nha trang", "cam ranh"] },
    { name: "Ninh Thuận", region: "Trung", lon: 108.99, lat: 11.56, aliases: ["ninh thuan", "phan rang"] },
    { name: "Bình Thuận", region: "Trung", lon: 108.10, lat: 10.93, aliases: ["binh thuan", "phan thiet", "mui ne"] },
    { name: "Kon Tum", region: "Trung", lon: 108.00, lat: 14.35, aliases: ["kon tum"] },
    { name: "Gia Lai", region: "Trung", lon: 108.00, lat: 13.98, aliases: ["gia lai", "pleiku"] },
    { name: "Đắk Lắk", region: "Trung", lon: 108.05, lat: 12.67, aliases: ["dak lak", "dac lac", "buon ma thuot"] },
    { name: "Đắk Nông", region: "Trung", lon: 107.69, lat: 12.00, aliases: ["dak nong", "gia nghia"] },
    { name: "Thanh Hóa", region: "Trung", lon: 105.78, lat: 19.81, aliases: ["thanh hoa", "sam son"] },
    { name: "Nghệ An", region: "Trung", lon: 105.69, lat: 18.67, aliases: ["nghe an", "thanh pho vinh", "cua lo"] },
    { name: "Hà Tĩnh", region: "Trung", lon: 105.90, lat: 18.34, aliases: ["ha tinh"] },
    { name: "Quảng Bình", region: "Trung", lon: 106.62, lat: 17.47, aliases: ["quang binh", "dong hoi"] },
    { name: "Quảng Trị", region: "Trung", lon: 107.10, lat: 16.75, aliases: ["quang tri", "dong ha"] },
    // ---- Miền Bắc ----
    { name: "Hà Nội", region: "Bắc", lon: 105.85, lat: 21.03, aliases: ["ha noi", "hanoi"] },
    { name: "Hải Phòng", region: "Bắc", lon: 106.68, lat: 20.86, aliases: ["hai phong"] },
    { name: "Quảng Ninh", region: "Bắc", lon: 107.08, lat: 20.95, aliases: ["quang ninh", "ha long", "cam pha", "mong cai"] },
    { name: "Bắc Ninh", region: "Bắc", lon: 106.08, lat: 21.18, aliases: ["bac ninh"] },
    { name: "Hải Dương", region: "Bắc", lon: 106.33, lat: 20.94, aliases: ["hai duong"] },
    { name: "Hưng Yên", region: "Bắc", lon: 106.05, lat: 20.65, aliases: ["hung yen"] },
    { name: "Vĩnh Phúc", region: "Bắc", lon: 105.60, lat: 21.31, aliases: ["vinh phuc", "phuc yen"] },
    { name: "Thái Nguyên", region: "Bắc", lon: 105.84, lat: 21.59, aliases: ["thai nguyen"] },
    { name: "Bắc Giang", region: "Bắc", lon: 106.20, lat: 21.27, aliases: ["bac giang"] },
    { name: "Nam Định", region: "Bắc", lon: 106.18, lat: 20.42, aliases: ["nam dinh"] },
    { name: "Thái Bình", region: "Bắc", lon: 106.34, lat: 20.45, aliases: ["thai binh"] },
    { name: "Hà Nam", region: "Bắc", lon: 105.92, lat: 20.54, aliases: ["ha nam", "phu ly"] },
    { name: "Ninh Bình", region: "Bắc", lon: 105.97, lat: 20.25, aliases: ["ninh binh"] },
    { name: "Phú Thọ", region: "Bắc", lon: 105.22, lat: 21.40, aliases: ["phu tho", "viet tri"] },
    { name: "Lào Cai", region: "Bắc", lon: 103.97, lat: 22.40, aliases: ["lao cai", "sa pa", "sapa"] },
    { name: "Yên Bái", region: "Bắc", lon: 104.87, lat: 21.72, aliases: ["yen bai"] },
    { name: "Tuyên Quang", region: "Bắc", lon: 105.21, lat: 21.82, aliases: ["tuyen quang"] },
    { name: "Hà Giang", region: "Bắc", lon: 104.98, lat: 22.83, aliases: ["ha giang"] },
    { name: "Cao Bằng", region: "Bắc", lon: 106.25, lat: 22.67, aliases: ["cao bang"] },
    { name: "Lạng Sơn", region: "Bắc", lon: 106.76, lat: 21.85, aliases: ["lang son"] },
    { name: "Điện Biên", region: "Bắc", lon: 103.02, lat: 21.39, aliases: ["dien bien"] },
    { name: "Lai Châu", region: "Bắc", lon: 103.46, lat: 22.40, aliases: ["lai chau"] },
    { name: "Sơn La", region: "Bắc", lon: 103.92, lat: 21.33, aliases: ["son la", "moc chau"] },
    { name: "Hòa Bình", region: "Bắc", lon: 105.34, lat: 20.81, aliases: ["hoa binh"] },
  ];

  function stripDiacritics(s) {
    return String(s == null ? "" : s)
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D");
  }

  function normTokens(s) {
    return stripDiacritics(s)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  // Sorted (key, place) index — longest key first so multi-word names win
  // (e.g. "ba ria vung tau" before "vung tau"). Built once.
  const KEY_INDEX = (function () {
    const arr = [];
    PLACES.forEach((p) => {
      const keys = new Set();
      keys.add(normTokens(p.name));
      (p.aliases || []).forEach((a) => keys.add(normTokens(a)));
      const priority = p.specific ? 2 : 1;
      keys.forEach((k) => {
        if (k) arr.push({ key: " " + k + " ", place: p, priority: priority });
      });
    });
    arr.sort((a, b) => b.key.length - a.key.length);
    return arr;
  })();

  function detectPlace(description) {
    const padded = " " + normTokens(description) + " ";
    let best = null;
    let bestScore = -1;
    for (let i = 0; i < KEY_INDEX.length; i += 1) {
      const entry = KEY_INDEX[i];
      if (padded.indexOf(entry.key) !== -1) {
        // A more specific place (district/island) beats its parent province;
        // ties are broken by the longer matched key.
        const score = entry.priority * 1000 + entry.key.length;
        if (score > bestScore) {
          bestScore = score;
          best = entry.place;
        }
      }
    }
    return best;
  }

  function defaultPlace() {
    return PLACES.find((p) => p.name === DEFAULT_PLACE_NAME) || PLACES[0];
  }

  function analyze(transactions) {
    const txns = Array.isArray(transactions) ? transactions : [];
    const def = defaultPlace();
    const map = new Map();
    let defaulted = 0;

    txns.forEach((t) => {
      let place = detectPlace(t && t.description);
      if (!place) {
        place = def;
        defaulted += 1;
      }
      const amt = Number(t && t.amount) || 0;
      let agg = map.get(place.name);
      if (!agg) {
        agg = { name: place.name, region: place.region, lon: place.lon, lat: place.lat, count: 0, spend: 0, income: 0 };
        map.set(place.name, agg);
      }
      agg.count += 1;
      if (amt < 0) agg.spend += Math.abs(amt);
      else agg.income += amt;
    });

    const locations = Array.from(map.values()).map((a) => {
      a.total = a.spend + a.income;
      return a;
    });
    locations.sort((a, b) => b.total - a.total);

    const byRegion = {};
    locations.forEach((l) => {
      const r = l.region || "Khác";
      if (!byRegion[r]) byRegion[r] = { region: r, count: 0, spend: 0, income: 0, places: 0 };
      byRegion[r].count += l.count;
      byRegion[r].spend += l.spend;
      byRegion[r].income += l.income;
      byRegion[r].places += 1;
    });

    return { locations, byRegion, defaulted, total_count: txns.length };
  }

  // ---- Map projection + Việt Nam outline (shared lon/lat space) ----
  const LON_MIN = 101.9;
  const LON_MAX = 109.7;
  const LAT_MIN = 8.2;
  const LAT_MAX = 23.5;
  const SCALE = 42;
  const COS_MID = Math.cos((15.8 * Math.PI) / 180);
  const MAP_W = (LON_MAX - LON_MIN) * SCALE * COS_MID;
  const MAP_H = (LAT_MAX - LAT_MIN) * SCALE;

  function project(lon, lat) {
    return { x: (lon - LON_MIN) * SCALE * COS_MID, y: (LAT_MAX - lat) * SCALE };
  }

  // Clockwise boundary: north border → east coast → Cà Mau → west coast →
  // western (Lào/Cambodia) border → NW tip. Stylised but recognisable S-shape.
  const VN_OUTLINE = [
    [103.00, 22.45], [104.00, 22.80], [105.30, 23.35], [106.50, 22.90],
    [107.40, 21.65], [108.05, 21.50], [106.80, 20.70], [106.55, 20.20],
    [106.00, 19.40], [105.90, 18.80], [106.50, 17.50], [107.10, 16.85],
    [108.30, 16.05], [109.20, 13.80], [109.45, 12.70], [108.95, 11.55],
    [107.60, 10.70], [106.85, 10.35], [106.30, 9.60], [105.40, 9.00],
    [104.85, 8.60], [104.75, 9.55], [104.50, 10.40], [105.40, 10.95],
    [106.10, 11.70], [106.45, 12.30], [107.55, 13.95], [107.30, 15.50],
    [106.55, 16.60], [105.90, 17.70], [104.65, 18.70], [103.90, 19.65],
    [104.10, 20.80], [103.20, 21.40], [102.15, 22.40], [103.00, 22.45],
  ];

  function outlinePath() {
    return (
      VN_OUTLINE.map((pt, i) => {
        const p = project(pt[0], pt[1]);
        return (i ? "L" : "M") + p.x.toFixed(1) + " " + p.y.toFixed(1);
      }).join(" ") + " Z"
    );
  }

  function compactVnd(n) {
    const v = Math.abs(Number(n)) || 0;
    if (v >= 1e9) return (v / 1e9).toFixed(1).replace(/\.0$/, "") + " tỷ";
    if (v >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, "") + " tr";
    if (v >= 1e3) return Math.round(v / 1e3) + "k";
    return String(Math.round(v));
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function shortName(name) {
    return String(name).replace(/^TP\.?\s*/, "");
  }

  function buildSvg(locations) {
    const PADX = 80;
    const PADY = 18;
    const vb =
      (-PADX).toFixed(1) + " " + (-PADY).toFixed(1) + " " +
      (MAP_W + 2 * PADX).toFixed(1) + " " + (MAP_H + 2 * PADY).toFixed(1);
    const maxVal = locations.reduce((m, l) => Math.max(m, l.total), 0) || 1;
    const minR = 4;
    const maxR = 17;

    const markers = locations
      .map((l, idx) => {
        const p = project(l.lon, l.lat);
        const r = minR + (maxR - minR) * Math.sqrt(Math.max(0, l.total) / maxVal);
        const rightSide = p.x > MAP_W * 0.62;
        const lx = rightSide ? p.x - r - 4 : p.x + r + 4;
        const anchor = rightSide ? "end" : "start";
        const title =
          l.name + " · " + l.count + " GD · chi " + compactVnd(l.spend) +
          (l.income ? " · thu " + compactVnd(l.income) : "");
        const label =
          idx < 8
            ? '<text class="dash-geo__lbl" x="' + lx.toFixed(1) + '" y="' + (p.y + 3).toFixed(1) +
              '" text-anchor="' + anchor + '">' + esc(shortName(l.name)) + " · " + esc(compactVnd(l.total)) + "</text>"
            : "";
        return (
          '<g class="dash-geo__mk"><title>' + esc(title) + "</title>" +
          '<circle class="dash-geo__dot" cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="' + r.toFixed(1) + '"/>' +
          '<circle class="dash-geo__dotc" cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="1.6"/>' +
          label + "</g>"
        );
      })
      .join("");

    return (
      '<svg class="dash-geo__svg" viewBox="' + vb + '" preserveAspectRatio="xMidYMid meet" role="img" ' +
      'aria-label="Bản đồ giao dịch theo địa điểm tại Việt Nam">' +
      '<path class="dash-geo__land" d="' + outlinePath() + '"/>' +
      markers +
      "</svg>"
    );
  }

  function buildLegend(res) {
    const top = res.locations.slice(0, 12);
    const max = top.reduce((m, l) => Math.max(m, l.total), 0) || 1;
    const rows = top
      .map((l) => {
        const w = Math.max(4, Math.round((l.total / max) * 100));
        return (
          '<li class="dash-geo__row"><span class="dash-geo__rname" title="' + esc(l.name) + '">' + esc(shortName(l.name)) + "</span>" +
          '<span class="dash-geo__bar"><span class="dash-geo__barfill" style="width:' + w + '%"></span></span>' +
          '<span class="dash-geo__rval">' + esc(compactVnd(l.total)) + " · " + l.count + " GD</span></li>"
        );
      })
      .join("");

    const regMap = { "Bắc": "bac", "Trung": "trung", "Nam": "nam", "Khác": "khac" };
    const chips = ["Bắc", "Trung", "Nam", "Khác"]
      .filter((r) => res.byRegion[r])
      .map((r) => {
        const x = res.byRegion[r];
        const head = r === "Khác" ? "Khác" : "Miền " + r;
        return '<span class="dash-geo__chip dash-geo__chip--' + regMap[r] + '">' + esc(head) + ": " + x.count + " GD · " + esc(compactVnd(x.spend)) + "</span>";
      })
      .join("");

    return (
      '<div class="dash-geo__legend"><h3 class="dash-geo__lgtitle">Top địa điểm</h3>' +
      '<ul class="dash-geo__list">' + rows + "</ul>" +
      '<div class="dash-geo__regions">' + chips + "</div></div>"
    );
  }

  function render(transactions, container) {
    if (!container) return;
    const txns = Array.isArray(transactions) ? transactions : [];
    if (!txns.length) {
      container.innerHTML = '<p class="dash-geo__empty">Upload hóa đơn để xem phân bố giao dịch theo địa điểm.</p>';
      return;
    }
    const res = analyze(txns);
    const hint = res.defaulted
      ? '<p class="dash-geo__hint">' + res.defaulted + "/" + res.total_count +
        " giao dịch không ghi địa điểm → mặc định tính cho TP. Hồ Chí Minh.</p>"
      : "";
    container.innerHTML =
      '<div class="dash-geo__grid"><div class="dash-geo__map">' + buildSvg(res.locations) + "</div>" +
      buildLegend(res) + "</div>" + hint;
  }

  global.HDashboardGeo = { analyze, detectPlace, render };
})(typeof window !== "undefined" ? window : globalThis);
