#!/usr/bin/env python3
"""PR Status Checker + Auto-Fix Gate (kt9).

Usage:
  python3 scripts/pr_status_check.py          # check + auto-fix if issues found
  python3 scripts/pr_status_check.py --fix     # force fix mode
  python3 scripts/pr_status_check.py --no-fix  # check only, no auto-fix
  python3 scripts/pr_status_check.py --pr 1309 # check specific PR
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def tz_now():
    return datetime.now(timezone.utc).strftime("%H:%M %d/%m/%Y UTC")


def run(cmd, timeout=60, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


GH_REPO = "Banhang-Chogao/zola"


def get_open_prs():
    out, _ = run(["gh", "pr", "list", "--state", "open", "--json",
                  "number,title,headRefName,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,url"])
    if not out:
        return []
    return json.loads(out)


def get_failed_runs(hours=24):
    out, _ = run(["gh", "run", "list", "--limit", "30", "--json",
                  "status,conclusion,headBranch,displayTitle,workflowName,createdAt"])
    if not out:
        return []
    data = json.loads(out)
    return [r for r in data if r.get("conclusion") in ("failure", "cancelled")]


def get_deploy_runs():
    out, _ = run(["gh", "run", "list", "--workflow", "deploy.yml", "--limit", "20", "--json",
                  "status,conclusion,headBranch,displayTitle,workflowName,url,headSha,createdAt,updatedAt"])
    if not out:
        return []
    return json.loads(out)


def check_gatekeeper(pr):
    for check in pr.get("statusCheckRollup", []):
        if check.get("name") in ("qa-check", "QA Gatekeeper", "rule-check"):
            return check
    return None


def classify_pr_health(pr):
    checks = pr.get("statusCheckRollup", [])
    mergeable = pr.get("mergeable", "UNKNOWN")
    gate = check_gatekeeper(pr)
    has_failed = any(check.get("conclusion") == "FAILURE" for check in checks)
    has_running = any(check.get("status") == "IN_PROGRESS" for check in checks)
    review = pr.get("reviewDecision") or ""

    if mergeable == "CONFLICTING":
        return "🔴 BLOCK", "conflict"
    if has_failed:
        return "🔴 BLOCK", "failing check"
    if has_running or (gate and gate.get("status") == "IN_PROGRESS"):
        return "🟡 RUN", "waiting on CI"
    if review == "REVIEW_REQUIRED":
        return "🟦 REVIEW", "needs review"
    return "🟢 CLEAN", "all clear"


def deploy_bucket(run):
    s, c = run.get("status"), run.get("conclusion")
    if s == "completed":
        if c == "success": return "✅ success"
        if c == "failure": return "❌ failed"
        if c == "cancelled": return "⏹ cancelled"
        return f"⚪ {c or 'completed'}"
    if s == "in_progress": return "🔄 running"
    if s in ("queued", "pending"): return "⏳ pending"
    return f"❔ {s or 'unknown'}"


# ── Auto-fix: rerun failed checks ──────────────────────────

def autofix_rerun_failed(prs):
    """Rerun failed checks for known safe patterns."""
    fixed = []
    for pr in prs:
        for check in pr.get("statusCheckRollup", []):
            if check.get("conclusion") != "FAILURE":
                continue
            name = check["name"]
            branch = pr["headRefName"]
            pr_num = pr["number"]

            # Safe pattern: zola build or qa-check failed → rerun
            if "zola build" in name.lower() or "qa-check" in name.lower():
                out, _ = run(["gh", "run", "rerun", "--failed", "-R", GH_REPO])
                if out or True:
                    fixed.append({
                        "pr": f"#{pr_num}", "branch": branch,
                        "action": f"🔄 Rerun {name} (failed → retry)"
                    })
    return fixed


# ── Auto-fix: V18/V25 conflict resolution ──────────────────

def resolve_v18_v25_conflicts(prs):
    """Resolve merge conflicts using V18/V25 strategies.

    V18 — phân loại file:
      data/*.json (auto-gen)    → git checkout --theirs (lấy main)
      content/posting/*.md      → git checkout --ours (giữ PR)
      templates/*.html          → bỏ qua (manual)
    V25 — >5 content files conflict → mass migration, skip.
    """
    fixed = []
    current_branch, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    for pr in prs:
        if pr.get("mergeable") != "CONFLICTING":
            continue
        branch = pr["headRefName"]
        pr_num = pr["number"]

        tmpdir = tempfile.mkdtemp()
        try:
            # Fetch + worktree
            run(["git", "fetch", "origin", branch], timeout=30)
            out, rc = run(["git", "worktree", "add", "--force", tmpdir, branch], timeout=15)
            if rc != 0:
                fixed.append({"pr": f"#{pr_num}", "branch": branch,
                              "action": f"⚠️ Cannot checkout worktree: {out[:60]}"})
                run(["git", "worktree", "remove", tmpdir, "--force"], timeout=10)
                continue

            # Attempt merge with main
            run(["git", "merge", "origin/main", "--no-edit"], cwd=tmpdir, timeout=30)

            # List unmerged files
            uf_out, _ = run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=tmpdir)
            conflicted = [f for f in uf_out.split("\n") if f.strip()] if uf_out else []

            if not conflicted:
                # Merge succeeded with no conflicts — push and report
                run(["git", "push", "origin", f"HEAD:{branch}"], cwd=tmpdir, timeout=30)
                fixed.append({"pr": f"#{pr_num}", "branch": branch,
                              "action": "✅ Merge with main clean — pushed"})
                run(["git", "worktree", "remove", tmpdir, "--force"], timeout=10)
                continue

            # V25: >5 content files → mass migration, skip
            content_conflicts = [f for f in conflicted if f.startswith("content/")]
            if len(content_conflicts) > 5:
                fixed.append({"pr": f"#{pr_num}", "branch": branch,
                              "action": "⛔ Mass content conflict (V25) — needs manual recreate"})
                run(["git", "worktree", "remove", tmpdir, "--force"], timeout=10)
                continue

            # V18: classify and resolve
            data_files = [f for f in conflicted if f.startswith("data/") and f.endswith(".json")]
            content_files = [f for f in conflicted if f.startswith("content/posting/") and f.endswith(".md")]
            template_files = [f for f in conflicted if f.startswith("templates/")]

            for f in data_files:
                run(["git", "checkout", "--theirs", f], cwd=tmpdir, timeout=15)
                run(["git", "add", f], cwd=tmpdir, timeout=10)
                fixed.append({"pr": f"#{pr_num}", "branch": branch,
                              "action": f"V18: {f} ← took main (auto-gen data)"})

            for f in content_files:
                run(["git", "checkout", "--ours", f], cwd=tmpdir, timeout=15)
                run(["git", "add", f], cwd=tmpdir, timeout=10)
                fixed.append({"pr": f"#{pr_num}", "branch": branch,
                              "action": f"V18: {f} → kept PR side"})

            for f in template_files:
                fixed.append({"pr": f"#{pr_num}", "branch": branch,
                              "action": f"⚠️ {f} needs manual resolution — skipped"})

            # Remaining unhandled files (other categories)
            handled = set(data_files + content_files + template_files)
            remaining = [f for f in conflicted if f not in handled]
            for f in remaining:
                fixed.append({"pr": f"#{pr_num}", "branch": branch,
                              "action": f"⚠️ {f} unhandled type — needs manual review"})

            # Commit + push if we resolved anything
            resolved = [f for f in fixed if f["pr"] == f"#{pr_num}" and f["action"].startswith("V18:")]
            if resolved:
                run(["git", "commit", "-m", "kt9: auto-resolve conflicts (V18 strategy)\n\nAuto-fix by kt9 PR status checker. Data files → main, content files → PR side."],
                    cwd=tmpdir, timeout=15)
                push_out, push_rc = run(["git", "push", "origin", f"HEAD:{branch}"], cwd=tmpdir, timeout=60)
                if push_rc != 0:
                    fixed.append({"pr": f"#{pr_num}", "branch": branch,
                                  "action": f"⚠️ Push failed: {push_out[:80]}"})
                else:
                    fixed.append({"pr": f"#{pr_num}", "branch": branch,
                                  "action": "✅ Pushed auto-resolve to branch"})

            # Cleanup worktree
            run(["git", "worktree", "remove", "--force", tmpdir], timeout=10)

        except Exception as e:
            run(["git", "worktree", "remove", "--force", tmpdir], timeout=10)
            fixed.append({"pr": f"#{pr_num}", "branch": branch,
                          "action": f"⚠️ Error: {str(e)[:80]}"})

    # Restore original branch
    if current_branch:
        run(["git", "checkout", current_branch], timeout=15)
    return fixed


# ── Reporting ──────────────────────────────────────────────

def format_report(prs, failed_runs, deploy_runs, auto_fixed, issues):
    lines = []
    lines.append(f"🧭 **KT9 PR Health Dashboard** — {tz_now()}")
    lines.append("")

    deploy_counts = {}
    for run in deploy_runs:
        b = deploy_bucket(run)
        deploy_counts[b] = deploy_counts.get(b, 0) + 1

    clean = review = running = blocked = 0
    for pr in prs:
        h, _ = classify_pr_health(pr)
        if h == "🟢 CLEAN": clean += 1
        elif h == "🟦 REVIEW": review += 1
        elif h == "🟡 RUN": running += 1
        else: blocked += 1

    lines.append("### Snapshot")
    lines.append("| 🟢 Clean | 🟦 Review | 🟡 Running | 🔴 Blocked | 🚨 Deploy incidents |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| {clean} | {review} | {running} | {blocked} | {len(failed_runs)} |")
    lines.append("")

    lines.append("### PR Matrix")
    lines.append("| PR | Branch | Health | Mergeable | QA Check | Conflict | Gatekeeper |")
    lines.append("|---|---|---|---|---|---|---|")

    for pr in sorted(prs, key=lambda x: x["number"]):
        num = f"#{pr['number']}"
        branch = pr["headRefName"]
        mergeable = pr.get("mergeable", "UNKNOWN")
        health, reason = classify_pr_health(pr)

        m_status = "✅ MERGEABLE" if mergeable == "MERGEABLE" else ("❌ CONFLICT" if mergeable == "CONFLICTING" else "❓ UNKNOWN")

        gate = check_gatekeeper(pr)
        if gate:
            c = gate.get("conclusion")
            if c == "SUCCESS": qa_status = "✅ SUCCESS"
            elif c == "FAILURE": qa_status = "❌ FAILED"
            elif c == "CANCELLED": qa_status = "⊘ CANCELLED"
            elif gate.get("status") == "IN_PROGRESS": qa_status = "🔄 running"
            else: qa_status = f"⏳ {gate.get('status', '?')}"
        else:
            qa_status = "—"

        conflict = "✅ không" if mergeable != "CONFLICTING" else "❌ có"
        rule = next((c for c in pr.get("statusCheckRollup", []) if c.get("name") == "rule-check"), None)
        gk = "✅ pass" if rule and rule.get("conclusion") == "SUCCESS" else (f"❌ {rule.get('conclusion')}" if rule and rule.get("conclusion") else ("🔄 running" if rule else "—"))

        health_cell = health if reason == "all clear" else f"{health} · {reason}"
        lines.append(f"| {num} | {branch} | {health_cell} | {m_status} | {qa_status} | {conflict} | {gk} |")

    sq = sum(1 for p in prs if (g := check_gatekeeper(p)) and g.get("conclusion") == "SUCCESS")
    fq = sum(1 for p in prs if (g := check_gatekeeper(p)) and g.get("conclusion") == "FAILURE")
    rq = sum(1 for p in prs if (g := check_gatekeeper(p)) and g.get("status") == "IN_PROGRESS")
    cf = sum(1 for p in prs if p.get("mergeable") == "CONFLICTING")

    lines.append("")
    lines.append("### QA / Deploy Pulse")
    lines.append("| QA pass | QA running | QA failed | Conflict | Deploy success | Deploy running | Deploy failed | Deploy cancelled |")
    lines.append("|---|---|---|---|---|---|---|---|")
    lines.append(f"| {sq} | {rq} | {fq} | {cf} | {deploy_counts.get('✅ success', 0)} | {deploy_counts.get('🔄 running', 0)} | {deploy_counts.get('❌ failed', 0)} | {deploy_counts.get('⏹ cancelled', 0)} |")

    if deploy_runs:
        latest = deploy_runs[0]
        lines.append("")
        lines.append("### 🚀 Latest deploy")
        lines.append(f"- {deploy_bucket(latest)} · {latest.get('workflowName', 'deploy.yml')} · {latest.get('headBranch', '?')} · {latest.get('displayTitle', '?')}")

    if failed_runs:
        lines.append("")
        lines.append("### 🚨 Failed / cancelled runs (24h)")
        lines.append("| Workflow | Branch | Status | Title |")
        lines.append("|---|---|---|---|")
        for r in failed_runs[:5]:
            s = "❌ failure" if r.get("conclusion") == "failure" else "⏹ cancelled"
            lines.append(f"| {r.get('workflowName', '?')} | {r.get('headBranch', '?')} | {s} | {r.get('displayTitle', '?')[:50]} |")
    else:
        lines.append("\n✅ Không có failed/cancelled run gần đây.")

    if auto_fixed:
        lines.append("")
        lines.append("### 🔧 Auto-fix đã áp dụng")
        for f in auto_fixed:
            lines.append(f"- {f['pr']} ({f['branch']}): {f['action']}")

    if issues:
        lines.append("")
        lines.append(f"### ⚠️ Remaining issues ({len(issues)} chưa fix)")
        for i in issues:
            lines.append(f"- {i['pr']} ({i['branch']}): {i['detail']}")

    return "\n".join(lines)


def check_autofix_needed(pr):
    issues = []
    for check in pr.get("statusCheckRollup", []):
        if check.get("conclusion") == "FAILURE":
            issues.append({
                "pr": f"#{pr['number']}", "branch": pr["headRefName"],
                "check": check["name"],
                "detail": f"❌ {check['name']} FAILED"
            })
    if pr.get("mergeable") == "CONFLICTING":
        issues.append({
            "pr": f"#{pr['number']}", "branch": pr["headRefName"],
            "check": "conflict",
            "detail": "❌ Merge conflict"
        })
    return issues


def main():
    no_fix = "--no-fix" in sys.argv
    force_fix = "--fix" in sys.argv
    pr_filter = None
    for a in sys.argv:
        if a.startswith("--pr="):
            pr_filter = int(a.split("=")[1])

    prs = get_open_prs()
    if pr_filter:
        prs = [p for p in prs if p["number"] == pr_filter]

    failed_runs = get_failed_runs()
    deploy_runs = get_deploy_runs()

    issues = []
    for pr in prs:
        issues.extend(check_autofix_needed(pr))

    auto_fixed = []
    should_fix = force_fix or (issues and not no_fix)

    if should_fix and issues:
        print("🔧 Phát hiện issue — đang auto-fix...\n", file=sys.stderr)

        auto_fixed = autofix_rerun_failed(prs)

        conflict_fixes = resolve_v18_v25_conflicts(prs)
        auto_fixed.extend(conflict_fixes)

        # Re-check after fix
        prs = get_open_prs()
        if pr_filter:
            prs = [p for p in prs if p["number"] == pr_filter]
        issues = []
        for pr in prs:
            issues.extend(check_autofix_needed(pr))

    elif issues and not should_fix:
        print("\n⚠️  Phát hiện issue — chạy `kt9` (không --no-fix) để auto-fix.\n", file=sys.stderr)

    report = format_report(prs, failed_runs, deploy_runs, auto_fixed, issues)
    print(report)

    if issues:
        sys.exit(2 if not no_fix else 1)
    sys.exit(0)


if __name__ == "__main__":
    main()
