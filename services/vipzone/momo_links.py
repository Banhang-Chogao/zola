"""
MoMo Links Admin Routes — manage MoMo payment links across config, posts, templates.

Endpoints:
  GET  /admin/momo-links         (scan repo, return all MoMo links)
  POST /admin/momo-links/replace (replace old link with new link)

Auth: Google admin session required (GOOGLE_ADMIN_EMAILS).
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException
from pydantic import BaseModel

from cms_auth import (
    SESSION_COOKIE_NAME,
    cms_profile_from_session,
    is_admin,
    is_commenter_only,
)
from roles import is_superadmin

router = APIRouter(prefix="/admin", tags=["admin-momo"])


class ReplaceRequest(BaseModel):
    """Replace MoMo link request."""
    old_url: str
    new_url: str
    scope: Literal["single", "all_same_url"] = "single"
    target: str | None = None  # file/key path if scope=single


class ReplaceResponse(BaseModel):
    """Replace response."""
    success: bool
    message: str
    files_modified: list[str] | None = None
    commit_sha: str | None = None
    pr_url: str | None = None


def _validate_momo_url(url: str) -> bool:
    """Validate MoMo URL format."""
    if not url:
        return False
    if not url.startswith("https://me.momo.vn/"):
        return False
    # Basic format check: https://me.momo.vn/{user}/{key}
    parts = url.split("/")
    if len(parts) < 5:
        return False
    return True


async def require_momo_admin(
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    """Admin-only guard for the MoMo link manager.

    Resolves the VIPZone CMS session from the ``Authorization: Bearer <sid>``
    header (primary, cross-origin-safe) OR the session cookie (fallback), then
    requires an admin/superadmin profile. A commenter-only session can never pass
    (defense-in-depth). Raises 401 when there is no session and 403 when the
    authenticated account is not on the admin allowlist.

    Previously this router read ``authorization`` as a *query parameter* (so the
    real Bearer header never reached it) and the GET endpoint skipped the check
    entirely — leaving the admin data endpoint effectively unauthenticated yet
    unreachable with a valid token. This dependency fixes both (auth-vaccine A1).
    """
    from main import get_db

    profile = await cms_profile_from_session(
        get_db(), authorization or "", cookie_sid=cookie_sid
    )
    if is_commenter_only(profile):
        raise HTTPException(403, "admin_only")
    if not (
        is_admin(profile.get("email"), profile.get("username"))
        or is_superadmin(profile)
    ):
        raise HTTPException(403, "admin_only")
    return profile


@router.get("/momo-links")
async def get_momo_links(
    _admin: dict[str, Any] = Depends(require_momo_admin),
) -> dict[str, Any]:
    """
    Scan repo and return all MoMo links, their locations, and usage.

    Returns: {
        "generated_at": "ISO timestamp",
        "total_urls": int,
        "links_by_url": {
            "https://me.momo.vn/...": {
                "url": "...",
                "category": "Premium default|Donate|Premium post|Template|Workflow|Docs",
                "locations": ["config.toml:[extra].momo_payment_link", ...],
                "count": int,
                "post_slug": "...",
                "post_title": "...",
            }
        },
        "summary": {...}
    }
    """
    # For now, read from cached data/momo-links-audit.json
    # In production, could re-run audit script or cache with cron refresh

    audit_file = Path(__file__).parents[2] / "data" / "momo-links-audit.json"

    if not audit_file.exists():
        raise HTTPException(
            404,
            "MoMo links audit not found. Run: python3 scripts/audit_momo_links.py"
        )

    try:
        audit_data = json.loads(audit_file.read_text(encoding="utf-8"))

        blocks_by_url: dict[str, list[dict[str, Any]]] = {}
        cp_file = Path(__file__).parents[2] / "data" / "content-placements.json"
        if cp_file.exists():
            try:
                cp_data = json.loads(cp_file.read_text(encoding="utf-8"))
                for block in cp_data.get("blocks", []):
                    block_url = (block.get("url") or "").strip()
                    if not block_url:
                        continue
                    display = (
                        block.get("title")
                        or block.get("button_text")
                        or block.get("id")
                        or ""
                    )
                    blocks_by_url.setdefault(block_url, []).append(
                        {
                            "id": block.get("id"),
                            "placement_id": block.get("placement_id"),
                            "display_text": display,
                            "enabled": bool(block.get("enabled")),
                        }
                    )
            except Exception:
                pass

        # Load public usage data (if available)
        public_usage_data = {}
        public_usage_file = Path(__file__).parents[2] / "data" / "momo-public-usage.json"
        if public_usage_file.exists():
            try:
                public_usage_data = json.loads(public_usage_file.read_text(encoding="utf-8"))
                public_usage_data = public_usage_data.get("links_with_public_usage", {})
            except Exception:
                pass

        # Reshape for frontend
        links_by_url = {}
        for url, link_info in audit_data.get("links_by_url", {}).items():
            content_blocks = blocks_by_url.get(url, [])
            placement_ids = sorted(
                {b["placement_id"] for b in content_blocks if b.get("placement_id")}
            )
            display_text = ", ".join(
                b.get("display_text") or b.get("id", "")
                for b in content_blocks
                if b.get("display_text") or b.get("id")
            )
            locations = list(link_info.get("locations", []))
            for block in content_blocks:
                loc = f"data/content-placements.json:block:{block.get('id')}"
                if loc not in locations:
                    locations.append(loc)

            # Get public usage from the public usage audit
            public_usages = []
            technical_usages = locations
            if url in public_usage_data:
                public_usages = public_usage_data[url].get("public_usages", [])
                technical_usages = public_usage_data[url].get("technical_usages", locations)

            links_by_url[url] = {
                "url": url,
                "category": link_info.get("category", "Unknown"),
                "locations": locations,  # Keep for backward compat
                "count": len(locations),
                "post_slug": link_info.get("post_slug"),
                "post_title": link_info.get("post_title"),
                "content_blocks": content_blocks,
                "placement_ids": placement_ids,
                "display_text": display_text,
                # New fields for modal:
                "public_usages": public_usages,
                "technical_usages": technical_usages,
            }

        return {
            "generated_at": audit_data.get("generated_at"),
            "total_urls": len(links_by_url),
            "links_by_url": links_by_url,
            "summary": audit_data.get("summary", {}),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to read audit data: {str(e)}")


@router.post("/momo-links/replace", response_model=ReplaceResponse)
async def replace_momo_link(
    request: ReplaceRequest,
    _admin: dict[str, Any] = Depends(require_momo_admin),
) -> ReplaceResponse:
    """
    Replace old MoMo link with new one.

    Modes:
      - scope="single" + target: replace only in specified file/key
      - scope="all_same_url": replace everywhere the old URL appears

    Performs:
      1. Validate URLs
      2. Update files
      3. Commit to GitHub (no PR for now — direct commit)
      4. Return commit SHA + status
    """

    # Validate URLs
    if not _validate_momo_url(request.old_url):
        raise HTTPException(400, "Invalid old_url format")
    if not _validate_momo_url(request.new_url):
        raise HTTPException(400, "Invalid new_url format")

    if request.old_url == request.new_url:
        raise HTTPException(400, "old_url and new_url must differ")

    repo_root = Path(__file__).parents[2]
    files_modified = []

    try:
        # Read audit to know what to replace
        audit_file = repo_root / "data" / "momo-links-audit.json"
        if not audit_file.exists():
            raise HTTPException(400, "Run audit first: python3 scripts/audit_momo_links.py")

        audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
        link_info = audit_data.get("links_by_url", {}).get(request.old_url)

        if not link_info:
            raise HTTPException(404, f"URL not found in audit: {request.old_url}")

        targets = link_info.get("locations", [])

        # Filter targets if scope=single
        if request.scope == "single" and request.target:
            targets = [t for t in targets if request.target in t]
            if not targets:
                raise HTTPException(400, f"Target not found: {request.target}")
        elif request.scope != "all_same_url":
            raise HTTPException(400, f"Invalid scope: {request.scope}")

        # Group targets by file
        files_to_update: dict[str, list[str]] = {}
        for target in targets:
            # target format: "config.toml:[extra].momo_payment_link" or "content/posting/file.md"
            parts = target.split(":", 1)
            file_path = parts[0]
            key_path = parts[1] if len(parts) > 1 else None

            if file_path not in files_to_update:
                files_to_update[file_path] = []
            if key_path:
                files_to_update[file_path].append(key_path)

        # Update each file
        for file_path_str, keys in files_to_update.items():
            file_path = repo_root / file_path_str

            if not file_path.exists():
                raise HTTPException(400, f"File not found: {file_path_str}")

            content = file_path.read_text(encoding="utf-8")
            new_content = content.replace(request.old_url, request.new_url)

            if new_content == content:
                raise HTTPException(400, f"No replacement made in {file_path_str}")

            file_path.write_text(new_content, encoding="utf-8")
            files_modified.append(file_path_str)

        # After modifying, re-run audit to update data/momo-links-audit.json
        import sys
        sys.path.insert(0, str(repo_root / "scripts"))
        try:
            from audit_momo_links import run_audit
            new_audit = run_audit()
            audit_file.write_text(
                json.dumps(new_audit, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Warning: Failed to re-run audit: {e}")
        finally:
            sys.path.pop(0)

        # TODO: Commit to GitHub via GitHub API
        # For now, return success without commit
        # (In production: use cms_repo module to commit)

        return ReplaceResponse(
            success=True,
            message=f"Replaced in {len(files_modified)} file(s)",
            files_modified=files_modified,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Replace failed: {str(e)}")
