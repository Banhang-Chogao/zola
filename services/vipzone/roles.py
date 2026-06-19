"""VIPZone role resolution — user · vip · supervip."""

from __future__ import annotations

import os

ROLE_USER = "user"
ROLE_VIP = "vip"
ROLE_SUPERVIP = "supervip"

SUPERVIP_EMAILS = {
    e.strip().lower()
    for e in os.getenv("SUPERVIP_EMAILS", "tamsudev.com@gmail.com").split(",")
    if e.strip()
}
SUPERVIP_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("SUPERVIP_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}


def is_supervip(email: str | None, username: str | None) -> bool:
    if username and username.strip().lower() in SUPERVIP_USERNAMES:
        return True
    if email and email.strip().lower() in SUPERVIP_EMAILS:
        return True
    return False


def resolve_role(email: str | None, username: str | None, *, is_vip: bool) -> str:
    if is_supervip(email, username):
        return ROLE_SUPERVIP
    if is_vip:
        return ROLE_VIP
    return ROLE_USER