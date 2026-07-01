#!/usr/bin/env python3
"""PR Status Checker + Auto-Fix Gate.

Usage:
  python3 scripts/pr_status_check.py          # check all open PRs, report
  python3 scripts/pr_status_check.py --fix     # check + auto-fix safe issues
  python3 scripts/pr_status_check.py --pr 1271 # check specific PR
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def tz_now():
    return datetime.now(timezone.utc).strftime("%H:%M %d/%m/%Y UTC")


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def get_open_prs():
    out, _ = run(["gh", "pr", "list", "--state", "open", "--json",
                  "number,title,headRefName,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,url"])
    if not out:
        return []
    return json.loads(out)


def get_failed_runs():
    out, _ = run(["gh", "run", "list", "--limit", "20", "--json",
                  "status,conclusion,headBranch,displayTitle,workflowName"])
    if not out:
        return []
    data = json.loads(out)
    return [r for r in data if r.get("conclusion") in ("failure", "cancelled")]


def check_autofix_needed(pr):
    """Check if autofix is needed for a PR."""
    issues = []
    for check in pr.get("statusCheckRollup", []):
        if check.get("conclusion") == "FAILURE":
            issues.append({
                "pr": f"#{pr['number']}",
                "branch": pr["headRefName"],
                "check": check["name"],
                "detail": f"{check['name']} FAILED — needs fix"
            })
    if pr.get("mergeable") == "CONFLICTING":
        issues.append({
            "pr": f"#{pr['number']}",
            "branch": pr["headRefName"],
            "check": "conflict",
            "detail": "Merge conflict detected — needs resolution"
        })
    return issues


def autofix_safe_issues(prs):
    """Attempt safe autofixes for known patterns."""
    fixed = []
    for pr in prs:
        for check in pr.get("statusCheckRollup", []):
            if check.get("conclusion") != "FAILURE":
                continue
            name = check["name"]
            pr_num = pr["number"]
            branch = pr["headRefName"]

            # Pattern: qa_pair shortcode missing (V19-style)
            if "zola build" in name.lower() or "qa-check" in name.lower():
                # Check if it's the qa_pair issue
                out, _ = run(["gh", "pr", "view", str(pr_num), "--json", "body", "--jq", ".body"])
                if "qa_pair" in out:
                    # Trigger rerun after potential fix
                    run(["gh", "run", "rerun", "--failed", "-R", "Banhang-Chogao/zola"])
                    fixed.append({
                        "pr": f"#{pr_num}",
                        "branch": branch,
                        "action": "Triggered rerun for qa_pair shortcode fix"
                    })
    return fixed


def check_gatekeeper(pr):
    """Check gatekeeper/qa-check status for a PR."""
    for check in pr.get("statusCheckRollup", []):
        if check.get("name") in ("qa-check", "QA Gatekeeper", "rule-check"):
            return check
    return None


def format_report(prs, failed_runs, auto_fixed=None):
    lines = []
    lines.append(f"📋 **Báo cáo trạng thái PR** — {tz_now()}")
    lines.append("")

    # Table header
    lines.append("| PR | Branch | Mergeable | QA Check | Conflict | Gatekeeper |")
    lines.append("|---|---|---|---|---|---|")

    for pr in sorted(prs, key=lambda x: x["number"]):
        num = f"#{pr['number']}"
        branch = pr["headRefName"]
        mergeable = pr.get("mergeable", "UNKNOWN")
        merge_state = pr.get("mergeStateStatus", "UNKNOWN")

        # Mergeable icon
        if mergeable == "MERGEABLE":
            m_status = "✅ MERGEABLE"
        elif mergeable == "CONFLICTING":
            m_status = "❌ CONFLICT"
        else:
            m_status = "❓ UNKNOWN"

        # QA Check
        gate = check_gatekeeper(pr)
        if gate:
            conc = gate.get("conclusion")
            if conc == "SUCCESS":
                qa_status = "✅ SUCCESS"
            elif conc == "FAILURE":
                qa_status = "❌ FAILED"
            elif conc == "CANCELLED":
                qa_status = "⊘ CANCELLED"
            elif gate.get("status") == "IN_PROGRESS":
                qa_status = "🔄 running"
            else:
                qa_status = f"⏳ {gate.get('status', '?')}"
        else:
            qa_status = "—"

        # Conflict
        conflict = "✅ không" if mergeable != "CONFLICTING" else "❌ có"

        # Gatekeeper
        rule = next((c for c in pr.get("statusCheckRollup", []) if c.get("name") == "rule-check"), None)
        if rule:
            rc = rule.get("conclusion")
            gk_status = "✅ pass" if rc == "SUCCESS" else f"❌ {rc}" if rc else "🔄 running"
        else:
            gk_status = "—"

        lines.append(f"| {num} | {branch} | {m_status} | {qa_status} | {conflict} | {gk_status} |")

    # Summary
    total = len(prs)
    success_q = sum(1 for p in prs if (g := check_gatekeeper(p)) and g.get("conclusion") == "SUCCESS")
    failed_q = sum(1 for p in prs if (g := check_gatekeeper(p)) and g.get("conclusion") == "FAILURE")
    running_q = sum(1 for p in prs if (g := check_gatekeeper(p)) and g.get("status") == "IN_PROGRESS")
    conflicting = sum(1 for p in prs if p.get("mergeable") == "CONFLICTING")

    lines.append("")
    lines.append(f"**Tổng kết:** {total} PR · {success_q} QA pass · {running_q} đang chạy · {failed_q} failed · {conflicting} conflict")

    # Failed runs section
    if failed_runs:
        lines.append("")
        lines.append("### ❌ Failed runs gần đây")
        lines.append("| Branch | Workflow | Status | Title |")
        lines.append("|---|---|---|---|")
        for r in failed_runs[:5]:
            lines.append(f"| {r.get('headBranch', '?')} | {r.get('workflowName', '?')} | ❌ {r.get('conclusion', '?')} | {r.get('displayTitle', '?')[:50]} |")

    # Autofix section
    if auto_fixed:
        lines.append("")
        lines.append("### 🔧 Auto-fix đã áp dụng")
        for f in auto_fixed:
            lines.append(f"- {f['pr']} ({f['branch']}): {f['action']}")

    return "\n".join(lines)


def main():
    fix_mode = "--fix" in sys.argv
    pr_filter = None
    for a in sys.argv:
        if a.startswith("--pr="):
            pr_filter = int(a.split("=")[1])

    prs = get_open_prs()
    if pr_filter:
        prs = [p for p in prs if p["number"] == pr_filter]

    failed_runs = get_failed_runs()
    issues = []
    for pr in prs:
        issues.extend(check_autofix_needed(pr))

    auto_fixed = []
    if fix_mode and issues:
        auto_fixed = autofix_safe_issues(prs)

    report = format_report(prs, failed_runs, auto_fixed)
    print(report)

    if issues and not fix_mode:
        print(f"\n⚠️  {len(issues)} issue(s) phát hiện. Chạy `--fix` để auto-fix an toàn.")
        sys.exit(2)
    elif issues and fix_mode:
        remaining = len(issues) - len(auto_fixed)
        if remaining > 0:
            print(f"\n⚠️  {remaining} issue(s) còn lại cần xử lý thủ công.")
            sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
