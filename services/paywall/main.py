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


# ---------------------------------------------------------------------------
# Optional self-hosted TLS entry point.
#
# Production (Render/PaaS) runs `uvicorn main:app` and terminates TLS at the
# platform edge, so this block never executes there — routing/architecture are
# unchanged. When a host runs `python main.py` directly, TLS is enabled only in
# production *and* only when cert files exist. See services/ssl_support.py.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # services/
    from ssl_support import run

    run("main:app")