"""GitHub repo permission check for superadmin role."""

from __future__ import annotations

import os

import httpx

REPO_OWNER = os.getenv("SUPERADMIN_REPO_OWNER", "Banhang-Chogao")
REPO_NAME = os.getenv("SUPERADMIN_REPO_NAME", "zola")

SUPERADMIN_GITHUB_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("SUPERADMIN_GITHUB_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}
# Legacy alias
for _u in os.getenv("SUPERVIP_USERNAMES", "").split(","):
    if _u.strip():
        SUPERADMIN_GITHUB_USERNAMES.add(_u.strip().lower())

ADMIN_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("ADMIN_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}


def username_env_fallback(username: str | None) -> bool:
    uname = (username or "").strip().lower()
    if not uname:
        return False
    return uname in SUPERADMIN_GITHUB_USERNAMES or uname in ADMIN_USERNAMES


async def check_repo_superadmin(
    client: httpx.AsyncClient,
    access_token: str,
    username: str,
) -> bool:
    """True if user is repo owner, has admin permission, or matches env fallback."""
    if username_env_fallback(username):
        return True
    if not access_token or not username:
        return False

    gh_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    uname = username.strip().lower()
    repo_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

    try:
        repo_res = await client.get(repo_url, headers=gh_headers)
    except httpx.HTTPError:
        return username_env_fallback(username)

    if repo_res.status_code == 200:
        data = repo_res.json()
        if (data.get("owner") or {}).get("login", "").lower() == uname:
            return True
        if (data.get("permissions") or {}).get("admin"):
            return True

    try:
        perm_res = await client.get(
            f"{repo_url}/collaborators/{username}/permission",
            headers=gh_headers,
        )
    except httpx.HTTPError:
        return username_env_fallback(username)

    if perm_res.status_code == 200:
        return perm_res.json().get("permission") == "admin"

    return username_env_fallback(username)