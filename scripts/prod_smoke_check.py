#!/usr/bin/env python3
"""deploysafe29 — post-deploy production smoke check for the Render backend (V29).

GitHub Pages deploy (`deploy.yml`) ships the latest `main`, but the FastAPI backend
on Render (`blog-vipzone-api`) only redeploys on a **manual** Blueprint sync. So a
PR that adds/changes a backend route (`services/vipzone`, `render.yaml`, GSC/CMS API)
is **"code merged, prod pending"** until a Render Manual Sync lands AND the live route
answers. A green Pages deploy is NOT proof the backend serves the new code.

This verifies the critical routes return **non-404** (route present = backend has the
code). A 404 on any of them = the backend lags `main` → Render Manual Sync needed.

Sandbox-safe: the agent's sandbox egress often blocks `blog-vipzone-api.onrender.com`
(`host_not_allowed`). When that happens we DO NOT retry forever — we report
"external verification blocked" and print the exact curl commands for a human to run
from an allowlisted host. Report-only by default (exit 0) unless `--strict`.

    python3 scripts/prod_smoke_check.py            # human summary + data/prod-smoke-report.json
    python3 scripts/prod_smoke_check.py --json      # machine JSON
    python3 scripts/prod_smoke_check.py --curl       # just print the curl commands
    python3 scripts/prod_smoke_check.py --offline    # skip network → print curls, exit 0
    python3 scripts/prod_smoke_check.py --strict      # exit 2 if a route is confirmed 404
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
REPORT = ROOT / "data" / "prod-smoke-report.json"
DEFAULT_API = "https://blog-vipzone-api.onrender.com"

# Critical routes whose absence (404) proves the deployed backend lags `main`.
# Each is reachable WITHOUT auth and answers non-404 when the router is mounted:
#   /health            → 200
#   /gsc/status        → 200 (public)
#   /gsc/oauth/start   → 401 missing_token (NOT 404)
#   /cms/save-post     → 401 missing_token (NOT 404)
# Kept in sync with services/vipzone/main.py CRITICAL_ROUTES (test asserts parity).
CRITICAL_ROUTES = [
    {"method": "GET", "path": "/health", "why": "service alive + backend_sha / mount flags"},
    {"method": "GET", "path": "/gsc/status", "why": "GSC router mounted (SEO Reality Check)"},
    {"method": "GET", "path": "/gsc/oauth/start", "why": "GSC OAuth mounted (401 w/o auth = present)"},
    {"method": "POST", "path": "/cms/save-post", "why": "CMS write mounted (401 w/o auth = present)"},
]

# Signatures that mean the sandbox network policy blocked egress to the host — NOT a
# backend failure. The definitive signal is the proxy's `x-deny-reason: host_not_allowed`
# header; the body/error substrings are a fallback. Keyed tightly so a genuine app 403
# (e.g. superadmin_required) never false-trips.
_EGRESS_TOKENS = (
    "host_not_allowed",
    "host not allowed",
    "not in allowlist",
    "network egress",
    "egress settings",
    "egress blocked",
)


def _is_egress_blocked(status_code: int | None, body: str, error: str, headers: dict | None = None) -> bool:
    if headers:
        deny = ""
        for k, v in headers.items():
            if str(k).lower() == "x-deny-reason":
                deny = str(v).lower()
                break
        if "host_not_allowed" in deny:
            return True
    blob = f"{body or ''}\n{error or ''}".lower()
    return any(tok in blob for tok in _EGRESS_TOKENS)


def classify_route(method: str, path: str, status_code: int | None, body: str, error: str,
                   headers: dict | None = None) -> dict:
    """Pure per-route classifier (unit-tested, no I/O).

    present=True  → route answered non-404 (backend has the code)
    present=False → 404 (route missing → backend stale / not redeployed)
    present=None  → could not verify (egress blocked / unreachable)
    """
    route = f"{method} {path}"
    if _is_egress_blocked(status_code, body or "", error or "", headers):
        return {"route": route, "method": method, "path": path, "status_code": status_code,
                "present": None, "state": "blocked",
                "note": "egress blocked (host_not_allowed) — verify from an allowlisted host"}
    if error:
        return {"route": route, "method": method, "path": path, "status_code": None,
                "present": None, "state": "unreachable",
                "note": f"không phản hồi ({error}) — Render free dyno có thể đang ngủ"}
    if status_code == 404:
        return {"route": route, "method": method, "path": path, "status_code": 404,
                "present": False, "state": "missing",
                "note": "404 — route THIẾU trên backend deploy → cần Render Manual Sync"}
    return {"route": route, "method": method, "path": path, "status_code": status_code,
            "present": True, "state": "present",
            "note": f"{status_code} (non-404) — route đã có trên backend"}


def classify_smoke(route_results: list[dict]) -> dict:
    """Pure overall classifier from per-route results (unit-tested, no I/O)."""
    states = [r["state"] for r in route_results]
    if not states:
        return {"overall": "unknown", "ok": False,
                "message": "Không có route nào được kiểm tra.", "action": "check-config"}
    if "blocked" in states:
        return {
            "overall": "verification_blocked",
            "ok": False,
            "message": ("External verification blocked — sandbox egress chặn host "
                        "(host_not_allowed). KHÔNG retry; chạy curl thủ công từ host được allowlist."),
            "action": "human-curl",
        }
    if "missing" in states:
        missing = [r["route"] for r in route_results if r["state"] == "missing"]
        return {
            "overall": "routes_missing",
            "ok": False,
            "message": ("BACKEND STALE — route 404 trên production: %s. GitHub Pages deploy != "
                        "Render deploy → Render dashboard → Blueprints → Manual Sync `blog-vipzone-api`."
                        % ", ".join(missing)),
            "action": "render-deploy",
        }
    if "unreachable" in states:
        return {
            "overall": "unreachable",
            "ok": False,
            "message": "Backend không phản hồi (dyno ngủ?) — thử lại sau, KHÔNG kết luận stale.",
            "action": "retry",
        }
    return {
        "overall": "all_present",
        "ok": True,
        "message": "Tất cả critical route trả non-404 — backend đã phục vụ code mới.",
        "action": "none",
    }


def curl_commands(api: str) -> list[str]:
    """Exact curl commands a human can paste from an allowlisted host."""
    base = api.rstrip("/")
    cmds: list[str] = []
    for r in CRITICAL_ROUTES:
        fmt = "%{http_code}  " + r["path"] + "\\n"
        if r["method"] == "POST":
            cmds.append(
                "curl -sS -o /dev/null -w '%s' -X POST -H 'Content-Type: application/json' "
                "-d '{}' %s%s" % (fmt, base, r["path"])
            )
        else:
            cmds.append("curl -sS -o /dev/null -w '%s' %s%s" % (fmt, base, r["path"]))
    return cmds


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
    try:
        import re

        m = re.search(r'(?m)^\s*vipzone_api_url\s*=\s*"([^"]+)"', cfg.read_text(encoding="utf-8"))
        if m:
            return m.group(1).rstrip("/")
    except Exception:
        pass
    return DEFAULT_API


def probe(api: str, method: str, path: str, timeout: int = 8, attempts: int = 3) -> dict:
    """Probe one route. Retries only transient connection errors; an egress block or
    any HTTP response (incl. 4xx/5xx/404) returns immediately — never retry forever."""
    url = api.rstrip("/") + path
    err = ""
    for i in range(attempts):
        try:
            data = b"{}" if method == "POST" else None
            req = urllib.request.Request(
                url,
                data=data,
                method=method,
                headers={
                    "User-Agent": "deploysafe29/1.0",
                    "Accept": "application/json",
                    **({"Content-Type": "application/json"} if data else {}),
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read(2048).decode("utf-8", "replace")
                return {"status_code": getattr(resp, "status", resp.getcode()),
                        "body": body, "error": "", "headers": dict(resp.headers)}
        except urllib.error.HTTPError as exc:  # 4xx/5xx — the route (or proxy) answered
            body = ""
            try:
                body = exc.read(2048).decode("utf-8", "replace")
            except Exception:
                pass
            hdrs = dict(exc.headers or {})
            # A sandbox-proxy 403 (x-deny-reason: host_not_allowed) is an egress block,
            # not a real route answer — return immediately, do not retry.
            return {"status_code": exc.code, "body": body, "error": "", "headers": hdrs}
        except Exception as exc:  # connection-level failure
            err = f"{type(exc).__name__}: {exc}"
            if _is_egress_blocked(None, "", err):  # blocked → bail now, no retry
                return {"status_code": None, "body": "", "error": err, "headers": {}}
            if i < attempts - 1:
                time.sleep(min(2 ** i, 8))
    return {"status_code": None, "body": "", "error": err, "headers": {}}


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description="deploysafe29 — production backend smoke check (V29)")
    ap.add_argument("--api", default="", help="override backend base URL")
    ap.add_argument("--offline", action="store_true", help="skip network → print curls, exit 0")
    ap.add_argument("--curl", action="store_true", help="only print curl commands and exit 0")
    ap.add_argument("--strict", action="store_true", help="exit 2 if a route is confirmed 404")
    ap.add_argument("--json", action="store_true", help="print machine JSON")
    ap.add_argument("--timeout", type=int, default=8, help="per-route timeout seconds")
    ap.add_argument("--no-write", action="store_true", help="do not write data/prod-smoke-report.json")
    args = ap.parse_args(argv)

    api = (args.api or config_api()).rstrip("/")
    curls = curl_commands(api)

    if args.curl:
        print("# Production backend smoke check — run from an allowlisted host:")
        print("\n".join(curls))
        return 0

    route_results: list[dict] = []
    health_info: dict = {}
    if args.offline:
        for r in CRITICAL_ROUTES:
            route_results.append(classify_route(r["method"], r["path"], None, "", "offline"))
    else:
        for r in CRITICAL_ROUTES:
            p = probe(api, r["method"], r["path"], timeout=args.timeout)
            rr = classify_route(r["method"], r["path"], p["status_code"], p["body"],
                                p["error"], p.get("headers"))
            route_results.append(rr)
            if r["path"] == "/health" and p["body"]:
                try:
                    h = json.loads(p["body"])
                    health_info = {
                        "backend_sha": h.get("backend_sha") or h.get("deployed_sha", ""),
                        "gsc_mounted": h.get("gsc_mounted"),
                        "cms_mounted": h.get("cms_mounted"),
                        "premium_content": h.get("premium_content"),
                    }
                except Exception:
                    pass
            # Egress blocked → stop hammering a blocked host (no retry forever).
            if rr["state"] == "blocked":
                for rest in CRITICAL_ROUTES[len(route_results):]:
                    route_results.append(
                        classify_route(rest["method"], rest["path"], None, "host_not_allowed", "")
                    )
                break

    verdict = classify_smoke(route_results)

    now = datetime.now(_TZ)
    report = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generated_display": now.strftime("%H:%M %d/%m/%Y"),
        "service": "blog-vipzone-api",
        "api": api,
        "routes": route_results,
        "health": health_info,
        "curl": curls,
        **verdict,
    }

    if not args.no_write:
        try:
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"[deploysafe29] warn: could not write report: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        icon = {"all_present": "✅", "routes_missing": "❌", "verification_blocked": "🚧",
                "unreachable": "❔", "unknown": "❔"}.get(verdict["overall"], "•")
        print("deploysafe29 — production backend smoke check (V29)")
        print(f"  service : blog-vipzone-api  ({api})")
        for rr in route_results:
            mark = {"present": "✅", "missing": "❌", "blocked": "🚧", "unreachable": "❔"}.get(rr["state"], "•")
            code = rr["status_code"] if rr["status_code"] is not None else "—"
            print(f"  {mark} {rr['route']:<22} {str(code):>4}  {rr['note']}")
        print(f"  status  : {icon} {verdict['overall'].upper()}")
        print(f"  {verdict['message']}")
        if verdict["action"] == "render-deploy":
            print("  → fix : Render dashboard → Blueprints → Manual Sync `blog-vipzone-api`")
        if verdict["action"] in ("human-curl",) or verdict["overall"] in ("verification_blocked", "unreachable"):
            print("  → verify manually from an allowlisted host:")
            for c in curls:
                print(f"      {c}")
            print("    (non-404 = route present; 404 = backend stale → Render Manual Sync)")

    if args.strict and verdict["overall"] == "routes_missing":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
