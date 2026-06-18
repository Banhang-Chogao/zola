#!/usr/bin/env python3
"""Auto-merge engine — ZERO_BARRIER.

Tự động squash-merge PR mở vào `main` khi **QA Gatekeeper** (job `qa-check`)
đã xanh và PR mergeable (không conflict). Gọi từ
`.github/workflows/auto-merge.yml`:

- Sự kiện `workflow_run` (QA Gatekeeper completed=success): merge PR của đúng
  head branch vừa pass.
- `workflow_dispatch` (input `pr_number` tùy chọn): merge 1 PR cụ thể, hoặc quét
  toàn bộ PR mở đủ điều kiện nếu bỏ trống.

Chỉ dùng stdlib (`urllib`) + `GITHUB_TOKEN`. Không merge được → comment lý do cụ
thể trên PR (post_skip_comment) theo CLAUDE.md §5b, KHÔNG im lặng.

Chạy tay:
    GITHUB_TOKEN=... GH_REPO=Banhang-Chogao/zola \\
    INPUT_PR=412 EVENT_NAME=workflow_dispatch python3 scripts/try_auto_merge.py
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
POLICY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "auto-merge-policy.json")

MERGE_METHOD = "squash"
MERGEABLE_OK_STATES = {"clean", "unstable", "has_hooks"}
MERGE_RETRY = 6
MERGE_WAIT_S = 5


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


def open_prs_for_branch(branch: str) -> list:
    owner = REPO.split("/")[0]
    st, prs = _req("GET", f"/repos/{REPO}/pulls?state=open&head={owner}:{branch}&per_page=20")
    return prs if isinstance(prs, list) else []


def all_open_prs() -> list:
    st, prs = _req("GET", f"/repos/{REPO}/pulls?state=open&base=main&per_page=100")
    return prs if isinstance(prs, list) else []


def get_pr(num) -> dict | None:
    st, pr = _req("GET", f"/repos/{REPO}/pulls/{num}")
    return pr if st == 200 and isinstance(pr, dict) else None


def qa_passed(sha: str) -> tuple[bool, str]:
    """qa-check (job của QA Gatekeeper) cho head sha đã success?"""
    st, data = _req("GET", f"/repos/{REPO}/commits/{sha}/check-runs?per_page=100")
    runs = data.get("check_runs", []) if isinstance(data, dict) else []
    qa = [r for r in runs if r.get("name") == "qa-check"]
    if not qa:
        return False, "qa-check chưa chạy cho head sha"
    latest = sorted(qa, key=lambda r: r.get("started_at") or "")[-1]
    if latest.get("status") != "completed":
        return False, "qa-check đang chạy"
    if latest.get("conclusion") != "success":
        return False, f"qa-check kết luận: {latest.get('conclusion')}"
    return True, "qa-check success"


def post_skip_comment(num: int, reason: str) -> None:
    body = (
        f"🤖 **Auto-merge tạm hoãn** — {reason}.\n\n"
        "Workflow sẽ thử lại ở lần QA Gatekeeper xanh tiếp theo. "
        "Nếu do conflict, vui lòng rebase branch lên `main`."
    )
    _req("POST", f"/repos/{REPO}/issues/{num}/comments", {"body": body})


def is_eligible(pr: dict, policy: dict) -> tuple[bool, str]:
    if pr.get("draft"):
        return False, "PR là draft"
    if pr.get("state") != "open":
        return False, "PR không mở"
    if pr.get("base", {}).get("ref") != "main":
        return False, "base không phải main"
    labels = {l.get("name") for l in pr.get("labels", []) if isinstance(l, dict)}
    blocked = set(policy.get("blocked_labels", []))
    hit = labels & blocked
    if hit:
        return False, f"có label chặn: {', '.join(sorted(hit))}"
    return True, "đủ điều kiện"


def try_merge(num: int) -> tuple[bool, str]:
    """Poll mergeable (GitHub tính async) rồi squash-merge."""
    state = "unknown"
    for _ in range(MERGE_RETRY):
        pr = get_pr(num)
        if not pr:
            return False, "không lấy được PR"
        if pr.get("merged"):
            return True, "đã merged"
        state = pr.get("mergeable_state")
        mergeable = pr.get("mergeable")
        if state == "dirty":
            return False, "conflict với main (mergeable_state=dirty)"
        if mergeable is True and state in MERGEABLE_OK_STATES:
            sha = pr["head"]["sha"]
            st, res = _req(
                "PUT",
                f"/repos/{REPO}/pulls/{num}/merge",
                {"merge_method": MERGE_METHOD, "sha": sha},
            )
            if st == 200 and res.get("merged"):
                return True, "merged (squash)"
            if st in (405, 409):
                return False, f"merge bị từ chối ({st}): {res.get('message')}"
            time.sleep(MERGE_WAIT_S)  # 422/5xx tạm thời → thử lại
            continue
        time.sleep(MERGE_WAIT_S)  # mergeable=None → đang tính
    return False, f"chưa mergeable sau khi chờ (state={state})"


def main() -> int:
    if not REPO or not TOKEN:
        print("[auto-merge] thiếu GH_REPO / GITHUB_TOKEN — thoát")
        return 0

    policy = load_policy()
    event = os.environ.get("EVENT_NAME", "")
    input_pr = os.environ.get("INPUT_PR", "").strip()

    if input_pr:
        pr = get_pr(input_pr)
        candidates = [pr] if pr else []
    elif event == "workflow_run":
        branch = os.environ.get("WR_HEAD_BRANCH", "").strip()
        candidates = open_prs_for_branch(branch) if branch and branch != "main" else []
    else:
        candidates = all_open_prs()

    if not candidates:
        print("[auto-merge] không có PR ứng viên.")
        return 0

    for pr in candidates:
        num = pr.get("number")
        ok, reason = is_eligible(pr, policy)
        if not ok:
            print(f"[auto-merge] PR #{num}: bỏ qua — {reason}")
            continue
        passed, qreason = qa_passed(pr["head"]["sha"])
        if not passed:
            print(f"[auto-merge] PR #{num}: chưa merge — {qreason}")
            continue
        merged, mreason = try_merge(num)
        print(f"[auto-merge] PR #{num}: {'✅ ' if merged else '⏭️ '}{mreason}")
        if not merged and "conflict" in mreason:
            post_skip_comment(num, mreason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
