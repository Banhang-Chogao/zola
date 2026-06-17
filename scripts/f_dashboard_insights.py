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


def chart_datasets(transactions: list[dict[str, Any]], health: dict[str, Any]) -> dict[str, Any]:
    income = sum(t["amount"] for t in transactions if t["amount"] > 0)
    expense = abs(sum(t["amount"] for t in transactions if t["amount"] < 0))

    donut = {
        "labels": ["Thu", "Chi"],
        "values": [income, expense],
    }

    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"income": 0, "expense": 0, "net": 0})
    for tx in transactions:
        mk = _month_key(tx["date"])
        if tx["amount"] > 0:
            monthly[mk]["income"] += tx["amount"]
        else:
            monthly[mk]["expense"] += abs(tx["amount"])
        monthly[mk]["net"] += tx["amount"]

    months = sorted(monthly.keys())
    area = {
        "labels": months,
        "income": [monthly[m]["income"] for m in months],
        "expense": [monthly[m]["expense"] for m in months],
        "net": [monthly[m]["net"] for m in months],
    }

    category_totals: dict[str, int] = defaultdict(int)
    for tx in transactions:
        if tx["amount"] < 0:
            cat = categorize_expense(tx["description"])
            category_totals[cat] += abs(tx["amount"])

    treemap = [
        {"label": k, "value": v}
        for k, v in sorted(category_totals.items(), key=lambda x: -x[1])
    ]

    waterfall_labels = ["Tổng thu"] + months + ["Ròng"]
    waterfall_values: list[int] = [income]
    running = income
    for m in months:
        delta = monthly[m]["net"]
        waterfall_values.append(delta)
        running += 0
    waterfall_values.append(summary_net := income - expense)

    waterfall = {
        "labels": waterfall_labels,
        "values": waterfall_values,
        "summary_net": summary_net,
    }

    gauge = {
        "score": health["financial_score"],
        "label": health["health_label"],
    }

    return {
        "donut": donut,
        "area": area,
        "treemap": treemap,
        "waterfall": waterfall,
        "gauge": gauge,
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