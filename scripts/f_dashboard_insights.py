"""Financial insights, health scoring, and chart datasets for F-Dashboard."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

EXPENSE_CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("Ăn uống", ("an uong", "food", "cafe", "starbucks", "grab food", "shopeefood", "lotteria", "kfc", "pizza", "com ", "bun ", "pho ", "highlands", "the coffee")),
    ("Chuyển tiền", ("chuyen tien", "chuyen khoan", "qr -", "ck ")),
    ("Mua sắm", ("shopee", "lazada", "tiki", "amazon", "sendo")),
    ("Di chuyển", ("grab", "be group", "gojek", "xang", "petrol", "shell", "vinfast")),
    ("Giải trí", ("netflix", "spotify", "game", "cgv", "youtube", "apple.com")),
    ("Hóa đơn", ("dien ", "nuoc ", "internet", "fpt", "viettel", "mobifone")),
]

HEALTH_LABELS = (
    (85, "Excellent"),
    (70, "Good"),
    (50, "Average"),
    (30, "Risky"),
    (0, "Danger"),
)


def _parse_iso(date_str: str) -> datetime:
    return datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")


def _norm_desc(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def categorize_expense(description: str) -> str:
    norm = _norm_desc(description)
    for label, keywords in EXPENSE_CATEGORIES:
        if any(kw in norm for kw in keywords):
            return label
    return "Khác"


def compute_summary(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    income = sum(t["amount"] for t in transactions if t["amount"] > 0)
    expense = abs(sum(t["amount"] for t in transactions if t["amount"] < 0))
    net = income - expense
    count = len(transactions)

    date_from = ""
    date_to = ""
    if transactions:
        dates = sorted(t["date"] for t in transactions)
        date_from = dates[0][:10]
        date_to = dates[-1][:10]

    return {
        "total_income": income,
        "total_expense": expense,
        "net_cash_flow": net,
        "transaction_count": count,
        "date_from": date_from,
        "date_to": date_to,
    }


def financial_health(summary: dict[str, Any]) -> dict[str, Any]:
    income = summary["total_income"]
    expense = summary["total_expense"]
    net = summary["net_cash_flow"]

    saving_rate = (net / income) if income > 0 else 0.0
    expense_ratio = (expense / income) if income > 0 else 1.0

    score = 0.0
    if income > 0:
        score += min(45.0, max(0.0, saving_rate * 100 * 0.9))
        score += max(0.0, 25.0 - expense_ratio * 25.0)
    if net > 0:
        score += 15.0
    elif net < 0:
        score -= 10.0
    if summary["transaction_count"] >= 10:
        score += 5.0
    if summary["date_from"] and summary["date_to"]:
        try:
            span = (_parse_iso(summary["date_to"] + "T00:00:00") - _parse_iso(summary["date_from"] + "T00:00:00")).days
            if span >= 60:
                score += 10.0
        except ValueError:
            pass

    score = max(0.0, min(100.0, round(score, 1)))
    label = "Danger"
    for threshold, name in HEALTH_LABELS:
        if score >= threshold:
            label = name
            break

    return {
        "saving_rate": round(saving_rate, 4),
        "expense_ratio": round(expense_ratio, 4),
        "net_cash_flow": net,
        "financial_score": score,
        "health_label": label,
    }


def _month_key(date_str: str) -> str:
    return date_str[:7]


def _day_month(date_str: str) -> str:
    s = str(date_str or "")
    day = s[8:10]
    month = s[5:7]
    if day and month:
        return f"{day}/{month}"
    return s[:10]


def _short_label(text: Any, max_len: int = 28) -> str:
    s = re.sub(r"\s+", " ", str("" if text is None else text)).strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _rolling_average(values: list[int], window: int) -> list[int]:
    out: list[int] = []
    running = 0
    for i, v in enumerate(values):
        running += v
        if i >= window:
            running -= values[i - window]
        span = min(i + 1, window)
        out.append(round(running / span) if span > 0 else 0)
    return out


def chart_datasets(transactions: list[dict[str, Any]], health: dict[str, Any]) -> dict[str, Any]:
    income = sum(t["amount"] for t in transactions if t["amount"] > 0)
    expense = abs(sum(t["amount"] for t in transactions if t["amount"] < 0))

    donut = {
        "labels": ["Thu", "Chi"],
        "values": [income, expense],
    }

    gauge = {
        "score": health["financial_score"],
        "label": health["health_label"],
    }

    # balanceTimeline: running balance per txn, sorted by date asc.
    by_date = sorted(transactions, key=lambda t: str(t.get("date", "")))
    balance_series = [t.get("balance", 0) or 0 for t in by_date]
    bal_avg = round(sum(balance_series) / len(balance_series)) if balance_series else 0
    bal_min = min(balance_series) if balance_series else 0
    balance_timeline = {
        "labels": [_day_month(t.get("date", "")) for t in by_date],
        "balance": balance_series,
        "avg": bal_avg,
        "min": bal_min,
    }

    # dailyNet: Σ amount per calendar day + 7-day rolling average.
    day_totals: dict[str, int] = defaultdict(int)
    for tx in transactions:
        day = str(tx.get("date", ""))[:10]
        if day:
            day_totals[day] += tx["amount"]
    days = sorted(day_totals.keys())
    net_series = [round(day_totals[d]) for d in days]
    daily_net = {
        "labels": [_day_month(d) for d in days],
        "net": net_series,
        "rolling": _rolling_average(net_series, 7),
    }

    # topTxns: diverging top-5 incomes + top-5 expenses.
    expenses = sorted(
        (t for t in transactions if t["amount"] < 0),
        key=lambda t: abs(t["amount"]),
        reverse=True,
    )[:5]
    incomes = sorted(
        (t for t in transactions if t["amount"] > 0),
        key=lambda t: t["amount"],
        reverse=True,
    )[:5]

    def _to_item(t: dict[str, Any]) -> dict[str, Any]:
        return {
            "label": _short_label(t.get("description", "")),
            "date": _day_month(t.get("date", "")),
            "value": t["amount"],
        }

    items = sorted((_to_item(t) for t in incomes), key=lambda x: -x["value"]) + sorted(
        (_to_item(t) for t in expenses), key=lambda x: -x["value"]
    )

    recurring_groups: dict[str, int] = defaultdict(int)
    for tx in transactions:
        amt = tx["amount"]
        if amt == 0:
            continue
        bucket = round(abs(amt) / 1000) * 1000
        prefix = _norm_desc(tx["description"])[:12]
        recurring_groups[f"{bucket}|{prefix}"] += 1
    recurring = sum(1 for c in recurring_groups.values() if c >= 2)

    return {
        "donut": donut,
        "gauge": gauge,
        "balanceTimeline": balance_timeline,
        "dailyNet": daily_net,
        "topTxns": {"items": items, "recurring": recurring},
    }


def _keyword_trend(
    transactions: list[dict[str, Any]],
    keyword: str,
    *,
    window_days: int = 30,
) -> dict[str, Any] | None:
    if not transactions:
        return None
    latest = max(_parse_iso(t["date"]) for t in transactions)
    recent_start = latest - timedelta(days=window_days)
    prior_start = latest - timedelta(days=window_days * 2)
    kw = keyword.lower()

    recent = 0
    prior = 0
    for tx in transactions:
        if tx["amount"] >= 0:
            continue
        if kw not in _norm_desc(tx["description"]):
            continue
        dt = _parse_iso(tx["date"])
        if dt >= recent_start:
            recent += abs(tx["amount"])
        elif dt >= prior_start:
            prior += abs(tx["amount"])

    if recent == 0 and prior == 0:
        return None
    return {"keyword": keyword, "recent": recent, "prior": prior, "delta": recent - prior}


def generate_insights(
    transactions: list[dict[str, Any]],
    summary: dict[str, Any],
    health: dict[str, Any],
) -> list[str]:
    insights: list[str] = []
    expense = summary["total_expense"]

    if expense > 0:
        category_totals: dict[str, int] = defaultdict(int)
        for tx in transactions:
            if tx["amount"] < 0:
                category_totals[categorize_expense(tx["description"])] += abs(tx["amount"])
        if category_totals:
            top_cat, top_val = max(category_totals.items(), key=lambda x: x[1])
            pct = round(top_val / expense * 100)
            insights.append(f"Chi tiêu {top_cat.lower()} chiếm {pct}% tổng chi.")

    if summary["total_income"] > 0:
        sr_pct = round(health["saving_rate"] * 100)
        insights.append(f"Tỷ lệ tiết kiệm hiện đạt {sr_pct}%.")

    if transactions:
        now = max(_parse_iso(t["date"]) for t in transactions)
        mk = now.strftime("%m/%Y")
        month_net = sum(
            t["amount"]
            for t in transactions
            if _month_key(t["date"]) == now.strftime("%Y-%m")
        )
        tone = "tích cực" if month_net >= 0 else "âm"
        insights.append(f"Dòng tiền tháng {mk} đang {tone}.")

    for kw in ("starbucks", "grab", "shopee"):
        trend = _keyword_trend(transactions, kw)
        if trend and trend["delta"] > 0 and trend["recent"] > 0:
            insights.append(
                f"Có dấu hiệu tăng chi tiêu {kw.title()} trong 30 ngày gần nhất."
            )
            break

    if health["expense_ratio"] > 0.9 and summary["total_income"] > 0:
        insights.append("Tỷ lệ chi/thu trên 90% — cần theo dõi chi tiêu chặt hơn.")

    recurring_groups: dict[str, int] = defaultdict(int)
    for tx in transactions:
        amt = tx["amount"]
        if amt == 0:
            continue
        bucket = round(abs(amt) / 1000) * 1000
        prefix = _norm_desc(tx["description"])[:12]
        recurring_groups[f"{bucket}|{prefix}"] += 1
    recurring_count = sum(1 for c in recurring_groups.values() if c >= 2)
    if recurring_count > 0:
        insights.append(f"Phát hiện {recurring_count} khoản chi/thu lặp lại (có thể là định kỳ).")

    if not insights:
        insights.append("Chưa đủ dữ liệu để phân tích sâu — hãy upload thêm sao kê.")

    return insights


def build_insights_payload(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    summary = compute_summary(transactions)
    health = financial_health(summary)
    charts = chart_datasets(transactions, health)
    insights = generate_insights(transactions, summary, health)
    return {
        "summary": summary,
        "health": health,
        "charts": charts,
        "insights": insights,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute F-Dashboard insights from transaction JSON")
    parser.add_argument("json_file", type=argparse.FileType("r", encoding="utf-8"), help="JSON array of transactions")
    args = parser.parse_args()

    data = json.load(args.json_file)
    if isinstance(data, dict):
        transactions = data.get("transactions", data.get("new_transactions", []))
    else:
        transactions = data

    payload = build_insights_payload(transactions)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())