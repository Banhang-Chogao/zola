"""VIPZone role resolution — THE single source of truth.

Every role + permission decision for the VIPZone system is made here:

  * role tiers        — user · vip · admin · superadmin (no other strings)
  * is_admin          — admin tier from env config (ADMIN_USERNAMES / ADMIN_EMAILS)
  * is_superadmin     — superadmin from the OAuth-time repo-permission flag, else env
  * resolve_role      — booleans → one role string (super > admin > vip > user)
  * build_permissions — role → permission object the FRONTEND renders from
  * build_identity    — the unified `/me` payload (both /api/vipzone/me and /auth/me)

No other backend module — and no frontend file — may re-derive a role from an
email/username. They call build_identity()/build_permissions() and read `role`
+ `permissions`. This is the SSoT.
"""

from __future__ import annotations

import os
from typing import Any

from github_repo import username_env_fallback as _superadmin_username_fallback

# ── Role tiers (the only valid `role` strings) ────────────────────────────
ROLE_USER = "user"
ROLE_VIP = "vip"
ROLE_ADMIN = "admin"
ROLE_SUPERADMIN = "superadmin"
ROLE_SUPERVIP = ROLE_SUPERADMIN  # legacy alias — consumers may still send "supervip"
ROLES = (ROLE_USER, ROLE_VIP, ROLE_ADMIN, ROLE_SUPERADMIN)

# ── Admin identity config — env-driven; the ONLY place admin lists live ───
# (Superadmin identity lives in github_repo.SUPERADMIN_GITHUB_USERNAMES + the
#  OAuth-time GitHub repo-permission check; admin is this lighter env tier.)
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "").split(",")
    if e.strip()
}
ADMIN_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("ADMIN_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}


def username_is_superadmin(username: str | None) -> bool:
    """Env username fallback for superadmin (SUPERADMIN_GITHUB_USERNAMES)."""
    return _superadmin_username_fallback(username)


def is_admin(email: str | None, username: str | None) -> bool:
    """Admin tier — env config only (ADMIN_USERNAMES / ADMIN_EMAILS)."""
    if username and username.strip().lower() in ADMIN_USERNAMES:
        return True
    if email and email.strip().lower() in ADMIN_EMAILS:
        return True
    return False


def is_superadmin(session: dict | None) -> bool:
    """Superadmin — OAuth-time repo flag (`is_super`/`is_superadmin`) or env username."""
    if not session:
        return False
    if session.get("is_superadmin") or session.get("is_super"):
        return True
    return username_is_superadmin(session.get("username"))


def resolve_role(is_super: bool, *, is_vip: bool, is_admin: bool = False) -> str:
    """Map identity booleans → one role string. Precedence: super > admin > vip > user."""
    if is_super:
        return ROLE_SUPERADMIN
    if is_admin:
        return ROLE_ADMIN
    if is_vip:
        return ROLE_VIP
    return ROLE_USER


def build_permissions(role: str) -> dict[str, bool]:
    """Permission matrix derived from a role. The frontend renders ONLY from this."""
    is_super = role == ROLE_SUPERADMIN
    can_admin = role in (ROLE_ADMIN, ROLE_SUPERADMIN)
    can_premium = role in (ROLE_VIP, ROLE_ADMIN, ROLE_SUPERADMIN)
    return {
        "can_read_premium": can_premium,   # premium VIP content (public/premium/admin_only matrix)
        "can_write": can_admin,            # content creator access
        "can_admin": can_admin,            # VIPZone admin panel (codes/users/picker/stats)
        "can_superadmin": is_super,        # destructive / superadmin-only actions
    }


def build_identity(profile: dict[str, Any], *, vip_row: dict[str, Any] | None) -> dict[str, Any]:
    """The unified `/me` payload — both /api/vipzone/me and /auth/me return this.

    `profile` is the CMS session dict (email/username/name/avatar/is_super);
    `vip_row` is db.get_active_vip(email) or None. Returns role + permissions —
    nothing downstream re-derives a role.
    """
    email = profile.get("email") or ""
    username = profile.get("username") or ""
    is_super = is_superadmin(profile)
    admin = is_admin(email, username)
    is_vip = vip_row is not None
    role = resolve_role(is_super, is_vip=is_vip, is_admin=admin)
    out: dict[str, Any] = {
        "email": profile.get("email"),
        "username": username,
        "name": profile.get("name") or username,
        "avatar": profile.get("avatar") or "",
        "role": role,
        "is_super": is_super,
        "is_admin": role in (ROLE_ADMIN, ROLE_SUPERADMIN),
        "permissions": build_permissions(role),
    }
    if vip_row:
        out["vip_plan"] = vip_row.get("plan")
        out["vip_expires_at"] = vip_row.get("expires_at")
    return out
