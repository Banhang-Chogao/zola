#!/usr/bin/env python3
"""
build_prod_snapshot.py — Production snapshot for the `??` shortcut UI.

Combines read-only CI data (deploy-monitor.json), git main HEAD, VIPZone
backend /health, and open PR count into data/prod-snapshot.json. The Changelog
page renders this at build time — the browser never calls GitHub or backend APIs.

Sources (same as chat `??` diagnosis):
  * main HEAD        — git rev-parse in CI, or GITHUB API /commits/main
  * deploy live SHA  — data/deploy-monitor.json (deploy.yml last success)
  * backend SHA      — GET {cms_auth_url}/health → deployed_sha
  * open PRs         — GitHub API (optional, token required)

Stdlib only. Exit 0 on non-critical errors (keeps prior snapshot).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "prod-snapshot.json"
DEPLOY_MONITOR = ROOT / "data" / "deploy-monitor.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
BACKEND_HEALTH_URL = os.environ.get(
    "PROD_SNAPSHOT_BACKEND_URL",
    "https://blog-vipzone-api.onrender.com/health",
)
TIMEOUT = 12


def _now_iso() -> str:
    return datetime.now(TZ).astimezone().isoformat()


def _fmt_display(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
        return dt.strftime("%H:%M %d/%m/%Y")
    except ValueError:
        return "—"


def _short(sha: str | None) -> str:
    return (sha or "")[:7] if sha else "—"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _git_main_sha() -> tuple[str | None, str | None]:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True, cwd=ROOT,
        ).stdout.strip()
        short = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True, cwd=ROOT,
        ).stdout.strip()
        return sha or None, short or None
    except (subprocess.SubprocessError, OSError):
        return None, None


def _api_get(path: str) -> dict | list | None:
    if not TOKEN:
        return None
    req = Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "prod-snapshot/1.0",
        },
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _fetch_main_via_api() -> tuple[str | None, str | None, str | None]:
    data = _api_get(f"/repos/{REPO}/commits/main")
    if not isinstance(data, dict):
        return None, None, None
    sha = data.get("sha")
    msg = ((data.get("commit") or {}).get("message") or "").splitlines()[0][:80]
    return sha, _short(sha), msg or None


def _fetch_open_prs() -> int | None:
    data = _api_get(f"/repos/{REPO}/pulls?state=open&per_page=1")
    if not isinstance(data, list):
        return None
    # Need total count — use search API or paginate link header; simple: second call with per_page=100
    all_prs = _api_get(f"/repos/{REPO}/pulls?state=open&per_page=100")
    if isinstance(all_prs, list):
        return len(all_prs)
    return None


def _fetch_backend() -> dict:
    url = BACKEND_HEALTH_URL.strip()
    if not url:
        return {"ok": False, "error": "no_url"}
    req = Request(url, headers={"User-Agent": "prod-snapshot/1.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if not isinstance(body, dict):
            return {"ok": False, "error": "bad_json"}
        sha = body.get("deployed_sha") or body.get("backend_sha") or ""
        return {
            "ok": body.get("status") == "ok",
            "sha": sha or None,
            "sha_short": _short(sha),
            "comments_mounted": bool(body.get("comments_mounted")),
            "oauth_configured": bool(body.get("oauth_configured")),
            "url": url.rsplit("/health", 1)[0] if "/health" in url else url,
        }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": type(e).__name__}


def _drift(main_sha: str | None, deploy_sha: str | None, backend_sha: str | None, dm: dict) -> dict:
    summary = (dm.get("summary") or {}) if dm else {}
    prod_status = summary.get("prod_status") or "unknown"
    deploying = bool(summary.get("deploying"))

    main_ahead = bool(main_sha and deploy_sha and main_sha != deploy_sha)
    backend_behind = bool(main_sha and backend_sha and backend_sha != main_sha)

    if prod_status == "red":
        status = "red"
        status_vi = "Deploy lỗi"
        hint = "Chạy ff để chẩn đoán log deploy.yml."
    elif deploying or prod_status == "yellow":
        status = "yellow"
        status_vi = "Đang deploy"
        hint = "Có commit đang chờ hoặc deploy đang chạy — đợi workflow xanh."
    elif main_ahead:
        status = "yellow"
        status_vi = "Main mới hơn production"
        hint = "Code đã merge nhưng GitHub Pages chưa ship bản mới — đợi deploy hoặc dispatch deploy.yml."
    elif backend_behind:
        status = "yellow"
        status_vi = "Backend tụt sau main"
        hint = "Static site đã cập nhật; Render backend cần Manual Sync nếu dùng API mới."
    elif prod_status == "green":
        status = "green"
        status_vi = "Đồng bộ"
        hint = "Main, deploy và backend khớp (hoặc chỉ lệch bot data không ảnh hưởng UI)."
    else:
        status = "unknown"
        status_vi = "Chưa rõ"
        hint = "Thiếu dữ liệu deploy-monitor — đợi cron hoặc chạy fetch_deploy_monitor.py."

    parts = []
    if main_sha:
        parts.append(f"main {_short(main_sha)}")
    if deploy_sha:
        parts.append(f"deploy {_short(deploy_sha)}")
    if backend_sha:
        parts.append(f"backend {_short(backend_sha)}")
    status_line = " · ".join(parts) if parts else "—"

    return {
        "status": status,
        "status_vi": status_vi,
        "hint": hint,
        "main_ahead_of_deploy": main_ahead,
        "backend_behind_main": backend_behind,
        "status_line": status_line,
    }


def build_snapshot() -> dict:
    dm = _load_json(DEPLOY_MONITOR)
    ds = dm.get("summary") or {}

    main_sha, main_short = _git_main_sha()
    main_title = None
    if not main_sha:
        main_sha, main_short, main_title = _fetch_main_via_api()
    if main_sha and not main_title:
        main_title = f"main @ {_short(main_sha)}"

    deploy_sha = ds.get("prod_commit")
    deploy_short = ds.get("prod_commit_short") or _short(deploy_sha)
    deploy_at = ds.get("prod_deployed_at")

    backend = _fetch_backend()
    open_prs = _fetch_open_prs()

    drift = _drift(main_sha, deploy_sha, backend.get("sha"), dm)

    generated = _now_iso()
    return {
        "generated_at": generated,
        "generated_at_display": _fmt_display(generated),
        "source": "build_prod_snapshot.py",
        "shortcut": "??",
        "main": {
            "sha": main_sha,
            "sha_short": main_short or _short(main_sha),
            "title": main_title,
            "url": f"https://github.com/{REPO}/commit/{main_sha}" if main_sha else None,
        },
        "deploy": {
            "sha": deploy_sha,
            "sha_short": deploy_short,
            "status": ds.get("prod_status"),
            "deployed_at": deploy_at,
            "deployed_at_display": _fmt_display(deploy_at),
            "run_number": ds.get("last_success_run"),
            "status_line": ds.get("status_line"),
            "deploying": bool(ds.get("deploying")),
        },
        "backend": backend,
        "drift": drift,
        "open_prs": open_prs,
        "deploy_monitor_stale": bool(dm.get("stale")),
        "deploy_monitor_ok": bool(dm.get("ok", True)),
    }


def main() -> int:
    try:
        snap = build_snapshot()
    except Exception as e:
        print(f"[prod-snapshot] error: {type(e).__name__}: {e}", file=sys.stderr)
        if OUTPUT.exists():
            return 0
        return 1

    serialized = json.dumps(snap, ensure_ascii=False)
    for env in ("GITHUB_TOKEN", "GH_TOKEN"):
        tok = (os.environ.get(env) or "").strip()
        if tok and tok in serialized:
            print("[prod-snapshot] FATAL: token in output", file=sys.stderr)
            return 2

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d = snap.get("drift") or {}
    print(f"[prod-snapshot] wrote {OUTPUT.relative_to(ROOT)} — {d.get('status_vi')} — {d.get('status_line')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())