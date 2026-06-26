"""CMS repo-write routes (save-post / bulk-delete / categories) for the VIPZone API.

These endpoints originally lived in ``services/visitor-counter/main.py`` (the
Redis-backed counter service). The blog editor (`static/js/editor.js`) and the
deployed Render backend, however, point at THIS service (``blog-vipzone-api`` →
``services/vipzone``). After PR #588 the editor stopped doing draft-only file
downloads and started ``POST {AUTH_API}/cms/save-post`` — but that route never
existed on the deployed vipzone app, so every save/edit/sticky returned
``404 {"detail":"Not Found"}``.

This module re-serves the CMS write surface HERE, mirroring the same pattern PR
#594 used to port ``/gsc/*`` onto vipzone. Logic (GitHub Contents API helpers,
featured/sticky single-active auto-demote, category ensure) is a faithful port of
the visitor-counter implementation. Auth differs only in HOW the GitHub token is
obtained: instead of a Redis session it is injected via :func:`configure` from the
vipzone CMS session payload (see ``cms_auth.github_token_from_session``).
"""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Awaitable, Callable, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter()

# Token getter injected by configure(): async (authorization) -> github_access_token.
# Raises HTTPException(401) when the session is missing / has no token.
_get_token: Optional[Callable[[str], Awaitable[str]]] = None


def configure(get_token: Callable[[str], Awaitable[str]]) -> None:
    """Wire the GitHub-token resolver from the host app (vipzone main.py)."""
    global _get_token
    _get_token = get_token


async def _token(authorization: str) -> str:
    if _get_token is None:  # pragma: no cover - defensive: configure() always called
        raise HTTPException(503, "cms_repo_not_configured")
    return await _get_token(authorization)


# ============= CMS — Publish Post to GitHub =============
CMS_REPO_OWNER  = os.getenv("CMS_REPO_OWNER",  "Banhang-Chogao")
CMS_REPO_NAME   = os.getenv("CMS_REPO_NAME",   "zola")
CMS_REPO_BRANCH = os.getenv("CMS_REPO_BRANCH", "main")
# Fixed path so a user can never write outside the content dir (defense-in-depth;
# the slug regex already blocks '../').
CMS_CONTENT_DIR = "content/posting"
CMS_CATEGORIES_PATH = "categories.json"

# Valid slug: a-z + 0-9 + dash, 2-80 chars. Matches the Zola slug pattern.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
_CATEGORY_RE = re.compile(r"^[\wÀ-ſḀ-ỿ\s\-+&()]{1,100}$", re.UNICODE)

_CATEGORY_FRONTMATTER_RE = re.compile(
    r'\[taxonomies\][^\[]*?categories\s*=\s*\[\s*"([^"]+)"',
    re.DOTALL,
)
_EXTRA_BLOCK_RE = re.compile(r"(?ms)^(\[extra\]\s*\n)(.*?)(?=^\[|\Z)")
_FEATURED_TRUE_RE = re.compile(r"(?m)^featured\s*=\s*true\s*$")
_FEATURED_LINE_RE = re.compile(r"(?m)^featured\s*=\s*true\s*\n?")
_FEATURED_AT_LINE_RE = re.compile(r'(?m)^featured_at\s*=\s*"[^"]*"\s*\n?')
# Sticky (ghim) — only ONE post may be sticky at a time. Saving a sticky post
# auto-clears sticky on every other post (mirrors featured semantics).
_STICKY_TRUE_RE = re.compile(r"(?m)^sticky\s*=\s*true\s*$")
_STICKY_LINE_RE = re.compile(r"(?m)^sticky\s*=\s*true\s*\n?")


def _gh_headers(token: str) -> dict:
    return {
        "Authorization":        f"Bearer {token}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent":           "zola-cms",
    }


# ============= Helpers GitHub Contents API =============
async def _gh_get_file(client: httpx.AsyncClient, path: str, token: str) -> tuple:
    """GET file content. Return (sha, decoded_text) or (None, None) on 404."""
    res = await client.get(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        params={"ref": CMS_REPO_BRANCH},
        headers=_gh_headers(token),
    )
    if res.status_code == 404:
        return None, None
    if res.status_code != 200:
        raise HTTPException(502, f"github_read_failed_{res.status_code}")
    data = res.json()
    try:
        decoded = base64.b64decode(data.get("content", "")).decode("utf-8")
    except Exception:
        decoded = ""
    return data.get("sha"), decoded


async def _gh_list_dir(client: httpx.AsyncClient, path: str, token: str) -> list:
    """GET directory listing. Return [] if the directory is missing."""
    res = await client.get(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        params={"ref": CMS_REPO_BRANCH},
        headers=_gh_headers(token),
    )
    if res.status_code == 404:
        return []
    if res.status_code != 200:
        raise HTTPException(502, f"github_read_failed_{res.status_code}")
    data = res.json()
    return data if isinstance(data, list) else []


async def _gh_put_file(client: httpx.AsyncClient, path: str, content: str,
                       sha: Optional[str], message: str, token: str) -> dict:
    """PUT (create/update) a text file via the Contents API."""
    payload = {
        "message": message[:200],
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch":  CMS_REPO_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    res = await client.put(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        headers=_gh_headers(token),
        json=payload,
    )
    if res.status_code not in (200, 201):
        err = {}
        try:
            err = res.json()
        except json.JSONDecodeError:
            pass
        raise HTTPException(
            res.status_code if res.status_code in (403, 422) else 502,
            f"github_api: {err.get('message', 'error')}",
        )
    return res.json()


async def _load_categories(client: httpx.AsyncClient, token: str) -> tuple:
    """Load categories.json from the repo. Default ['Posting'] if missing/corrupt."""
    sha, text = await _gh_get_file(client, CMS_CATEGORIES_PATH, token)
    if not text:
        return sha, ["Posting"]
    try:
        data = json.loads(text)
        cats = data.get("categories", []) if isinstance(data, dict) else []
        cats = [c.strip() for c in cats if isinstance(c, str) and c.strip()]
        return sha, cats or ["Posting"]
    except json.JSONDecodeError:
        return sha, ["Posting"]


async def _ensure_category(client: httpx.AsyncClient, name: str, token: str) -> None:
    """Best-effort: append a new category to categories.json. Never raises."""
    if not name or not _CATEGORY_RE.match(name):
        return
    try:
        sha, cats = await _load_categories(client, token)
        if name in cats:
            return
        cats.append(name)
        new_text = json.dumps({"categories": cats}, ensure_ascii=False, indent=2) + "\n"
        await _gh_put_file(client, CMS_CATEGORIES_PATH, new_text, sha,
                           f"CMS: auto-add category '{name}'", token)
    except HTTPException:
        return
    except Exception:
        return


# ============= Frontmatter featured/sticky single-active =============
def _frontmatter_forces_featured(content: str) -> bool:
    extra = _EXTRA_BLOCK_RE.search(content or "")
    return bool(extra and _FEATURED_TRUE_RE.search(extra.group(2)))


def _demote_featured_frontmatter(content: str) -> str:
    """Remove the manual Featured override from a file's [extra] block."""
    def replace_extra(match: "re.Match") -> str:
        body = _FEATURED_LINE_RE.sub("", match.group(2))
        body = _FEATURED_AT_LINE_RE.sub("", body)
        return match.group(1) + body

    return _EXTRA_BLOCK_RE.sub(replace_extra, content or "", count=1)


def _frontmatter_forces_sticky(content: str) -> bool:
    extra = _EXTRA_BLOCK_RE.search(content or "")
    return bool(extra and _STICKY_TRUE_RE.search(extra.group(2)))


def _demote_sticky_frontmatter(content: str) -> str:
    """Remove the `sticky = true` override from a file's [extra] block."""
    def replace_extra(match: "re.Match") -> str:
        body = _STICKY_LINE_RE.sub("", match.group(2))
        return match.group(1) + body

    return _EXTRA_BLOCK_RE.sub(replace_extra, content or "", count=1)


async def _demote_other_featured_posts(
    client: httpx.AsyncClient, selected_path: str, selected_slug: str, token: str,
) -> int:
    """Clear older manual Featured overrides from every OTHER CMS post."""
    entries = await _gh_list_dir(client, CMS_CONTENT_DIR, token)
    demoted = 0
    for entry in entries:
        path = entry.get("path", "")
        if (
            entry.get("type") != "file"
            or not path.endswith(".md")
            or path.endswith("/_index.md")
            or path == selected_path
        ):
            continue
        sha, text = await _gh_get_file(client, path, token)
        if not sha or not _frontmatter_forces_featured(text):
            continue
        demoted_text = _demote_featured_frontmatter(text)
        if demoted_text == text:
            continue
        await _gh_put_file(
            client, path, demoted_text, sha,
            f"CMS: bỏ Featured cũ khi chọn '{selected_slug}'", token,
        )
        demoted += 1
    return demoted


async def _demote_other_sticky_posts(
    client: httpx.AsyncClient, selected_path: str, selected_slug: str, token: str,
) -> int:
    """Enforce the "only ONE sticky post" rule: saving a sticky post clears the
    sticky flag from every OTHER post in the SAME save op (single-active sticky)."""
    entries = await _gh_list_dir(client, CMS_CONTENT_DIR, token)
    demoted = 0
    for entry in entries:
        path = entry.get("path", "")
        if (
            entry.get("type") != "file"
            or not path.endswith(".md")
            or path.endswith("/_index.md")
            or path == selected_path
        ):
            continue
        sha, text = await _gh_get_file(client, path, token)
        if not sha or not _frontmatter_forces_sticky(text):
            continue
        demoted_text = _demote_sticky_frontmatter(text)
        if demoted_text == text:
            continue
        await _gh_put_file(
            client, path, demoted_text, sha,
            f"CMS: bỏ Sticky cũ khi ghim '{selected_slug}'", token,
        )
        demoted += 1
    return demoted


# ============= Categories Endpoints =============
@router.get("/api/categories/list")
async def categories_list(authorization: str = Header(default="")):
    """Return the category list from categories.json (auth required)."""
    token = await _token(authorization)
    async with httpx.AsyncClient(timeout=15.0) as client:
        _, cats = await _load_categories(client, token)
    return {"categories": cats}


@router.post("/api/categories/add")
async def categories_add(request: Request, authorization: str = Header(default="")):
    """Append a new category to categories.json. Idempotent."""
    token = await _token(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")
    name = str(body.get("name", "")).strip()
    if not name or not _CATEGORY_RE.match(name):
        raise HTTPException(400, "invalid_name")

    async with httpx.AsyncClient(timeout=20.0) as client:
        sha, cats = await _load_categories(client, token)
        if name in cats:
            return {"ok": True, "categories": cats, "added": False}
        cats.append(name)
        new_text = json.dumps({"categories": cats}, ensure_ascii=False, indent=2) + "\n"
        await _gh_put_file(client, CMS_CATEGORIES_PATH, new_text, sha,
                           f"CMS: thêm category '{name}'", token)
    return {"ok": True, "categories": cats, "added": True}


# ============= Save Post =============
@router.post("/cms/save-post")
async def cms_save_post(request: Request, authorization: str = Header(default="")):
    """Create/update content/posting/{slug}.md via the GitHub Contents API.

    Body JSON: slug, content (full markdown incl. frontmatter), message (optional),
    sha (optional — sent by the editor when updating an existing file).

    Sticky/featured are single-active: saving a sticky (or featured) post clears the
    flag from every other post in the same operation.
    """
    token = await _token(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")

    slug    = str(body.get("slug", "")).strip().lower()
    content = body.get("content", "")
    message = str(body.get("message", "")).strip()
    # Optional sha sent by the editor when updating an existing file. We re-read the
    # live sha (authoritative, avoids a stale-sha 409) but fall back to client_sha.
    client_sha = str(body.get("sha", "") or "").strip() or None

    if not _SLUG_RE.match(slug):
        raise HTTPException(400, "invalid_slug")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(400, "empty_content")
    if len(content) > 200_000:
        raise HTTPException(400, "content_too_large")
    if not message:
        message = f"CMS: {slug}"

    path = f"{CMS_CONTENT_DIR}/{slug}.md"
    force_featured = _frontmatter_forces_featured(content)
    force_sticky = _frontmatter_forces_sticky(content)

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. Read current sha for update. 404 → new file. Fallback to client_sha.
        try:
            existing_sha, _ = await _gh_get_file(client, path, token)
        except HTTPException:
            existing_sha = client_sha
        if existing_sha is None:
            existing_sha = client_sha

        # 2. PUT create/update the .md file.
        data = await _gh_put_file(client, path, content, existing_sha, message, token)

        # 3. Best-effort: auto-add a new category to categories.json.
        cat_match = _CATEGORY_FRONTMATTER_RE.search(content)
        if cat_match:
            await _ensure_category(client, cat_match.group(1).strip(), token)

        # 4. Featured single-active.
        demoted_featured = 0
        if force_featured:
            demoted_featured = await _demote_other_featured_posts(client, path, slug, token)

        # 5. Sticky single-active.
        demoted_sticky = 0
        if force_sticky:
            demoted_sticky = await _demote_other_sticky_posts(client, path, slug, token)

        return {
            "ok":         True,
            "action":     "updated" if existing_sha else "created",
            "path":       path,
            "commit_url": data.get("commit", {}).get("html_url", ""),
            "commit_sha": data.get("commit", {}).get("sha", ""),
            "demoted_featured": demoted_featured,
            "demoted_sticky":   demoted_sticky,
            "deploy_eta": "1-2 phút (GitHub Actions auto-build + deploy)",
        }


# ============= Bulk Delete =============
@router.post("/cms/posts/bulk-delete")
async def cms_bulk_delete(request: Request, authorization: str = Header(default="")):
    """Delete multiple posts in a single commit via GraphQL createCommitOnBranch."""
    token = await _token(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")

    slugs = body.get("slugs", [])
    if not isinstance(slugs, list) or len(slugs) == 0:
        raise HTTPException(400, "empty_slugs")
    if len(slugs) > 50:
        raise HTTPException(400, "too_many_slugs_max_50")

    seen: set = set()
    paths: list = []
    for s in slugs:
        if not isinstance(s, str) or not _SLUG_RE.match(s):
            raise HTTPException(400, f"invalid_slug: {s[:50] if isinstance(s, str) else type(s).__name__}")
        if s in seen:
            continue
        seen.add(s)
        paths.append(f"{CMS_CONTENT_DIR}/{s}.md")

    headers = _gh_headers(token)
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            sha_res = await client.get(
                f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}"
                f"/git/ref/heads/{CMS_REPO_BRANCH}",
                headers=headers,
            )
        except httpx.HTTPError:
            raise HTTPException(502, "github_unreachable")
        if sha_res.status_code != 200:
            raise HTTPException(502, f"fetch_head_failed_{sha_res.status_code}")
        head_oid = (sha_res.json().get("object") or {}).get("sha", "")
        if not head_oid:
            raise HTTPException(502, "no_head_sha")

        mutation = """
        mutation BulkDelete($input: CreateCommitOnBranchInput!) {
          createCommitOnBranch(input: $input) {
            commit { url oid }
          }
        }
        """
        variables = {
            "input": {
                "branch": {
                    "repositoryNameWithOwner": f"{CMS_REPO_OWNER}/{CMS_REPO_NAME}",
                    "branchName": CMS_REPO_BRANCH,
                },
                "message": {"headline": f"CMS: bulk xoá {len(paths)} bài viết"},
                "fileChanges": {"deletions": [{"path": p} for p in paths]},
                "expectedHeadOid": head_oid,
            }
        }
        try:
            gql_res = await client.post(
                "https://api.github.com/graphql",
                headers=headers,
                json={"query": mutation, "variables": variables},
            )
        except httpx.HTTPError:
            raise HTTPException(502, "graphql_unreachable")

    if gql_res.status_code != 200:
        raise HTTPException(502, f"graphql_failed_{gql_res.status_code}")

    gql_data = gql_res.json()
    if "errors" in gql_data and gql_data["errors"]:
        err = gql_data["errors"][0].get("message", "graphql_error")
        code = 422 if "expectedheadoid" in err.lower() else 400
        raise HTTPException(code, f"graphql: {err}")

    commit_info = (((gql_data.get("data") or {}).get("createCommitOnBranch")) or {}).get("commit") or {}
    return {
        "ok":            True,
        "deleted_count": len(paths),
        "deleted_slugs": list(seen),
        "commit_url":    commit_info.get("url", ""),
        "commit_oid":    commit_info.get("oid", ""),
        "deploy_eta":    "1-2 phút (Pages auto-build)",
    }
