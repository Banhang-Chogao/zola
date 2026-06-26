import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["heartbeat"])

REPO = os.getenv("BLOG_HEARTBEAT_REPO", "Banhang-Chogao/zola")
CACHE_TTL = int(os.getenv("BLOG_HEARTBEAT_CACHE_TTL", "60"))
CACHE: dict[str, Any] = {"payload": None, "until": 0.0}


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SEOMONEY-Blog-Heartbeat",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json(url: str) -> Any:
    req = Request(url, headers=github_headers())
    with urlopen(req, timeout=10) as res:
        raw = res.read().decode("utf-8")
    return json.loads(raw)


def run_item(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id") or x.get("databaseId"),
        "title": x.get("display_title") or x.get("displayTitle") or x.get("name") or "Workflow run",
        "workflow": x.get("name") or x.get("workflowName") or "GitHub Actions",
        "branch": x.get("head_branch") or x.get("headBranch") or "",
        "sha": str(x.get("head_sha") or x.get("headSha") or "")[:7],
        "event": x.get("event") or "",
        "status": x.get("status") or "",
        "conclusion": x.get("conclusion") or "",
        "created_at": x.get("created_at") or x.get("createdAt") or "",
        "updated_at": x.get("updated_at") or x.get("updatedAt") or "",
        "url": x.get("html_url") or x.get("url") or "",
    }


def pr_item(x: dict[str, Any]) -> dict[str, Any]:
    head = x.get("head") or {}
    base = x.get("base") or {}
    return {
        "number": x.get("number"),
        "title": x.get("title") or "Pull request",
        "head": head.get("ref") or x.get("headRefName") or "",
        "base": base.get("ref") or x.get("baseRefName") or "",
        "state": x.get("state") or "",
        "draft": bool(x.get("draft") or x.get("isDraft")),
        "merge_state": x.get("mergeable_state") or x.get("mergeStateStatus") or "",
        "created_at": x.get("created_at") or x.get("createdAt") or "",
        "updated_at": x.get("updated_at") or x.get("updatedAt") or "",
        "url": x.get("html_url") or x.get("url") or "",
    }


def summarize(runs: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "in_progress": sum(1 for r in runs if r.get("status") == "in_progress"),
        "queued": sum(1 for r in runs if r.get("status") in {"queued", "waiting", "requested", "pending"}),
        "success": sum(1 for r in runs if r.get("conclusion") == "success"),
        "failure": sum(1 for r in runs if r.get("conclusion") in {"failure", "cancelled", "timed_out", "action_required"}),
    }


def build_payload() -> dict[str, Any]:
    runs_url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=10"
    prs_url = f"https://api.github.com/repos/{REPO}/pulls?state=open&per_page=10"

    runs_data = get_json(runs_url)
    prs_data = get_json(prs_url)

    runs = [run_item(x) for x in runs_data.get("workflow_runs", [])]
    prs = [pr_item(x) for x in prs_data]

    deploy_runs = [
        r for r in runs
        if "deploy" in str(r.get("workflow") or "").lower()
        or "pages" in str(r.get("workflow") or "").lower()
    ]

    return {
        "schema_version": 2,
        "ok": True,
        "source": "render-api",
        "name": "Blog Heart Beat",
        "repository": REPO,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summarize(runs),
        "pull_requests": prs,
        "runs": runs,
        "deploy_runs": deploy_runs,
    }


def error_payload(message: str) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "ok": False,
        "source": "render-api-error",
        "name": "Blog Heart Beat",
        "repository": REPO,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "error": message,
        "summary": {"in_progress": 0, "queued": 0, "success": 0, "failure": 1},
        "pull_requests": [],
        "runs": [],
        "deploy_runs": [],
    }


@router.get("/api/blog-heartbeat")
@router.get("/blog-heartbeat")
def blog_heartbeat(fresh: bool = False) -> JSONResponse:
    now = time.time()

    if not fresh and CACHE.get("payload") and now < float(CACHE.get("until") or 0):
        payload = dict(CACHE["payload"])
        payload["cache_state"] = "warm"
        return JSONResponse(
            payload,
            headers={
                "Cache-Control": "public, max-age=60",
                "Access-Control-Allow-Origin": "*",
            },
        )

    try:
        payload = build_payload()
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        payload = error_payload(str(exc))

    CACHE["payload"] = payload
    CACHE["until"] = now + CACHE_TTL

    return JSONResponse(
        payload,
        headers={
            "Cache-Control": "public, max-age=60",
            "Access-Control-Allow-Origin": "*",
        },
    )
