#!/usr/bin/env python3
"""
Fetch Google Search Console metrics → data/gsc-metrics.json + static mirror.

Env (GitHub Actions secrets):
  GSC_REFRESH_TOKEN
  GSC_PROPERTY_URL      — e.g. https://banhang-chogao.github.io/zola/
  GSC_CLIENT_ID
  GSC_CLIENT_SECRET

After OAuth connect on blog backend, copy refresh token + property to secrets
for CI snapshot (build-time seo-reality fallback).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "visitor-counter"))

from gsc_client import disconnected_payload, fetch_metrics_bundle  # noqa: E402

DATA_OUT = ROOT / "data" / "gsc-metrics.json"
STATIC_OUT = ROOT / "static" / "data" / "gsc-metrics.json"


def main() -> int:
    refresh = os.environ.get("GSC_REFRESH_TOKEN", "").strip()
    prop = os.environ.get("GSC_PROPERTY_URL", "").strip()
    client_id = os.environ.get("GSC_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GSC_CLIENT_SECRET", "").strip()

    if not all([refresh, prop, client_id, client_secret]):
        print("SKIP: GSC secrets incomplete — writing disconnected placeholder", file=sys.stderr)
        payload = disconnected_payload("not_connected")
    else:
        try:
            payload = fetch_metrics_bundle(refresh, client_id, client_secret, prop)
            print(
                f"gsc: {prop} · impressions={payload.get('impressions')} "
                f"clicks={payload.get('clicks')} · health={payload.get('index_health')}"
            )
        except Exception as exc:
            print(f"ERROR: GSC fetch failed: {exc}", file=sys.stderr)
            if DATA_OUT.is_file():
                print("Keeping previous gsc-metrics.json", file=sys.stderr)
                return 0
            payload = disconnected_payload("api_error")

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(text, encoding="utf-8")
    STATIC_OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())