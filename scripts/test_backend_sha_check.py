"""Tests for backend8 split-brain classifier (V16) — stdlib only, no network."""

import unittest

from backend_sha_check import _sha_match, classify

SHA_A = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
SHA_B = "ffeeddccbbaa00112233445566778899aabbccdd"


class BackendShaClassifyTests(unittest.TestCase):
    def test_in_sync_full(self):
        r = classify(SHA_A, SHA_A, True)
        self.assertEqual(r["status"], "in_sync")
        self.assertFalse(r["outdated"])

    def test_in_sync_prefix(self):
        # Render may report a short SHA; a 12-char prefix still matches.
        r = classify(SHA_A, SHA_A[:12], True)
        self.assertEqual(r["status"], "in_sync")
        self.assertFalse(r["outdated"])

    def test_outdated(self):
        r = classify(SHA_A, SHA_B, True)
        self.assertEqual(r["status"], "outdated")
        self.assertTrue(r["outdated"])
        self.assertIn("BACKEND_OUTDATED", r["message"])
        self.assertEqual(r["action"], "render-deploy")

    def test_unreachable_is_unknown_not_outdated(self):
        r = classify(SHA_A, "", False)
        self.assertEqual(r["status"], "unknown")
        self.assertFalse(r["outdated"])
        self.assertEqual(r["action"], "retry")

    def test_reachable_but_no_backend_sha(self):
        r = classify(SHA_A, "", True)
        self.assertEqual(r["status"], "unknown")
        self.assertEqual(r["action"], "set-render-git-commit")

    def test_no_main_sha(self):
        r = classify("", SHA_B, True)
        self.assertEqual(r["status"], "unknown")
        self.assertEqual(r["action"], "check-git")

    def test_sha_match_helper(self):
        self.assertTrue(_sha_match(SHA_A, SHA_A))
        self.assertTrue(_sha_match(SHA_A, SHA_A[:7]))
        self.assertFalse(_sha_match(SHA_A, SHA_B))
        self.assertFalse(_sha_match(SHA_A, "a1b2c"))  # < 7 chars → no false match
        self.assertFalse(_sha_match("", SHA_A))


if __name__ == "__main__":
    unittest.main()
