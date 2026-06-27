#!/usr/bin/env python3
"""
Add a rollback milestone entry to data/theme-log.json.

Usage:
  python3 scripts/add_milestone.py --type feature --title "My Feature" \
    --commit abc1234 --pr 1234 --routes "/route-a/,/route-b/" \
    --scope "scope description" --restore-mode cherry-pick-files \
    --status merged --risk low [--notes "..."] [--summary "..."]

  python3 scripts/add_milestone.py --help
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "theme-log.json"
TZ_VN = timezone(timedelta(hours=7))

VALID_TYPES = {"theme", "feature", "tool", "content", "data", "hotfix", "deploy"}
VALID_STATUS = {"live", "merged", "pending", "rollback-target", "reference", "archived", "failed"}
VALID_RISK = {"low", "medium", "high"}
VALID_RESTORE = {
    "rollback-full", "cherry-pick-files", "restore-toolkit",
    "rebuild-data", "manual-recreate", "reference-only",
}


def stable_id(type_: str, title: str, commit: str, date_str: str) -> str:
    date_slug = date_str[:10].replace("-", "") if date_str else datetime.now(TZ_VN).strftime("%Y%m%d")
    raw = f"{type_}-{title}-{commit}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:6]
    title_slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:30].strip("-")
    return f"milestone-{date_slug}-{title_slug}-{h}"


def load_data():
    if not DATA_FILE.exists():
        print(f"[ERROR] {DATA_FILE} not found. Run scripts/theme_audit.py first.", file=sys.stderr)
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Add a rollback milestone to data/theme-log.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/add_milestone.py \\
    --type feature --title "AdSense Audit V2" \\
    --commit 0ef1910 --pr 1122 \\
    --routes "/ad-report-v2/,/ad-report/" \\
    --scope "adsense audit, content health" \\
    --restore-mode cherry-pick-files \\
    --status merged --risk low

  python3 scripts/add_milestone.py \\
    --type hotfix --title "Fix deploy rate limit" \\
    --commit a1b2c3d --status merged --risk low
        """,
    )
    parser.add_argument("--type", required=True, choices=sorted(VALID_TYPES), help="Milestone type")
    parser.add_argument("--title", required=True, help="Short descriptive title")
    parser.add_argument("--summary", default="", help="One-line summary (Vietnamese OK)")
    parser.add_argument("--commit", default="", help="Short commit hash (7 chars)")
    parser.add_argument("--pr", default="", help="PR number e.g. 1122 or #1122")
    parser.add_argument("--branch", default="", help="Feature branch name")
    parser.add_argument("--routes", default="", help="Comma-separated routes e.g. /route-a/,/route-b/")
    parser.add_argument("--files", default="", help="Comma-separated key files")
    parser.add_argument("--scope", default="", help="Comma-separated scope keywords")
    parser.add_argument("--restore-mode", default="cherry-pick-files",
                        choices=sorted(VALID_RESTORE), help="How to restore this milestone")
    parser.add_argument("--restore-hint", default="", help="Human instructions for restore")
    parser.add_argument("--status", default="merged", choices=sorted(VALID_STATUS))
    parser.add_argument("--risk", default="low", choices=sorted(VALID_RISK))
    parser.add_argument("--notes", default="", help="Additional notes")
    parser.add_argument("--date", default="", help="ISO8601 date (default: now in GMT+7)")
    parser.add_argument("--dry-run", action="store_true", help="Print entry only, do not write")
    args = parser.parse_args()

    # Normalise PR
    pr = args.pr.strip()
    if pr and not pr.startswith("#"):
        pr = f"#{pr}"

    # Date
    date_str = args.date.strip()
    if not date_str:
        date_str = datetime.now(TZ_VN).isoformat(timespec="seconds")

    routes = [r.strip() for r in args.routes.split(",") if r.strip()] if args.routes else []
    files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else []

    entry_id = stable_id(args.type, args.title, args.commit, date_str)

    entry = {
        "id": entry_id,
        "type": args.type,
        "title": args.title,
        "summary": args.summary,
        "commit": args.commit.strip(),
        "merge_commit": "",
        "pr": pr,
        "branch": args.branch.strip(),
        "date": date_str,
        "status": args.status,
        "scope": args.scope,
        "routes": routes,
        "files": files,
        "restore_mode": args.restore_mode,
        "restore_hint": args.restore_hint,
        "qa": {"zola_build": "unknown", "qa_check": "unknown", "qa_404": "unknown"},
        "risk": args.risk,
        "notes": args.notes,
    }

    print(json.dumps(entry, ensure_ascii=False, indent=2))

    if args.dry_run:
        print("\n[DRY RUN] Not written.", file=sys.stderr)
        return

    data = load_data()
    if "milestones" not in data:
        data["milestones"] = []

    # Dedup by id
    existing_ids = {m.get("id") for m in data["milestones"]}
    if entry_id in existing_ids:
        print(f"\n[SKIP] Duplicate id: {entry_id}", file=sys.stderr)
        sys.exit(0)

    # Also check same commit+title
    for m in data["milestones"]:
        if m.get("commit") == args.commit and m.get("title") == args.title and args.commit:
            print(f"\n[SKIP] Already exists: commit={args.commit!r} title={args.title!r}", file=sys.stderr)
            sys.exit(0)

    # Insert newest first
    data["milestones"].insert(0, entry)

    save_data(data)
    print(f"\n[OK] Added milestone {entry_id!r} to {DATA_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
