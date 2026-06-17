"""
Build semantic related posts index using sentence-transformers.

Quét content/posting + content/baochi → topic-aware embeddings →
cosine similarity → data/related.json + data/scores.json.

Run locally:
    pip install -r scripts/requirements.txt
    python scripts/build_related.py

Run in CI:
    Triggered by .github/workflows/build-related.yml
    Daily QA: .github/workflows/related-qa.yml (22:00 VN)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from related_engine import rebuild_related  # noqa: E402


def main() -> None:
    rebuild_related(write=True, use_embeddings=True)


if __name__ == "__main__":
    main()