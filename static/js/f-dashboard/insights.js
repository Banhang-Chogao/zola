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

  function chartDatasets(transactions, health) {
    let income = 0;
    let expense = 0;
    const monthly = {};

    transactions.forEach((t) => {
      const mk = monthKey(t.date);
      if (!monthly[mk]) monthly[mk] = { income: 0, expense: 0, net: 0 };
      if (t.amount > 0) {
        income += t.amount;
        monthly[mk].income += t.amount;
      } else {
        expense += Math.abs(t.amount);
        monthly[mk].expense += Math.abs(t.amount);
      }
      monthly[mk].net += t.amount;
    });

    const months = Object.keys(monthly).sort();
    const categoryTotals = {};

    transactions.forEach((t) => {
      if (t.amount < 0) {
        const cat = categorizeExpense(t.description);
        categoryTotals[cat] = (categoryTotals[cat] || 0) + Math.abs(t.amount);
      }
    });

    const treemap = Object.entries(categoryTotals)
      .sort((a, b) => b[1] - a[1])
      .map(([label, value]) => ({ label, value }));

    const waterfallLabels = ["Tổng thu", ...months, "Ròng"];
    const waterfallValues = [income, ...months.map((m) => monthly[m].net), income - expense];

    return {
      donut: { labels: ["Thu", "Chi"], values: [income, expense] },
      area: {
        labels: months,
        income: months.map((m) => monthly[m].income),
        expense: months.map((m) => monthly[m].expense),
        net: months.map((m) => monthly[m].net),
      },
      treemap,
      waterfall: {
        labels: waterfallLabels,
        values: waterfallValues,
        summary_net: income - expense,
      },
      gauge: { score: health.financial_score, label: health.health_label },
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
    return new Intl.NumberFormat("vi-VN").format(n) + " ₫";
  }

  global.FDashboardInsights = {
    buildInsightsPayload,
    categorizeExpense,
    computeSummary,
    financialHealth,
    formatVnd,
  };
})(typeof window !== "undefined" ? window : globalThis);