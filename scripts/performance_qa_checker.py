#!/usr/bin/env python3
"""
Performance QA Checker — audit Lighthouse/PageSpeed, so sánh regression,
đề xuất fix SAFE (img lazy/decoding qua qa_check.py).

Dùng trong perf-audit.yml (cron 00:00 Asia/Ho_Chi_Minh).
KHÔNG push/merge main — chỉ output report + branch fix cho PR.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = ROOT / "data" / "performance-audit-snapshot.json"
PAGESPEED_PATH = ROOT / "data" / "pagespeed.json"
REPORT_DIR = ROOT / "reports" / "performance"
PERF_THRESHOLD = 90

# Import shared PageSpeed helpers (same package).
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_pagespeed import TARGET_URL, fetch_lighthouse, parse_lighthouse_result  # noqa: E402


def now_vn() -> str:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y%m%d")


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def primary_score(data: dict) -> int:
    """Ưu tiên desktop performance (khớp QA Dashboard base.html)."""
    desktop = data.get("desktop", {}).get("performance", 0)
    mobile = data.get("mobile", {}).get("performance", 0)
    return desktop if desktop > 0 else mobile


def run_local_perf_scan() -> tuple[str, list[str]]:
    """Chạy qa_check.py --perf, trả (stdout, list warning PERF)."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "qa_check.py"), "--perf"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    warnings = [
        line.strip()
        for line in output.splitlines()
        if "PERF:" in line or "⚠" in line
    ]
    return output, warnings


def run_safe_fix() -> tuple[bool, str, list[str]]:
    """Chạy qa_check.py --perf --fix perf. Trả (changed, stdout, fixed_lines)."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "qa_check.py"), "--perf", "--fix", "perf"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    fixed = [ln for ln in output.splitlines() if ln.startswith("FIXED:")]
    changed = bool(fixed)
    return changed, output, fixed


def compare_regression(current: dict, previous: dict | None) -> dict:
    """So sánh score + core web vitals với snapshot trước."""
    result = {
        "has_previous": previous is not None,
        "score_delta": 0,
        "regression": False,
        "details": [],
    }
    if not previous:
        return result

    cur_score = primary_score(current)
    prev_score = primary_score(previous)
    delta = cur_score - prev_score
    result["score_delta"] = delta
    if delta < 0:
        result["regression"] = True
        result["details"].append(
            f"Performance giảm {abs(delta)} điểm ({prev_score} → {cur_score})"
        )

    for strategy in ("mobile", "desktop"):
        for metric in ("lcp_ms", "fcp_ms", "tbt_ms", "si_ms", "cls_value"):
            cur_v = current.get(strategy, {}).get(metric)
            prev_v = previous.get(strategy, {}).get(metric)
            if cur_v is None or prev_v is None:
                continue
            # CLS thấp hơn = tốt hơn; các metric khác thấp hơn = tốt hơn
            worse = cur_v > prev_v if metric != "cls_value" else cur_v > prev_v
            if worse and abs(cur_v - prev_v) > 0.05:
                label = metric.replace("_ms", "").replace("_value", "")
                result["regression"] = True
                result["details"].append(
                    f"{strategy}/{label}: {prev_v} → {cur_v} (xấu hơn)"
                )
    return result


def collect_bottlenecks(audit: dict) -> list[str]:
    """Tổng hợp bottleneck từ Lighthouse + local scan."""
    items = []
    for strategy in ("mobile", "desktop"):
        data = audit.get(strategy, {})
        score = data.get("performance", 0)
        if score < PERF_THRESHOLD:
            items.append(f"[{strategy}] Performance {score}/100 (< {PERF_THRESHOLD})")
        if data.get("lcp"):
            items.append(f"[{strategy}] LCP {data['lcp']}")
        if data.get("tbt"):
            items.append(f"[{strategy}] TBT {data['tbt']}")
        rb = data.get("render_blocking", [])
        if rb:
            items.append(f"[{strategy}] {len(rb)} render-blocking resource(s)")
        unused = data.get("unused_assets", {})
        for kind in ("css", "js"):
            wasted = unused.get(kind, {}).get("wasted_bytes", 0)
            if wasted > 50_000:
                items.append(
                    f"[{strategy}] Unused {kind.upper()} ~{wasted // 1024}KB"
                )
        for img in data.get("image_issues", []):
            items.append(f"[{strategy}] {img.get('title', img.get('id'))}")
    return items


def build_fix_proposals(audit: dict, local_warnings: list[str]) -> list[dict]:
    """Đề xuất fix theo hướng user yêu cầu (phân tích, không auto-apply hết)."""
    proposals = []

    for strategy in ("mobile", "desktop"):
        data = audit.get(strategy, {})
        if data.get("performance", 100) < PERF_THRESHOLD:
            proposals.append({
                "area": "Lighthouse score",
                "strategy": strategy,
                "action": "Giảm JS blocking, tối ưu LCP image, defer non-critical scripts",
                "expected": f"Tăng Performance {strategy} từ {data['performance']} → 90+",
                "risk": "medium",
            })
        for img in data.get("image_issues", []):
            proposals.append({
                "area": "Image optimization",
                "strategy": strategy,
                "action": f"Fix: {img.get('title')} — convert WebP, resize, responsive srcset",
                "expected": "Giảm image weight + cải thiện LCP",
                "risk": "low",
            })
        rb = data.get("render_blocking", [])
        if rb:
            proposals.append({
                "area": "Render-blocking",
                "strategy": strategy,
                "action": "Defer/async non-critical CSS/JS; inline critical CSS",
                "expected": f"Giảm FCP/LCP (~{len(rb)} resources blocking)",
                "risk": "medium",
            })
        unused = data.get("unused_assets", {})
        if unused.get("js", {}).get("wasted_bytes", 0) > 30_000:
            proposals.append({
                "area": "Unused JS",
                "strategy": strategy,
                "action": "Tree-shake / lazy-load modules; audit third-party scripts",
                "expected": "Giảm TBT + bootup time",
                "risk": "medium",
            })
        if unused.get("css", {}).get("wasted_bytes", 0) > 30_000:
            proposals.append({
                "area": "Unused CSS",
                "strategy": strategy,
                "action": "Purge unused SCSS; split critical CSS",
                "expected": "Giảm CSS transfer + render time",
                "risk": "low",
            })

    if any("lazy" in w.lower() or "<img>" in w for w in local_warnings):
        proposals.append({
            "area": "Lazy-load images",
            "strategy": "local",
            "action": "SAFE auto-fix: thêm loading=lazy + decoding=async (qa_check --fix perf)",
            "expected": "Giảm initial image payload below-fold",
            "risk": "low",
        })

    if any("CDN" in w for w in local_warnings):
        proposals.append({
            "area": "Third-party / CDN",
            "strategy": "local",
            "action": "Thêm preconnect cho top CDN; giảm external script nếu có thể",
            "expected": "Giảm connection latency",
            "risk": "low",
        })

    if any(re.search(r"ảnh.*KB", w, re.I) for w in local_warnings):
        proposals.append({
            "area": "Static image weight",
            "strategy": "local",
            "action": "Resize ≤1280px, WebP quality 80 (optimize-images workflow)",
            "expected": "Giảm total page size",
            "risk": "low",
        })

    # Dedupe by area+action
    seen = set()
    unique = []
    for p in proposals:
        key = (p["area"], p["action"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def write_pr_body(
    audit: dict,
    regression: dict,
    bottlenecks: list[str],
    proposals: list[dict],
    fixed_lines: list[str],
    local_warnings: list[str],
    branch_name: str,
) -> str:
    score = primary_score(audit)
    lines = [
        "## QA: Performance optimization proposal for blog",
        "",
        f"**Audit URL**: `{TARGET_URL}`",
        f"**Audit time (UTC)**: `{audit.get('audited_at', '')}`",
        f"**Branch**: `{branch_name}`",
        "",
        "### Điểm Performance hiện tại",
        f"- **Desktop**: {audit.get('desktop', {}).get('performance', '—')}/100",
        f"- **Mobile**: {audit.get('mobile', {}).get('performance', '—')}/100",
        f"- **Primary (dashboard)**: **{score}/100**",
        "",
        "### Core Web Vitals",
        "| Metric | Mobile | Desktop |",
        "|--------|--------|---------|",
    ]
    for metric, key in (
        ("LCP", "lcp"),
        ("CLS", "cls"),
        ("INP", "inp"),
        ("TBT", "tbt"),
        ("FCP", "fcp"),
        ("Speed Index", "si"),
    ):
        m = audit.get("mobile", {}).get(key, "—")
        d = audit.get("desktop", {}).get(key, "—")
        lines.append(f"| {metric} | {m} | {d} |")

    lines.extend(["", "### Vấn đề phát hiện"])
    if regression.get("regression"):
        lines.append("**⚠ REGRESSION** so với lần audit trước:")
        for d in regression.get("details", []):
            lines.append(f"- {d}")
    else:
        lines.append("- Không phát hiện regression score/CWV (hoặc chưa có baseline).")

    if score < PERF_THRESHOLD:
        lines.append(f"- Performance **{score}/100** dưới ngưỡng **{PERF_THRESHOLD}**")

    for b in bottlenecks[:20]:
        lines.append(f"- {b}")

    lines.extend(["", "### File đã sửa (SAFE auto-fix)"])
    if fixed_lines:
        for fl in fixed_lines:
            lines.append(f"- `{fl}`")
    else:
        lines.append("- *(Chưa có file sửa — chỉ báo cáo phân tích)*")

    lines.extend(["", "### Đề xuất fix (trước/sau dự kiến)"])
    for p in proposals[:15]:
        lines.append(f"- **{p['area']}** ({p['strategy']}): {p['action']}")
        lines.append(f"  - *Dự kiến*: {p['expected']}")

    lines.extend([
        "",
        "### Risk assessment",
        "- **SAFE fixes** (img lazy/decoding): risk **low** — không đổi layout/LCP hero",
        "- **Manual fixes** (JS defer, CSS purge, image resize): risk **medium** — cần review diff",
        "- **KHÔNG** auto-merge; **KHÔNG** push trực tiếp `main`",
        "",
        "### Cách validate",
        "1. Review diff trên branch này",
        "2. `python3 qa_check.py --perf` — không error mới",
        "3. `zola build` — build pass",
        "4. Sau merge + deploy: chờ `pagespeed.yml` cập nhật `data/pagespeed.json`",
        "5. Performance target ≥ 90/100",
        "",
        "### Checklist manual review",
        "- [ ] LCP hero image vẫn có `fetchpriority=high` (không bị lazy)",
        "- [ ] Không có `<img>` trong comment bị sửa nhầm",
        "- [ ] Layout không vỡ trên mobile/desktop",
        "- [ ] Third-party scripts vẫn hoạt động",
        "- [ ] Chấp nhận merge → deploy thủ công",
        "",
        "### Local scan warnings (top 20)",
        "```",
    ])
    for w in local_warnings[:20]:
        lines.append(w)
    if not local_warnings:
        lines.append("(không có warning PERF local)")
    lines.append("```")
    return "\n".join(lines)


def fetch_full_audit(api_key: str = "") -> dict:
    result = {
        "audited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url": TARGET_URL,
        "audit_type": "lighthouse_pagespeed_v5",
        "source": "live_api",
    }
    try:
        for strategy in ("mobile", "desktop"):
            lhr = fetch_lighthouse(strategy, api_key)
            result[strategy] = parse_lighthouse_result(lhr)
        return result
    except Exception as exc:
        cached = load_json(PAGESPEED_PATH)
        if not cached:
            raise
        print(
            f"[perf-qa] ⚠ PageSpeed API failed ({exc}) — fallback data/pagespeed.json",
            flush=True,
        )
        result["source"] = "cached_pagespeed_json"
        result["api_error"] = str(exc)[:200]
        for strategy in ("mobile", "desktop"):
            if strategy in cached:
                result[strategy] = cached[strategy]
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Performance QA Checker")
    parser.add_argument("--report-only", action="store_true", help="Chỉ audit + report, không fix")
    parser.add_argument("--fix", action="store_true", help="Áp dụng SAFE perf fix sau audit")
    parser.add_argument("--write-pr-body", type=Path, help="Ghi PR body markdown ra file")
    parser.add_argument("--output", type=Path, help="Ghi full JSON report")
    args = parser.parse_args()

    api_key = os.environ.get("PAGESPEED_API_KEY", "")
    print("[perf-qa] Fetching Lighthouse/PageSpeed...", flush=True)
    audit = fetch_full_audit(api_key)

    previous = load_json(SNAPSHOT_PATH) or load_json(PAGESPEED_PATH)
    regression = compare_regression(audit, previous)

    print("[perf-qa] Running local perf scan...", flush=True)
    scan_output, local_warnings = run_local_perf_scan()

    fixed_lines: list[str] = []
    fix_changed = False
    if args.fix and not args.report_only:
        print("[perf-qa] Applying SAFE auto-fix...", flush=True)
        fix_changed, fix_output, fixed_lines = run_safe_fix()
        print(fix_output)

    bottlenecks = collect_bottlenecks(audit)
    proposals = build_fix_proposals(audit, local_warnings)
    score = primary_score(audit)

    needs_action = (
        score < PERF_THRESHOLD
        or regression["regression"]
        or fix_changed
    )

    report = {
        "audited_at": audit["audited_at"],
        "url": TARGET_URL,
        "primary_score": score,
        "threshold": PERF_THRESHOLD,
        "needs_action": needs_action,
        "regression": regression,
        "bottlenecks": bottlenecks,
        "proposals": proposals,
        "fixed": fixed_lines,
        "local_scan_tail": scan_output[-4000:] if scan_output else "",
        "mobile": audit.get("mobile"),
        "desktop": audit.get("desktop"),
    }

    # Lưu snapshot mới (commit trên branch fix, không main)
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {**audit, "primary_score": score, "regression": regression}
    SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"audit-{now_vn()}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[perf-qa] Report: {report_path.relative_to(ROOT)}")

    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    branch_name = f"qa/performance-auto-fix-{now_vn()}"
    if args.write_pr_body:
        body = write_pr_body(
            audit, regression, bottlenecks, proposals,
            fixed_lines, local_warnings, branch_name,
        )
        args.write_pr_body.write_text(body, encoding="utf-8")
        print(f"[perf-qa] PR body: {args.write_pr_body}")

    print(f"[perf-qa] Primary score: {score}/100 | needs_action={needs_action}")
    if regression["regression"]:
        print("[perf-qa] ⚠ REGRESSION detected")
    for b in bottlenecks[:10]:
        print(f"  • {b}")

    # Exit 2 = cần tạo PR/issue; 0 = OK
    return 2 if needs_action else 0


if __name__ == "__main__":
    sys.exit(main())