#!/usr/bin/env python3
"""backend8 — compare `main` SHA vs the deployed Render backend SHA (V16).

Detects a static-site ↔ backend *split-brain*: GitHub Pages always ships the
latest `main`, but the FastAPI backends on Render only redeploy on a **manual**
Blueprint sync. When `blog-vipzone-api` lags `main`, premium VIP content endpoints
exist in the repo but 404 in production → "Premium gộp gói" silently broken.

Report-only + offline-safe by design: never gates CI (exit 0) unless `--strict`.
Rate-limit friendly — one cached `/health` GET with exponential backoff, no GitHub
API calls (main SHA comes from local git).

    python3 scripts/backend_sha_check.py            # human summary + data/backend-status.json
    python3 scripts/backend_sha_check.py --json      # machine JSON
    python3 scripts/backend_sha_check.py --offline    # skip network → status unknown
    python3 scripts/backend_sha_check.py --strict      # exit 2 if BACKEND_OUTDATED
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:  # py3.9+ stdlib
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover - fallback when tzdata missing
    _TZ = timezone.utc

try:  # py3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "backend-status.json"
DEFAULT_API = "https://blog-vipzone-api.onrender.com"


def _sha_match(a: str, b: str) -> bool:
    a, b = (a or "").strip(), (b or "").strip()
    if not a or not b:
        return False
    n = min(len(a), len(b))
    return n >= 7 and a[:n] == b[:n]


def classify(main_sha: str, backend_sha: str, reachable: bool) -> dict:
    """Pure status classifier (unit-tested, no I/O)."""
    main_sha = (main_sha or "").strip()
    backend_sha = (backend_sha or "").strip()
    if not reachable:
        return {
            "status": "unknown",
            "outdated": False,
            "message": "Backend không phản hồi (Render free dyno có thể đang ngủ — thử lại sau).",
            "action": "retry",
        }
    if not backend_sha:
        return {
            "status": "unknown",
            "outdated": False,
            "message": "Backend chưa expose deployed_sha — đặt RENDER_GIT_COMMIT cho blog-vipzone-api.",
            "action": "set-render-git-commit",
        }
    if not main_sha:
        return {
            "status": "unknown",
            "outdated": False,
            "message": "Không xác định được main SHA (git rev-parse thất bại).",
            "action": "check-git",
        }
    if _sha_match(main_sha, backend_sha):
        return {
            "status": "in_sync",
            "outdated": False,
            "message": "Backend khớp main — không cần deploy.",
            "action": "none",
        }
    return {
        "status": "outdated",
        "outdated": True,
        "message": (
            "BACKEND_OUTDATED — backend (%s) đang sau main (%s). "
            "Render → Blueprint → Manual Sync `blog-vipzone-api` để hết split-brain."
            % (backend_sha[:7], main_sha[:7])
        ),
        "action": "render-deploy",
    }


def main_sha() -> str:
    for ref in ("origin/main", "main", "HEAD"):
        try:
            out = subprocess.run(
                ["git", "rev-parse", ref],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except Exception:
            continue
    return ""


def config_api() -> str:
    cfg = ROOT / "config.toml"
    if not cfg.exists():
        return DEFAULT_API
    if tomllib:
        try:
            data = tomllib.loads(cfg.read_text(encoding="utf-8"))
            url = (data.get("extra", {}) or {}).get("vipzone_api_url", "")
            if url:
                return str(url).rstrip("/")
        except Exception:
            pass
    # Best-effort regex fallback if tomllib is unavailable / parse fails.
    try:
        import re

        m = re.search(r'(?m)^\s*vipzone_api_url\s*=\s*"([^"]+)"', cfg.read_text(encoding="utf-8"))
        if m:
            return m.group(1).rstrip("/")
    except Exception:
        pass
    return DEFAULT_API


def fetch_health(api: str, attempts: int = 3, timeout: int = 8):
    """One cached /health GET with exponential backoff. Returns (payload|None, error)."""
    if not api:
        return None, "no_api_url"
    err = ""
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                api.rstrip("/") + "/health",
                headers={"User-Agent": "backend8/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8")), ""
        except Exception as exc:  # network/parse — stay offline-safe
            err = f"{type(exc).__name__}: {exc}"
            if i < attempts - 1:
                time.sleep(min(2 ** i, 8))
    return None, err


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description="backend8 — main SHA vs Render backend SHA (V16)")
    ap.add_argument("--api", default="", help="override backend base URL")
    ap.add_argument("--offline", action="store_true", help="skip network → status unknown")
    ap.add_argument("--strict", action="store_true", help="exit 2 when BACKEND_OUTDATED")
    ap.add_argument("--json", action="store_true", help="print machine JSON")
    ap.add_argument("--no-write", action="store_true", help="do not write data/backend-status.json")
    args = ap.parse_args(argv)

    api = (args.api or config_api()).rstrip("/")
    main = main_sha()
    if args.offline:
        health, herr, reachable = None, "offline", False
    else:
        health, herr = fetch_health(api)
        reachable = health is not None
    backend_sha = (health or {}).get("deployed_sha", "") if health else ""
    result = classify(main, backend_sha, reachable)

    now = datetime.now(_TZ)
    report = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generated_display": now.strftime("%H:%M %d/%m/%Y"),
        "service": "blog-vipzone-api",
        "api": api,
        "main_sha": main,
        "backend_sha": backend_sha,
        "reachable": reachable,
        "premium_content": bool((health or {}).get("premium_content")) if health else None,
        "error": herr,
        **result,
    }

    if not args.no_write:
        try:
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"[backend8] warn: could not write report: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        icon = {"in_sync": "✅", "outdated": "⚠️", "unknown": "❔"}.get(result["status"], "•")
        print("backend8 — VIPZone backend split-brain check (V16)")
        print(f"  service : blog-vipzone-api  ({api})")
        print(f"  main    : {main[:12] or '—'}")
        print(f"  backend : {backend_sha[:12] or '—'}")
        print(f"  status  : {icon} {result['status'].upper()}")
        print(f"  {result['message']}")
        if result["outdated"]:
            print("  → fix : Render dashboard → Blueprints → Manual Sync `blog-vipzone-api`")

    return 2 if (args.strict and result["outdated"]) else 0


if __name__ == "__main__":
    raise SystemExit(run())
