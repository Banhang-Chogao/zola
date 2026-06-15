"""
QA-Failed pipeline: auto-analyze failed workflow runs, attempt safe fixes.

Trigger: .github/workflows/qa-failed-handler.yml chạy khi 1 workflow nào
khác fail. Script này:

1. WAIT cho run status = "completed" (retry max 5 lần, 30s/lần).
2. Fetch logs qua `gh run view --log-failed` chỉ KHI status completed.
3. Parse stderr tìm error pattern đã biết.
4. Apply safe fix nếu match pattern:
   - ModuleNotFoundError → append module vào requirements.txt liên quan
   - frontmatter YAML invalid → chạy qa_check.py --fix safe
   - git push rejected non-fast-forward → no-op (chỉ log, không tự force push)
   - GitHub Actions permission denied → log + notify (cần repo settings)
5. Apply được → commit + push lên main → trigger deploy lại.
6. KHÔNG match pattern → tạo GitHub issue chi tiết + exit 1.

CONSERVATIVE: Script chỉ fix khi 100% chắc. Lỗi chưa biết → escalate.

Run local (debug):
    GITHUB_RUN_ID=12345 GITHUB_REPOSITORY=owner/repo python qa-failed.py
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "qa-failed.log"

# Retry config — đợi run state "completed" trước khi fetch logs
MAX_WAIT_ATTEMPTS = 5
WAIT_BACKOFF_SECONDS = 30  # 5 × 30s = 2.5 phút max


def log(msg: str) -> None:
    line = f"[qa-failed] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(cmd: list, check: bool = True, capture: bool = True) -> str:
    log(f"$ {' '.join(cmd)}")
    res = subprocess.run(
        cmd, capture_output=capture, text=True, check=False
    )
    out = (res.stdout or "") + (res.stderr or "")
    if check and res.returncode != 0:
        log(f"FAILED (exit {res.returncode}): {out[:500]}")
        raise RuntimeError(f"cmd_failed: {' '.join(cmd)}")
    return out


def get_run_status(run_id: str) -> dict:
    """Return {status, conclusion}. status in {queued, in_progress, completed}.
    conclusion in {success, failure, cancelled, ...} chỉ valid khi completed."""
    try:
        out = sh(["gh", "run", "view", run_id, "--json", "status,conclusion"],
                 check=False)
        return json.loads(out.strip().split("\n")[-1])
    except Exception as e:
        log(f"get_run_status error: {e}")
        return {"status": "unknown", "conclusion": None}


def wait_for_completion(run_id: str) -> bool:
    """Poll run status đến khi completed. Return True nếu hoàn tất trong
    timeout, False nếu vẫn in_progress sau MAX_WAIT_ATTEMPTS."""
    for attempt in range(1, MAX_WAIT_ATTEMPTS + 1):
        info = get_run_status(run_id)
        status = info.get("status", "unknown")
        log(f"poll #{attempt}/{MAX_WAIT_ATTEMPTS} run {run_id}: status={status}")
        if status == "completed":
            return True
        if status == "unknown":
            # gh CLI lỗi — return False để escalate
            return False
        if attempt < MAX_WAIT_ATTEMPTS:
            time.sleep(WAIT_BACKOFF_SECONDS)
    return False


def fetch_logs(run_id: str) -> str:
    """Fetch logs failed jobs. CHỈ gọi sau khi wait_for_completion=True
    để tránh 'still in progress' error."""
    try:
        return sh(["gh", "run", "view", run_id, "--log-failed"], check=False)
    except Exception as e:
        log(f"fetch_logs error: {e}")
        return ""


def detect_pattern(logs: str) -> dict | None:
    # 1. Python ModuleNotFoundError
    m = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", logs)
    if m:
        return {"kind": "missing_python_dep", "module": m.group(1)}

    # 2. Zola build error (frontmatter / template syntax)
    if "Failed to build the site" in logs or "frontmatter" in logs.lower():
        m2 = re.search(r"(content/posting/[^\s:]+\.md)", logs)
        return {"kind": "frontmatter_issue", "file": m2.group(1) if m2 else None}

    # 3. Git push non-fast-forward → likely race condition, không tự fix
    if "non-fast-forward" in logs or "Updates were rejected" in logs:
        return {"kind": "git_race", "fix": "manual"}

    # 4. Workflow permissions error
    if "Resource not accessible by integration" in logs or "permission denied" in logs.lower():
        return {"kind": "workflow_permission", "fix": "manual"}

    return None


def fix_missing_python_dep(module: str) -> bool:
    # Map module → likely requirements file (heuristic)
    candidates = [
        ROOT / "services" / "visitor-counter" / "requirements.txt",
        ROOT / "scripts" / "requirements.txt",
    ]
    # Map common runtime modules to known versions (extend as needed)
    pinned = {
        "frontmatter": "python-frontmatter==1.1.0",
        "numpy": "numpy==2.1.3",
        "sentence_transformers": "sentence-transformers==3.3.1",
        "httpx": "httpx==0.27.2",
        "redis": "redis==5.2.0",
    }
    line = pinned.get(module, module)
    target = candidates[1] if "sentence" in module or "frontmatter" in module else candidates[0]
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


def fix_frontmatter(target_file: str | None) -> bool:
    qa = ROOT / "qa_check.py"
    if not qa.exists():
        log("qa_check.py missing, cannot safe-fix")
        return False
    sh(["python3", "qa_check.py", "--fix", "safe"], check=False)
    res = sh(["git", "diff", "--quiet"], check=False)
    if res.strip() == "":
        return True
    return False


def git_commit_push(message: str) -> bool:
    sh(["git", "config", "user.name", "github-actions[bot]"], check=False)
    sh(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=False)
    diff = sh(["git", "status", "--porcelain"], check=False)
    if not diff.strip():
        log("no changes to commit")
        return False
    sh(["git", "add", "-A"], check=False)
    sh(["git", "commit", "-m", message], check=False)
    try:
        sh(["git", "push", "origin", "HEAD:main"], check=True)
        return True
    except Exception as e:
        log(f"push failed: {e}")
        return False


def create_issue(title: str, body: str) -> None:
    try:
        sh(["gh", "issue", "create", "--title", title, "--body", body, "--label", "qa-failed"],
           check=False)
    except Exception as e:
        log(f"issue create failed: {e}")


def main() -> int:
    run_id = os.environ.get("GITHUB_RUN_ID") or os.environ.get("FAILED_RUN_ID")
    workflow_name = os.environ.get("FAILED_WORKFLOW_NAME", "?")
    if not run_id:
        log("no GITHUB_RUN_ID / FAILED_RUN_ID — exit")
        return 1

    log(f"analyzing failed run {run_id} ({workflow_name})")

    # WAIT: GitHub Actions có lag giữa "fail event triggered" và "logs ready".
    # Nếu fetch quá sớm → 'still in progress' error → classify nhầm unknown.
    if not wait_for_completion(run_id):
        log(f"run {run_id} vẫn chưa completed sau {MAX_WAIT_ATTEMPTS * WAIT_BACKOFF_SECONDS}s → escalate")
        create_issue(
            f"QA-Failed: run {run_id} không kết thúc trong timeout",
            f"Workflow `{workflow_name}` (run {run_id}) vẫn ở status in_progress / unknown "
            f"sau {MAX_WAIT_ATTEMPTS} lần poll × {WAIT_BACKOFF_SECONDS}s. "
            f"Có thể: 1) job hung/timeout, 2) gh CLI auth lỗi, 3) GitHub API lag bất thường. "
            f"Cần investigate manually."
        )
        return 1

    logs = fetch_logs(run_id)
    if not logs:
        log("empty logs, cannot analyze")
        create_issue(
            f"QA-Failed: empty logs cho run {run_id}",
            f"Workflow `{workflow_name}` failed nhưng logs không fetch được dù status=completed. Cần investigate manually."
        )
        return 1

    pattern = detect_pattern(logs)
    if not pattern:
        log("unknown error pattern → escalate")
        snippet = logs[-3000:]
        create_issue(
            f"QA-Failed: unknown error in {workflow_name} (run {run_id})",
            f"## Auto-detect failed\n\nKhông match pattern fix nào đã biết. Cần manual review.\n\n### Log tail (last 3000 chars)\n```\n{snippet}\n```"
        )
        return 1

    log(f"detected pattern: {pattern}")

    if pattern["kind"] == "missing_python_dep":
        if fix_missing_python_dep(pattern["module"]):
            if git_commit_push(f"Self-healing: thêm dep '{pattern['module']}' (qa-failed run {run_id})"):
                log("✓ fixed + pushed → deploy sẽ tự re-trigger")
                return 0

    elif pattern["kind"] == "frontmatter_issue":
        if fix_frontmatter(pattern.get("file")):
            if git_commit_push(f"Self-healing: fix frontmatter (qa-failed run {run_id})"):
                log("✓ fixed + pushed")
                return 0

    elif pattern["kind"] in ("git_race", "workflow_permission"):
        log(f"pattern {pattern['kind']} cần manual fix → escalate")
        create_issue(
            f"QA-Failed: {pattern['kind']} in {workflow_name}",
            f"Pattern `{pattern['kind']}` không tự fix được. Run {run_id}.\n\nXem `fix: manual` field trong detect_pattern() để biết steps."
        )
        return 1

    log("fix not applied / push failed → escalate")
    create_issue(
        f"QA-Failed: {pattern['kind']} chưa fix được (run {run_id})",
        f"Detected pattern `{pattern['kind']}` nhưng auto-fix không thành công. Cần investigate."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
