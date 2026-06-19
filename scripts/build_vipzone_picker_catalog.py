#!/usr/bin/env python3
"""Generate data/vipzone-picker-catalog.json for VIPZone Content Picker."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "vipzone-picker-catalog.json"

sys.path.insert(0, str(ROOT / "scripts"))
from vipzone_picker_catalog import build_catalog  # noqa: E402


def main() -> int:
    catalog = build_catalog()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tools_n = len(catalog.get("tools") or [])
    prem_n = len(catalog.get("premium") or [])
    print(f"Wrote {OUTPUT} — {tools_n} tools, {prem_n} premium posts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())