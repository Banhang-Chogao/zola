"""Compatibility tests for retired QA vaccines.

Paywall/MoMo/ShortenSEA gates are retired. This file remains so CI imports
scripts.test_qa_vaccines without breaking older workflow references.
"""

import unittest


class TestRetiredQaVaccines(unittest.TestCase):
    def test_retired_paywall_gate_is_non_blocking(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
