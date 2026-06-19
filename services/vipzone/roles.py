"""VIPZone role resolution — user · vip · superadmin."""

from __future__ import annotations

from github_repo import username_env_fallback

ROLE_USER = "user"
ROLE_VIP = "vip"
ROLE_SUPERADMIN = "superadmin"
ROLE_SUPERVIP = ROLE_SUPERADMIN


def username_is_superadmin(username: str | None) -> bool:
    """Env username fallback (SUPERADMIN_GITHUB_USERNAMES + ADMIN_USERNAMES)."""
    return username_env_fallback(username)


def is_superadmin(session: dict | None) -> bool:
    if not session:
        return False
    if session.get("is_superadmin") or session.get("is_super"):
        return True
    return username_env_fallback(session.get("username"))


def is_supervip(email: str | None, username: str | None) -> bool:
    return username_env_fallback(username)


def resolve_role(is_super: bool, *, is_vip: bool) -> str:
    if is_super:
        return ROLE_SUPERADMIN
    if is_vip:
        return ROLE_VIP
    return ROLE_USER