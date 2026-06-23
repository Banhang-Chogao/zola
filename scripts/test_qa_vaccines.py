import unittest

from scripts import qa_vaccines


class QaVaccinesRetiredPaywallTest(unittest.TestCase):
    def test_paywall_integrity_check_is_retired_or_safe(self):
        check = getattr(qa_vaccines, "check_paywall_integrity", None)
        if check is None:
            self.skipTest("paywall integrity check removed")

        result = check({})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("status"), "pass")


if __name__ == "__main__":
    unittest.main()
