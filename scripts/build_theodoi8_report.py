#!/usr/bin/env python3
"""
Build THEODOI8 LIVE report → data/theodoi8-report.json + static/data/theodoi8-report.json.

Snapshot trạng thái CI/CD (commit gần nhất × workflow run) cho banner header
"👀 THEODOI8 LIVE". Tái dùng pipeline báo cáo hiện có (giống build_google_rank /
fetch_build_dashboard): fetch GitHub REST API bằng GITHUB_TOKEN, dual-write
data/ (build-time load_data) + static/data/ (runtime fetch, auto-refresh).

Anti-hang / graceful: thiếu token hoặc lỗi network → GIỮ report cũ nếu có, ngược
lại ghi seed 'idle'. LUÔN exit 0 (không bao giờ làm sập build).

Chạy local:  GITHUB_TOKEN=ghp_... python3 scripts/build_theodoi8_report.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC_DATA = ROOT / "static" / "data"
FILENAME = "theodoi8-report.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = (
    os.environ.get("GITHUB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or os.environ.get("ZOLA_GH_TOKEN")
    or ""
)
API = "https://api.github.com"
VN_TZ = timezone(timedelta(hours=7))
ACTIONS_URL = f"https://github.com/{REPO}/actions"
MAX_COMMITS = 8
MAX_RUNS = 40

STATUS_ICON = {
    "running": "🔄", "success": "✅", "failure": "❌",
    "cancelled": "⊘", "idle": "📡",
}
STATUS_LABEL = {
    "running": "ĐANG CHẠY", "success": "ỔN ĐỊNH", "failure": "CÓ LỖI",
    "cancelled": "ĐÃ HUỶ", "idle": "TRỰC TIẾP",
}
CTA = {
    "running": "Xem commit đang chạy",
    "failure": "Xem log lỗi CI",
    "success": "Xem CI/CD trực tiếp",
    "cancelled": "Xem GitHub Actions",
    "idle": "Mở GitHub Actions",
}


def _api_get(path: str):
    req = Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zola-theodoi8",
        },
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310 (trusted GitHub API)
        return json.loads(resp.read().decode("utf-8"))


def _normalize(status: str, conclusion: str | None) -> str:
    if status in ("queued", "in_progress", "waiting", "pending", "requested"):
        return "running"
    if conclusion == "success":
        return "success"
    if conclusion in ("failure", "timed_out", "startup_failure"):
        return "failure"
    if conclusion == "cancelled":
        return "cancelled"
    if conclusion == "skipped":
        return "skipped"
    return "running" if status != "completed" else "success"


def _fmt_dt(iso: str | None) -> tuple[str, str]:
    """ISO (machine) + 'HH:MM dd/mm/yyyy' GMT+7 (display) — tuân quy tắc timezone."""
    now = datetime.now(VN_TZ)
    if iso:
        try:
            now = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(VN_TZ)
        except (ValueError, TypeError):
            now = datetime.now(VN_TZ)
    return now.strftime("%Y-%m-%dT%H:%M:%S%z"), now.strftime("%H:%M %d/%m/%Y")


def build_report() -> dict:
    commits = _api_get(f"/repos/{REPO}/commits?per_page={MAX_COMMITS}")
    runs = _api_get(
        f"/repos/{REPO}/actions/runs?per_page={MAX_RUNS}"
    ).get("workflow_runs", [])

    by_sha: dict[str, list] = {}
    for r in runs:
        by_sha.setdefault(r.get("head_sha", ""), []).append(r)

    rows: list[dict] = []
    counts = {"running": 0, "success": 0, "failure": 0, "cancelled": 0, "skipped": 0}
    for c in commits:
        sha = c.get("sha", "")
        crs = sorted(
            by_sha.get(sha, []), key=lambda r: r.get("updated_at", ""), reverse=True
        )
        if not crs:
            continue
        norms = [_normalize(r.get("status", ""), r.get("conclusion")) for r in crs]
        if "running" in norms:
            st = "running"
        elif "failure" in norms:
            st = "failure"
        elif "cancelled" in norms and "success" not in norms:
            st = "cancelled"
        else:
            st = "success"
        counts[st] = counts.get(st, 0) + 1
        top = crs[0]
        _, tdisp = _fmt_dt(top.get("updated_at"))
        msg = (c.get("commit", {}).get("message", "") or "").split("\n")[0][:80]
        rows.append({
            "sha": sha[:7],
            "message": msg,
            "status": st,
            "icon": STATUS_ICON.get(st, "📡"),
            "run_name": top.get("name", ""),
            "run_number": top.get("run_number"),
            "url": top.get("html_url") or f"https://github.com/{REPO}/commit/{sha}",
            "time_display": tdisp,
        })

    total = sum(counts.values())
    if counts["running"]:
        overall = "running"
    elif counts["failure"]:
        overall = "failure"
    elif total == 0:
        overall = "idle"
    else:
        overall = "success"

    parts = []
    if counts["running"]:
        parts.append(f"🔄 {counts['running']} đang chạy")
    if counts["success"]:
        parts.append(f"✅ {counts['success']} pass")
    if counts["failure"]:
        parts.append(f"❌ {counts['failure']} fail")
    if counts["cancelled"]:
        parts.append(f"⊘ {counts['cancelled']} huỷ")
    summary = (
        " · ".join(parts)
        if parts
        else "Theo dõi commit & CI/CD chạy trực tiếp trên GitHub Actions"
    )

    gen_iso, gen_disp = _fmt_dt(datetime.now(timezone.utc).isoformat())
    return {
        "generated_at": gen_iso,
        "generated_at_display": gen_disp,
        "status": overall,
        "status_label": STATUS_LABEL.get(overall, "TRỰC TIẾP"),
        "status_icon": STATUS_ICON.get(overall, "📡"),
        "summary": summary,
        "counts": {**counts, "total": total},
        "cta": CTA.get(overall, "Xem chi tiết"),
        "url": ACTIONS_URL,
        "source_label": "GitHub Actions",
        "commits": rows,
    }


def _seed() -> dict:
    gen_iso, gen_disp = _fmt_dt(datetime.now(timezone.utc).isoformat())
    return {
        "generated_at": gen_iso,
        "generated_at_display": gen_disp,
        "status": "idle",
        "status_label": STATUS_LABEL["idle"],
        "status_icon": STATUS_ICON["idle"],
        "summary": "Theo dõi commit & CI/CD chạy trực tiếp trên GitHub Actions",
        "counts": {
            "running": 0, "success": 0, "failure": 0,
            "cancelled": 0, "skipped": 0, "total": 0,
        },
        "cta": CTA["idle"],
        "url": ACTIONS_URL,
        "source_label": "GitHub Actions",
        "commits": [],
    }


def _existing() -> dict | None:
    for p in (STATIC_DATA / FILENAME, DATA / FILENAME):
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _write(payload: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    STATIC_DATA.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (DATA / FILENAME).write_text(text, encoding="utf-8")
    (STATIC_DATA / FILENAME).write_text(text, encoding="utf-8")


def main() -> int:
    if not TOKEN:
        payload = _existing() or _seed()
        _write(payload)
        print(f"theodoi8: no token → giữ/seed report (status={payload.get('status')})")
        return 0
    try:
        payload = build_report()
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as e:
        if _existing():
            print(f"theodoi8: fetch lỗi ({e}) → giữ report cũ (cache)")
            return 0
        payload = _seed()
        payload["fetch_error"] = str(e)
        _write(payload)
        print(f"theodoi8: fetch lỗi ({e}) → seed idle")
        return 0
    _write(payload)
    print(f"theodoi8: status={payload['status']} · {payload['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
