#!/usr/bin/env python3
"""Migrate changelog.json data into SQLite database."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from db import VipzoneDB, DEFAULT_DB


def migrate(json_path: Path, db_path: Path | None = None) -> int:
    """
    Load changelog.json and insert entries into SQLite.
    Returns count of entries migrated. Idempotent (no duplicates).
    """
    if not json_path.exists():
        print(f"❌ {json_path} not found")
        return 0

    try:
        with open(json_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse {json_path}: {e}")
        return 0

    if not isinstance(data, dict) or "items" not in data:
        print(f"❌ Invalid format in {json_path}: expected {{\"items\": [...]}}")
        return 0

    items = data["items"]
    if not isinstance(items, list):
        print(f"❌ Invalid items: expected list, got {type(items).__name__}")
        return 0

    db = VipzoneDB(db_path or DEFAULT_DB)
    migrated = 0

    for i, item in enumerate(items):
        # Skip if already exists (by date+title combo as key)
        existing = db.list_changelog()
        key = (item.get("date"), item.get("title"))
        if any((e["date"], e["title"]) == key for e in existing):
            print(f"⊘ Entry {i+1}: {key[0]} {key[1][:40]}… (skip, already exists)")
            continue

        try:
            entry_data = {
                "title": item.get("title", ""),
                "tag": item.get("tag", "chore"),
                "date": item.get("date", ""),
                "pr": item.get("pr"),
                "commit": item.get("commit"),
                "lines_added": item.get("lines_added", 0),
                "lines_removed": item.get("lines_removed", 0),
                "highlights": item.get("highlights", []),
            }
            cid = db.insert_changelog(entry_data)
            print(f"✓ Entry {i+1}: {key[0]} (id={cid})")
            migrated += 1
        except Exception as e:
            print(f"✗ Entry {i+1}: {key[0]} — {e}")

    return migrated


if __name__ == "__main__":
    # Default: migrate from ../../changelog.json (project root)
    root = Path(__file__).resolve().parents[2]
    json_file = root / "changelog.json"
    db_file = root / "data" / "vipzone.db"

    print(f"Migrating {json_file} → {db_file}")
    count = migrate(json_file, db_file)
    print(f"\n✓ Migrated {count} entries")
    sys.exit(0)
