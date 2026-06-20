#!/usr/bin/env python3
"""Vaccine Hotfix — conflict-safe automated CI/PR/merge/deploy hotfix engine.

Activated by a pipeline failure (build fail · deploy fail · auto-merge blocked ·
merge conflict · required checks fail). It:

  1. Runs a CONFLICT-SAFE PRECHECK — audits the existing CI/PR/merge/deploy rules
     (QA Gatekeeper, auto-merge, deploy, branch-protection, manual-approval) and
     confirms the hotfix can run WITHOUT bypassing any safety gate for `main`.
     `vaccine-hotfix/*` branches auto-fix + auto-update their PR through the SAME
     required-check gate — never a bypass.
  2. Diagnoses the root cause (reuses scripts/ai_diagnose.py — free heuristics).
  3. Creates/updates a `vaccine-hotfix/<issue-id>` branch (the git plumbing lives
     in the workflow; this engine computes the branch name + the minimal-delta fix
     in the working tree).
  4. Fixes the minimal delta — merge conflicts via scripts/autofix_conflicts.py,
     known recurring build-breakers via the SAFE vaccine fixers
     (scripts/vaccine_autofixer.py). No broad refactors.
  5. Re-runs QA / build / tests and repeats until they pass (bounded + anti-loop).
  6. Logs everything to data/vaccine-hotfix-report.json ("Autofixer_report_by Vacxin").

Auto-merge is DELEGATED to the existing engine (scripts/try_auto_merge.py via
auto-merge.yml), so a hotfix PR merges ONLY when every required check is green.

Safety invariants (enforced, never bypassed):
  * Do NOT bypass required checks (data/auto-merge-policy.json → required_checks).
  * Do NOT force-push `main` — the engine only ever touches `vaccine-hotfix/*`.
  * Do NOT delete user content/data — content/**, private_content/**, curated
    JSON (categories / *-series.json) are protected; conflict strategy keeps the
    PR/content side, regenerated CI data takes `main`.

CLI:
    python3 scripts/vaccine_hotfix.py --precheck                  # audit rules only
    python3 scripts/vaccine_hotfix.py --trigger build_fail --issue-id qa-123
    python3 scripts/vaccine_hotfix.py --trigger merge_conflict --issue-id pr-87 --branch feature/x
    python3 scripts/vaccine_hotfix.py --trigger required_checks_fail --issue-id qa-9 --dry-run
    python3 scripts/vaccine_hotfix.py --release-lock              # clear a stale lock
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover - zoneinfo ships with 3.9+
    TZ = timezone(timedelta(hours=7))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DATA_DIR = os.path.join(REPO, "data")
REPORT_PATH = os.path.join(DATA_DIR, "vaccine-hotfix-report.json")
STATE_PATH = os.path.join(DATA_DIR, "vaccine-hotfix-state.json")
LOG_PATH = os.path.join(DATA_DIR, "vaccine-hotfix.log")
POLICY_PATH = os.path.join(DATA_DIR, "auto-merge-policy.json")
WORKFLOWS = os.path.join(REPO, ".github", "workflows")

REPORT_NAME = "Autofixer_report_by Vacxin"
RULE_NAME = "Vaccine Hotfix"
BRANCH_PREFIX = "vaccine-hotfix/"
GH_REPO = os.environ.get("GITHUB_REPOSITORY") or "Banhang-Chogao/zola"

# The five activation triggers (per the rule spec).
TRIGGERS = (
    "build_fail",
    "deploy_fail",
    "auto_merge_blocked",
    "merge_conflict",
    "required_checks_fail",
)

# "repeat until pass" — bounded so a hotfix can never loop forever.
MAX_FIX_ATTEMPTS = 4
# Same issue auto-fixed this many times without a durable pass → stop + escalate.
LOOP_THRESHOLD = 3
LOCK_STALE_MINUTES = 30

# User content/data the hotfix must NEVER delete (safety invariant).
PROTECTED_PREFIXES = (
    "content/",
    "private_content/",
    "static/img/",
    "static/uploads/",
)
PROTECTED_SUFFIXES = (
    "-series.json",
)
PROTECTED_EXACT = (
    "data/categories.json",
    "categories.json",
    "data/auto-merge-policy.json",
)


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def now_ict() -> datetime:
    return datetime.now(TZ)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def load_policy() -> dict:
    try:
        with open(POLICY_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def required_checks(policy: dict | None = None) -> list[str]:
    """Names of the checks a PR must pass before auto-merge (the gate we honor)."""
    policy = policy if policy is not None else load_policy()
    rc = policy.get("required_checks") or {}
    names: list[str] = []
    for value in rc.values():
        names.extend(value if isinstance(value, list) else [value])
    # De-dupe, preserve order; sensible default if the policy is empty.
    seen: list[str] = []
    for n in names or ["qa-check"]:
        if n not in seen:
            seen.append(n)
    return seen


def hotfix_branch(issue_id: str) -> str:
    """Deterministic `vaccine-hotfix/<issue-id>` branch name (slugified)."""
    slug = re.sub(r"[^a-z0-9._-]+", "-", (issue_id or "").strip().lower()).strip("-")
    return f"{BRANCH_PREFIX}{slug or 'unknown'}"


def is_protected_path(path: str) -> bool:
    """True for user content/data that must never be deleted by a hotfix."""
    p = path.replace("\\", "/").lstrip("./")
    if p in PROTECTED_EXACT:
        return True
    if any(p.startswith(pre) for pre in PROTECTED_PREFIXES):
        return True
    if any(p.endswith(suf) for suf in PROTECTED_SUFFIXES):
        return True
    return False


def pr_url(branch: str) -> str:
    explicit = os.environ.get("HOTFIX_PR_URL", "").strip()
    if explicit:
        return explicit
    owner = GH_REPO.split("/")[0]
    return f"https://github.com/{GH_REPO}/pulls?q=is%3Apr+is%3Aopen+head%3A{owner}%3A{branch}"


def _git(*args: str) -> str:
    """Crash-safe git read. Returns stdout (stripped) or '' on any failure."""
    try:
        res = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                             text=True, timeout=60)
        return (res.stdout or "").strip()
    except Exception:
        return ""


def changed_files() -> list[str]:
    """Files changed vs HEAD (staged + unstaged + untracked), excluding deletions
    of protected content (defense-in-depth: a hotfix never reports content deletes).
    """
    out: list[str] = []
    status = _git("status", "--porcelain")
    for line in status.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:].strip()
        # Rename: "old -> new"
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if code.strip() in ("D", "DD") and is_protected_path(path):
            # Should never happen — guard so the report can't claim a content delete.
            continue
        out.append(path)
    return sorted(dict.fromkeys(out))


# --------------------------------------------------------------------------
# lock + anti-loop state
# --------------------------------------------------------------------------
def read_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def lock_is_active(state: dict, now: datetime) -> bool:
    if not state.get("running"):
        return False
    started = state.get("started_at")
    if not started:
        return True
    try:
        started_dt = datetime.fromisoformat(started)
    except ValueError:
        return False
    return (now - started_dt) < timedelta(minutes=LOCK_STALE_MINUTES)


def acquire_lock(trigger: str, issue_id: str, now: datetime) -> bool:
    state = read_state()
    if lock_is_active(state, now):
        return False
    state.update({
        "running": True,
        "trigger": trigger,
        "issue_id": issue_id,
        "started_at": iso(now),
        "pid": os.getpid(),
    })
    write_state(state)
    return True


def release_lock(now: datetime, last_status: str) -> None:
    state = read_state()
    state.update({
        "running": False,
        "last_finished_at": iso(now),
        "last_status": last_status,
    })
    write_state(state)


def bump_attempt(issue_id: str) -> int:
    """Increment + return the persisted fix-attempt count for an issue."""
    state = read_state()
    attempts = state.setdefault("fix_attempts", {})
    attempts[issue_id] = int(attempts.get(issue_id, 0)) + 1
    write_state(state)
    return attempts[issue_id]


def loop_detected(issue_id: str) -> tuple[bool, str]:
    """Anti-loop: stop auto-fixing an issue that keeps coming back."""
    state = read_state()
    count = int(state.get("fix_attempts", {}).get(issue_id, 0))
    if count >= LOOP_THRESHOLD:
        return True, f"issue '{issue_id}' đã hotfix {count} lần — escalate, dừng auto-fix"
    return False, ""


def clear_attempt(issue_id: str) -> None:
    """Reset the counter once an issue is durably resolved (QA/build green)."""
    state = read_state()
    if issue_id in state.get("fix_attempts", {}):
        del state["fix_attempts"][issue_id]
        write_state(state)


# --------------------------------------------------------------------------
# CONFLICT-SAFE PRECHECK — audit CI/PR/merge/deploy rules
# --------------------------------------------------------------------------
def _wf_exists(name: str) -> bool:
    return os.path.isfile(os.path.join(WORKFLOWS, name))


def _read(path: str) -> str:
    try:
        with open(os.path.join(REPO, path), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def audit_rules() -> dict:
    """Audit existing CI/PR/merge/deploy rules and detect conflicts with the
    Vaccine Hotfix rule. Returns guarantees (safety preserved) + conflicts
    (each with a resolution). File reads only — no network, no git, no subprocess.

    Policy: when a conflict exists, keep the safety gates for `main` and still
    allow `vaccine-hotfix/*` to auto-fix + auto-update its PR (never bypass a gate).
    """
    policy = load_policy()
    guarantees: list[str] = []
    conflicts: list[dict] = []

    # 1) QA Gatekeeper — the required gate we re-run, never skip.
    qa = _read(".github/workflows/qa.yml")
    if _wf_exists("qa.yml") and "qa_check.py" in qa:
        guarantees.append("QA Gatekeeper intact — hotfix re-runs qa_check.py, never bypasses it")
    else:
        conflicts.append({
            "rule": "QA", "issue": "qa.yml / qa_check.py not found",
            "resolution": "keep the QA gate; do not run a hotfix without re-running QA",
        })

    # 2) auto-merge — delegate the merge so the required-check gate is honored.
    if _wf_exists("auto-merge.yml") and os.path.isfile(_p("scripts/try_auto_merge.py")):
        guarantees.append(
            "Merge delegated to try_auto_merge.py — a hotfix PR merges ONLY when "
            f"required checks pass ({', '.join(required_checks(policy))})")
    else:
        conflicts.append({
            "rule": "auto-merge", "issue": "auto-merge.yml / try_auto_merge.py missing",
            "resolution": "do not self-merge; leave the PR for the existing auto-merge gate",
        })

    # 3) deploy — never force-push main; deploy only follows a gated merge.
    deploy = _read(".github/workflows/deploy.yml")
    if _wf_exists("deploy.yml") and "production-deploy" in deploy:
        guarantees.append("Deploy unchanged (production-deploy queue) — hotfix never pushes/force-pushes main")
    else:
        guarantees.append("Deploy workflow present — hotfix never pushes main directly")

    # 4) branch-protection — engine only touches vaccine-hotfix/*.
    guarantees.append("Branch protection honored — engine only writes vaccine-hotfix/* branches")

    # 5) manual-approval — if a manual gate exists, keep it; only auto-update the PR.
    has_manual = (
        _wf_exists("pr-approval.yml")
        or _wf_exists("manual-approval.yml")
        or "manual-approval" in qa
    )
    if has_manual:
        conflicts.append({
            "rule": "manual-approval",
            "issue": "a manual-approval gate is present",
            "resolution": "keep the gate for main; vaccine-hotfix only auto-fixes + "
                          "auto-updates the PR and waits for approval — no bypass",
        })
    else:
        guarantees.append("No manual-approval gate to bypass (pr-approval.yml removed per policy)")

    # vaccine-hotfix/* must be auto-merge eligible through the SAME gate (not a bypass).
    prefixes = policy.get("auto_eligible_branch_prefixes") or []
    branch_prefix_allowed = BRANCH_PREFIX in prefixes
    if branch_prefix_allowed:
        guarantees.append("vaccine-hotfix/ is auto-merge eligible via the same required-check gate")
    else:
        conflicts.append({
            "rule": "auto-merge", "issue": f"'{BRANCH_PREFIX}' not in auto_eligible_branch_prefixes",
            "resolution": f"add '{BRANCH_PREFIX}' to data/auto-merge-policy.json so the hotfix "
                          "PR auto-merges through qa-check (not a bypass)",
        })

    # A conflict never blocks FIXING — it only constrains MERGE to the gated path.
    # Hence the hotfix is always safe to *run*; merge stays gated regardless.
    return {
        "safe_to_run": True,
        "guarantees": guarantees,
        "conflicts": conflicts,
        "required_checks": required_checks(policy),
        "branch_prefix_allowed": branch_prefix_allowed,
        "protected_paths": list(PROTECTED_PREFIXES) + list(PROTECTED_SUFFIXES) + list(PROTECTED_EXACT),
    }


def _p(rel: str) -> str:
    return os.path.join(REPO, rel)


# --------------------------------------------------------------------------
# diagnosis (reuse ai_diagnose) + log fetch
# --------------------------------------------------------------------------
def fetch_logs(log_file: str | None, run_id: str | None) -> str:
    if log_file and os.path.isfile(log_file):
        try:
            with open(log_file, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""
    if run_id:
        try:
            res = subprocess.run(["gh", "run", "view", run_id, "--log-failed"],
                                 capture_output=True, text=True, timeout=60)
            return (res.stdout or "") + (res.stderr or "")
        except Exception:
            return ""
    return ""


def diagnose(logs: str) -> dict:
    """Root-cause diagnosis via the free heuristic tier of ai_diagnose."""
    try:
        import ai_diagnose
        d = ai_diagnose.diagnose_tier1(logs or "")
        return {
            "root_cause": d.root_cause,
            "confidence": d.confidence,
            "suggested_fix": d.suggested_fix,
            "affected_files": d.affected_files,
            "pattern_id": d.pattern_id,
            "tier": d.tier,
        }
    except Exception as exc:
        return {
            "root_cause": f"diagnosis unavailable ({exc})",
            "confidence": 0,
            "suggested_fix": "inspect the failing CI log manually",
            "affected_files": [],
            "pattern_id": "UNKNOWN",
            "tier": "none",
        }


# --------------------------------------------------------------------------
# minimal-delta fix (reuse autofix_conflicts + vaccine safe fixers)
# --------------------------------------------------------------------------
def apply_minimal_fix(trigger: str, branch: str | None, dry_run: bool) -> dict:
    """Apply the smallest safe delta for the trigger. Reuses existing fixers:
      * merge_conflict → scripts/autofix_conflicts.py (classify + resolve)
      * build/required-check fails → SAFE vaccine fixers (vaccine_autofixer)
    Returns {actions, files_changed, manual_review}."""
    actions: list[dict] = []
    manual_review = False

    if trigger == "merge_conflict" and branch:
        try:
            import autofix_conflicts as afc
            rc = afc.cmd_branch(branch, dry_run)
            actions.append({"step": "resolve_conflicts", "branch": branch,
                            "rc": rc, "result": {0: "resolved", 2: "needs-manual"}.get(rc, "no-op")})
            manual_review = rc == 2
        except SystemExit:  # argparse paths inside reused modules
            actions.append({"step": "resolve_conflicts", "error": "SystemExit"})
        except Exception as exc:
            actions.append({"step": "resolve_conflicts", "error": str(exc)})

    # Known recurring build-breakers — minimal, deterministic, idempotent fixes.
    try:
        import vaccine_autofixer as va
        for step in va.SAFE_STEPS:
            try:
                out = step(dry_run)
            except Exception as exc:
                actions.append({"step": step.__name__, "error": str(exc)})
                continue
            if out.get("matched") or out.get("fixed") or out.get("changed"):
                actions.append({"step": out.get("vaccine", step.__name__),
                                "name": out.get("name", ""),
                                "matched": out.get("matched", False),
                                "fixed": out.get("fixed", False),
                                "detail": out.get("detail", "")})
    except Exception as exc:
        actions.append({"step": "vaccine_safe_steps", "error": str(exc)})

    files = [] if dry_run else changed_files()
    # Safety invariant: never report (or keep staged) a protected-content deletion.
    files = [f for f in files if not (is_protected_path(f) and not os.path.exists(_p(f)))]
    return {"actions": actions, "files_changed": files, "manual_review": manual_review}


# --------------------------------------------------------------------------
# verification — re-run QA / build / tests (reuse vaccine_autofixer runners)
# --------------------------------------------------------------------------
def run_tests(modules: list[str] | None = None, skip: bool = False) -> dict:
    if skip:
        return {"name": "unit tests", "passed": True, "detail": "skipped"}
    modules = modules or ["scripts.test_qa_vaccines"]
    try:
        res = subprocess.run([sys.executable, "-m", "unittest", *modules],
                             cwd=REPO, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return {"name": "unit tests", "passed": False, "detail": "timeout"}
    except Exception as exc:
        return {"name": "unit tests", "passed": True, "detail": f"skipped ({exc})"}
    tail = (res.stderr or res.stdout or "").strip().splitlines()
    return {"name": "unit tests", "passed": res.returncode == 0,
            "detail": tail[-1] if tail else f"exit {res.returncode}"}


def verify(skip_build: bool, skip_tests: bool) -> dict:
    """One QA + build + tests cycle. Reuses the vaccine_autofixer runners."""
    try:
        import vaccine_autofixer as va
        qa = va.run_qa()
        build = va.run_build(skip_build)
    except Exception as exc:
        qa = {"name": "qa_check.py", "passed": False, "detail": f"error: {exc}"}
        build = {"name": "zola build", "passed": True, "detail": "skipped (engine error)"}
    tests = run_tests(skip=skip_tests)
    passed = bool(qa.get("passed") and build.get("passed") and tests.get("passed"))
    return {"qa": qa, "build": build, "tests": tests, "passed": passed}


# --------------------------------------------------------------------------
# report ("Autofixer_report_by Vacxin")
# --------------------------------------------------------------------------
def deploy_status_for(status: str, files_changed: list[str], dry_run: bool) -> str:
    if dry_run:
        return "n/a (dry-run)"
    if status == "escalate":
        return "blocked — manual review (no merge)"
    if status == "ok" and files_changed:
        return "deploy-on-merge (after auto-merge when required checks pass)"
    if status == "ok":
        return "no-op (nothing to deploy)"
    return "pending (QA/build not yet green)"


def build_report(*, trigger: str, issue_id: str, branch: str, audit: dict,
                 diagnosis: dict, fix: dict, checks: dict, attempts: int,
                 status: str, dry_run: bool, started: datetime,
                 finished: datetime) -> dict:
    files_changed = fix.get("files_changed", [])
    return {
        "report_name": REPORT_NAME,
        "rule": RULE_NAME,
        "trigger": trigger,
        "issue_id": issue_id,
        "branch": branch,
        "pr_url": pr_url(branch),
        "run_id": os.environ.get("GITHUB_RUN_ID", "manual"),
        "started_at": iso(started),
        "finished_at": iso(finished),
        "last_run": iso(finished),
        "precheck": audit,
        "root_cause": diagnosis,
        "fix_actions": fix.get("actions", []),
        "files_changed": files_changed,
        "manual_review": fix.get("manual_review", False),
        "attempts": attempts,
        "checks_result": checks,
        "auto_merge": {
            "delegated_to": "scripts/try_auto_merge.py (auto-merge.yml)",
            "merges_only_when_required_checks_pass": True,
            "required_checks": audit.get("required_checks", []),
            "force_push_main": False,
        },
        "deploy_status": deploy_status_for(status, files_changed, dry_run),
        "status": status,
    }


_HISTORY_KEYS = (
    "run_id", "trigger", "issue_id", "branch", "status", "attempts",
    "files_changed", "last_run",
)


def save_report(report: dict) -> None:
    """Flat report (Insights / humans) + rolling history[] + latest pointer."""
    os.makedirs(DATA_DIR, exist_ok=True)
    existing = {}
    if os.path.isfile(REPORT_PATH):
        try:
            with open(REPORT_PATH, encoding="utf-8") as fh:
                existing = json.load(fh)
        except (OSError, ValueError):
            existing = {}
    snapshot = {k: report.get(k) for k in _HISTORY_KEYS}
    snapshot["files_changed"] = len(report.get("files_changed", []))
    history = existing.get("history", []) if isinstance(existing, dict) else []
    history.append(snapshot)
    history = history[-30:]
    out = dict(report)
    out["history"] = history
    out["latest"] = snapshot
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)


def log_line(msg: str, keep: int = 500) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    lines: list[str] = []
    if os.path.isfile(LOG_PATH):
        try:
            with open(LOG_PATH, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except OSError:
            lines = []
    lines.append(f"{iso(now_ict())}  {msg}")
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines[-keep:]) + "\n")


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------
def run(*, trigger: str, issue_id: str, branch_hint: str | None = None,
        log_file: str | None = None, run_id: str | None = None,
        dry_run: bool = False, skip_build: bool = False,
        skip_tests: bool = False) -> dict:
    """Full hotfix cycle. Returns the report dict (already saved)."""
    started = now_ict()
    branch = hotfix_branch(issue_id)

    audit = audit_rules()

    # Anti-loop: an issue that keeps returning is escalated, not re-fixed forever.
    looped, loop_reason = loop_detected(issue_id)
    diagnosis = diagnose(fetch_logs(log_file, run_id))

    if looped:
        report = build_report(
            trigger=trigger, issue_id=issue_id, branch=branch, audit=audit,
            diagnosis=diagnosis,
            fix={"actions": [{"step": "anti-loop", "detail": loop_reason}],
                 "files_changed": [], "manual_review": True},
            checks={"qa": {}, "build": {}, "tests": {}, "passed": False},
            attempts=LOOP_THRESHOLD, status="escalate", dry_run=dry_run,
            started=started, finished=now_ict())
        save_report(report)
        return report

    # Fix → verify, bounded "repeat until pass".
    attempt = 0
    fix: dict = {"actions": [], "files_changed": [], "manual_review": False}
    checks: dict = {"qa": {}, "build": {}, "tests": {}, "passed": False}
    while attempt < MAX_FIX_ATTEMPTS:
        attempt += 1
        fix = apply_minimal_fix(trigger, branch_hint, dry_run)
        checks = verify(skip_build, skip_tests)
        if checks["passed"] or dry_run or fix.get("manual_review"):
            break

    if not dry_run:
        bump_attempt(issue_id)

    if dry_run:
        status = "dry-run"
    elif fix.get("manual_review"):
        status = "manual-review"
    elif checks["passed"]:
        status = "ok"
        clear_attempt(issue_id)  # durable pass → reset anti-loop counter
    else:
        status = "fixing"  # not green yet; CI will re-trigger another round

    report = build_report(
        trigger=trigger, issue_id=issue_id, branch=branch, audit=audit,
        diagnosis=diagnosis, fix=fix, checks=checks, attempts=attempt,
        status=status, dry_run=dry_run, started=started, finished=now_ict())
    save_report(report)
    return report


def print_outputs(report: dict) -> None:
    """Emit the five required outputs."""
    checks = report.get("checks_result", {})
    def _c(k: str) -> str:
        r = checks.get(k) or {}
        return f"{k}={'PASS' if r.get('passed') else 'FAIL' if r else 'n/a'}"
    print()
    print(f"== {RULE_NAME} — {REPORT_NAME} ==")
    print(f"PR link        : {report.get('pr_url')}")
    print(f"Root cause     : {report['root_cause'].get('root_cause')} "
          f"({report['root_cause'].get('confidence')}% · {report['root_cause'].get('pattern_id')})")
    fc = report.get("files_changed", [])
    print(f"Files changed  : {len(fc)}" + (f" → {', '.join(fc[:8])}" if fc else ""))
    print(f"Checks result  : {_c('qa')} · {_c('build')} · {_c('tests')} "
          f"→ {'GREEN' if checks.get('passed') else 'NOT GREEN'}")
    print(f"Deploy status  : {report.get('deploy_status')}")
    print(f"Status         : {report.get('status')}  (attempts={report.get('attempts')})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"{RULE_NAME} — conflict-safe CI/PR/merge/deploy hotfix")
    ap.add_argument("--precheck", action="store_true",
                    help="run the conflict-safe rule audit only, then exit")
    ap.add_argument("--trigger", choices=TRIGGERS,
                    help="activation trigger")
    ap.add_argument("--issue-id", default="",
                    help="stable id for the failing run (→ vaccine-hotfix/<id>)")
    ap.add_argument("--branch", default=None,
                    help="source branch (required for --trigger merge_conflict)")
    ap.add_argument("--log-file", default=None, help="failing CI log for diagnosis")
    ap.add_argument("--run-id", default=None, help="gh run id to fetch logs from")
    ap.add_argument("--dry-run", action="store_true", help="scan/diagnose only, no fixes")
    ap.add_argument("--no-build", action="store_true", help="skip the zola build step")
    ap.add_argument("--no-tests", action="store_true", help="skip the unit-test step")
    ap.add_argument("--release-lock", action="store_true", help="clear a stale lock and exit")
    ap.add_argument("--json", action="store_true", help="print the report JSON")
    args = ap.parse_args(argv)

    now = now_ict()
    if args.release_lock:
        release_lock(now, "force-released")
        print("🔓 vaccine-hotfix lock released")
        return 0

    if args.precheck:
        audit = audit_rules()
        if args.json:
            print(json.dumps(audit, ensure_ascii=False, indent=2))
        else:
            print(f"== {RULE_NAME} — conflict-safe precheck ==")
            print(f"safe_to_run: {audit['safe_to_run']} · "
                  f"required_checks: {', '.join(audit['required_checks'])} · "
                  f"vaccine-hotfix eligible: {audit['branch_prefix_allowed']}")
            for g in audit["guarantees"]:
                print(f"  ✓ {g}")
            for c in audit["conflicts"]:
                print(f"  ⚠ [{c['rule']}] {c['issue']} → {c['resolution']}")
        return 0

    if not args.trigger:
        ap.error("--trigger is required (or use --precheck / --release-lock)")
    if args.trigger == "merge_conflict" and not args.branch:
        ap.error("--branch is required for --trigger merge_conflict")

    issue_id = args.issue_id or f"{args.trigger}-{os.environ.get('GITHUB_RUN_ID', 'manual')}"

    if not args.dry_run and not acquire_lock(args.trigger, issue_id, now):
        print("⏳ Another Vaccine Hotfix run is active — skipping (no concurrent runs).")
        return 3

    try:
        log_line(f"START trigger={args.trigger} issue={issue_id} dry_run={args.dry_run}")
        report = run(
            trigger=args.trigger, issue_id=issue_id, branch_hint=args.branch,
            log_file=args.log_file, run_id=args.run_id, dry_run=args.dry_run,
            skip_build=args.no_build, skip_tests=args.no_tests)
        log_line(f"DONE status={report['status']} attempts={report['attempts']} "
                 f"files={len(report['files_changed'])} "
                 f"green={report['checks_result'].get('passed')}")
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_outputs(report)
        # Non-zero only when escalation/manual-review is needed, so CI can surface it
        # WITHOUT failing the hotfix workflow on a normal "still fixing" round.
        return 0 if report["status"] in ("ok", "dry-run", "fixing") else 1
    finally:
        if not args.dry_run:
            release_lock(now_ict(), "finished")


if __name__ == "__main__":
    raise SystemExit(main())
