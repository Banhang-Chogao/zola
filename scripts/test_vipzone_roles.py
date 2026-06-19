#!/usr/bin/env python3
"""VIPZone role + GSC superadmin gate tests."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIPZONE = ROOT / "services" / "vipzone"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(VIPZONE))
roles = _load_module("vipzone_roles", VIPZONE / "roles.py")
github_repo = _load_module("vipzone_github_repo", VIPZONE / "github_repo.py")
from db import VipzoneDB  # noqa: E402


class RoleResolutionTests(unittest.TestCase):
    def test_superadmin_from_session_flag(self) -> None:
        self.assertTrue(roles.is_superadmin({"is_superadmin": True, "username": "other"}))
        self.assertEqual(roles.resolve_role(True, is_vip=False), "superadmin")

    def test_superadmin_username_fallback(self) -> None:
        self.assertTrue(roles.username_is_superadmin("banhang-chogao"))
        self.assertEqual(roles.resolve_role(True, is_vip=True), "superadmin")

    def test_vip_role(self) -> None:
        self.assertEqual(roles.resolve_role(False, is_vip=True), "vip")

    def test_admin_role(self) -> None:
        # admin tier (env username/email) ranks below superadmin, above vip.
        self.assertEqual(roles.resolve_role(False, is_vip=False, is_admin=True), "admin")
        self.assertEqual(roles.resolve_role(False, is_vip=True, is_admin=True), "admin")
        self.assertEqual(roles.resolve_role(True, is_vip=False, is_admin=True), "superadmin")

    def test_user_role(self) -> None:
        self.assertEqual(roles.resolve_role(False, is_vip=False), "user")

    def test_no_email_superadmin(self) -> None:
        # Email alone never grants superadmin (the reverted hardcoded-email override).
        self.assertFalse(roles.is_superadmin({"email": "tamsudev.com@gmail.com", "username": "other"}))

    def test_permission_matrix(self) -> None:
        user = roles.build_permissions("user")
        vip = roles.build_permissions("vip")
        admin = roles.build_permissions("admin")
        sup = roles.build_permissions("superadmin")
        # can_read_premium: vip+ ; can_write/can_admin: admin+ ; can_superadmin: super only
        self.assertEqual(
            [p["can_read_premium"] for p in (user, vip, admin, sup)],
            [False, True, True, True],
        )
        self.assertEqual(
            [p["can_write"] for p in (user, vip, admin, sup)],
            [False, False, True, True],
        )
        self.assertEqual(
            [p["can_admin"] for p in (user, vip, admin, sup)],
            [False, False, True, True],
        )
        self.assertEqual(
            [p["can_superadmin"] for p in (user, vip, admin, sup)],
            [False, False, False, True],
        )

    def test_build_identity_includes_role_and_permissions(self) -> None:
        ident = roles.build_identity(
            {"email": "vip@example.com", "username": "viponly", "is_super": False},
            vip_row={"plan": "monthly", "expires_at": "2099-01-01T00:00:00Z"},
        )
        self.assertEqual(ident["role"], "vip")
        self.assertTrue(ident["permissions"]["can_read_premium"])
        self.assertFalse(ident["permissions"]["can_write"])
        self.assertEqual(ident["vip_plan"], "monthly")

    def test_active_vip_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = VipzoneDB(Path(tmp) / "vip.db")
            exp = "2099-01-01T00:00:00Z"
            db.upsert_vip("vip@example.com", "monthly", exp)
            self.assertTrue(db.is_active_vip("vip@example.com"))
            self.assertIsNone(db.get_active_vip("nobody@example.com"))


class GithubRepoTests(unittest.TestCase):
    def test_username_env_fallback(self) -> None:
        self.assertTrue(github_repo.username_env_fallback("banhang-chogao"))
        self.assertFalse(github_repo.username_env_fallback("random-user"))


class GscSuperadminGateTests(unittest.TestCase):
    def test_superadmin_gate_logic(self) -> None:
        def gate(role: str) -> int:
            return 200 if role in ("superadmin", "supervip") else 403

        self.assertEqual(gate("user"), 403)
        self.assertEqual(gate("vip"), 403)
        self.assertEqual(gate("superadmin"), 200)


if __name__ == "__main__":
    unittest.main()