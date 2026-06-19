/**
 * H-Dashboard V2 — Coffee Life Analytics engine.
 * Highlands receipt OCR → visits, drinks, seasonality, personality, discoveries.
 * S-DNA: data-first, no bank-statement concepts.
 */
(function (global) {
  "use strict";

  const DRINK_CATEGORIES = [
    ["Americano", ["americano", "espresso", "phin", "den da", "den nong", "ca phe den", "cafe den"]],
    ["Freeze", ["freeze", "smoothie", "frapp", "da xay"]],
    ["Tea", ["tra ", "tra-", "tra thai", "tra sen", "tra chanh", "tra sua", "tra vai", "tra xanh", "tra den", "tra atiso"]],
    ["Matcha", ["matcha"]],
    ["Water", ["dasani", "nuoc tinh khiet", "nuoc suoi", "aquafina", "lavie", "nuoc khoang"]],
    ["Milk Coffee", ["bac xiu", "ca phe sua", "cafe sua", "caphe sua", "latte", "cappuccino", "macchiato", "flat white"]],
    ["Juice", ["nuoc ep", "juice", "cam vat", "xoai", "dua hau"]],
    ["Bakery", ["banh", "croissant", "muffin", "cookie", "sandwich"]],
    ["Other", []],
  ];

  const SEASONS = {
    dry: { id: "dry", label: "Mùa khô", months: [12, 1, 2] },
    hot: { id: "hot", label: "Mùa nóng", months: [3, 4, 5] },
    rainy: { id: "rainy", label: "Mùa mưa", months: [6, 7, 8, 9, 10, 11] },
  };

  const DAY_NAMES = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
  const MONTH_NAMES = ["", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
    "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"];

  function safeNum(n) {
    const v = Number(n);
    return Number.isFinite(v) ? v : 0;
  }

  function norm(s) {
    return String(s || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .trim();
  }

  function formatVnd(n) {
    const v = Number(n);
    if (!Number.isFinite(v)) return "—";
    return new Intl.NumberFormat("vi-VN").format(v) + " ₫";
  }

  function parseTs(dateStr) {
    const s = String(dateStr || "");
    const d = Date.parse(s.includes("T") ? s : s.slice(0, 10) + "T12:00:00");
    return Number.isFinite(d) ? d : 0;
  }

  function getHour(dateStr) {
    const m = String(dateStr || "").match(/T(\d{2}):(\d{2})/);
    return m ? parseInt(m[1], 10) : 12;
  }

  function getMonth(dateStr) {
    return parseInt(String(dateStr || "").slice(5, 7), 10) || 0;
  }

  function getSeason(month) {
    if (SEASONS.dry.months.includes(month)) return SEASONS.dry;
    if (SEASONS.hot.months.includes(month)) return SEASONS.hot;
    return SEASONS.rainy;
  }

  function timeSlot(hour) {
    if (hour >= 22 || hour < 5) return "lateNight";
    if (hour < 11) return "morning";
    if (hour < 14) return "lunch";
    if (hour < 17) return "afternoon";
    return "evening";
  }

  function timeSlotLabel(slot) {
    return { morning: "Sáng", lunch: "Trưa", afternoon: "Chiều", evening: "Tối", lateNight: "Khuya" }[slot] || slot;
  }

  function categorizeDrink(name) {
    const n = norm(name);
    for (const [cat, keywords] of DRINK_CATEGORIES) {
      if (cat === "Other") continue;
      if (keywords.some((kw) => n.includes(kw))) return cat;
    }
    if (n.includes("ca phe") || n.includes("cafe") || n.includes("coffee")) return "Milk Coffee";
    return "Other";
  }

  function groupVisits(transactions) {
    const map = new Map();
    (transactions || []).forEach((t) => {
      const vid = t.visit_id || `${t.merchant}|${t.value_date || t.date.slice(0, 10)}|${t.txn_no?.split("-")[0] || ""}`;
      if (!map.has(vid)) {
        map.set(vid, {
          visit_id: vid,
          date: t.date,
          value_date: t.value_date || t.date.slice(0, 10),
          merchant: t.merchant || "Highlands Coffee",
          address: t.address || "",
          payment_method: t.payment_method || "",
          items: [],
          total: 0,
        });
      }
      const v = map.get(vid);
      v.items.push(t);
      v.total += safeNum(t.debit);
      if (!v.address && t.address) v.address = t.address;
      if (!v.payment_method && t.payment_method) v.payment_method = t.payment_method;
    });
    return Array.from(map.values()).sort((a, b) => parseTs(a.date) - parseTs(b.date));
  }

  function rollingAvg(values, window) {
    const out = [];
    let sum = 0;
    for (let i = 0; i < values.length; i++) {
      sum += values[i];
      if (i >= window) sum -= values[i - window];
      out.push(Math.round(sum / Math.min(i + 1, window) * 10) / 10);
    }
    return out;
  }

  function countInRange(visits, start, end) {
    return visits.filter((v) => {
      const ts = parseTs(v.date);
      return ts >= start && ts <= end;
    }).length;
  }

  function buildDna(visits, transactions) {
    const now = new Date();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - now.getDay());
    weekStart.setHours(0, 0, 0, 0);
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const yearStart = new Date(now.getFullYear(), 0, 1);

    const storeCounts = {};
    const drinkCounts = {};
    let totalSpend = 0;
    let maxOrder = { total: 0, date: "", merchant: "" };
    const timeSlots = { morning: 0, lunch: 0, afternoon: 0, evening: 0, lateNight: 0 };
    let weekday = 0;
    let weekend = 0;

    visits.forEach((v) => {
      totalSpend += v.total;
      const store = v.merchant || "Highlands Coffee";
      storeCounts[store] = (storeCounts[store] || 0) + 1;
      if (v.total > maxOrder.total) maxOrder = { total: v.total, date: v.value_date, merchant: store };
      const h = getHour(v.date);
      timeSlots[timeSlot(h)] += 1;
      const dow = new Date(v.value_date + "T12:00:00").getDay();
      if (dow === 0 || dow === 6) weekend += 1;
      else weekday += 1;
    });

    transactions.forEach((t) => {
      const name = t.description || "";
      drinkCounts[name] = (drinkCounts[name] || 0) + safeNum(t.qty) || 1;
    });

    const favStore = Object.entries(storeCounts).sort((a, b) => b[1] - a[1])[0];
    const favDrink = Object.entries(drinkCounts).sort((a, b) => b[1] - a[1])[0];

    // Longest visit streak (consecutive days with ≥1 visit)
    const visitDays = [...new Set(visits.map((v) => v.value_date))].sort();
    let streak = 0;
    let maxStreak = 0;
    let prev = null;
    visitDays.forEach((d) => {
      if (prev) {
        const diff = (Date.parse(d) - Date.parse(prev)) / 86400000;
        streak = diff === 1 ? streak + 1 : 1;
      } else {
        streak = 1;
      }
      maxStreak = Math.max(maxStreak, streak);
      prev = d;
    });

    const totalTime = weekday + weekend || 1;
    const totalSlot = Object.values(timeSlots).reduce((s, v) => s + v, 0) || 1;

    return {
      totalVisits: visits.length,
      thisWeek: countInRange(visits, weekStart.getTime(), now.getTime()),
      thisMonth: countInRange(visits, monthStart.getTime(), now.getTime()),
      thisYear: countInRange(visits, yearStart.getTime(), now.getTime()),
      avgBill: visits.length ? Math.round(totalSpend / visits.length) : 0,
      totalSpend,
      favoriteStore: favStore ? favStore[0] : "—",
      favoriteStoreVisits: favStore ? favStore[1] : 0,
      favoriteDrink: favDrink ? favDrink[0] : "—",
      favoriteDrinkCount: favDrink ? favDrink[1] : 0,
      longestStreak: maxStreak,
      mostExpensiveOrder: maxOrder,
      totalDrinks: transactions.reduce((s, t) => s + (safeNum(t.qty) || 1), 0),
      morningRatio: Math.round((timeSlots.morning / totalSlot) * 100),
      afternoonRatio: Math.round(((timeSlots.afternoon + timeSlots.lunch) / totalSlot) * 100),
      eveningRatio: Math.round((timeSlots.evening / totalSlot) * 100),
      lateNightRatio: Math.round((timeSlots.lateNight / totalSlot) * 100),
      weekdayRatio: Math.round((weekday / totalTime) * 100),
      weekendRatio: Math.round((weekend / totalTime) * 100),
    };
  }

  function buildTimeline(visits) {
    const daily = {};
    const weekly = {};
    const monthly = {};
    const yearly = {};

    visits.forEach((v) => {
      const d = v.value_date;
      const dt = new Date(d + "T12:00:00");
      const wk = `${dt.getFullYear()}-W${String(Math.ceil((dt.getDate() + 6 - dt.getDay()) / 7)).padStart(2, "0")}`;
      const mo = d.slice(0, 7);
      const yr = d.slice(0, 4);
      daily[d] = (daily[d] || 0) + 1;
      weekly[wk] = (weekly[wk] || 0) + 1;
      monthly[mo] = (monthly[mo] || 0) + 1;
      yearly[yr] = (yearly[yr] || 0) + 1;
    });

    const pack = (obj) => {
      const keys = Object.keys(obj).sort();
      const values = keys.map((k) => obj[k]);
      return { labels: keys, values, rolling: rollingAvg(values, 7) };
    };

    return { daily: pack(daily), weekly: pack(weekly), monthly: pack(monthly), yearly: pack(yearly) };
  }

  function buildDrinks(transactions) {
    const byName = {};
    const byCat = {};

    transactions.forEach((t) => {
      const name = t.description || "Khác";
      const cat = categorizeDrink(name);
      const qty = safeNum(t.qty) || 1;
      const spend = safeNum(t.debit);
      const hour = getHour(t.date);
      const slot = timeSlot(hour);

      if (!byName[name]) {
        byName[name] = { name, category: cat, count: 0, spend: 0, first: t.date, last: t.date, timeSlots: {} };
      }
      const d = byName[name];
      d.count += qty;
      d.spend += spend;
      if (t.date < d.first) d.first = t.date;
      if (t.date > d.last) d.last = t.date;
      d.timeSlots[slot] = (d.timeSlots[slot] || 0) + qty;

      if (!byCat[cat]) byCat[cat] = { category: cat, count: 0, spend: 0 };
      byCat[cat].count += qty;
      byCat[cat].spend += spend;
    });

    const topDrinks = Object.values(byName)
      .map((d) => ({
        ...d,
        avgPrice: d.count ? Math.round(d.spend / d.count) : 0,
        favoriteTime: timeSlotLabel(
          Object.entries(d.timeSlots).sort((a, b) => b[1] - a[1])[0]?.[0] || "afternoon"
        ),
        firstDate: d.first.slice(0, 10),
        lastDate: d.last.slice(0, 10),
      }))
      .sort((a, b) => b.count - a.count);

    const topCategories = Object.values(byCat).sort((a, b) => b.count - a.count);
    const signature = topDrinks[0]?.name || "—";

    return { topDrinks, topCategories, signature };
  }

  function buildClock(visits) {
    const grid = Array.from({ length: 7 }, () => Array(24).fill(0));
    visits.forEach((v) => {
      const dow = new Date(v.value_date + "T12:00:00").getDay();
      const h = getHour(v.date);
      grid[dow][h] += 1;
    });
    const max = Math.max(1, ...grid.flat());
    return { grid, dayNames: DAY_NAMES, max };
  }

  function buildSeasonality(transactions, visits) {
    const bySeason = { dry: {}, hot: {}, rainy: {} };
    const seasonSpend = { dry: 0, hot: 0, rainy: 0 };
    const seasonVisits = { dry: 0, hot: 0, rainy: 0 };

    transactions.forEach((t) => {
      const m = getMonth(t.date);
      const season = getSeason(m).id;
      const cat = categorizeDrink(t.description);
      bySeason[season][cat] = (bySeason[season][cat] || 0) + (safeNum(t.qty) || 1);
      seasonSpend[season] += safeNum(t.debit);
    });

    visits.forEach((v) => {
      const m = getMonth(v.date);
      seasonVisits[getSeason(m).id] += 1;
    });

    const prefs = {};
    ["dry", "hot", "rainy"].forEach((s) => {
      const cats = Object.entries(bySeason[s]).sort((a, b) => b[1] - a[1]);
      prefs[s] = cats[0] ? { category: cats[0][0], count: cats[0][1] } : null;
    });

    return { bySeason, seasonSpend, seasonVisits, prefs, seasons: SEASONS };
  }

  function buildPersonality(dna, drinks, clock, seasonality) {
    const traits = [];
    if (dna.weekdayRatio >= 65) traits.push("Người uống cà phê ngày thường");
    if (dna.weekendRatio >= 40) traits.push("Người thích cà phê cuối tuần");
    if (dna.morningRatio >= 45) traits.push("Tín đồ cà phê buổi sáng");
    if (dna.eveningRatio >= 35) traits.push("Thói quen sau giờ làm");
    if (dna.lateNightRatio >= 15) traits.push("Dân làm đêm");
    if (drinks.topCategories[0]?.category === "Tea") traits.push("Người của trà");
    if (drinks.topCategories[0]?.category === "Water") traits.push("Ưu tiên hydration");
    if (dna.avgBill >= 80000) traits.push("Chi tiêu premium");
    if (dna.totalVisits >= 5 && dna.longestStreak >= 3) traits.push("Người yêu thói quen");
    const storeVariety = new Set();
    // filled by caller if needed
    if (traits.length < 3) traits.push("Người khám phá Highlands");
    return traits.slice(0, 5);
  }

  function buildMonthlyReports(visits, transactions) {
    const byMonth = {};
    visits.forEach((v) => {
      const mo = v.value_date.slice(0, 7);
      if (!byMonth[mo]) byMonth[mo] = { month: mo, visits: 0, spend: 0, stores: {}, hours: [] };
      byMonth[mo].visits += 1;
      byMonth[mo].spend += v.total;
      byMonth[mo].stores[v.merchant] = (byMonth[mo].stores[v.merchant] || 0) + 1;
      byMonth[mo].hours.push(getHour(v.date));
    });

    transactions.forEach((t) => {
      const mo = t.date.slice(0, 7);
      if (!byMonth[mo]) return;
      if (!byMonth[mo].drinks) byMonth[mo].drinks = {};
      const n = t.description || "";
      byMonth[mo].drinks[n] = (byMonth[mo].drinks[n] || 0) + 1;
    });

    return Object.keys(byMonth)
      .sort()
      .map((mo) => {
        const m = byMonth[mo];
        const favStore = Object.entries(m.stores).sort((a, b) => b[1] - a[1])[0];
        const favDrink = m.drinks ? Object.entries(m.drinks).sort((a, b) => b[1] - a[1])[0] : null;
        const peakHour = m.hours.length
          ? m.hours.sort((a, b) =>
              m.hours.filter((h) => h === b).length - m.hours.filter((h) => h === a).length
            )[0]
          : null;
        return {
          month: mo,
          monthLabel: MONTH_NAMES[parseInt(mo.slice(5, 7), 10)] || mo,
          visits: m.visits,
          spend: m.spend,
          favoriteStore: favStore ? favStore[0] : "—",
          favoriteDrink: favDrink ? favDrink[0] : "—",
          peakTime: peakHour != null ? `${String(peakHour).padStart(2, "0")}:00` : "—",
          newDrinks: [],
        };
      });
  }

  function buildFunInsights(visits, transactions, dna, drinks) {
    const insights = [];
    const visitDays = [...new Set(visits.map((v) => v.value_date))].sort();
    let maxGap = 0;
    let gapStart = "";
    for (let i = 1; i < visitDays.length; i++) {
      const gap = (Date.parse(visitDays[i]) - Date.parse(visitDays[i - 1])) / 86400000;
      if (gap > maxGap) {
        maxGap = gap;
        gapStart = visitDays[i - 1];
      }
    }
    if (maxGap > 1) {
      insights.push(`Chuỗi không uống cà phê dài nhất: ${maxGap} ngày (sau ${gapStart}).`);
    }

    const weekdayCounts = [0, 0, 0, 0, 0, 0, 0];
    visits.forEach((v) => {
      weekdayCounts[new Date(v.value_date + "T12:00:00").getDay()] += 1;
    });
    const topDow = weekdayCounts.indexOf(Math.max(...weekdayCounts));
    if (visits.length) insights.push(`Ngày ghé nhiều nhất: ${DAY_NAMES[topDow]}.`);

    if (visits.length) {
      const peakHour = visits
        .map((v) => getHour(v.date))
        .sort((a, b) =>
          visits.filter((v) => getHour(v.date) === b).length -
          visits.filter((v) => getHour(v.date) === a).length
        )[0];
      insights.push(`Bạn thường mua cà phê khoảng ${String(peakHour).padStart(2, "0")}:00.`);
    }

    const payments = {};
    visits.forEach((v) => {
      if (v.payment_method) payments[v.payment_method] = (payments[v.payment_method] || 0) + 1;
    });
    const favPay = Object.entries(payments).sort((a, b) => b[1] - a[1])[0];
    if (favPay) insights.push(`Hình thức thanh toán ưa thích: ${favPay[0]}.`);

    if (visits.length >= 2) {
      const intervals = [];
      for (let i = 1; i < visits.length; i++) {
        intervals.push((parseTs(visits[i].date) - parseTs(visits[i - 1].date)) / 86400000);
      }
      const avgInt = Math.round(intervals.reduce((s, v) => s + v, 0) / intervals.length);
      insights.push(`Khoảng cách trung bình giữa các lần ghé: ${avgInt} ngày.`);
    }

    if (transactions.length) {
      const first = transactions.reduce((a, b) => (a.date < b.date ? a : b));
      insights.push(`Lần mua đầu tiên: ${first.description} (${first.date.slice(0, 10)}).`);
    }

    const milestones = [50, 100, 500, 1000];
    milestones.forEach((n) => {
      if (dna.totalDrinks >= n) insights.push(`Đã đạt mốc ${n} đồ uống!`);
    });

    return insights;
  }

  function buildDiscoveries(transactions, drinks) {
    const discoveries = [];
    const now = Date.now();
    const thirtyDays = 30 * 86400000;

    const recent = {};
    const older = {};
    transactions.forEach((t) => {
      const name = t.description || "";
      const ts = parseTs(t.date);
      const bucket = ts >= now - thirtyDays ? recent : older;
      bucket[name] = (bucket[name] || 0) + 1;
    });

    Object.keys(recent).forEach((name) => {
      if (!older[name]) discoveries.push({ type: "new", text: `Đồ uống mới: ${name}` });
    });

    Object.keys(older).forEach((name) => {
      if (!recent[name] && older[name] >= 3) {
        discoveries.push({ type: "abandoned", text: `Đã lâu không gọi: ${name}` });
      }
    });

    if (drinks.topDrinks.length >= 2) {
      const sig = drinks.topDrinks[0].name;
      discoveries.push({ type: "tip", text: `Signature drink của bạn: ${sig}` });
    }

    return discoveries;
  }

  function buildJourney(visits, transactions) {
    const milestones = [];
    if (visits.length) {
      milestones.push({ n: 1, label: "Lần đầu tiên", date: visits[0].value_date, detail: visits[0].merchant });
    }
    [50, 100, 500, 1000].forEach((n) => {
      if (visits.length >= n) {
        milestones.push({ n, label: `Lần thứ ${n}`, date: visits[n - 1].value_date, detail: formatVnd(visits[n - 1].total) });
      }
    });
    if (transactions.length) {
      const total = transactions.reduce((s, t) => s + (safeNum(t.qty) || 1), 0);
      [100, 500, 1000].forEach((n) => {
        if (total >= n) milestones.push({ n, label: `${n} đồ uống`, date: "—", detail: "Mốc tích lũy" });
      });
    }
    return milestones;
  }

  function buildExecutiveSummary(dna, drinks, seasonality, geoHint) {
    const lines = [];
    if (dna.weekdayRatio >= 60) lines.push("Bạn là người uống cà phê ngày thường.");
    else if (dna.weekendRatio >= 40) lines.push("Bạn thích ghé Highlands vào cuối tuần.");
    if (dna.eveningRatio >= 30) lines.push("Phần lớn lần mua diễn ra sau giờ làm.");
    lines.push(`Signature drink: ${drinks.signature}.`);
    if (geoHint) lines.push(geoHint);
    const rainy = seasonality.prefs.rainy;
    const hot = seasonality.prefs.hot;
    if (rainy) lines.push(`Mùa mưa bạn thường chọn ${rainy.category}.`);
    if (hot) lines.push(`Mùa nóng bạn ưa ${hot.category}.`);
    if (dna.longestStreak >= 3) lines.push("Thói quen cà phê đang trở nên đều đặn hơn.");
    return lines.join(" ");
  }

  function buildAnnualReport(dna, drinks, monthly, seasonality, personality, year) {
    const yr = year || String(new Date().getFullYear());
    const yearMonths = monthly.filter((m) => m.month.startsWith(yr));
    return {
      year: yr,
      executiveSummary: buildExecutiveSummary(dna, drinks, seasonality, ""),
      highlights: [
        { label: "Tổng lần ghé", value: dna.totalVisits },
        { label: "Tổng chi tiêu", value: formatVnd(dna.totalSpend) },
        { label: "Hóa đơn TB", value: formatVnd(dna.avgBill) },
        { label: "Chuỗi dài nhất", value: `${dna.longestStreak} ngày` },
      ],
      favoriteDrinks: drinks.topDrinks.slice(0, 5),
      favoriteStores: dna.favoriteStore,
      seasonality,
      monthlyTrend: yearMonths,
      personality,
      discoveries: drinks.signature,
    };
  }

  function buildCoffeePayload(transactions) {
    const txns = Array.isArray(transactions) ? transactions : [];
    const visits = groupVisits(txns);
    const dna = buildDna(visits, txns);
    const timeline = buildTimeline(visits);
    const drinks = buildDrinks(txns);
    const clock = buildClock(visits);
    const seasonality = buildSeasonality(txns, visits);
    const personality = buildPersonality(dna, drinks, clock, seasonality);
    const monthlyReports = buildMonthlyReports(visits, txns);
    const funInsights = buildFunInsights(visits, txns, dna, drinks);
    const discoveries = buildDiscoveries(txns, drinks);
    const journey = buildJourney(visits, txns);
    const annualReport = buildAnnualReport(dna, drinks, monthlyReports, seasonality, personality);
    const executiveSummary = buildExecutiveSummary(dna, drinks, seasonality, "");

    const narrativeInsights = [
      `Signature drink: ${drinks.signature}.`,
      dna.weekdayRatio >= 60
        ? "Bạn là weekday coffee drinker."
        : "Bạn thường ghé Highlands vào cuối tuần.",
      `Cửa hàng yêu thích: ${dna.favoriteStore} (${dna.favoriteStoreVisits} lần).`,
      `Hóa đơn trung bình: ${formatVnd(dna.avgBill)}.`,
    ];

    if (seasonality.prefs.hot) {
      narrativeInsights.push(`Mùa nóng bạn ưa ${seasonality.prefs.hot.category}.`);
    }
    if (seasonality.prefs.rainy) {
      narrativeInsights.push(`Mùa mưa bạn hay chọn ${seasonality.prefs.rainy.category}.`);
    }

    return {
      visits,
      dna,
      timeline,
      drinks,
      clock,
      seasonality,
      personality,
      monthlyReports,
      annualReport,
      funInsights,
      discoveries,
      journey,
      executiveSummary,
      narrativeInsights: [...narrativeInsights, ...funInsights].slice(0, 10),
      charts: {
        timeline,
        drinks,
        clock,
        seasonality,
      },
    };
  }

  const api = {
    buildCoffeePayload,
    groupVisits,
    categorizeDrink,
    getSeason,
    formatVnd,
    DRINK_CATEGORIES,
    SEASONS,
  };
  global.HDashboardCoffee = api;
  if (typeof window !== "undefined") window.HDashboardCoffee = api;
})(typeof window !== "undefined" ? window : globalThis);