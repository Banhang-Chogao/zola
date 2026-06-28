import unittest

from qa_check import is_valid_seo_date


class QaCheckDateTests(unittest.TestCase):
    def test_accepts_date_only(self):
        self.assertTrue(is_valid_seo_date("2026-06-28"))

    def test_accepts_iso_datetime(self):
        self.assertTrue(is_valid_seo_date("2026-06-28T09:15:00+07:00"))

    def test_rejects_invalid_date(self):
        self.assertFalse(is_valid_seo_date("28/06/2026"))


if __name__ == "__main__":
    unittest.main()
