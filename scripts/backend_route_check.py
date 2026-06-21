#!/usr/bin/env python3
"""backend_route_check — V24 post-deploy smoke for blog-vipzone-api routes.

Render deploys ONLY services/vipzone (render.yaml rootDir). A frontend route whose
handler lives only in services/visitor-counter is dead in production → 404
split-brain (see CLAUDE.md V24 / V16 / V22b). This checker hits the LIVE backend
and asserts the routes the production frontend depends on never return 404:

  * GET  /health        → 200 (and, when present, critical_routes all mounted)
  * GET  /gsc/status    → NOT 404 (401/200 fine — the SEO widget is auth-gated)
  * POST /cms/save-post → 401 / 403 / 405, NEVER 404 (auth gate, not missing route)

Offline-safe + report-only by design: network errors → status "unknown", exit 0.
`--strict` exits 2 when any critical route returns 404 (a real split-backend bug).

    python3 scripts/backend_route_check.py            # human summary + JSON report
    python3 scripts/backend_route_check.py --json      # machine JSON
    python3 scripts/backend_route_check.py --strict     # exit 2 on any critical 404
    python3 scripts/backend_route_check.py --api https://blog-vipzone-api.onrender.com
"""

from __future__ import annotations

import argparse
import json
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
REPORT = ROOT / "data" / "backend-route-status.json"
DEFAULT_API = "https://blog-vipzone-api.onrender.com"

# Each critical route: (name, method, path, accepted-status-codes).
# `0` is reserved for network/unknown and is never an acceptable terminal status.
CRITICAL_CHECKS = (
    # /health must be a live 200.
    ("health", "GET", "/health", (200,)),
    # /gsc/status is auth-gated: anything except 404 (route missing) is fine.
    ("gsc_status", "GET", "/gsc/status", (200, 401, 403, 405)),
    # /cms/save-post unauthenticated → auth/method gate, but NEVER 404.
    ("cms_save_post", "POST", "/cms/save-post", (401, 403, 405)),
)


def classify(status: int, accepted: tuple[int, ...]) -> str:
    """Pure classifier (no network) — used by tests and the runner.

    Returns one of: "ok" · "missing" (404) · "unexpected" · "unknown".
    """
    if status == 0:
        return "unknown"
    if status == 404:
        return "missing"
    if status in accepted:
        return "ok"
    return "unexpected"


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def config_api() -> str:
    """Read vipzone_api_url from config.toml [extra]; fall back to the default."""
    cfg = ROOT / "config.toml"
    if tomllib and cfg.exists():
        try:
            data = tomllib.loads(cfg.read_text(encoding="utf-8"))
            url = (data.get("extra", {}) or {}).get("vipzone_api_url", "")
            if url:
                return url.rstrip("/")
        except Exception:  # pragma: no cover - malformed config → default
            pass
    return DEFAULT_API


def probe(api: str, method: str, path: str, attempts: int = 3, timeout: int = 10) -> tuple[int, str]:
    """Return (http_status, error). status 0 + error on network failure.

    A 4xx/5xx is a *successful* probe (we want the status code), not an error —
    urllib raises HTTPError for those, so we read `.code` from it.
    """
    if not api:
        return 0, "no_api_url"
    url = api.rstrip("/") + path
    err = ""
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                url, method=method,
                headers={"User-Agent": "backend-route-check/1.0",
                         "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.getcode(), ""
        except urllib.error.HTTPError as exc:  # 4xx/5xx — a real status code
            return exc.code, ""
        except Exception as exc:  # network/timeout — stay offline-safe, retry
            err = f"{type(exc).__name__}: {exc}"
            if i < attempts - 1:
                time.sleep(min(2 ** i, 8))
    return 0, err


def fetch_health(api: str, timeout: int = 10) -> dict | None:
    """Best-effort GET /health JSON (for backend_sha / *_mounted / critical_routes)."""
    if not api:
        return None
    try:
        req = urllib.request.Request(
            api.rstrip("/") + "/health",
            headers={"User-Agent": "backend-route-check/1.0",
                     "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="V24 post-deploy route smoke for blog-vipzone-api")
    ap.add_argument("--api", default="", help="override backend base URL")
    ap.add_argument("--offline", action="store_true", help="skip network → status unknown")
    ap.add_argument("--strict", action="store_true", help="exit 2 on any critical 404")
    ap.add_argument("--json", action="store_true", help="print machine JSON")
    ap.add_argument("--no-write", action="store_true", help="do not write the report file")
    args = ap.parse_args(argv)

    api = (args.api or config_api()).rstrip("/")
    health = None if args.offline else fetch_health(api)

    results = []
    for name, method, path, accepted in CRITICAL_CHECKS:
        if args.offline:
            status, err, verdict = 0, "offline", "unknown"
        else:
            status, err = probe(api, method, path)
            verdict = classify(status, accepted)
        results.append({
            "name": name, "method": method, "path": path,
            "status": status, "verdict": verdict,
            "accepted": list(accepted), "error": err,
        })

    missing = [r for r in results if r["verdict"] == "missing"]
    unexpected = [r for r in results if r["verdict"] == "unexpected"]
    unknown = [r for r in results if r["verdict"] == "unknown"]
    if missing:
        overall = "split_backend_404"
    elif unexpected:
        overall = "unexpected"
    elif unknown and not args.offline:
        overall = "unreachable"
    elif args.offline:
        overall = "offline"
    else:
        overall = "ok"

    report = {
        "generated_at": _now_iso(),
        "api": api,
        "overall": overall,
        "backend_sha": (health or {}).get("backend_sha")
        or (health or {}).get("deployed_sha", ""),
        "cms_mounted": (health or {}).get("cms_mounted"),
        "gsc_mounted": (health or {}).get("gsc_mounted"),
        "health_critical_routes": (health or {}).get("critical_routes"),
        "checks": results,
    }

    if not args.no_write:
        try:
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        except OSError:
            pass

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Backend Route Check — V24 split-backend smoke")
        print(f"  API:     {api or '(none)'}")
        print(f"  Overall: {overall}")
        if report["backend_sha"]:
            print(f"  Backend SHA: {report['backend_sha']}")
        for r in results:
            mark = {"ok": "✓", "missing": "✗ 404", "unexpected": "⚠",
                    "unknown": "•"}.get(r["verdict"], "?")
            print(f"  {mark} {r['method']:4} {r['path']:18} "
                  f"→ {r['status'] or '—'} ({r['verdict']})")
        if missing:
            print("\n  V24: route(s) 404 on deployed services/vipzone — split-backend.")
            print("  FIXER: mount the route on services/vipzone (not visitor-counter).")

    # Report-only by default (exit 0). Strict gate fails only on a real 404.
    if args.strict and missing:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(run())
