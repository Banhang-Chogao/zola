"""
Build-failure auto-remediation: analyze failed workflow runs, apply safe fixes,
push fix thẳng main → deploy production.

Trigger: .github/workflows/build-failure-handler.yml khi workflow fail trên main.

Pipeline:
  1. WAIT run status = completed (retry max 5 × 30s).
  2. Fetch logs qua `gh run view --log-failed`.
  3. Đối chiếu log với vaccine rules (scripts/vaccine_rules.py ↔ CLAUDE.md V1–V4).
  4. Apply safe fix nếu match.
  5. Commit → push thẳng main.
  6. QA.yml + deploy chạy lại trên push main.
  7. Unknown / manual-only → tạo GitHub issue.

Run local:
    FAILED_RUN_ID=12345 GITHUB_REPOSITORY=owner/repo python3 qa-failed.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "qa-failed.log"
CLAUDE_MD = ROOT / "CLAUDE.md"

sys.path.insert(0, str(ROOT / "scripts"))
from ai_diagnose import diagnose_tier1, format_markdown  # noqa: E402
from vaccine_rules import VACCINE_RULES, match_vaccine, vaccine_summary  # noqa: E402

MAX_WAIT_ATTEMPTS = 5
WAIT_BACKOFF_SECONDS = 30


def log(msg: str) -> None:
    line = f"[qa-failed] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _github_output(key: str, value: str) -> None:
    out_path = os.environ.get("GITHUB_OUTPUT")
    if not out_path:
        return
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def sh(cmd: list, check: bool = True, capture: bool = True) -> str:
    log(f"$ {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=capture, text=True, check=False)
    out = (res.stdout or "") + (res.stderr or "")
    if check and res.returncode != 0:
        log(f"FAILED (exit {res.returncode}): {out[:500]}")
        raise RuntimeError(f"cmd_failed: {' '.join(cmd)}")
    return out


def sh_rc(cmd: list) -> int:
    log(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=False).returncode


def get_run_status(run_id: str) -> dict:
    try:
        out = sh(["gh", "run", "view", run_id, "--json", "status,conclusion,html_url"],
                 check=False)
        for line in out.strip().splitlines():
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        return json.loads(out.strip().split("\n")[-1])
    except Exception as e:
        log(f"get_run_status error: {e}")
        return {"status": "unknown", "conclusion": None}


def wait_for_completion(run_id: str) -> bool:
    for attempt in range(1, MAX_WAIT_ATTEMPTS + 1):
        info = get_run_status(run_id)
        status = info.get("status", "unknown")
        log(f"poll #{attempt}/{MAX_WAIT_ATTEMPTS} run {run_id}: status={status}")
        if status == "completed":
            return True
        if status == "unknown":
            return False
        if attempt < MAX_WAIT_ATTEMPTS:
            time.sleep(WAIT_BACKOFF_SECONDS)
    return False


def fetch_logs(run_id: str) -> str:
    try:
        return sh(["gh", "run", "view", run_id, "--log-failed"], check=False)
    except Exception as e:
        log(f"fetch_logs error: {e}")
        return ""


def detect_pattern(logs: str) -> dict | None:
    rule = match_vaccine(logs)
    if not rule:
        return None

    pattern: dict = {
        "kind": rule.fixer_kind,
        "vaccine_id": rule.vaccine_id,
        "vaccine_name": rule.name,
        "manual_only": rule.manual_only,
        "rule": rule,
    }

    if rule.fixer_kind == "missing_python_dep":
        m = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", logs)
        if m:
            pattern["module"] = m.group(1)

    if rule.fixer_kind == "frontmatter_issue":
        m2 = re.search(r"(content/[^\s:]+\.md)", logs)
        pattern["file"] = m2.group(1) if m2 else None

    return pattern


def fix_missing_python_dep(module: str) -> bool:
    candidates = [
        ROOT / "services" / "visitor-counter" / "requirements.txt",
        ROOT / "scripts" / "requirements.txt",
    ]
    pinned = {
        "frontmatter": "python-frontmatter==1.1.0",
        "numpy": "numpy==2.1.3",
        "sentence_transformers": "sentence-transformers==3.3.1",
        "httpx": "httpx==0.27.2",
        "redis": "redis==5.2.0",
    }
    line = pinned.get(module, module)
    target = (
        candidates[1]
        if "sentence" in module or "frontmatter" in module
        else candidates[0]
    )
    if not target.exists():
        log(f"target {target} missing, skip")
        return False
    existing = target.read_text(encoding="utf-8")
    if module in existing:
        log(f"{module} already in {target.name}, no fix needed")
        return False
    target.write_text(existing.rstrip() + "\n" + line + "\n", encoding="utf-8")
    log(f"appended {line} → {target.relative_to(ROOT)}")
    return True


def fix_hf_model_org_prefix() -> bool:
    """V1 FIXER — đảm bảo MODEL_NAME có org prefix sentence-transformers/."""
    path = ROOT / "scripts" / "build_related.py"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    full = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    if full in text:
        log("V1: MODEL_NAME đã đúng org prefix")
        return False
    new_text, n = re.subn(
        r'MODEL_NAME\s*=\s*["\']paraphrase-multilingual-MiniLM-L12-v2["\']',
        f'MODEL_NAME = "{full}"',
        text,
    )
    if n == 0:
        return False
    path.write_text(new_text, encoding="utf-8")
    log(f"V1: updated MODEL_NAME → {full}")
    return True


def fix_frontmatter(_target_file: str | None) -> bool:
    qa = ROOT / "qa_check.py"
    if not qa.exists():
        log("qa_check.py missing, cannot safe-fix")
        return False
    sh(["python3", "qa_check.py", "--fix", "safe"], check=False)
    return sh_rc(["git", "diff", "--quiet"]) != 0


def apply_fix(pattern: dict) -> bool:
    kind = pattern["kind"]
    if kind == "missing_python_dep":
        module = pattern.get("module")
        return bool(module and fix_missing_python_dep(module))
    if kind == "hf_model_org_prefix":
        return fix_hf_model_org_prefix()
    if kind == "frontmatter_issue":
        return fix_frontmatter(pattern.get("file"))
    return False


def git_setup() -> None:
    sh(["git", "config", "user.name", "github-actions[bot]"], check=False)
    sh(
        ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        check=False,
    )


def has_changes() -> bool:
    return sh_rc(["git", "diff", "--quiet"]) != 0 or sh_rc(["git", "diff", "--cached", "--quiet"]) != 0


def push_fix_to_main(
    *,
    run_id: str,
    pattern: dict,
) -> bool:
    git_setup()
    sh(["git", "fetch", "origin", "main"], check=False)
    sh(["git", "checkout", "main"], check=False)
    sh(["git", "pull", "--rebase", "origin", "main"], check=False)

    sh(
        [
            "git", "add",
            "content/", "scripts/", "sass/", "templates/", "static/",
            "config.toml", "qa_check.py",
            "services/visitor-counter/requirements.txt",
            "scripts/requirements.txt",
        ],
        check=False,
    )

    if not has_changes():
        log("no staged changes after fix")
        return False

    commit_msg = (
        f"fix(ci): auto-remediation {pattern.get('vaccine_id', '?')} "
        f"— {pattern.get('vaccine_name', pattern['kind'])} (run {run_id}) [skip changelog]"
    )
    sh(["git", "commit", "-m", commit_msg], check=False)
    sh(["git", "push", "origin", "HEAD:main"], check=True)
    log("pushed fix directly to main")
    _github_output("pushed", "true")
    return True


def diagnosis_section(logs: str, run_url: str = "") -> str:
    """Free Tier-1 diagnosis block for issue bodies (no Claude credits)."""
    d = diagnose_tier1(logs)
    return format_markdown(d, run_url=run_url)


def create_issue(title: str, body: str) -> None:
    try:
        sh(
            ["gh", "issue", "create", "--title", title, "--body", body, "--label", "qa-failed"],
            check=False,
        )
    except Exception as e:
        log(f"issue create failed: {e}")


def load_claude_vaccine_refs() -> str:
    if not CLAUDE_MD.exists():
        return ""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    if "THƯ VIỆN VACCINE" not in text:
        return ""
    return "CLAUDE.md vaccine library loaded"


def main() -> int:
    run_id = os.environ.get("FAILED_RUN_ID") or os.environ.get("GITHUB_RUN_ID")
    workflow_name = os.environ.get("FAILED_WORKFLOW_NAME", "?")
    workflow_url = os.environ.get("FAILED_WORKFLOW_URL", "")

    _github_output("pushed", "false")

    if not run_id:
        log("no FAILED_RUN_ID / GITHUB_RUN_ID — exit")
        return 1

    log(f"analyzing failed run {run_id} ({workflow_name})")
    log(load_claude_vaccine_refs() or "CLAUDE.md not found — using vaccine_rules.py only")

    if not wait_for_completion(run_id):
        create_issue(
            f"Build-failure: run {run_id} timeout",
            f"Workflow `{workflow_name}` (run {run_id}) chưa completed sau "
            f"{MAX_WAIT_ATTEMPTS}×{WAIT_BACKOFF_SECONDS}s. Cần investigate manually.",
        )
        return 1

    logs = fetch_logs(run_id)
    if not logs:
        create_issue(
            f"Build-failure: empty logs run {run_id}",
            f"Workflow `{workflow_name}` failed nhưng không fetch được log.",
        )
        return 1

    diag_block = diagnosis_section(logs, workflow_url)

    pattern = detect_pattern(logs)
    if not pattern:
        log("unknown error pattern → escalate")
        create_issue(
            f"Build-failure: unknown error {workflow_name} (run {run_id})",
            diag_block
            + "\n## Vaccine\n\nKhông khớp vaccine auto-fix nào.\n\n"
            "Cần chạy `python3 scripts/ff.py` thủ công (Claude chỉ khi "
            "`AI_DIAGNOSE_USE_CLAUDE=1`) hoặc append vaccine mới.\n\n"
            f"### Log tail\n```\n{logs[-3000:]}\n```",
        )
        return 1

    log(f"matched vaccine {pattern.get('vaccine_id')}: {pattern}")

    if pattern.get("manual_only"):
        create_issue(
            f"Build-failure: {pattern['vaccine_id']} manual fix ({workflow_name})",
            diag_block + "\n" + vaccine_summary(pattern["rule"], logs)
            + f"\nRun: {workflow_url or run_id}\n\n"
            "Pattern chỉ có hướng dẫn thủ công trong CLAUDE.md — không auto-apply.",
        )
        return 1

    if not apply_fix(pattern):
        log("no automatic fix applied")
        create_issue(
            f"Build-failure: {pattern['kind']} chưa fix được (run {run_id})",
            diag_block + "\n" + vaccine_summary(pattern["rule"], logs)
            + "\nDetector khớp nhưng fixer không tạo thay đổi.",
        )
        return 1

    if not has_changes():
        log("fixer ran but no git diff")
        create_issue(
            f"Build-failure: {pattern['kind']} no diff (run {run_id})",
            diag_block + "\nPattern khớp, fixer chạy nhưng không có thay đổi file.",
        )
        return 1

    if push_fix_to_main(run_id=run_id, pattern=pattern):
        log("remediation pushed to main — awaiting CI → deploy")
        return 0

    create_issue(
        f"Build-failure: push to main failed (run {run_id})",
        "Fix đã apply local nhưng không push được lên main. Kiểm tra workflow permissions.",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())