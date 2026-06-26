#!/usr/bin/env python3
"""
Fetch Google Search Console metrics → data/gsc-metrics.json + static mirror.

Two real-data sources, in order of preference (NEVER fakes numbers):

  1. Direct GSC API — when the CI secrets below are all present.
  2. Live backend cache — GET <backend>/gsc/metrics. The blog backend
     (blog-vipzone-api) holds an OAuth-acquired refresh token and serves a
     cached metrics bundle publicly. When the operator connected GSC via OAuth
     on the backend but has NOT copied the refresh token into repo secrets, the
     direct path is unavailable — so we reuse the backend's already-cached REAL
     bundle for the build-time snapshot instead of writing a "not connected"
     placeholder. This does not touch OAuth; it only reads a public aggregate.

Env (GitHub Actions secrets) for the direct path:
  GSC_REFRESH_TOKEN
  GSC_PROPERTY_URL      — domain property: sc-domain:seomoney.org
                          (enforced by scripts/gsc_preflight.py deploy gate)
  GSC_CLIENT_ID
  GSC_CLIENT_SECRET

Env for the backend fallback (optional):
  GSC_BACKEND_URL       — default https://blog-vipzone-api.onrender.com

GSC_PROPERTY_URL secret must be the sc-domain property (not the old URL-prefix).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "vipzone"))

from gsc_client import (  # noqa: E402
    DEFAULT_GSC_PROPERTY_URL,
    disconnected_payload,
    fetch_metrics_bundle,
    normalize_gsc_property_url,
)

DATA_OUT = ROOT / "data" / "gsc-metrics.json"
STATIC_OUT = ROOT / "static" / "data" / "gsc-metrics.json"

# Public backend that serves the live OAuth-backed GSC cache (read-only aggregate).
DEFAULT_BACKEND_URL = "https://blog-vipzone-api.onrender.com"


def bundle_has_data(payload) -> bool:
    """True when a bundle is connected AND carries at least one real metric."""
    if not isinstance(payload, dict) or not payload.get("connected"):
        return False
    if payload.get("impressions") is not None or payload.get("clicks") is not None:
        return True
    if payload.get("indexed_pages") is not None:
        return True
    if payload.get("top_pages") or payload.get("top_queries"):
        return True
    trend = payload.get("trend") or {}
    return bool(trend.get("daily") or trend.get("weekly") or trend.get("monthly"))


def fetch_from_backend(backend_url: str, timeout: float = 45.0):
    """GET <backend>/gsc/metrics — the live OAuth-backed cache (no secrets needed).

    Returns the bundle only when it carries real connected data; otherwise None so
    the caller keeps its existing snapshot. Tolerant of Render free-tier cold starts.
    """
    url = backend_url.rstrip("/") + "/gsc/metrics"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) not in (200, None):
                return None
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network error, cold-start timeout, bad JSON
        print(f"backend gsc fetch failed: {exc}", file=sys.stderr)
        return None
    return payload if bundle_has_data(payload) else None


def resolve_payload(env: dict) -> dict | None:
    """Pick the best REAL bundle: direct GSC API → live backend cache → None."""
    refresh = env.get("GSC_REFRESH_TOKEN", "").strip()
    prop = normalize_gsc_property_url(
        env.get("GSC_PROPERTY_URL", DEFAULT_GSC_PROPERTY_URL).strip()
    )
    client_id = env.get("GSC_CLIENT_ID", "").strip()
    client_secret = env.get("GSC_CLIENT_SECRET", "").strip()
    backend_url = env.get("GSC_BACKEND_URL", DEFAULT_BACKEND_URL).strip()

    payload = None
    if all([refresh, prop, client_id, client_secret]):
        try:
            payload = fetch_metrics_bundle(refresh, client_id, client_secret, prop)
            print(
                f"gsc(direct): {prop} · impressions={payload.get('impressions')} "
                f"clicks={payload.get('clicks')} · health={payload.get('index_health')}"
            )
        except Exception as exc:
            print(f"ERROR: direct GSC fetch failed: {exc}", file=sys.stderr)
            payload = None

    # Secrets missing OR direct fetch failed → reuse the live backend cache so the
    # build-time snapshot still reflects the REAL data the backend already holds.
    if not bundle_has_data(payload) and backend_url:
        backend_payload = fetch_from_backend(backend_url)
        if backend_payload:
            payload = backend_payload
            print(
                f"gsc(backend): {backend_payload.get('property')} · "
                f"impressions={backend_payload.get('impressions')} "
                f"clicks={backend_payload.get('clicks')} · "
                f"health={backend_payload.get('index_health')}"
            )

    return payload if bundle_has_data(payload) else None


def main() -> int:
    payload = resolve_payload(dict(os.environ))

    if payload is None:
        # No real data available from either source. Never overwrite a previously
        # good snapshot with a placeholder; only seed one if none exists yet.
        if DATA_OUT.is_file():
            print("No live GSC data — keeping previous gsc-metrics.json", file=sys.stderr)
            return 0
        print("SKIP: GSC not connected — writing disconnected placeholder", file=sys.stderr)
        payload = disconnected_payload("not_connected")

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(text, encoding="utf-8")
    STATIC_OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
