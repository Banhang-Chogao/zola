"""
Fetch GitHub Actions build history → data/build-dashboard.json.

Dùng GitHub REST API (GITHUB_TOKEN) + phân tích nguyên nhân lỗi tiếng Việt
(rule-based, mở rộng optional AI qua BUILD_DASHBOARD_AI_API_KEY).

Workflows theo dõi (ưu tiên deploy):
  - Build and deploy Zola site to GitHub Pages (deploy.yml)
  - QA Gatekeeper (qa.yml)

Chạy local:
  GITHUB_TOKEN=ghp_... python scripts/fetch_build_dashboard.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "build-dashboard.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"

# Workflow file → tên hiển thị tiếng Việt
WORKFLOW_LABELS: dict[str, str] = {
    "deploy.yml": "Deploy blog lên GitHub Pages",
    "qa.yml": "Kiểm tra QA Gatekeeper",
}

TRACKED_WORKFLOWS = ("deploy.yml", "qa.yml")
MAX_RUNS_PER_WORKFLOW = 15
MAX_TOTAL_BUILDS = 30


def _api_get(path: str) -> Any:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN chưa set — cần token read Actions")
    url = f"{API}{path}"
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zola-build-dashboard",
        },
    )
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"GitHub API {e.code}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"GitHub API unreachable: {e}") from e


def _paginate(path: str, key: str, limit: int) -> list:
    items: list = []
    page = 1
    while len(items) < limit:
        sep = "&" if "?" in path else "?"
        data = _api_get(f"{path}{sep}per_page=30&page={page}")
        batch = data.get(key) or []
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 30:
            break
        page += 1
    return items[:limit]


def _fetch_failed_log_snippet(run_id: int) -> str:
    """Best-effort: gh CLI trong Actions, hoặc job steps qua API."""
    if shutil_which("gh"):
        try:
            out = subprocess.run(
                ["gh", "run", "view", str(run_id), "--log-failed"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if out.stdout:
                return out.stdout[-4000:]
        except (subprocess.TimeoutExpired, OSError):
            pass

    try:
        jobs = _api_get(f"/repos/{REPO}/actions/runs/{run_id}/jobs").get("jobs") or []
        failed_steps: list[str] = []
        for job in jobs:
            if job.get("conclusion") != "failure":
                continue
            for step in job.get("steps") or []:
                if step.get("conclusion") == "failure" and step.get("name"):
                    failed_steps.append(step["name"])
        if failed_steps:
            return "Failed steps: " + "; ".join(failed_steps)
    except RuntimeError:
        pass
    return ""


def shutil_which(cmd: str) -> str | None:
    from shutil import which
    return which(cmd)


# Pattern → mô tả nguyên nhân tiếng Việt (rule-based "AI-lite")
FAILURE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ModuleNotFoundError.*['\"]([^'\"]+)['\"]", re.I),
     "Thiếu thư viện Python `{0}` — cần thêm vào requirements.txt."),
    (re.compile(r"Failed to build the site", re.I),
     "Zola build thất bại — lỗi template, frontmatter hoặc cú pháp Markdown."),
    (re.compile(r"frontmatter|yaml", re.I),
     "Frontmatter YAML không hợp lệ trong file nội dung."),
    (re.compile(r"non-fast-forward|Updates were rejected", re.I),
     "Git push bị từ chối do xung đột commit (race condition trên main)."),
    (re.compile(r"Resource not accessible by integration|permission denied", re.I),
     "Workflow thiếu quyền GitHub Actions — kiểm tra permissions trong YAML."),
    (re.compile(r"exit code 1|exit code 2", re.I),
     "Một bước trong pipeline trả về mã lỗi — xem log chi tiết trên GitHub."),
    (re.compile(r"timeout|timed out", re.I),
     "Bước build/deploy quá thời gian chờ (timeout)."),
    (re.compile(r"ZOLA_GH_TOKEN|rate limit", re.I),
     "Giới hạn GitHub API hoặc token build không đủ quyền."),
    (re.compile(r"error|failed|failure", re.I),
     "Pipeline gặp lỗi — mở log trên GitHub Actions để xem chi tiết."),
]


def analyze_cause_vi(logs: str, conclusion: str | None) -> str:
    if conclusion in ("success", "skipped"):
        return "Không có lỗi — build hoàn tất bình thường."
    if conclusion == "cancelled":
        return "Build bị huỷ thủ công hoặc do concurrency."
    if not logs.strip():
        return "Không lấy được log — kiểm tra trực tiếp trên GitHub Actions."

    for pattern, template in FAILURE_PATTERNS:
        m = pattern.search(logs)
        if m:
            try:
                return template.format(*m.groups())
            except (IndexError, TypeError):
                return template

    # Optional: gọi AI nếu có API key (OpenAI-compatible)
    ai_key = os.environ.get("BUILD_DASHBOARD_AI_API_KEY", "")
    ai_url = os.environ.get(
        "BUILD_DASHBOARD_AI_API_URL",
        "https://api.openai.com/v1/chat/completions",
    )
    if ai_key and len(logs) > 50:
        cause = _ai_analyze_vi(logs[:3000], ai_key, ai_url)
        if cause:
            return cause

    return "Lỗi chưa phân loại — xem log GitHub Actions để chẩn đoán thêm."


def _ai_analyze_vi(log_excerpt: str, api_key: str, api_url: str) -> str:
    """Optional OpenAI-compatible call — chỉ khi secret được cấu hình."""
    payload = {
        "model": os.environ.get("BUILD_DASHBOARD_AI_MODEL", "gpt-4o-mini"),
        "max_tokens": 200,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Bạn là kỹ sư DevOps. Tóm tắt NGUYÊN NHÂN lỗi CI/CD "
                    "trong 1-2 câu tiếng Việt, ngắn gọn, không markdown."
                ),
            },
            {"role": "user", "content": f"Log lỗi GitHub Actions:\n\n{log_excerpt}"},
        ],
    }
    try:
        body = json.dumps(payload).encode("utf-8")
        req = Request(
            api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = (
            (data.get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        return text[:500] if text else ""
    except (HTTPError, URLError, json.JSONDecodeError, KeyError):
        return ""


def summarize_vi(workflow_file: str, run_number: int, commit_msg: str) -> str:
    label = WORKFLOW_LABELS.get(workflow_file, "Chạy workflow CI/CD")
    msg = (commit_msg or "").strip().split("\n")[0][:120]
    if msg:
        return f"Build #{run_number} — {label}: {msg}"
    return f"Build #{run_number} — {label}"


def status_vi(conclusion: str | None) -> tuple[str, bool]:
    if conclusion == "success":
        return "Thành công", True
    if conclusion == "failure":
        return "Thất bại", False
    if conclusion == "cancelled":
        return "Đã huỷ", False
    if conclusion == "skipped":
        return "Bỏ qua", True
    return "Không xác định", False


def _parse_duration(run: dict) -> int | None:
    started = run.get("run_started_at") or run.get("created_at")
    updated = run.get("updated_at")
    if not started or not updated:
        return None
    try:
        t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        return max(0, int((t1 - t0).total_seconds()))
    except ValueError:
        return None


def fetch_builds() -> list[dict]:
    workflows = _paginate(f"/repos/{REPO}/actions/workflows", "workflows", 100)
    by_file = {
        (w.get("path") or "").split("/")[-1]: w
        for w in workflows
        if w.get("path")
    }

    all_builds: list[dict] = []
    owner, name = REPO.split("/", 1)

    for wf_file in TRACKED_WORKFLOWS:
        wf = by_file.get(wf_file)
        if not wf:
            print(f"  skip {wf_file}: workflow not found", file=sys.stderr)
            continue
        wf_id = wf["id"]
        runs = _paginate(
            f"/repos/{REPO}/actions/workflows/{wf_id}/runs?branch=main",
            "workflow_runs",
            MAX_RUNS_PER_WORKFLOW,
        )
        print(f"  {wf_file}: {len(runs)} runs", flush=True)

        for run in runs:
            if run.get("status") != "completed":
                continue
            conclusion = run.get("conclusion")
            run_id = run["id"]
            run_number = run.get("run_number", 0)
            head_sha = (run.get("head_sha") or "")[:40]
            commit_msg = ""
            head = run.get("head_commit") or {}
            if isinstance(head, dict):
                commit_msg = head.get("message") or ""

            logs = ""
            if conclusion == "failure":
                logs = _fetch_failed_log_snippet(run_id)

            status_label, success = status_vi(conclusion)
            cause = analyze_cause_vi(logs, conclusion)

            all_builds.append({
                "id": run_id,
                "run_number": run_number,
                "commit_id": head_sha,
                "commit_short": head_sha[:7] if head_sha else "",
                "commit_url": f"https://github.com/{owner}/{name}/commit/{head_sha}"
                if head_sha else "",
                "run_url": run.get("html_url", ""),
                "workflow": run.get("name") or wf.get("name", ""),
                "workflow_file": wf_file,
                "summary_vi": summarize_vi(wf_file, run_number, commit_msg),
                "status_vi": status_label,
                "success": success,
                "conclusion": conclusion or "unknown",
                "cause_vi": cause,
                "started_at": run.get("run_started_at") or run.get("created_at", ""),
                "duration_sec": _parse_duration(run),
            })

    all_builds.sort(key=lambda b: b.get("started_at") or "", reverse=True)
    return all_builds[:MAX_TOTAL_BUILDS]


def main() -> int:
    print(f"Fetching build dashboard for {REPO}...", flush=True)
    try:
        builds = fetch_builds()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        # Giữ file cũ nếu fetch fail trong CI
        if OUTPUT.exists():
            print("Giữ nguyên build-dashboard.json hiện có.", file=sys.stderr)
            return 0
        return 1

    success_n = sum(1 for b in builds if b.get("success"))
    failure_n = sum(1 for b in builds if b.get("conclusion") == "failure")
    cancelled_n = sum(1 for b in builds if b.get("conclusion") == "cancelled")

    owner, name = REPO.split("/", 1)
    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_repo": f"https://github.com/{owner}/{name}",
        "source_label": "GitHub Actions",
        "stats": {
            "total": len(builds),
            "success": success_n,
            "failure": failure_n,
            "cancelled": cancelled_n,
        },
        "builds": builds,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(builds)} builds → {OUTPUT.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())