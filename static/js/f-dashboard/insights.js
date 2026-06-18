/**
 * Financial insights — mirrors scripts/f_dashboard_insights.py
 */
(function (global) {
  "use strict";

  const EXPENSE_CATEGORIES = [
    ["Ăn uống", ["an uong", "food", "cafe", "starbucks", "grab food", "shopeefood", "lotteria", "kfc", "pizza", "com ", "bun ", "pho ", "highlands", "the coffee"]],
    ["Chuyển tiền", ["chuyen tien", "chuyen khoan", "qr -", "ck "]],
    ["Mua sắm", ["shopee", "lazada", "tiki", "amazon", "sendo"]],
    ["Di chuyển", ["grab", "be group", "gojek", "xang", "petrol", "shell", "vinfast"]],
    ["Giải trí", ["netflix", "spotify", "game", "cgv", "youtube", "apple.com"]],
    ["Hóa đơn", ["dien ", "nuoc ", "internet", "fpt", "viettel", "mobifone"]],
  ];

  const HEALTH_LABELS = [
    [85, "Excellent"],
    [70, "Good"],
    [50, "Average"],
    [30, "Risky"],
    [0, "Danger"],
  ];

  const HEALTH_LEVELS = [
    { min: 85, label: "Excellent", range: "≥ 85", desc: "Tích lũy mạnh, chi tiêu kiểm soát, dòng tiền dương ổn định." },
    { min: 70, label: "Good", range: "70 – 84", desc: "Cân bằng tốt — tiết kiệm đủ, chi tiêu hợp lý so với thu nhập." },
    { min: 50, label: "Average", range: "50 – 69", desc: "Trung bình — cần theo dõi chi tiêu, tỷ lệ chi/thu còn cao." },
    { min: 30, label: "Risky", range: "30 – 49", desc: "Rủi ro — chi gần hoặc vượt thu, ít dư tiền mặt." },
    { min: 0, label: "Danger", range: "< 30", desc: "Nguy hiểm — thâm hụt kéo dài, cần cắt giảm chi ngay." },
  ];

  function normDesc(text) {
    return String(text).toLowerCase().trim().replace(/\s+/g, " ");
  }

  function categorizeExpense(description) {
    const norm = normDesc(description);
    for (const [label, keywords] of EXPENSE_CATEGORIES) {
      if (keywords.some((kw) => norm.includes(kw))) return label;
    }
    return "Khác";
  }

  function computeSummary(transactions) {
    let income = 0;
    let expense = 0;
    transactions.forEach((t) => {
      if (t.amount > 0) income += t.amount;
      else expense += Math.abs(t.amount);
    });

    const dates = transactions.map((t) => t.date).sort();
    return {
      total_income: income,
      total_expense: expense,
      net_cash_flow: income - expense,
      transaction_count: transactions.length,
      date_from: dates[0] ? dates[0].slice(0, 10) : "",
      date_to: dates.length ? dates[dates.length - 1].slice(0, 10) : "",
    };
  }

  function financialHealth(summary) {
    const income = summary.total_income;
    const expense = summary.total_expense;
    const net = summary.net_cash_flow;

    const savingRate = income > 0 ? net / income : 0;
    const expenseRatio = income > 0 ? expense / income : 1;

    let score = 0;
    if (income > 0) {
      score += Math.min(45, Math.max(0, savingRate * 100 * 0.9));
      score += Math.max(0, 25 - expenseRatio * 25);
    }
    if (net > 0) score += 15;
    else if (net < 0) score -= 10;
    if (summary.transaction_count >= 10) score += 5;
    if (summary.date_from && summary.date_to) {
      const from = new Date(summary.date_from);
      const to = new Date(summary.date_to);
      if ((to - from) / 86400000 >= 60) score += 10;
    }

    score = Math.max(0, Math.min(100, Math.round(score * 10) / 10));
    let label = "Danger";
    for (const [threshold, name] of HEALTH_LABELS) {
      if (score >= threshold) {
        label = name;
        break;
      }
    }

    return {
      saving_rate: Math.round(savingRate * 10000) / 10000,
      expense_ratio: Math.round(expenseRatio * 10000) / 10000,
      net_cash_flow: net,
      financial_score: score,
      health_label: label,
    };
  }

  function monthKey(dateStr) {
    return dateStr.slice(0, 7);
  }

  // --- helpers shared by the new analytics layer ---------------------------
  function safeNum(n) {
    const v = Number(n);
    return Number.isFinite(v) ? v : 0;
  }

  function dayMonth(dateStr) {
    // ISO 'YYYY-MM-DDTHH:MM:SS' -> 'DD/MM' (display, never machine readable).
    const s = String(dateStr || "");
    const d = s.slice(8, 10);
    const m = s.slice(5, 7);
    if (d && m) return `${d}/${m}`;
    return s.slice(0, 10);
  }

  function shortLabel(text, max = 28) {
    const s = String(text == null ? "" : text).replace(/\s+/g, " ").trim();
    if (s.length <= max) return s;
    return s.slice(0, max - 1).trimEnd() + "…";
  }

  function rollingAverage(values, window) {
    // Aligned trailing rolling mean: out[i] = mean(values[max(0,i-w+1)..i]).
    const out = [];
    let sum = 0;
    for (let i = 0; i < values.length; i += 1) {
      sum += values[i];
      if (i >= window) sum -= values[i - window];
      const span = Math.min(i + 1, window);
      out.push(span > 0 ? Math.round(sum / span) : 0);
    }
    return out;
  }

  function chartDatasets(transactions, health) {
    const txns = Array.isArray(transactions) ? transactions : [];
    let income = 0;
    let expense = 0;
    txns.forEach((t) => {
      const amt = safeNum(t.amount);
      if (amt > 0) income += amt;
      else expense += Math.abs(amt);
    });

    // --- balanceTimeline: running balance per txn, sorted by date asc ------
    const byDate = txns
      .slice()
      .sort((a, b) => String(a.date).localeCompare(String(b.date)));
    const balanceLabels = byDate.map((t) => dayMonth(t.date));
    const balanceSeries = byDate.map((t) => safeNum(t.balance));
    const balAvg = balanceSeries.length
      ? Math.round(balanceSeries.reduce((s, v) => s + v, 0) / balanceSeries.length)
      : 0;
    const balMin = balanceSeries.length ? Math.min(...balanceSeries) : 0;
    const balanceTimeline = {
      labels: balanceLabels,
      balance: balanceSeries,
      avg: balAvg,
      min: balMin,
    };

    // --- dailyNet: Σ amount per calendar day + 7-day rolling average -------
    const dayTotals = {};
    txns.forEach((t) => {
      const day = String(t.date || "").slice(0, 10);
      if (!day) return;
      dayTotals[day] = (dayTotals[day] || 0) + safeNum(t.amount);
    });
    const days = Object.keys(dayTotals).sort();
    const netSeries = days.map((d) => Math.round(dayTotals[d]));
    const dailyNet = {
      labels: days.map((d) => dayMonth(d)),
      net: netSeries,
      rolling: rollingAverage(netSeries, 7),
    };

    // --- topTxns: diverging top-5 incomes + top-5 expenses ----------------
    const expenses = txns
      .filter((t) => safeNum(t.amount) < 0)
      .sort((a, b) => Math.abs(safeNum(b.amount)) - Math.abs(safeNum(a.amount)))
      .slice(0, 5);
    const incomes = txns
      .filter((t) => safeNum(t.amount) > 0)
      .sort((a, b) => safeNum(b.amount) - safeNum(a.amount))
      .slice(0, 5);
    const toItem = (t) => ({
      label: shortLabel(t.description),
      date: dayMonth(t.date),
      value: safeNum(t.amount),
    });
    // Incomes (positive/teal) on top, expenses (negative/red) below — sorted
    // so the diverging horizontal bar reads high→low across the zero axis.
    const items = [
      ...incomes.map(toItem).sort((a, b) => b.value - a.value),
      ...expenses.map(toItem).sort((a, b) => b.value - a.value),
    ];

    // recurring: same rounded magnitude + desc prefix appearing >= 2 times.
    const recurringGroups = {};
    txns.forEach((t) => {
      const amt = safeNum(t.amount);
      if (amt === 0) return;
      const bucket = Math.round(Math.abs(amt) / 1000) * 1000;
      const prefix = normDesc(t.description).slice(0, 12);
      const key = `${bucket}|${prefix}`;
      recurringGroups[key] = (recurringGroups[key] || 0) + 1;
    });
    const recurring = Object.values(recurringGroups).filter((c) => c >= 2).length;

    return {
      donut: { labels: ["Thu", "Chi"], values: [income, expense] },
      gauge: { score: health.financial_score, label: health.health_label },
      balanceTimeline,
      dailyNet,
      topTxns: { items, recurring },
    };
  }

  function keywordTrend(transactions, keyword, windowDays = 30) {
    if (!transactions.length) return null;
    const latest = Math.max(...transactions.map((t) => new Date(t.date).getTime()));
    const recentStart = latest - windowDays * 86400000;
    const priorStart = latest - windowDays * 2 * 86400000;
    const kw = keyword.toLowerCase();

    let recent = 0;
    let prior = 0;
    transactions.forEach((t) => {
      if (t.amount >= 0) return;
      if (!normDesc(t.description).includes(kw)) return;
      const ts = new Date(t.date).getTime();
      const amt = Math.abs(t.amount);
      if (ts >= recentStart) recent += amt;
      else if (ts >= priorStart) prior += amt;
    });

    if (recent === 0 && prior === 0) return null;
    return { keyword, recent, prior, delta: recent - prior };
  }

  function generateInsights(transactions, summary, health) {
    const insights = [];
    const expense = summary.total_expense;

    if (expense > 0) {
      const categoryTotals = {};
      transactions.forEach((t) => {
        if (t.amount < 0) {
          const cat = categorizeExpense(t.description);
          categoryTotals[cat] = (categoryTotals[cat] || 0) + Math.abs(t.amount);
        }
      });
      const entries = Object.entries(categoryTotals);
      if (entries.length) {
        const [topCat, topVal] = entries.sort((a, b) => b[1] - a[1])[0];
        const pct = Math.round((topVal / expense) * 100);
        insights.push(`Chi tiêu ${topCat.toLowerCase()} chiếm ${pct}% tổng chi.`);
      }
    }

    if (summary.total_income > 0) {
      const srPct = Math.round(health.saving_rate * 100);
      insights.push(`Tỷ lệ tiết kiệm hiện đạt ${srPct}%.`);
    }

    if (transactions.length) {
      const latest = new Date(
        Math.max(...transactions.map((t) => new Date(t.date).getTime()))
      );
      const mk = `${String(latest.getMonth() + 1).padStart(2, "0")}/${latest.getFullYear()}`;
      const monthKeyStr = `${latest.getFullYear()}-${String(latest.getMonth() + 1).padStart(2, "0")}`;
      const monthNet = transactions
        .filter((t) => monthKey(t.date) === monthKeyStr)
        .reduce((s, t) => s + t.amount, 0);
      const tone = monthNet >= 0 ? "tích cực" : "âm";
      insights.push(`Dòng tiền tháng ${mk} đang ${tone}.`);
    }

    for (const kw of ["starbucks", "grab", "shopee"]) {
      const trend = keywordTrend(transactions, kw);
      if (trend && trend.delta > 0 && trend.recent > 0) {
        insights.push(`Có dấu hiệu tăng chi tiêu ${kw.charAt(0).toUpperCase() + kw.slice(1)} trong 30 ngày gần nhất.`);
        break;
      }
    }

    if (health.expense_ratio > 0.9 && summary.total_income > 0) {
      insights.push("Tỷ lệ chi/thu trên 90% — cần theo dõi chi tiêu chặt hơn.");
    }

    const recurringGroups = {};
    transactions.forEach((t) => {
      const amt = Number(t.amount);
      if (!Number.isFinite(amt) || amt === 0) return;
      const bucket = Math.round(Math.abs(amt) / 1000) * 1000;
      const prefix = normDesc(t.description).slice(0, 12);
      const key = `${bucket}|${prefix}`;
      recurringGroups[key] = (recurringGroups[key] || 0) + 1;
    });
    const recurringCount = Object.values(recurringGroups).filter((c) => c >= 2).length;
    if (recurringCount > 0) {
      insights.push(`Phát hiện ${recurringCount} khoản chi/thu lặp lại (có thể là định kỳ).`);
    }

    if (!insights.length) {
      insights.push("Chưa đủ dữ liệu để phân tích sâu — hãy upload thêm sao kê.");
    }

    return insights;
  }

  function buildInsightsPayload(transactions) {
    const summary = computeSummary(transactions);
    const health = financialHealth(summary);
    const charts = chartDatasets(transactions, health);
    const insights = generateInsights(transactions, summary, health);
    return { summary, health, charts, insights };
  }

  function formatVnd(n) {
    // Display guard: never surface NaN/undefined/null — fall back to em dash.
    if (n === null || n === undefined || typeof n !== "number" || !Number.isFinite(n)) {
      return "—";
    }
    return new Intl.NumberFormat("vi-VN").format(n) + " ₫";
  }

  global.FDashboardInsights = {
    HEALTH_LEVELS,
    buildInsightsPayload,
    categorizeExpense,
    computeSummary,
    financialHealth,
    formatVnd,
  };
})(typeof window !== "undefined" ? window : globalThis);