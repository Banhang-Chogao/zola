"""Tests for VIPZone picker access levels."""

from __future__ import annotations

import unittest

from picker_access import (
    ACCESS_ADMIN_ONLY,
    ACCESS_PREMIUM,
    ACCESS_PUBLIC,
    can_access_content,
    expand_items,
    migrate_picker_items,
    sparse_items,
)


class PickerAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = {
            "tools": [
                {"slug": "f-dashboard", "title": "F", "url": "/tools/f-dashboard/"},
                {"slug": "secret", "title": "Secret", "url": "/tools/secret-tool/"},
            ],
            "premium": [
                {"slug": "premium-a", "title": "A", "url": "/posting/premium-a/"},
            ],
        }

    def test_migrate_legacy_string_picks_to_premium(self) -> None:
        raw = ["/tools/f-dashboard/", "/insights/"]
        out = migrate_picker_items(raw, self.catalog)
        self.assertEqual(out, [{"url": "/tools/f-dashboard/", "access": ACCESS_PREMIUM}])

    def test_migrate_object_items(self) -> None:
        raw = [{"url": "/tools/secret-tool/", "access": "admin_only"}]
        out = migrate_picker_items(raw, self.catalog)
        self.assertEqual(out[0]["access"], ACCESS_ADMIN_ONLY)

    def test_sparse_and_expand_roundtrip(self) -> None:
        sparse = [{"url": "/tools/f-dashboard/", "access": ACCESS_PREMIUM}]
        expanded = expand_items(sparse, self.catalog)
        self.assertEqual(len(expanded), 3)
        by_url = {i["url"]: i["access"] for i in expanded}
        self.assertEqual(by_url["/tools/f-dashboard/"], ACCESS_PREMIUM)
        self.assertEqual(by_url["/tools/secret-tool/"], ACCESS_PUBLIC)
        self.assertEqual(sparse_items(expanded), sparse)

    def test_public_access(self) -> None:
        self.assertTrue(can_access_content(ACCESS_PUBLIC, is_super=False, is_admin=False, is_vip=False))

    def test_premium_access_vip_and_superadmin(self) -> None:
        self.assertTrue(can_access_content(ACCESS_PREMIUM, is_vip=True))
        self.assertTrue(can_access_content(ACCESS_PREMIUM, is_super=True))
        self.assertFalse(can_access_content(ACCESS_PREMIUM, is_vip=False, is_super=False))

    def test_admin_only_denied_for_user_and_vip(self) -> None:
        self.assertFalse(can_access_content(ACCESS_ADMIN_ONLY, is_vip=True))
        self.assertFalse(can_access_content(ACCESS_ADMIN_ONLY, is_vip=False))

    def test_admin_only_allowed_for_superadmin_and_admin(self) -> None:
        self.assertTrue(can_access_content(ACCESS_ADMIN_ONLY, is_super=True))
        self.assertTrue(can_access_content(ACCESS_ADMIN_ONLY, is_admin=True))


if __name__ == "__main__":
    unittest.main()