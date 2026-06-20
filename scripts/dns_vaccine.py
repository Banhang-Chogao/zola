#!/usr/bin/env python3
"""
DNS Vaccine — early detection of Cloudflare/GitHub Pages origin failures.

Born from the `seomoney.org` migration (github.io → custom apex domain) that
hit **Cloudflare Error 1016 (Origin DNS error)**: Cloudflare's edge could not
resolve the origin a proxied DNS record pointed at, so every request to the
apex failed before reaching GitHub Pages.

This vaccine codifies the correct setup and checks it on a schedule + before
deploy, so a 1016 / NXDOMAIN / base_url drift is caught early instead of in
production.

What it validates
-----------------
REPO (offline, deterministic — safe to gate a deploy on):
  R1  static/CNAME exists and holds exactly one bare apex domain.
  R2  config.toml base_url host == the CNAME domain  (no drift).
  R3  base_url uses https and has no leftover "/zola" path segment.

LIVE (network via DNS-over-HTTPS + HTTP probes — monitor/alert):
  L1  apex A records ⊆ the 4 GitHub Pages anycast IPs; NO apex CNAME (1016 risk).
  L2  www resolves to banhang-chogao.github.io (CNAME) or the GitHub Pages IPs.
  L3  https://<domain>/ is reachable AND not a Cloudflare error page
      (explicit 1016 / "Origin DNS error" / 5xx cf-error detection).
  L4  the GitHub Pages origin (banhang-chogao.github.io) is itself reachable.

Correct GitHub Pages + Cloudflare DNS (the fix this vaccine enforces)
--------------------------------------------------------------------
  apex  seomoney.org   A   185.199.108.153
                       A   185.199.109.153
                       A   185.199.110.153
                       A   185.199.111.153
  www   www.seomoney.org  CNAME  banhang-chogao.github.io
  - Remove any apex CNAME (it cannot coexist with A records and, if its target
    is unresolvable, is the classic 1016 cause).
  - SSL/TLS mode: Full (Strict) once GitHub issues the cert; never Flexible.
  - A records always resolve, so Cloudflare can never raise 1016 for the apex.

Exit codes
----------
  0  healthy (or warnings only)
  2  hard failure: 1016 detected, apex NXDOMAIN/CNAME, or repo drift under --gate

Usage
-----
  python3 scripts/dns_vaccine.py                 # full check (repo + live)
  python3 scripts/dns_vaccine.py --offline       # repo invariants only (no net)
  python3 scripts/dns_vaccine.py --gate          # fail on repo drift (pre-deploy)
  python3 scripts/dns_vaccine.py --strict         # also fail on any live failure
  python3 scripts/dns_vaccine.py --json           # machine-readable to stdout

Stdlib only. Never crashes the caller — every network/parse path is guarded and
degrades to status "unknown" so a restricted runner cannot hang or false-fail.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config.toml"
CNAME_FILE = REPO / "static" / "CNAME"
REPORT = REPO / "data" / "dns-vaccine-report.json"

# The 4 GitHub Pages apex anycast IPs (A records). All end in .153; third octet
# 108–111. These ALWAYS resolve, which is why apex A (not CNAME) avoids 1016.
GITHUB_PAGES_IPV4 = {
    "185.199.108.153",
    "185.199.109.153",
    "185.199.110.153",
    "185.199.111.153",
}
GITHUB_PAGES_IPV6 = {
    "2606:50c0:8000::153",
    "2606:50c0:8001::153",
    "2606:50c0:8002::153",
    "2606:50c0:8003::153",
}
# Org/user Pages host that a project-site custom domain ultimately serves from.
PAGES_ORIGIN_HOST = "banhang-chogao.github.io"

DOH_ENDPOINTS = (
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query",
)

# Body / header signatures of a Cloudflare origin-resolution failure.
CF_1016_SIGNS = (
    "error 1016",
    "origin dns error",
    "dns points to prohibited ip",
    "1016:",
)

UA = "dns-vaccine/1.0 (+github-actions)"
TIMEOUT = 8


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(name: str, status: str, detail: str, **extra) -> dict:
    rec = {"check": name, "status": status, "detail": detail}
    rec.update(extra)
    return rec


def doh_query(name: str, rtype: str) -> list[str] | None:
    """Resolve via DNS-over-HTTPS JSON API. Returns list of record data, or
    None on network/parse failure (caller treats None as 'unknown')."""
    for base in DOH_ENDPOINTS:
        url = f"{base}?name={name}&type={rtype}"
        req = urllib.request.Request(
            url, headers={"accept": "application/dns-json", "user-agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001 - any failure → try next / unknown
            continue
        if not isinstance(data, dict):
            continue
        answers = data.get("Answer") or []
        # type numbers: A=1, AAAA=28, CNAME=5
        want = {"A": 1, "AAAA": 28, "CNAME": 5, "NS": 2, "SOA": 6}.get(rtype)
        out = [a.get("data", "").rstrip(".") for a in answers
               if want is None or a.get("type") == want]
        return out
    return None


def http_probe(url: str) -> dict:
    """GET a URL; classify reachability + Cloudflare 1016/error pages."""
    req = urllib.request.Request(url, headers={"user-agent": UA})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            body = resp.read(8192).decode("utf-8", "replace").lower()
            return {
                "url": url, "ok": True, "code": resp.status,
                "server": resp.headers.get("Server", ""),
                "cf_ray": resp.headers.get("CF-RAY", ""),
                "is_1016": any(s in body for s in CF_1016_SIGNS),
            }
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read(8192).decode("utf-8", "replace").lower()
        except Exception:  # noqa: BLE001
            pass
        return {
            "url": url, "ok": False, "code": exc.code,
            "server": exc.headers.get("Server", "") if exc.headers else "",
            "cf_ray": exc.headers.get("CF-RAY", "") if exc.headers else "",
            "is_1016": any(s in body for s in CF_1016_SIGNS),
        }
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "ok": False, "code": None, "error": type(exc).__name__}


def read_base_url_host() -> tuple[str, str]:
    """Return (base_url, host) from config.toml."""
    try:
        for line in CONFIG.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("base_url") and "=" in s:
                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                return val, urlparse(val).netloc
    except OSError:
        pass
    return "", ""


def read_cname() -> str:
    try:
        return CNAME_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except (OSError, IndexError):
        return ""


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def repo_checks(checks: list[dict]) -> str | None:
    """Deterministic repo-local invariants. Returns the apex domain (from CNAME
    or base_url) for the live checks, or None."""
    base_url, base_host = read_base_url_host()
    cname = read_cname()

    # R1 — CNAME file
    if cname:
        bare = re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", cname.lower())
        if bare:
            checks.append(_check("R1-cname-file", "pass",
                                 f"static/CNAME = {cname}"))
        else:
            checks.append(_check("R1-cname-file", "fail",
                                 f"static/CNAME content not a bare domain: {cname!r}"))
    else:
        checks.append(_check("R1-cname-file", "warn",
                             "static/CNAME missing — GitHub Pages may drop the "
                             "custom domain on deploy. Add a CNAME file holding "
                             "the apex domain."))

    # R3 — base_url shape
    if base_url.startswith("https://"):
        checks.append(_check("R3-base-https", "pass", f"base_url = {base_url}"))
    else:
        checks.append(_check("R3-base-https", "warn",
                             f"base_url should be https://… (got {base_url!r})"))
    if "/zola" in urlparse(base_url).path:
        checks.append(_check("R3-base-path", "warn",
                             "base_url still contains the /zola GitHub Pages "
                             "subpath; an apex-domain deploy expects no path."))

    # R2 — base_url host vs CNAME domain (drift)
    apex = cname or base_host
    if cname and base_host:
        if base_host.lower() == cname.lower():
            checks.append(_check("R2-host-match", "pass",
                                 f"base_url host == CNAME ({cname})"))
        else:
            checks.append(_check(
                "R2-host-match", "fail",
                f"DRIFT: base_url host '{base_host}' != CNAME '{cname}'. "
                f"Set base_url = https://{cname} so generated URLs/sitemap/RSS/"
                f"canonical match the served domain."))
    return apex or None


def live_checks(domain: str, checks: list[dict], offline: bool) -> None:
    if offline:
        checks.append(_check("live", "skip", "offline mode — live checks skipped"))
        return

    apex = domain
    www = f"www.{domain}"

    # L1 — apex A + apex CNAME conflict
    a = doh_query(apex, "A")
    cname_apex = doh_query(apex, "CNAME")
    if a is None:
        checks.append(_check("L1-apex-a", "unknown",
                             "could not query DNS (restricted runner?)"))
    elif not a:
        checks.append(_check("L1-apex-a", "fail",
                             f"NXDOMAIN / no A records for {apex} — Cloudflare "
                             f"will 1016. Add the 4 GitHub Pages A records.",
                             resolved=a))
    else:
        extra = set(a) - GITHUB_PAGES_IPV4
        if extra:
            checks.append(_check("L1-apex-a", "warn",
                                 f"{apex} A records include non-GitHub IPs: "
                                 f"{sorted(extra)}", resolved=a))
        else:
            checks.append(_check("L1-apex-a", "pass",
                                 f"{apex} → GitHub Pages IPs {sorted(a)}",
                                 resolved=a))
    if cname_apex:
        checks.append(_check("L1-apex-cname", "fail",
                             f"{apex} has a CNAME ({cname_apex}) — apex must use "
                             f"A records; a CNAME to an unresolvable target is the "
                             f"classic Error 1016 cause.", resolved=cname_apex))

    # L2 — www
    cn = doh_query(www, "CNAME")
    wa = doh_query(www, "A")
    if cn and any(PAGES_ORIGIN_HOST in c for c in cn):
        checks.append(_check("L2-www", "pass", f"{www} CNAME → {cn}"))
    elif wa and set(wa) <= GITHUB_PAGES_IPV4:
        checks.append(_check("L2-www", "pass", f"{www} A → {wa}"))
    elif cn is None and wa is None:
        checks.append(_check("L2-www", "unknown", "could not query DNS"))
    elif not cn and not wa:
        checks.append(_check("L2-www", "warn",
                             f"{www} has no CNAME/A — add CNAME {www} → "
                             f"{PAGES_ORIGIN_HOST}"))
    else:
        checks.append(_check("L2-www", "warn",
                             f"{www} resolves unexpectedly (CNAME={cn}, A={wa})"))

    # L3 — HTTP probe of apex (the actual 1016 surface)
    probe = http_probe(f"https://{apex}/")
    if probe.get("is_1016"):
        checks.append(_check("L3-http", "fail",
                             f"https://{apex}/ returns Cloudflare Error 1016 "
                             f"(Origin DNS error). Fix apex DNS records.",
                             probe=probe))
    elif probe.get("ok") or (probe.get("code") in (301, 302, 304, 404)):
        checks.append(_check("L3-http", "pass",
                             f"https://{apex}/ reachable (HTTP {probe.get('code')})",
                             probe=probe))
    elif probe.get("code") is None:
        checks.append(_check("L3-http", "unknown",
                             f"could not reach https://{apex}/ "
                             f"({probe.get('error', 'network')})", probe=probe))
    else:
        checks.append(_check("L3-http", "warn",
                             f"https://{apex}/ HTTP {probe.get('code')}", probe=probe))

    # L4 — GitHub Pages origin reachable
    origin = http_probe(f"https://{PAGES_ORIGIN_HOST}/")
    if origin.get("code") is not None:
        checks.append(_check("L4-origin", "pass",
                             f"origin {PAGES_ORIGIN_HOST} reachable "
                             f"(HTTP {origin.get('code')})"))
    else:
        checks.append(_check("L4-origin", "unknown",
                             f"origin {PAGES_ORIGIN_HOST} unreachable from runner"))


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def summarize(checks: list[dict]) -> dict:
    fails = [c for c in checks if c["status"] == "fail"]
    warns = [c for c in checks if c["status"] == "warn"]
    unknown = [c for c in checks if c["status"] == "unknown"]
    status = "fail" if fails else ("warn" if warns else "ok")
    return {
        "status": status,
        "fail": len(fails),
        "warn": len(warns),
        "unknown": len(unknown),
        "pass": sum(1 for c in checks if c["status"] == "pass"),
    }


def write_report(payload: dict) -> None:
    try:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if REPORT.exists():
            try:
                prev = json.loads(REPORT.read_text(encoding="utf-8"))
                history = prev.get("history", [])
            except (OSError, json.JSONDecodeError):
                history = []
        history.insert(0, {
            "at": payload["generated_at"],
            "domain": payload.get("domain"),
            "status": payload["summary"]["status"],
            "fail": payload["summary"]["fail"],
            "warn": payload["summary"]["warn"],
        })
        payload["history"] = history[:30]
        REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    except OSError as exc:
        print(f"WARN: could not write report: {exc}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="DNS Vaccine — Cloudflare/GitHub Pages health.")
    ap.add_argument("--domain", help="apex domain to check (default: from CNAME/base_url)")
    ap.add_argument("--offline", action="store_true", help="repo invariants only")
    ap.add_argument("--gate", action="store_true",
                    help="exit 2 on repo DRIFT/FAIL (pre-deploy gate)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 on any live FAIL too")
    ap.add_argument("--json", action="store_true", help="machine-readable stdout")
    args = ap.parse_args()

    checks: list[dict] = []
    apex = repo_checks(checks)
    domain = args.domain or apex
    if domain:
        live_checks(domain, checks, offline=args.offline)
    else:
        checks.append(_check("live", "skip",
                             "no domain (set static/CNAME or --domain) — live skipped"))

    summary = summarize(checks)
    payload = {
        "generated_at": _now(),
        "domain": domain,
        "summary": summary,
        "checks": checks,
        "expected": {
            "apex_a_records": sorted(GITHUB_PAGES_IPV4),
            "www_cname": PAGES_ORIGIN_HOST,
            "ssl_mode": "Full (Strict)",
        },
    }
    write_report(payload)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"DNS Vaccine — domain={domain or '(none)'} status={summary['status'].upper()} "
              f"(pass={summary['pass']} warn={summary['warn']} "
              f"fail={summary['fail']} unknown={summary['unknown']})")
        for c in checks:
            mark = {"pass": "✅", "warn": "⚠️ ", "fail": "❌", "skip": "·",
                    "unknown": "❔"}.get(c["status"], "?")
            print(f"  {mark} {c['check']:<16} {c['detail']}")

    # Exit policy
    repo_drift = any(c["status"] == "fail" and c["check"].startswith(("R1", "R2", "R3"))
                     for c in checks)
    live_fail = any(c["status"] == "fail" and c["check"].startswith("L")
                    for c in checks)
    if args.gate and repo_drift:
        return 2
    if args.strict and (repo_drift or live_fail):
        return 2
    # Default: 1016 / apex NXDOMAIN is always worth a non-zero (alert), but only
    # when we actually reached the network (avoid false-fail on restricted runner).
    if live_fail and not args.offline:
        return 2 if args.strict else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
