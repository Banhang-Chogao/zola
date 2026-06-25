#!/usr/bin/env python3
import json
import subprocess
import datetime
from pathlib import Path

OUT = Path("static/data/pr-sentinel.json")

def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()

def main():
    try:
        raw = run([
            "gh", "pr", "list",
            "--state", "open",
            "--limit", "100",
            "--json",
            "number,title,url,author,headRefName,baseRefName,updatedAt,isDraft,statusCheckRollup,labels"
        ])
        prs = json.loads(raw)
        error = None
    except Exception as exc:
        prs = []
        error = str(exc)

    items = []

    for pr in prs:
        checks = pr.get("statusCheckRollup") or []

        counts = {
            "total": len(checks),
            "success": 0,
            "failure": 0,
            "pending": 0,
            "skipped": 0,
        }

        for c in checks:
            conclusion = (c.get("conclusion") or "").lower()
            status = (c.get("status") or "").lower()

            if conclusion in ("success", "neutral"):
                counts["success"] += 1
            elif conclusion in ("failure", "cancelled", "timed_out"):
                counts["failure"] += 1
            elif conclusion == "skipped":
                counts["skipped"] += 1
            elif status in ("queued", "in_progress"):
                counts["pending"] += 1
            else:
                counts["pending"] += 1

        state = "unknown"

        if counts["failure"]:
            state = "failure"
        elif counts["pending"]:
            state = "pending"
        elif counts["total"]:
            state = "success"

        items.append({
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["url"],
            "author": (pr.get("author") or {}).get("login", ""),
            "branch": pr.get("headRefName"),
            "base": pr.get("baseRefName"),
            "updated_at": pr.get("updatedAt"),
            "is_draft": pr.get("isDraft", False),
            "labels": [
                x["name"]
                for x in pr.get("labels", [])
                if x.get("name")
            ],
            "checks": counts,
            "state": state,
        })

    payload = {
        "generated_at": datetime.datetime.now(
            datetime.UTC
        ).isoformat(),
        "error": error,
        "summary": {
            "open": len(items),
            "passing": sum(1 for x in items if x["state"] == "success"),
            "failing": sum(1 for x in items if x["state"] == "failure"),
            "pending": sum(1 for x in items if x["state"] == "pending"),
            "draft": sum(1 for x in items if x["is_draft"]),
        },
        "items": items,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )

    print(f"generated {OUT}")

if __name__ == "__main__":
    main()
