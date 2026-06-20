#!/usr/bin/env python3
"""ensure_pr_after_push — ZERO_BARRIER "Done means PR opened".

Sau MỖI lần push lên feature branch (`claude/**`, `codex/**`, `vaccine-hotfix/**`,
hay bất kỳ prefix auto-eligible nào), script này đảm bảo branch ấy LUÔN có một
Pull Request mở vào `main`. "Push xong branch" mà KHÔNG có PR là việc dở dang —
QA → auto-merge → deploy không thể tiếp tục (CLAUDE.md "Quy tắc hoàn thành task").

Hành vi:
  1. Resolve branch (env BRANCH / GITHUB_REF_NAME / git rev-parse). Bỏ qua `main`.
  2. Branch không thuộc prefix auto-eligible → bỏ qua (trừ khi --force).
  3. PR đã mở cho branch → REUSE (cập nhật title/body), KHÔNG tạo trùng.
  4. Chưa có → tạo PR mới target `main`, title rõ ràng + body gồm:
       summary · changed files · QA/build status · rollback note.
  5. Preflight conflict: mergeable_state == dirty → comment cảnh báo conflict
     (gợi ý vaccine V10/`ff9`/autofix_conflicts), KHÔNG merge.
  6. --enable-auto-merge: nếu qa-check XANH → DELEGATE cho try_auto_merge (gated
     merge, không bypass QA). QA đỏ → comment failed checks + next fix action,
     KHÔNG merge. QA đang chạy → để auto-merge.yml (cron 5') lo.

Chỉ dùng stdlib (`urllib`) + `GITHUB_TOKEN`. Không force-push, không merge PR đỏ,
không tạo PR trùng. Reuse pipeline auto-merge sẵn có (try_auto_merge.py).

Chạy tay:
    GITHUB_TOKEN=... GH_REPO=Banhang-Chogao/zola \\
    BRANCH=claude/foo python3 scripts/ensure_pr_after_push.py --enable-auto-merge
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", "")
POLICY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "auto-merge-policy.json")

BASE_BRANCH = "main"
# Prefixes mà ZERO_BARRIER tự động mở PR cho. Đồng bộ với
# data/auto-merge-policy.json → auto_eligible_branch_prefixes.
DEFAULT_PREFIXES = (
    "claude/",
    "codex/",
    "vaccine-hotfix/",
    "fix/",
    "feature/",
    "chore/",
    "content/",
    "qa/",
    "autofix/",
    "policy/",
)
MERGEABLE_POLL = 6
MERGEABLE_WAIT_S = 4


# --------------------------------------------------------------------------- #
# GitHub REST helpers
# --------------------------------------------------------------------------- #
def _req(method: str, path: str, data: dict | None = None):
    """Gọi GitHub REST API. Trả (status_code, payload)."""
    url = path if path.startswith("http") else f"{API}{path}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"message": raw}
        return e.code, payload
    except Exception as e:  # network/timeout — coi như tạm thời
        return 0, {"message": str(e)}


def load_policy() -> dict:
    try:
        with open(POLICY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# Pure helpers (no network — unit-tested)
# --------------------------------------------------------------------------- #
def resolve_branch() -> str:
    """Lấy branch hiện tại từ env hoặc git, ưu tiên override rõ ràng."""
    for key in ("BRANCH", "GITHUB_HEAD_REF", "WR_HEAD_BRANCH"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    ref = (os.environ.get("GITHUB_REF_NAME") or "").strip()
    if ref:
        return ref
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return ""


def eligible_prefixes(policy: dict) -> tuple[str, ...]:
    prefixes = policy.get("auto_eligible_branch_prefixes")
    if isinstance(prefixes, list) and prefixes:
        merged = set(str(p) for p in prefixes) | set(DEFAULT_PREFIXES)
        return tuple(sorted(merged))
    return DEFAULT_PREFIXES


def branch_eligible(branch: str, policy: dict, force: bool = False) -> tuple[bool, str]:
    """Có nên tự mở PR cho branch này không?"""
    if not branch:
        return False, "không xác định được branch"
    if branch == BASE_BRANCH:
        return False, "branch là main — không mở PR"
    if force:
        return True, "force"
    for p in eligible_prefixes(policy):
        if branch.startswith(p):
            return True, f"khớp prefix '{p}'"
    return False, f"branch '{branch}' không thuộc prefix auto-eligible"


def task_name_from_branch(branch: str) -> str:
    """Phần task name (sau prefix) để đưa vào title."""
    if "/" in branch:
        return branch.split("/", 1)[1]
    return branch


def build_pr_title(branch: str, commit_subject: str = "") -> str:
    """Title rõ ràng gồm branch/task name."""
    subj = (commit_subject or "").strip().splitlines()[0] if commit_subject else ""
    task = task_name_from_branch(branch)
    if subj:
        # Tránh lặp nếu subject đã chứa task slug.
        return f"{subj} [{branch}]"
    return f"chore: {task} [{branch}]"


def _fmt_files(files: list) -> str:
    if not files:
        return "_(không phát hiện file thay đổi qua compare API)_"
    lines = []
    for f in files[:50]:
        name = f.get("filename", "?")
        add = f.get("additions", 0)
        rem = f.get("deletions", 0)
        status = f.get("status", "")
        lines.append(f"- `{name}` ({status}, +{add}/-{rem})")
    if len(files) > 50:
        lines.append(f"- … và {len(files) - 50} file khác")
    return "\n".join(lines)


def build_pr_body(
    branch: str,
    summary: str,
    files: list,
    qa_status: str,
    qa_detail: str = "",
) -> str:
    """Body PR: summary · changed files · QA/build status · rollback note."""
    qa_icon = {
        "success": "✅ green",
        "pending": "🟡 đang chạy",
        "failure": "❌ failed",
        "missing": "⏳ chưa chạy",
    }.get(qa_status, qa_status)
    files_block = _fmt_files(files)
    detail = f" — {qa_detail}" if qa_detail else ""
    return (
        f"## Summary\n{summary or 'Tự động mở bởi ensure_pr_after_push (ZERO_BARRIER).'}\n\n"
        f"## Changed files ({len(files)})\n{files_block}\n\n"
        f"## QA / Build status\n"
        f"- **QA Gatekeeper (qa-check):** {qa_icon}{detail}\n"
        f"- Auto-merge chỉ chạy khi qa-check **xanh** (gated qua `try_auto_merge.py`).\n\n"
        f"## Rollback note\n"
        f"- Squash-merge → 1 commit duy nhất trên `main`; revert bằng "
        f"`git revert <merge_sha>` rồi push qua PR là rollback hoàn toàn.\n"
        f"- Chưa merge: đóng PR + xoá branch `{branch}` là đủ (không ảnh hưởng `main`).\n\n"
        f"---\n"
        f"🤖 Mở/cập nhật tự động bởi `ensure_pr_after_push.py` — "
        f"\"Done means: branch pushed + PR opened + QA green + auto-merge attempted.\"\n"
    )


def summarize_commits(commits: list) -> str:
    """Tổng hợp summary từ commit subjects (compare API)."""
    if not commits:
        return ""
    subjects = []
    for c in commits[-10:]:
        msg = ((c.get("commit") or {}).get("message") or "").strip()
        if msg:
            subjects.append(msg.splitlines()[0])
    if not subjects:
        return ""
    if len(subjects) == 1:
        return subjects[0]
    return "\n".join(f"- {s}" for s in subjects)


# --------------------------------------------------------------------------- #
# Network operations
# --------------------------------------------------------------------------- #
def open_pr_for_branch(branch: str) -> dict | None:
    owner = REPO.split("/")[0]
    st, prs = _req(
        "GET", f"/repos/{REPO}/pulls?state=open&head={owner}:{branch}&per_page=20"
    )
    if isinstance(prs, list) and prs:
        return prs[0]
    return None


def compare_main(branch: str) -> tuple[list, list]:
    """Trả (files, commits) giữa main..branch qua compare API."""
    st, data = _req("GET", f"/repos/{REPO}/compare/{BASE_BRANCH}...{branch}")
    if st == 200 and isinstance(data, dict):
        return data.get("files", []) or [], data.get("commits", []) or []
    return [], []


def qa_status_for(sha: str) -> tuple[str, str]:
    """Trạng thái qa-check cho head sha: success/pending/failure/missing."""
    st, data = _req("GET", f"/repos/{REPO}/commits/{sha}/check-runs?per_page=100")
    runs = data.get("check_runs", []) if isinstance(data, dict) else []
    qa = [r for r in runs if r.get("name") == "qa-check"]
    if not qa:
        return "missing", "qa-check chưa chạy cho head sha"
    latest = sorted(qa, key=lambda r: r.get("started_at") or "")[-1]
    if latest.get("status") != "completed":
        return "pending", "qa-check đang chạy"
    concl = latest.get("conclusion")
    if concl == "success":
        return "success", "qa-check success"
    return "failure", f"qa-check kết luận: {concl}"


def create_pr(branch: str, title: str, body: str) -> dict | None:
    st, pr = _req(
        "POST",
        f"/repos/{REPO}/pulls",
        {"title": title, "head": branch, "base": BASE_BRANCH, "body": body},
    )
    if st in (200, 201) and isinstance(pr, dict) and pr.get("number"):
        return pr
    print(f"[ensure-pr] tạo PR thất bại ({st}): {pr.get('message')}")
    return None


def update_pr(num: int, title: str, body: str) -> None:
    _req("PATCH", f"/repos/{REPO}/pulls/{num}", {"title": title, "body": body})


def post_comment(num: int, body: str) -> None:
    _req("POST", f"/repos/{REPO}/issues/{num}/comments", {"body": body})


def mergeable_state(num: int) -> tuple[str | None, dict]:
    """Poll mergeable_state (GitHub tính async)."""
    state = None
    pr: dict = {}
    for _ in range(MERGEABLE_POLL):
        st, pr = _req("GET", f"/repos/{REPO}/pulls/{num}")
        if st != 200 or not isinstance(pr, dict):
            return None, {}
        state = pr.get("mergeable_state")
        if pr.get("mergeable") is not None and state not in (None, "unknown"):
            return state, pr
        time.sleep(MERGEABLE_WAIT_S)
    return state, pr


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Ensure a PR exists after pushing a branch.")
    ap.add_argument("--branch", help="Branch (mặc định: env/git).")
    ap.add_argument("--force", action="store_true", help="Bỏ qua kiểm tra prefix.")
    ap.add_argument(
        "--enable-auto-merge",
        action="store_true",
        help="Khi qa-check xanh → delegate merge cho try_auto_merge.py (gated).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Không gọi API ghi.")
    args = ap.parse_args()

    if not REPO or not TOKEN:
        print("[ensure-pr] thiếu GH_REPO / GITHUB_TOKEN — thoát")
        return 0

    policy = load_policy()
    branch = (args.branch or resolve_branch()).strip()
    ok, reason = branch_eligible(branch, policy, force=args.force)
    if not ok:
        print(f"[ensure-pr] bỏ qua: {reason}")
        return 0

    files, commits = compare_main(branch)
    if not commits and not files:
        # Branch chưa có gì khác main → không cần PR.
        print(f"[ensure-pr] branch '{branch}' không có thay đổi so với main — bỏ qua")
        return 0

    summary = summarize_commits(commits)
    subject = ""
    if commits:
        subject = ((commits[-1].get("commit") or {}).get("message") or "").strip()
    head_sha = commits[-1].get("sha") if commits else ""
    qa_state, qa_detail = qa_status_for(head_sha) if head_sha else ("missing", "")

    title = build_pr_title(branch, subject)
    body = build_pr_body(branch, summary, files, qa_state, qa_detail)

    existing = open_pr_for_branch(branch)
    if args.dry_run:
        action = "cập nhật" if existing else "tạo"
        print(f"[ensure-pr] (dry-run) sẽ {action} PR cho '{branch}'")
        print(f"  title: {title}")
        print(f"  qa: {qa_state} ({qa_detail})")
        return 0

    if existing:
        num = existing["number"]
        update_pr(num, title, body)
        print(f"[ensure-pr] reuse PR #{num} cho '{branch}' (đã cập nhật title/body)")
        pr = existing
    else:
        pr = create_pr(branch, title, body)
        if not pr:
            print("::warning::ensure-pr: không mở được PR — kiểm tra quyền pull-requests:write")
            return 0
        num = pr["number"]
        print(f"[ensure-pr] đã mở PR #{num}: {pr.get('html_url')}")

    # Preflight conflict check.
    state, pr_full = mergeable_state(num)
    if state == "dirty":
        post_comment(
            num,
            "⚠️ **Preflight conflict** — branch xung đột với `main` "
            "(`mergeable_state=dirty`). Auto-merge tạm hoãn.\n\n"
            "Cách xử lý (CLAUDE.md V10/V12): merge `origin/main` vào branch → resolve "
            "(data `*.json` lấy `main` rồi regenerate; registry giữ cả 2 bên) → "
            "`python3 qa_check.py` → push. Hoặc chạy "
            "`python3 scripts/autofix_conflicts.py --branch " + branch + "`.",
        )
        print(f"[ensure-pr] PR #{num}: conflict với main — KHÔNG merge (đã comment)")
        return 0

    if not args.enable_auto_merge:
        print(f"[ensure-pr] PR #{num}: để auto-merge.yml (cron) lo phần merge")
        return 0

    # Gated auto-merge: chỉ khi qa-check xanh, DELEGATE cho try_auto_merge (no bypass).
    if qa_state == "success":
        try:
            import try_auto_merge as tam  # type: ignore
        except Exception:
            import importlib.util
            import sys

            spec = importlib.util.spec_from_file_location(
                "try_auto_merge", os.path.join(os.path.dirname(__file__), "try_auto_merge.py")
            )
            tam = importlib.util.module_from_spec(spec)  # type: ignore
            sys.modules["try_auto_merge"] = tam
            spec.loader.exec_module(tam)  # type: ignore
        merged, mreason = tam.try_merge(num)
        print(f"[ensure-pr] PR #{num}: {'✅ ' if merged else '⏭️ '}{mreason}")
    elif qa_state == "failure":
        post_comment(
            num,
            "❌ **QA Gatekeeper đỏ** — auto-merge bị chặn (không bypass QA).\n\n"
            f"Chi tiết: {qa_detail}\n\n"
            "**Next fix action:** đọc log `qa-check`, đối chiếu §4 Vaccine library "
            "(CLAUDE.md). Lỗi build/Tera/link → `ff` hoặc `vacxin11`; conflict data "
            "`*.json` → `ff9`. Fix trên CÙNG branch, push lại → CI tự chạy lại.",
        )
        print(f"[ensure-pr] PR #{num}: qa-check failed — đã comment next fix action")
    else:
        print(f"[ensure-pr] PR #{num}: qa-check {qa_state} — chờ CI, auto-merge.yml sẽ merge khi xanh")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
