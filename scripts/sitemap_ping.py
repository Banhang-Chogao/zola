#!/usr/bin/env python3
"""Submit sitemap to search engines after deploy.

1. Bing sitemap ping (no auth needed, always runs).
2. GSC sitemaps.submit() when GSC_* secrets are present.

Best-effort: all errors are printed, never raise, exit 0.

Usage:
    python3 scripts/sitemap_ping.py
    python3 scripts/sitemap_ping.py --dry-run
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRY = "--dry-run" in sys.argv

SITEMAP_URL = ""  # resolved from config.toml
GSC_PROPERTY_URL = ""  # resolved below

# ---------------------------------------------------------------------------
# Read base_url from config.toml
# ---------------------------------------------------------------------------

def _read_base_url() -> str:
    cfg = ROOT / "config.toml"
    for line in cfg.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*base_url\s*=\s*"([^"]+)"', line)
        if m:
            return m.group(1).rstrip("/")
    raise SystemExit("base_url not found in config.toml")


BASE_URL = _read_base_url()
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
GSC_PROPERTY_URL = f"{BASE_URL}/"

# ---------------------------------------------------------------------------
# Bing sitemap ping  (GET https://www.bing.com/ping?sitemap=<url>)
# ---------------------------------------------------------------------------

def ping_bing() -> None:
    encoded = urllib.parse.quote(SITEMAP_URL, safe="")
    url = f"https://www.bing.com/ping?sitemap={encoded}"
    print(f"[sitemap-ping] Bing: {url}")
    if DRY:
        print("[sitemap-ping] DRY-RUN — skipped")
        return
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "zola-sitemap-ping"}, method="GET"
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"[sitemap-ping] Bing → HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"[sitemap-ping] Bing HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}")
    except Exception as e:  # noqa: BLE001
        print(f"[sitemap-ping] Bing error: {e}")


# ---------------------------------------------------------------------------
# GSC sitemaps.submit()  (requires GSC_* env secrets + webmasters scope)
# ---------------------------------------------------------------------------

def _build_gsc_credentials(refresh: str, client_id: str, client_secret: str):
    """Build a Credentials object and force a token refresh."""
    try:
        from google.auth.transport.requests import Request  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
    except ImportError:
        print("[sitemap-ping] google-auth not installed — skipping GSC submit")
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        # webmasters (read+write) — needed for sitemaps.submit
        scopes=["https://www.googleapis.com/auth/webmasters"],
    )
    creds.refresh(Request())
    return creds


def submit_to_gsc() -> None:
    refresh = os.environ.get("GSC_REFRESH_TOKEN", "").strip()
    client_id = os.environ.get("GSC_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GSC_CLIENT_SECRET", "").strip()
    prop = os.environ.get("GSC_PROPERTY_URL", GSC_PROPERTY_URL).strip()
    if not prop.endswith("/"):
        prop += "/"

    if not all([refresh, client_id, client_secret]):
        print("[sitemap-ping] GSC_* secrets missing — skipping GSC submit (normal when not configured)")
        return

    print(f"[sitemap-ping] GSC sitemaps.submit: property={prop} sitemap={SITEMAP_URL}")
    if DRY:
        print("[sitemap-ping] DRY-RUN — skipped")
        return

    try:
        from googleapiclient.discovery import build  # type: ignore

        creds = _build_gsc_credentials(refresh, client_id, client_secret)
        if creds is None:
            return
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        # Note: sitemaps API uses the older webmasters v3 discovery internally.
        # The searchconsole v1 service exposes sitemaps() via webmasters scope.
        service.sitemaps().submit(siteUrl=prop, feedpath=SITEMAP_URL).execute()
        print(f"[sitemap-ping] GSC → sitemap submitted ✓")

        # Read back status
        try:
            result = service.sitemaps().get(siteUrl=prop, feedpath=SITEMAP_URL).execute()
            indexed = result.get("contents", [{}])[0].get("submitted", "?") if result.get("contents") else "?"
            pending = result.get("isPending", "?")
            print(f"[sitemap-ping] GSC status: isPending={pending} submitted={indexed}")
        except Exception as e:  # noqa: BLE001
            print(f"[sitemap-ping] GSC status read skipped: {e}")

    except Exception as e:  # noqa: BLE001
        print(f"[sitemap-ping] GSC submit error: {e} (best-effort, continuing)")


# ---------------------------------------------------------------------------
# Summary JSON  (written to data/sitemap-ping-report.json)
# ---------------------------------------------------------------------------

def write_report(steps: list[dict]) -> None:
    from datetime import datetime, timezone

    report = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sitemap_url": SITEMAP_URL,
        "gsc_property": GSC_PROPERTY_URL,
        "dry_run": DRY,
        "steps": steps,
    }
    out = ROOT / "data" / "sitemap-ping-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[sitemap-ping] report → {out.relative_to(ROOT)}")


# ---------------------------------------------------------------------------

def main() -> int:
    print(f"[sitemap-ping] sitemap={SITEMAP_URL}")
    steps: list[dict] = []

    try:
        ping_bing()
        steps.append({"engine": "bing", "status": "ok"})
    except Exception as e:  # noqa: BLE001
        steps.append({"engine": "bing", "status": "error", "detail": str(e)})

    try:
        submit_to_gsc()
        steps.append({"engine": "gsc", "status": "ok"})
    except Exception as e:  # noqa: BLE001
        steps.append({"engine": "gsc", "status": "error", "detail": str(e)})

    write_report(steps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
