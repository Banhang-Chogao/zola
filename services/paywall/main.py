"""
Render entrypoint — re-export FastAPI app from backend/paywall_app.py.

Repo root is two levels up; private_content/ and data/paywall.db live there.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.paywall_app import app  # noqa: E402

__all__ = ["app"]