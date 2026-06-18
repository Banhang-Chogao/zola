#!/usr/bin/env python3
"""Daily Vaccine Autofixer engine (Vaccine V11).

Same engine for the scheduled run (06:00 Asia/Ho_Chi_Minh) and the manual
`vacxin11` trigger. It:

  1. Reads the vaccine library from CLAUDE.md (the "THƯ VIỆN VACCINE" V1..Vn).
  2. Scans the repo/system for known vaccine-class issues.
  3. Auto-fixes the SAFE, deterministic ones (reusing existing fixers).
  4. Runs QA verification.
  5. Saves logs.
  6. Updates the report consumed by the Insights UI
     (data/vaccine-autofixer-report.json — "Autofixer report by Vacxin").

A lock (data/vaccine-autofixer-state.json) prevents concurrent / duplicate
runs. Code changes go through the PR flow in the workflow, never a direct
push to main.

CLI:
    python3 scripts/vaccine_autofixer.py                 # manual run
    python3 scripts/vaccine_autofixer.py --trigger schedule
    python3 scripts/vaccine_autofixer.py --dry-run       # scan only, no fixes
    python3 scripts/vaccine_autofixer.py --no-build      # skip zola build step
    python3 scripts/vaccine_autofixer.py --release-lock  # force-clear stale lock
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
CLAUDE_MD = os.path.join(REPO, "CLAUDE.md")
DATA_DIR = os.path.join(REPO, "data")
REPORT_PATH = os.path.join(DATA_DIR, "vaccine-autofixer-report.json")
STATE_PATH = os.path.join(DATA_DIR, "vaccine-autofixer-state.json")
LOG_PATH = os.path.join(DATA_DIR, "vaccine-autofixer.log")

# A run is considered stale (lock ignorable) after this many minutes.
LOCK_STALE_MINUTES = 30
SCHEDULE_HOUR_ICT = 6  # 06:00 Asia/Ho_Chi_Minh


def now_ict() -> datetime:
    return datetime.now(TZ)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def next_scheduled_run(after: datetime | None = None) -> datetime:
    """Next 06:00 Asia/Ho_Chi_Minh strictly after `after` (default: now)."""
    after = after or now_ict()
    candidate = after.replace(hour=SCHEDULE_HOUR_ICT, minute=0, second=0, microsecond=0)
    if candidate <= after:
        candidate += timedelta(days=1)
    return candidate


# --------------------------------------------------------------------------
# Vaccine registry — parse the library out of CLAUDE.md
# --------------------------------------------------------------------------
_VACCINE_HEADER = re.compile(r"^####\s+(V\d+)\s+—\s+(.+?)\s*$", re.MULTILINE)


def load_vaccines(path: str = CLAUDE_MD) -> list[dict]:
    """Parse `#### V<N> — <title>` blocks from CLAUDE.md into a registry.

    Each entry: {code, title, signature, fixer}. `signature`/`fixer` are short
    excerpts pulled from the "Dấu hiệu" / "FIXER" bullets when present.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []

    matches = list(_VACCINE_HEADER.finditer(text))
    vaccines: list[dict] = []
    for idx, m in enumerate(matches):
        code, title = m.group(1), m.group(2).strip()
        body_start = m.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        signature = _extract_field(body, "Dấu hiệu")
        fixer = _extract_field(body, "FIXER")
        vaccines.append({
            "code": code,
            "title": title,
            "signature": signature,
            "fixer": fixer,
        })
    return vaccines


def _extract_field(body: str, label: str) -> str:
    """Grab a short excerpt that follows `**<label>...`** in a vaccine body."""
    m = re.search(r"\*\*" + re.escape(label) + r"[^*]*\*\*[:：]?\s*(.+)", body)
    if not m:
        return ""
    excerpt = re.sub(r"\s+", " ", m.group(1)).strip()
    return excerpt[:240]


# --------------------------------------------------------------------------
# Lock — prevent concurrent / duplicate runs
# --------------------------------------------------------------------------
def read_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_state(state: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def lock_is_active(state: dict, now: datetime) -> bool:
    """True when another run holds a non-stale lock."""
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


def acquire_lock(trigger: str, now: datetime) -> bool:
    state = read_state()
    if lock_is_active(state, now):
        return False
    write_state({
        "running": True,
        "trigger": trigger,
        "started_at": iso(now),
        "pid": os.getpid(),
    })
    return True


def release_lock(now: datetime, last_status: str) -> None:
    write_state({
        "running": False,
        "last_finished_at": iso(now),
        "last_status": last_status,
    })


# --------------------------------------------------------------------------
# Safe fixer steps. Each returns a dict describing the outcome.
# --------------------------------------------------------------------------
def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=REPO, capture_output=True, text=True, timeout=900
    )


def _script(name: str) -> str:
    return os.path.join(REPO, name)


def step_build_related_model_id(dry_run: bool) -> dict:
    """V1 — HuggingFace model id must be org-qualified in build_related.py."""
    path = _script("scripts/build_related.py")
    out = {"vaccine": "V1", "name": "HF model id org-qualified", "matched": False,
           "fixed": False, "changed": False, "detail": ""}
    if not os.path.isfile(path):
        out["detail"] = "build_related.py absent"
        return out
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r'MODEL_NAME\s*=\s*["\']([^"\']+)["\']', src)
    if not m:
        out["detail"] = "MODEL_NAME not found"
        return out
    model = m.group(1)
    if "/" in model:
        out["detail"] = f"ok ({model})"
        return out
    out["matched"] = True
    fixed = f"sentence-transformers/{model}"
    out["detail"] = f"bare id '{model}' → '{fixed}'"
    if not dry_run:
        src2 = src.replace(m.group(0), m.group(0).replace(model, fixed), 1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src2)
        out["fixed"] = out["changed"] = True
    return out


def step_internal_links(dry_run: bool) -> dict:
    """Broken internal links — detect (and --fix when not dry-run)."""
    out = {"vaccine": "V-links", "name": "Internal link 404", "matched": False,
           "fixed": False, "changed": False, "detail": ""}
    checker = _script("qa-404-checker.py")
    if not os.path.isfile(checker):
        out["detail"] = "qa-404-checker.py absent"
        return out
    cmd = [sys.executable, checker] + ([] if dry_run else ["--fix"])
    try:
        res = _run(cmd)
    except subprocess.TimeoutExpired:
        out["detail"] = "timeout"
        return out
    # exit 2 => broken internal links found
    out["matched"] = res.returncode == 2
    summary = ""
    for line in (res.stdout or "").splitlines():
        if "broken" in line.lower():
            summary = line.strip()
            break
    out["detail"] = summary or f"exit {res.returncode}"
    if out["matched"] and not dry_run:
        out["fixed"] = True
    return out


def step_build_references(dry_run: bool) -> dict:
    out = {"vaccine": "V-refs", "name": "Reference index", "matched": False,
           "fixed": False, "changed": False, "detail": ""}
    script = _script("scripts/build_references.py")
    if not os.path.isfile(script) or dry_run:
        out["detail"] = "skipped" if dry_run else "absent"
        return out
    try:
        res = _run([sys.executable, script])
    except subprocess.TimeoutExpired:
        out["detail"] = "timeout"
        return out
    out["detail"] = (res.stdout or "").strip().splitlines()[-1:] and \
        (res.stdout.strip().splitlines()[-1]) or f"exit {res.returncode}"
    out["changed"] = res.returncode == 0
    return out


def step_rule_checker(dry_run: bool) -> dict:
    """Report-only: surface rule/policy conflicts (never auto-pushes here)."""
    out = {"vaccine": "V-rules", "name": "Rule conflict scan", "matched": False,
           "fixed": False, "changed": False, "detail": ""}
    script = _script("scripts/qa-auto-rule-checker.py")
    if not os.path.isfile(script):
        out["detail"] = "absent"
        return out
    try:
        res = _run([sys.executable, script, "--dry-run"])
    except subprocess.TimeoutExpired:
        out["detail"] = "timeout"
        return out
    out["detail"] = f"exit {res.returncode}"
    return out


SAFE_STEPS = [
    step_build_related_model_id,
    step_internal_links,
    step_build_references,
    step_rule_checker,
]


# --------------------------------------------------------------------------
# QA / build verification
# --------------------------------------------------------------------------
def run_qa() -> dict:
    script = _script("qa_check.py")
    if not os.path.isfile(script):
        return {"name": "qa_check.py", "passed": True, "detail": "absent"}
    try:
        res = _run([sys.executable, script])
    except subprocess.TimeoutExpired:
        return {"name": "qa_check.py", "passed": False, "detail": "timeout"}
    return {"name": "qa_check.py", "passed": res.returncode == 0,
            "detail": (res.stdout or res.stderr or "").strip().splitlines()[-1:] and
            (res.stdout or res.stderr).strip().splitlines()[-1] or f"exit {res.returncode}"}


def run_build(skip: bool) -> dict:
    if skip:
        return {"name": "zola build", "passed": True, "detail": "skipped"}
    from shutil import which
    if which("zola") is None:
        return {"name": "zola build", "passed": True, "detail": "zola not installed (CI builds)"}
    env = dict(os.environ)
    env.setdefault("ZOLA_GH_TOKEN", "dummy")
    try:
        res = subprocess.run(["zola", "build"], cwd=REPO, capture_output=True,
                             text=True, timeout=600, env=env)
    except subprocess.TimeoutExpired:
        return {"name": "zola build", "passed": False, "detail": "timeout"}
    return {"name": "zola build", "passed": res.returncode == 0,
            "detail": (res.stdout or "").strip().splitlines()[-1:] and
            res.stdout.strip().splitlines()[-1] or f"exit {res.returncode}"}


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def log_line(msg: str, keep: int = 500) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    lines = []
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    lines.append(f"{iso(now_ict())}  {msg}")
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines[-keep:]) + "\n")


def run(trigger: str = "manual", dry_run: bool = False, skip_build: bool = False) -> dict:
    now = now_ict()
    vaccines = load_vaccines()
    steps_out = []
    for step in SAFE_STEPS:
        try:
            steps_out.append(step(dry_run))
        except Exception as exc:  # never let one fixer crash the run
            steps_out.append({"vaccine": "?", "name": step.__name__,
                              "matched": False, "fixed": False, "changed": False,
                              "detail": f"error: {exc}"})

    matched = [s for s in steps_out if s.get("matched")]
    fixed_count = sum(1 for s in steps_out if s.get("fixed"))
    # Only an actual fix counts as a code change needing a production deploy;
    # idempotent maintenance regen (e.g. references) does not flip prod status.
    changed = fixed_count > 0

    qa = run_qa()
    build = run_build(skip_build)

    ok = qa["passed"] and build["passed"]
    status = "ok" if ok else "qa-failed"
    if dry_run:
        status = "dry-run"

    finished = now_ict()
    production_status = "up-to-date"
    if changed and not dry_run:
        production_status = "pending-pr"  # workflow opens a PR → deploy on merge

    report = {
        "trigger": trigger,
        "started_at": iso(now),
        "finished_at": iso(finished),
        "last_run": iso(finished),
        "next_scheduled_run": iso(next_scheduled_run(finished)),
        "vaccine_library_count": len(vaccines),
        "steps": steps_out,
        "matched_vaccines": [
            {"code": s.get("vaccine"), "name": s.get("name"),
             "fixed": s.get("fixed", False), "detail": s.get("detail", "")}
            for s in matched
        ],
        "fixed_count": fixed_count,
        "changed": changed,
        "qa_result": qa,
        "build_result": build,
        "production_status": production_status,
        "status": status,
    }
    return report


def save_report(report: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Daily Vaccine Autofixer engine")
    ap.add_argument("--trigger", default="manual", choices=["manual", "schedule"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--release-lock", action="store_true",
                    help="force-clear a stale lock and exit")
    args = ap.parse_args(argv)

    now = now_ict()
    if args.release_lock:
        release_lock(now, "force-released")
        print("🔓 lock released")
        return 0

    if not args.dry_run and not acquire_lock(args.trigger, now):
        print("⏳ Another Vaccine Autofixer run is active — skipping (no concurrent runs).")
        return 3

    try:
        log_line(f"START trigger={args.trigger} dry_run={args.dry_run}")
        report = run(args.trigger, args.dry_run, args.no_build)
        save_report(report)
        log_line(
            f"DONE status={report['status']} matched={len(report['matched_vaccines'])} "
            f"fixed={report['fixed_count']} qa={report['qa_result']['passed']} "
            f"build={report['build_result']['passed']}"
        )
        print(f"✅ Vaccine Autofixer: status={report['status']} · "
              f"matched={len(report['matched_vaccines'])} · fixed={report['fixed_count']}")
        print(f"   report → {os.path.relpath(REPORT_PATH, REPO)}")
        # Non-zero only on real QA/build failure so CI can surface it.
        return 0 if report["status"] in ("ok", "dry-run") else 1
    finally:
        if not args.dry_run:
            release_lock(now_ict(), "finished")


if __name__ == "__main__":
    raise SystemExit(main())
