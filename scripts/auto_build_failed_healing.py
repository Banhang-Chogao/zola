#!/usr/bin/env python3
"""auto-build-failed-healing — SEOMONEY auto maintainer bot.

Detect → Classify → Heal → Build → Learn → PR.

Scans GitHub Actions build/deploy/qa runs that FAILED in the last 48h, classifies
the failure (P0/P1/P2/P3) against a public-safe healing registry, applies a SAFE
deterministic fix when one is matched, runs a targeted build/QA, and opens a
hotfix PR (never pushes main directly). Reusable lessons are appended to the
public healing registry.

Culture (SEOMONEY): "Bug found → Fix it → Learn from it → Auto-healing".

Public vs private memory
------------------------
This bot only reads PUBLIC-SAFE, committed healing sources:
    CLAUDE.md, CULTURE_OF_DEPLOYMENT.md,
    data/healing-patterns.json (optional), docs/HEALING_PATTERNS.md (optional).
`CLAUDE_PRIVATE.md` is gitignored local memory. A local agent MAY read it when it
exists, but CI MUST NOT require it and its content is NEVER printed to logs or
committed. This script never fails because the private file is absent.

CLI
---
    python3 scripts/auto_build_failed_healing.py --dry-run --hours 48
    python3 scripts/auto_build_failed_healing.py --hours 48 --apply
    python3 scripts/auto_build_failed_healing.py --dry-run            # default 48h

Exit code is always 0 on the happy/empty/offline path — an observer/remediation
bot must never turn itself red (CLAUDE.md V3/V7).
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
except Exception:  # pragma: no cover - zoneinfo always present on 3.9+
    TZ = timezone(timedelta(hours=7))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
PATTERNS_PATH = os.path.join(DATA_DIR, "healing-patterns.json")
STATE_PATH = os.path.join(DATA_DIR, "auto-healing-state.json")
REPORT_PATH = os.path.join(DATA_DIR, "auto-healing-report.json")
LOG_PATH = os.path.join(DATA_DIR, "auto-healing.log")

# Public-safe healing sources only. NEVER add CLAUDE_PRIVATE.md here.
PUBLIC_HEALING_SOURCES = [
    "CLAUDE.md",
    "CULTURE_OF_DEPLOYMENT.md",
    "docs/HEALING_PATTERNS.md",
    "data/healing-patterns.json",
]
PRIVATE_MEMORY_FILE = "CLAUDE_PRIVATE.md"  # gitignored, local-only, optional

DEFAULT_WINDOW_HOURS = 48
REPO_SLUG = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")

# Workflows we care about (names + filenames). conclusion=failure only.
WATCHED_WORKFLOWS = (
    "deploy", "qa", "build", "zola deploy", "github pages",
    "build and deploy", "qa gatekeeper", "build semantic related posts",
)

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def log(msg: str) -> None:
    line = f"[auto-healing] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp (GitHub uses `...Z`). Returns aware UTC."""
    if not value:
        return None
    try:
        s = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


# --------------------------------------------------------------------------
# 48h windowing — pure + testable
# --------------------------------------------------------------------------
def age_hours(run_time: datetime, now: datetime | None = None) -> float:
    now = now or now_utc()
    return (now - run_time).total_seconds() / 3600.0


def is_within_hours(run_time: datetime | None, hours: float,
                    now: datetime | None = None) -> bool:
    """True iff run_time is at most `hours` old (and not in the future)."""
    if run_time is None:
        return False
    a = age_hours(run_time, now)
    return -0.5 <= a <= hours  # tiny negative tolerance for clock skew


def should_process_run(run: dict, hours: float = DEFAULT_WINDOW_HOURS,
                       now: datetime | None = None) -> tuple[bool, str]:
    """Decide whether a single run should be healed.

    Returns (process?, reason). Reasons: ok | stale_ignored | not_failure |
    cancelled_skipped | not_watched.
    """
    conclusion = (run.get("conclusion") or "").lower()
    name = (run.get("name") or run.get("workflow_name") or "").lower()
    created = parse_iso(run.get("created_at") or run.get("run_started_at") or "")

    # 48h hard rule first — never touch stale builds.
    if not is_within_hours(created, hours, now):
        return (False, "stale_ignored")

    if conclusion in ("cancelled", "skipped"):
        # Cancelled/skipped only matter if they block deploy; treat as non-actionable.
        return (False, "cancelled_skipped")

    if conclusion != "failure":
        return (False, "not_failure")

    if name and not any(w in name for w in WATCHED_WORKFLOWS):
        return (False, "not_watched")

    return (True, "ok")


# --------------------------------------------------------------------------
# healing registry
# --------------------------------------------------------------------------
def load_patterns(path: str = PATTERNS_PATH) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return list(data.get("patterns") or [])
    except Exception as exc:
        log(f"could not load healing patterns ({exc}) — using empty registry")
        return []


def classify(log_text: str, patterns: list[dict]) -> dict | None:
    """Match failure log against the registry. Returns the matched pattern dict
    augmented with `severity`, or None when nothing matches.

    A pattern matches when ALL of its `match` substrings appear (case-insensitive)
    OR — for single-token patterns — that token appears. Most-specific (most
    tokens) and most-severe pattern wins.
    """
    text = (log_text or "").lower()
    best: dict | None = None
    best_key = (99, -1)  # (severity_rank, -num_tokens) lower is better
    for pat in patterns:
        tokens = [t.lower() for t in (pat.get("match") or []) if t]
        if not tokens:
            continue
        hits = [t for t in tokens if t in text]
        # Match model: single-token patterns need that token; multi-token
        # patterns (often alternatives) need at least 2 distinct signals.
        threshold = 1 if len(tokens) == 1 else 2
        if len(hits) < threshold:
            continue
        sev = pat.get("severity", "P3")
        key = (SEVERITY_ORDER.get(sev, 3), -len(hits))
        if key < best_key:
            best_key = key
            best = dict(pat)
            best["severity"] = sev
            best["_matched_tokens"] = hits
    return best


# --------------------------------------------------------------------------
# safe fixers — deterministic, reuse existing repo scripts only
# --------------------------------------------------------------------------
def _run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        res = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                             timeout=timeout)
        return res.returncode, (res.stdout or "") + (res.stderr or "")
    except Exception as exc:
        return 1, f"command failed: {exc}"


def _git_dirty() -> bool:
    rc, out = _run(["git", "status", "--porcelain"], timeout=30)
    return rc == 0 and bool(out.strip())


def fix_regenerate_references(dry_run: bool) -> dict:
    """Regenerate data/references.json via the existing builder."""
    res = {"ran": False, "changed": False, "detail": ""}
    if dry_run:
        res["detail"] = "would run scripts/build_references.py"
        return res
    rc, out = _run(["python3", "scripts/build_references.py"])
    res["ran"] = True
    res["changed"] = _git_dirty()
    res["detail"] = "build_references.py ok" if rc == 0 else f"build_references.py rc={rc}"
    return res


def fix_clean_public(dry_run: bool) -> dict:
    """Remove the gitignored public/ artifact so the build starts clean."""
    res = {"ran": False, "changed": False, "detail": ""}
    public = os.path.join(REPO, "public")
    if not os.path.isdir(public):
        res["detail"] = "no public/ artifact present"
        return res
    if dry_run:
        res["detail"] = "would remove stale public/ artifact"
        return res
    rc, out = _run(["rm", "-rf", public], timeout=60)
    res["ran"] = True
    res["detail"] = "removed stale public/" if rc == 0 else "rm public/ failed"
    # public/ is gitignored → never a tracked change.
    return res


def fix_internal_link(dry_run: bool) -> dict:
    """Use the repo's 404 checker to remap broken internal links in source .md."""
    res = {"ran": False, "changed": False, "detail": ""}
    script = os.path.join(REPO, "qa-404-checker.py")
    if not os.path.isfile(script):
        res["detail"] = "qa-404-checker.py not found"
        return res
    if dry_run:
        res["detail"] = "would run qa-404-checker.py --fix"
        return res
    rc, out = _run(["python3", "qa-404-checker.py", "--fix"])
    res["ran"] = True
    res["changed"] = _git_dirty()
    res["detail"] = "qa-404-checker.py --fix ran"
    return res


def fix_faq_field_rename(dry_run: bool) -> dict:
    """Rename FAQ frontmatter keys question=/answer= → q=/a= (line-anchored).

    Deterministic + safe: only touches lines that start with the bad key inside
    files that contain an [[extra.faq]] block. Mirrors CLAUDE.md V19.
    """
    res = {"ran": False, "changed": False, "detail": "", "files": []}
    targets = []
    for sub in ("content/posting", "content/baochi", "content/pages"):
        d = os.path.join(REPO, sub)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if name.endswith(".md"):
                targets.append(os.path.join(d, name))
    changed_files = []
    q_re = re.compile(r"^question(\s*=)", re.MULTILINE)
    a_re = re.compile(r"^answer(\s*=)", re.MULTILINE)
    for path in targets:
        try:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
        except Exception:
            continue
        if "[[extra.faq]]" not in txt:
            continue
        if not (q_re.search(txt) or a_re.search(txt)):
            continue
        new = q_re.sub(r"q\1", a_re.sub(r"a\1", txt))
        if new != txt:
            changed_files.append(os.path.relpath(path, REPO))
            if not dry_run:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new)
                except Exception:
                    continue
    res["ran"] = not dry_run
    res["files"] = changed_files
    res["changed"] = bool(changed_files) and not dry_run
    res["detail"] = (
        f"{'would rename' if dry_run else 'renamed'} FAQ keys in "
        f"{len(changed_files)} file(s)"
    )
    return res


SAFE_FIXERS = {
    "regenerate-references": fix_regenerate_references,
    "clean-public": fix_clean_public,
    "internal-link-fix": fix_internal_link,
    "faq-field-rename": fix_faq_field_rename,
}


def apply_safe_fix(pattern: dict, dry_run: bool) -> dict:
    """Run the deterministic safe fixer for a pattern (if any)."""
    fixer_id = pattern.get("fixer")
    if not fixer_id:
        return {"ran": False, "changed": False,
                "detail": "no auto-fixer — requires manual/PR review"}
    fixer = SAFE_FIXERS.get(fixer_id)
    if not fixer:
        return {"ran": False, "changed": False,
                "detail": f"unknown fixer id '{fixer_id}'"}
    try:
        return fixer(dry_run)
    except Exception as exc:  # never crash the bot
        return {"ran": False, "changed": False, "detail": f"fixer error: {exc}"}


# --------------------------------------------------------------------------
# gh — fetch failed runs (best-effort, offline-safe)
# --------------------------------------------------------------------------
def _gh_available() -> bool:
    from shutil import which
    return which("gh") is not None and bool(
        os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))


def fetch_failed_runs(hours: float) -> list[dict]:
    """Return recent runs as plain dicts. Offline/no-gh → []. Never raises."""
    if not _gh_available():
        log("gh CLI/token unavailable — no live run scan (offline-safe).")
        return []
    try:
        # Most-recent 100 completed runs (GitHub returns newest first) is more
        # than enough for a ≤48h window; avoid unbounded --paginate.
        res = subprocess.run(
            ["gh", "api",
             f"repos/{REPO_SLUG}/actions/runs?status=completed&per_page=100",
             "--jq", ".workflow_runs[] | {id, name, conclusion, status, "
                     "created_at, run_started_at, head_branch, html_url, "
                     "event}"],
            cwd=REPO, capture_output=True, text=True, timeout=40)
        if res.returncode != 0:
            log("gh api runs failed (auth/rate-limit) — skipping live scan.")
            return []
        runs = []
        for line in (res.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except Exception:
                continue
        return runs
    except Exception as exc:
        log(f"fetch_failed_runs skipped ({exc})")
        return []


def fetch_run_log(run_id: int) -> str:
    """Best-effort failed-log fetch for a run. Empty string on any failure."""
    if not _gh_available():
        return ""
    try:
        res = subprocess.run(
            ["gh", "run", "view", str(run_id), "--log-failed", "--repo", REPO_SLUG],
            cwd=REPO, capture_output=True, text=True, timeout=45)
        if res.returncode != 0:
            # --log-failed unavailable for some events → fall back to full log.
            res = subprocess.run(
                ["gh", "run", "view", str(run_id), "--log", "--repo", REPO_SLUG],
                cwd=REPO, capture_output=True, text=True, timeout=45)
        return res.stdout or ""
    except Exception:
        return ""


# --------------------------------------------------------------------------
# dedup state
# --------------------------------------------------------------------------
def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "handled": []}


def save_state(state: dict) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as exc:
        log(f"could not persist state ({exc})")


def dedup_key(run_id, pattern_id: str, branch: str = "") -> str:
    return f"{run_id}:{pattern_id}:{branch or 'main'}"


def already_handled(state: dict, key: str) -> bool:
    return any(h.get("key") == key for h in state.get("handled", []))


def record_handled(state: dict, key: str, extra: dict) -> None:
    state.setdefault("handled", [])
    entry = {"key": key, "at": iso(now_utc())}
    entry.update(extra)
    state["handled"].append(entry)
    # keep last 200 to avoid unbounded growth; stale state must not block healing
    state["handled"] = state["handled"][-200:]


# --------------------------------------------------------------------------
# PR creation (gh) — never push main
# --------------------------------------------------------------------------
def _ensure_label(name: str, color: str, desc: str) -> None:
    if not _gh_available():
        return
    subprocess.run(["gh", "label", "create", name, "--color", color,
                    "--description", desc, "--repo", REPO_SLUG],
                   cwd=REPO, capture_output=True, text=True)


def open_existing_healing_pr(branch: str) -> str | None:
    """Return URL of an open auto-healing PR for `branch`, else None."""
    if not _gh_available():
        return None
    try:
        res = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--head", branch,
             "--json", "url", "--repo", REPO_SLUG],
            cwd=REPO, capture_output=True, text=True, timeout=20)
        data = json.loads(res.stdout or "[]")
        return data[0]["url"] if data else None
    except Exception:
        return None


def create_hotfix_pr(pattern: dict, run: dict, fix_result: dict,
                     build_result: dict, dry_run: bool) -> dict:
    """Create branch + commit + PR. Returns {created, url, branch, reason}."""
    pattern_id = pattern.get("id", "unknown")
    run_id = run.get("id", "manual")
    branch = f"auto-build-failed-healing/{pattern_id}-{run_id}"
    out = {"created": False, "url": "", "branch": branch, "reason": ""}

    if dry_run:
        out["reason"] = "dry-run — would open PR"
        return out
    if not _gh_available():
        out["reason"] = "gh/token unavailable — cannot open PR"
        return out
    if not fix_result.get("changed"):
        out["reason"] = "no tracked file change — nothing to PR"
        return out

    existing = open_existing_healing_pr(branch)
    if existing:
        out["reason"] = "dedup — PR already open"
        out["url"] = existing
        return out

    body = build_pr_body(pattern, run, fix_result, build_result)
    title = f"fix(auto-healing): {pattern_id}"
    cmds = [
        ["git", "config", "user.name", "github-actions[bot]"],
        ["git", "config", "user.email",
         "github-actions[bot]@users.noreply.github.com"],
        ["git", "checkout", "-B", branch],
        ["git", "add", "-A"],
        ["git", "commit", "-m", f"{title} [skip changelog]"],
        ["git", "push", "-u", "origin", branch, "--force-with-lease"],
    ]
    for c in cmds:
        rc, log_out = _run(c, timeout=120)
        if rc != 0 and c[1] == "commit":
            out["reason"] = "nothing to commit"
            return out
        if rc != 0 and c[1] == "push":
            out["reason"] = "push failed (protected?)"
            return out

    _ensure_label("auto-healing", "1d76db", "auto-build-failed-healing bot")
    _ensure_label("build-fix", "d93f0b", "build/deploy failure fix")
    pr = subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body,
         "--base", "main", "--head", branch,
         "--label", "auto-healing", "--label", "build-fix",
         "--repo", REPO_SLUG],
        cwd=REPO, capture_output=True, text=True)
    if pr.returncode == 0:
        out["created"] = True
        out["url"] = (pr.stdout or "").strip()
        out["reason"] = "PR created"
    else:
        # labels may not exist / perms — retry without labels.
        pr2 = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body,
             "--base", "main", "--head", branch, "--repo", REPO_SLUG],
            cwd=REPO, capture_output=True, text=True)
        if pr2.returncode == 0:
            out["created"] = True
            out["url"] = (pr2.stdout or "").strip()
            out["reason"] = "PR created (no labels)"
        else:
            out["reason"] = "gh pr create failed"
    return out


def build_pr_body(pattern: dict, run: dict, fix_result: dict,
                  build_result: dict) -> str:
    created = parse_iso(run.get("created_at") or "")
    age = f"{age_hours(created):.1f}h" if created else "unknown"
    return (
        "Auto-build-failed-healing report\n\n"
        f"Failed run: {run.get('id', 'n/a')} ({run.get('html_url', '')})\n"
        f"Workflow: {run.get('name', 'n/a')}\n"
        f"Branch/PR: {run.get('head_branch', 'n/a')}\n"
        f"Age: {age} (≤48h window)\n"
        f"Detected pattern: {pattern.get('id')} — {pattern.get('title', '')}\n"
        f"Severity: {pattern.get('severity')}\n"
        f"Fix applied: {fix_result.get('detail', '')}\n"
        f"QA/build result: {build_result.get('detail', '')}\n"
        f"Permanent prevention: registry pattern `{pattern.get('id')}` in "
        "data/healing-patterns.json; see docs/HEALING_PATTERNS.md.\n"
        "Experience update:\n"
        "- Public CLAUDE.md: No (registry-tracked)\n"
        "- Private CLAUDE_PRIVATE.md: No, local-only\n\n"
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
    )


# --------------------------------------------------------------------------
# targeted build/QA
# --------------------------------------------------------------------------
def run_targeted_checks(pattern: dict, dry_run: bool) -> dict:
    res = {"ran": False, "ok": True, "detail": ""}
    commands = pattern.get("commands") or []
    if dry_run or not commands:
        res["detail"] = "skipped (dry-run/advisory)" if dry_run else "no checks"
        return res
    details = []
    ok = True
    from shutil import which
    for cmd in commands:
        if cmd == "zola build":
            if which("zola") is None:
                details.append("zola not installed — build check skipped")
                continue
            rc, out = _run(["zola", "build"], timeout=420)
            ok = ok and rc == 0
            details.append(f"zola build {'ok' if rc == 0 else 'FAILED'}")
        else:
            rc, out = _run(cmd.split(), timeout=300)
            ok = ok and rc == 0
            details.append(f"{cmd} {'ok' if rc == 0 else 'FAILED'}")
    res["ran"] = True
    res["ok"] = ok
    res["detail"] = "; ".join(details) or "no checks"
    return res


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def write_report(report: dict) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as exc:
        log(f"could not write report ({exc})")


# --------------------------------------------------------------------------
# main pipeline
# --------------------------------------------------------------------------
def heal(hours: float, apply: bool, dry_run: bool,
         single_run_id: int | None = None) -> dict:
    patterns = load_patterns()
    state = load_state()
    runs = fetch_failed_runs(hours)

    if single_run_id is not None:
        # workflow_run trigger: focus on the one run that just failed.
        runs = [r for r in runs if str(r.get("id")) == str(single_run_id)] or [
            {"id": single_run_id,
             "name": os.environ.get("FAILED_WORKFLOW_NAME", "deploy"),
             "conclusion": "failure", "status": "completed",
             "created_at": iso(now_utc()),
             "head_branch": os.environ.get("FAILED_HEAD_BRANCH", "main"),
             "html_url": os.environ.get("FAILED_WORKFLOW_URL", "")}]

    report = {
        "generated_at": iso(now_utc()),
        "window_hours": hours,
        "mode": "dry-run" if dry_run else ("apply" if apply else "scan"),
        "scanned": len(runs),
        "processed": [],
        "stale_ignored": 0,
        "skipped": [],
        "healed": [],
        "advisory": [],
        "manual": [],
        "prs": [],
    }

    for run in runs:
        ok, reason = should_process_run(run, hours)
        if not ok:
            if reason == "stale_ignored":
                report["stale_ignored"] += 1
            report["skipped"].append({"id": run.get("id"), "reason": reason})
            continue

        log_text = fetch_run_log(int(run["id"])) if run.get("id") else ""
        # If no live log (offline), fall back to the workflow name as signal.
        signal = log_text or (run.get("name", ""))
        pattern = classify(signal, patterns)

        entry = {
            "id": run.get("id"),
            "workflow": run.get("name"),
            "branch": run.get("head_branch"),
            "url": run.get("html_url"),
            "age_hours": round(age_hours(parse_iso(run.get("created_at") or "")
                                         or now_utc()), 1),
            "pattern": pattern.get("id") if pattern else None,
            "severity": pattern.get("severity") if pattern else None,
        }
        report["processed"].append(entry)

        if not pattern:
            entry["action"] = "no_known_pattern"
            report["manual"].append(entry)
            continue

        # P2/P3 are advisory — NEVER block, NEVER PR.
        if pattern["severity"] in ("P2", "P3"):
            entry["action"] = "advisory"
            entry["note"] = pattern.get("safe_fix", "")
            report["advisory"].append(entry)
            continue

        # dedup
        key = dedup_key(run.get("id"), pattern["id"], run.get("head_branch", ""))
        if already_handled(state, key) and not dry_run:
            entry["action"] = "dedup_skip"
            report["skipped"].append({"id": run.get("id"), "reason": "dedup"})
            continue

        fix_result = apply_safe_fix(pattern, dry_run=dry_run or not apply)
        entry["fix"] = fix_result.get("detail")

        if not fix_result.get("ran") and not fix_result.get("changed"):
            entry["action"] = "manual_pr_required"
            report["manual"].append(entry)
            continue

        build_result = run_targeted_checks(pattern, dry_run=dry_run or not apply)
        entry["build"] = build_result.get("detail")

        if apply and not dry_run:
            pr = create_hotfix_pr(pattern, run, fix_result, build_result,
                                  dry_run=False)
            entry["pr"] = pr
            if pr.get("url"):
                report["prs"].append(pr["url"])
            record_handled(state, key, {"pattern": pattern["id"],
                                        "pr": pr.get("url", "")})
            entry["action"] = "healed_pr" if pr.get("created") else "healed_noop"
        else:
            entry["action"] = "would_heal"

        report["healed"].append(entry)

    if apply and not dry_run:
        save_state(state)
    write_report(report)
    return report


def print_summary(report: dict) -> None:
    log(f"mode={report['mode']} window={report['window_hours']}h "
        f"scanned={report['scanned']} processed={len(report['processed'])} "
        f"stale_ignored={report['stale_ignored']} healed={len(report['healed'])} "
        f"advisory={len(report['advisory'])} manual={len(report['manual'])} "
        f"prs={len(report['prs'])}")
    for e in report["processed"]:
        log(f"  run {e['id']} [{e.get('severity') or '-'}] "
            f"{e.get('pattern') or 'no-pattern'} → {e.get('action', 'n/a')}")


def confirm_private_safety() -> None:
    """Assert CI never depends on the private file; log a public-safe note."""
    has_private = os.path.isfile(os.path.join(REPO, PRIVATE_MEMORY_FILE))
    in_ci = bool(os.environ.get("GITHUB_ACTIONS"))
    if has_private and in_ci:
        # Defensive: should be gitignored; never read/print its content.
        log("note: private memory present but NOT read in CI (public sources only).")
    elif has_private:
        log("note: CLAUDE_PRIVATE.md present (local) — local agent may read it; "
            "this script does not require or print it.")
    else:
        log("note: no CLAUDE_PRIVATE.md (not required) — using public sources only.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="auto-build-failed-healing bot")
    p.add_argument("--hours", type=float, default=DEFAULT_WINDOW_HOURS,
                   help="lookback window in hours (default 48; never exceed 48 "
                        "in normal operation)")
    p.add_argument("--apply", action="store_true",
                   help="apply safe fixes and open hotfix PRs")
    p.add_argument("--dry-run", action="store_true",
                   help="scan + classify + propose only; no file changes, no PR")
    p.add_argument("--run-id", type=int, default=None,
                   help="focus on a single failed run id (workflow_run trigger)")
    args = p.parse_args(argv)

    # Hard 48h ceiling — do not heal stale builds even if asked.
    hours = min(args.hours, DEFAULT_WINDOW_HOURS)

    confirm_private_safety()

    # Default to dry-run when neither flag is given (safe by default).
    dry_run = args.dry_run or not args.apply
    run_id = args.run_id or (int(os.environ["FAILED_RUN_ID"])
                             if os.environ.get("FAILED_RUN_ID") else None)

    try:
        report = heal(hours=hours, apply=args.apply, dry_run=dry_run,
                      single_run_id=run_id)
        print_summary(report)
    except Exception as exc:  # observer must never self-red
        log(f"unexpected error (non-fatal): {exc}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
