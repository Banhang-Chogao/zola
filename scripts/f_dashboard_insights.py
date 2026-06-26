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

# Recognizable brands spotlighted individually in insights (keyword -> display
# name). Matched against normalized descriptions via _keyword_trend().
MERCHANT_WATCH: list[tuple[str, str]] = [
    ("starbucks", "Starbucks"),
    ("highlands", "Highlands Coffee"),
    ("the coffee", "The Coffee House"),
    ("phuc long", "Phúc Long"),
    ("grab", "Grab"),
    ("gojek", "Gojek"),
    ("be group", "Be"),
    ("shopee", "Shopee"),
    ("lazada", "Lazada"),
    ("tiki", "Tiki"),
    ("netflix", "Netflix"),
    ("spotify", "Spotify"),
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


def _format_vnd(n: Any) -> str:
    """Display guard mirroring formatVnd in insights.js."""
    try:
        v = float(n)
    except (TypeError, ValueError):
        return "—"
    if v != v or v in (float("inf"), float("-inf")):
        return "—"
    return f"{int(round(v)):,}".replace(",", ".") + " ₫"


def _safe_num(n: Any) -> float:
    try:
        v = float(n)
    except (TypeError, ValueError):
        return 0.0
    return v if v == v and v not in (float("inf"), float("-inf")) else 0.0


def generate_insights(
    transactions: list[dict[str, Any]],
    summary: dict[str, Any],
    health: dict[str, Any],
    charts: dict[str, Any] | None = None,
) -> list[str]:
    """Deterministic, network-free insights engine.

    Mirrors generateInsights() in static/js/{f,l}-dashboard/insights.js: each rule
    is a guarded push (only fires when data supports it), every divisor is checked,
    no NaN/empty leaks (money via _format_vnd, percents via round), priority order,
    then capped to the top 7. Reuses the already-computed `charts` payload.
    """
    insights: list[str] = []
    txns = transactions or []
    s = summary or {}
    h = health or {}
    c = charts or {}

    income = _safe_num(s.get("total_income"))
    expense = _safe_num(s.get("total_expense"))
    count = _safe_num(s.get("transaction_count"))

    balance_timeline = c.get("balanceTimeline") or {}
    bal_labels = balance_timeline.get("labels") or []
    bal_series = balance_timeline.get("balance") or []
    last_balance = (
        _safe_num(bal_series[-1]) if bal_series else _safe_num(h.get("last_balance"))
    )
    daily_net = c.get("dailyNet") or {}
    dn_labels = daily_net.get("labels") or []
    dn_net = daily_net.get("net") or []
    top_txns = c.get("topTxns") or {}
    top_items = top_txns.get("items") or []

    # 1. Net cash flow for the period.
    if count > 0:
        net = income - expense
        verb = "dư" if net >= 0 else "thâm hụt"
        insights.append(
            f"Kỳ này bạn {verb} {_format_vnd(abs(net))} (thu {_format_vnd(income)}, chi {_format_vnd(expense)})."
        )

    # 2. Saving rate + 20% benchmark.
    if income > 0:
        sr = round(_safe_num(h.get("saving_rate")) * 100)
        if sr > 20:
            verdict = "vượt mức khuyến nghị 20% 👍"
        elif sr >= 18:
            verdict = "đạt mức khuyến nghị ~20%"
        else:
            verdict = "dưới mức khuyến nghị 20%, nên tiết kiệm thêm"
        insights.append(f"Tỷ lệ tiết kiệm {sr}% — {verdict}.")

    # 3. Opening → closing balance + lowest point.
    if bal_labels and bal_series:
        first = _safe_num(bal_series[0])
        last = _safe_num(bal_series[-1])
        low = _safe_num(balance_timeline.get("min"))
        insights.append(
            f"Số dư: {_format_vnd(first)} đầu kỳ → {_format_vnd(last)} cuối kỳ (thấp nhất {_format_vnd(low)})."
        )

    # 3a. Top recognized spending category (behavioral signal).
    if expense > 0:
        category_totals: dict[str, float] = defaultdict(float)
        for t in txns:
            amt = _safe_num(t.get("amount"))
            if amt < 0:
                category_totals[categorize_expense(t.get("description", ""))] += abs(amt)
        # Prefer the largest *recognized* group; skip the catch-all "Khác".
        top_cat = None
        top_val = 0.0
        for cat, val in category_totals.items():
            if cat == "Khác":
                continue
            if val > top_val:
                top_val = val
                top_cat = cat
        if top_cat and top_val > 0:
            pct = round(top_val / expense * 100)
            insights.append(
                f"Nhóm chi nhiều nhất: {top_cat} — {_format_vnd(top_val)} ({pct}% tổng chi)."
            )

    # 3b. Merchant spotlight — a recognizable brand the user spends heavily on / trending.
    if expense > 0:
        pick = None
        for kw, name in MERCHANT_WATCH:
            try:
                trend = _keyword_trend(txns, kw)
            except (ValueError, TypeError):
                trend = None
            if not trend or trend["recent"] <= 0:
                continue
            if pick is None or trend["recent"] > pick["recent"]:
                pick = {
                    "name": name,
                    "recent": trend["recent"],
                    "prior": trend["prior"],
                    "delta": trend["delta"],
                }
        if pick:
            if pick["prior"] > 0 and pick["delta"] > 0:
                line = (
                    f"Chi tiêu {pick['name']} đang tăng: {_format_vnd(pick['recent'])} "
                    f"trong 30 ngày gần nhất (kỳ trước {_format_vnd(pick['prior'])})."
                )
            elif pick["prior"] > 0 and pick["delta"] < 0:
                line = (
                    f"Chi tiêu {pick['name']} đang giảm: {_format_vnd(pick['recent'])} "
                    f"trong 30 ngày gần nhất (kỳ trước {_format_vnd(pick['prior'])})."
                )
            else:
                line = f"Bạn đã chi {_format_vnd(pick['recent'])} cho {pick['name']} trong 30 ngày gần nhất."
            insights.append(line)

    # 4. Largest single expense (most-negative txn).
    if expense > 0:
        worst = None
        for it in top_items:
            v = _safe_num(it.get("value"))
            if v < 0 and (worst is None or v < _safe_num(worst.get("value"))):
                worst = it
        if worst is None:
            for t in txns:
                v = _safe_num(t.get("amount"))
                if v < 0 and (worst is None or v < _safe_num(worst.get("value"))):
                    worst = {
                        "value": v,
                        "label": _short_label(t.get("description", "")),
                        "date": _day_month(t.get("date", "")),
                    }
        if worst:
            label = _short_label(worst.get("label", "")) or "—"
            when = f" ngày {worst.get('date')}" if worst.get("date") else ""
            insights.append(
                f"Khoản chi lớn nhất: {_format_vnd(abs(_safe_num(worst.get('value'))))} — “{label}”{when}."
            )

    # 5. Largest single income (most-positive txn).
    if income > 0:
        best = None
        for it in top_items:
            v = _safe_num(it.get("value"))
            if v > 0 and (best is None or v > _safe_num(best.get("value"))):
                best = it
        if best is None:
            for t in txns:
                v = _safe_num(t.get("amount"))
                if v > 0 and (best is None or v > _safe_num(best.get("value"))):
                    best = {"value": v, "label": _short_label(t.get("description", ""))}
        if best:
            label = _short_label(best.get("label", "")) or "—"
            insights.append(f"Nguồn thu lớn nhất: {_format_vnd(_safe_num(best.get('value')))} — “{label}”.")

    # 6. Expense concentration — top 5 expenses as a share of total spend.
    if expense > 0:
        exp_mags = sorted(
            (abs(_safe_num(t.get("amount"))) for t in txns if _safe_num(t.get("amount")) < 0),
            reverse=True,
        )
        if len(exp_mags) >= 5:
            top5 = sum(exp_mags[:5])
            pct = round(top5 / expense * 100)
            line = f"Top 5 khoản chi chiếm {pct}% tổng chi"
            if pct >= 60:
                line += " — khá tập trung"
            insights.append(line + ".")

    # 7. Burn rate & runway.
    if expense > 0 and last_balance > 0:
        days = 0
        if s.get("date_from") and s.get("date_to"):
            try:
                frm = _parse_iso(str(s["date_from"])[:10] + "T00:00:00")
                to = _parse_iso(str(s["date_to"])[:10] + "T00:00:00")
                if to >= frm:
                    days = (to - frm).days + 1
            except ValueError:
                days = 0
        days = max(1, days)
        burn = expense / days
        if burn > 0:
            runway = int(last_balance // burn)
            runway_label = "999+" if runway > 999 else str(runway)
            insights.append(
                f"Mức chi TB {_format_vnd(round(burn))}/ngày; với số dư hiện tại đủ dùng ~{runway_label} ngày."
            )

    # 8. Heaviest spending day (most-negative daily net).
    if dn_labels and dn_net:
        worst_idx = -1
        worst_val = 0.0
        for i, raw in enumerate(dn_net):
            v = _safe_num(raw)
            if v < worst_val:
                worst_val = v
                worst_idx = i
        if worst_idx >= 0:
            label = dn_labels[worst_idx] or "—"
            insights.append(f"Chi mạnh nhất ngày {label}: {_format_vnd(abs(worst_val))}.")

    # 9. Recurring / periodic transactions.
    recurring = _safe_num(top_txns.get("recurring"))
    if recurring > 0:
        insights.append(f"Phát hiện {int(recurring)} khoản lặp lại — có thể là chi/thu định kỳ.")

    # 10. Expense-to-income warning.
    if income > 0 and _safe_num(h.get("expense_ratio")) > 0.9:
        insights.append("Tỷ lệ chi/thu trên 90% — cần kiểm soát chi tiêu chặt hơn.")

    # 11. Fallback when nothing above fired.
    if not insights:
        insights.append("Chưa đủ dữ liệu để phân tích sâu — hãy upload thêm sao kê.")

    return insights[:7]


def build_insights_payload(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    summary = compute_summary(transactions)
    health = financial_health(summary)
    charts = chart_datasets(transactions, health)
    insights = generate_insights(transactions, summary, health, charts)
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