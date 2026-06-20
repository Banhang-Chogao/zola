#!/usr/bin/env python3
"""GSC deploy preflight + verifier.

Hard gate for production deploys. Two layers:

1. **Offline gate (always runs):** fail unless ``GSC_PROPERTY_URL`` resolves to the
   canonical *domain* property ``sc-domain:seomoney.org``. A URL-prefix property
   (``https://seomoney.org/``) or any other value FAILS the deploy. This needs no
   network and cannot flake.

2. **Live verify (when OAuth creds are present, or forced with --require-live):**
   - ``sites.list`` → the property exists and the account is NOT a
     ``siteUnverifiedUser`` (real read permission).
   - ``sitemaps.list`` → ``https://seomoney.org/sitemap.xml`` is registered.
   - 7-day Search Analytics smoke fetch → endpoint answers for the property.

Security: this script NEVER logs credentials. Only booleans, the property string,
the sitemap URL, and aggregate counts are printed. Refresh tokens / client secrets
are read from the environment and passed straight to the Google client.

Env:
  GSC_PROPERTY_URL   — must be ``sc-domain:seomoney.org``
  GSC_REFRESH_TOKEN  — OAuth refresh token (live verify only)
  GSC_CLIENT_ID      — OAuth client id (live verify only)
  GSC_CLIENT_SECRET  — OAuth client secret (live verify only)

Exit codes:
  0 — all checks passed (or live skipped because creds absent and not required)
  2 — a preflight check FAILED → deploy must stop

Usage:
  python3 scripts/gsc_preflight.py                # gate + live-if-creds
  python3 scripts/gsc_preflight.py --gate-only    # offline property gate only
  python3 scripts/gsc_preflight.py --require-live  # creds mandatory; fail if missing
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICE_DIR = ROOT / "services" / "visitor-counter"
sys.path.insert(0, str(SERVICE_DIR))

# Canonical values are kept in sync with gsc_client.EXPECTED_GSC_PROPERTY /
# EXPECTED_SITEMAP_URL. Inlined here so the OFFLINE gate has zero dependency on
# the google-* wheels (gsc_client imports them at module load); those are only
# needed for the live-verify path below.
EXPECTED_GSC_PROPERTY = "sc-domain:seomoney.org"
EXPECTED_SITEMAP_URL = "https://seomoney.org/sitemap.xml"

CRED_VARS = ("GSC_REFRESH_TOKEN", "GSC_CLIENT_ID", "GSC_CLIENT_SECRET")


def normalize_property_for_match(value: str) -> str:
    """Canonicalize a property id for equality checks (case-insensitive host)."""
    v = (value or "").strip()
    if v.startswith("sc-domain:"):
        host = v[len("sc-domain:") :].strip().lower().rstrip("/")
        return f"sc-domain:{host}"
    if v and not v.endswith("/"):
        v += "/"
    return v.lower()


def is_expected_property(value: str) -> bool:
    """True only when ``value`` resolves to the canonical domain property."""
    return bool(value) and normalize_property_for_match(value) == EXPECTED_GSC_PROPERTY


def _ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}", file=sys.stderr)


def _skip(msg: str) -> None:
    print(f"  SKIP  {msg}")


def check_property_gate() -> bool:
    """Offline gate: GSC_PROPERTY_URL must be the canonical domain property."""
    raw = os.environ.get("GSC_PROPERTY_URL", "").strip()
    if not raw:
        _fail(
            "GSC_PROPERTY_URL is not set — expected "
            f"'{EXPECTED_GSC_PROPERTY}'"
        )
        return False
    if not is_expected_property(raw):
        # Echo the *normalized* value, never anything secret.
        _fail(
            f"GSC_PROPERTY_URL='{normalize_property_for_match(raw)}' "
            f"≠ required '{EXPECTED_GSC_PROPERTY}'. "
            "Use the domain property (sc-domain:seomoney.org), not a URL-prefix."
        )
        return False
    _ok(f"GSC_PROPERTY_URL = {EXPECTED_GSC_PROPERTY}")
    return True


def _creds_present() -> bool:
    return all(os.environ.get(v, "").strip() for v in CRED_VARS)


def verify_live() -> bool:
    """sites.list permission + sitemap registration + 7d analytics smoke."""
    from gsc_client import (
        build_credentials,
        find_property_permission,
        list_sitemap_paths,
        smoke_search_analytics,
    )

    refresh = os.environ["GSC_REFRESH_TOKEN"].strip()
    client_id = os.environ["GSC_CLIENT_ID"].strip()
    client_secret = os.environ["GSC_CLIENT_SECRET"].strip()
    prop = EXPECTED_GSC_PROPERTY

    try:
        creds = build_credentials(refresh, client_id, client_secret)
    except Exception as exc:  # noqa: BLE001 — surface a redacted reason only
        _fail(f"OAuth refresh failed: {type(exc).__name__}")
        return False

    ok = True

    # 1) sites.list permission
    try:
        verified, perm = find_property_permission(creds, prop)
    except Exception as exc:  # noqa: BLE001
        _fail(f"sites.list failed: {type(exc).__name__}")
        return False
    if verified:
        _ok(f"sites.list — property present, permissionLevel={perm}")
    else:
        if perm is None:
            _fail(f"sites.list — '{prop}' not in verified properties for this account")
        else:
            _fail(f"sites.list — '{prop}' present but permissionLevel={perm} (no read access)")
        ok = False

    # 2) sitemap registration
    try:
        paths = list_sitemap_paths(creds, prop)
    except Exception as exc:  # noqa: BLE001
        _fail(f"sitemaps.list failed: {type(exc).__name__}")
        return False
    want = EXPECTED_SITEMAP_URL.rstrip("/")
    if any(p.rstrip("/") == want for p in paths):
        _ok(f"sitemaps.list — {EXPECTED_SITEMAP_URL} registered")
    else:
        _fail(
            f"sitemaps.list — {EXPECTED_SITEMAP_URL} NOT registered "
            f"(found {len(paths)} sitemap(s))"
        )
        ok = False

    # 3) 7-day Search Analytics smoke fetch
    try:
        agg = smoke_search_analytics(creds, prop, days=7)
    except Exception as exc:  # noqa: BLE001
        _fail(f"searchanalytics.query (7d) failed: {type(exc).__name__}")
        return False
    _ok(
        "searchanalytics.query (7d) — "
        f"impressions={int(agg['impressions'])} clicks={int(agg['clicks'])}"
    )

    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GSC deploy preflight + verifier")
    parser.add_argument(
        "--gate-only",
        action="store_true",
        help="Run only the offline GSC_PROPERTY_URL gate (no network).",
    )
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Fail if OAuth creds are missing (forces live verification).",
    )
    args = parser.parse_args(argv)

    print("GSC preflight")

    gate_ok = check_property_gate()
    if not gate_ok:
        print("\nGSC preflight: FAILED (property gate)", file=sys.stderr)
        return 2

    if args.gate_only:
        print("\nGSC preflight: PASSED (gate-only)")
        return 0

    if not _creds_present():
        if args.require_live:
            _fail("OAuth creds missing (GSC_REFRESH_TOKEN/GSC_CLIENT_ID/GSC_CLIENT_SECRET)")
            print("\nGSC preflight: FAILED (creds required)", file=sys.stderr)
            return 2
        _skip("live verify — OAuth creds not provided (gate passed)")
        print("\nGSC preflight: PASSED (gate; live skipped)")
        return 0

    if verify_live():
        print("\nGSC preflight: PASSED (gate + live verify)")
        return 0

    print("\nGSC preflight: FAILED (live verify)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
