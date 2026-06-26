#!/usr/bin/env python3
"""CLI: gửi email approve code (dùng khi không qua admin UI)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.paywall_email import send_approve_email  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Gửi email approve code paywall")
    parser.add_argument("--to", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--expires", default="7 ngày")
    args = parser.parse_args()

    send_approve_email(
        to_email=args.to,
        post_title=args.title,
        post_url=args.url,
        approve_code=args.code,
        expires_at=args.expires,
    )
    print(f"Sent to {args.to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())