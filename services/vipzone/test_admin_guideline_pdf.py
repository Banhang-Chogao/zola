"""Tests for Admin Guideline PDF generation and endpoint."""

import unittest
import sys
import os
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from admin_guideline_pdf import (
    generate_watermark_hash,
    generate_pdf_watermark,
    GUIDELINES,
)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class TestWatermarkHash(unittest.TestCase):
    """Test watermark hash generation."""

    def test_hash_deterministic(self):
        """Hash should be deterministic for same seed."""
        hash1 = generate_watermark_hash("OPERATION_GUIDELINE")
        hash2 = generate_watermark_hash("OPERATION_GUIDELINE")
        self.assertEqual(hash1, hash2)

    def test_hash_uppercase_hex(self):
        """Hash should be 16-char uppercase hex."""
        h = generate_watermark_hash("OPERATION_GUIDELINE")
        self.assertEqual(len(h), 16)
        self.assertTrue(all(c in "0123456789ABCDEF" for c in h))

    def test_hash_different_seeds(self):
        """Different seeds should produce different hashes."""
        h1 = generate_watermark_hash("OPERATION_GUIDELINE")
        h2 = generate_watermark_hash("OPERATION_GUIDELINE_2026_06_21")
        self.assertNotEqual(h1, h2)

    def test_hash_short_seed(self):
        """Hash should work with short seeds."""
        h = generate_watermark_hash("V1")
        self.assertEqual(len(h), 16)
        self.assertTrue(all(c in "0123456789ABCDEF" for c in h))


class TestGuidelineStructure(unittest.TestCase):
    """Test Operation Guideline data structure."""

    def test_guidelines_present(self):
        """Guidelines list should not be empty."""
        self.assertGreater(len(GUIDELINES), 0)

    def test_required_fields(self):
        """Each guideline should have required fields."""
        required = {"code", "name", "purpose", "template"}
        for g in GUIDELINES:
            for field in required:
                self.assertIn(field, g, f"Missing {field} in guideline")
                self.assertIsNotNone(g[field], f"{field} is None")
                self.assertNotEqual(g[field], "", f"{field} is empty")

    def test_guideline_v1_content(self):
        """V1 (HuggingFace Model ID) should be present."""
        v1 = next((g for g in GUIDELINES if g["code"] == "V1"), None)
        self.assertIsNotNone(v1)
        self.assertIn("HuggingFace", v1["name"])
        self.assertIn("401", v1["purpose"])

    def test_guideline_codes_unique(self):
        """Guideline codes should be unique."""
        codes = [g["code"] for g in GUIDELINES]
        self.assertEqual(len(codes), len(set(codes)))


@unittest.skipIf(not HAS_REPORTLAB, "reportlab not installed")
class TestPDFGeneration(unittest.TestCase):
    """Test PDF generation with watermark."""

    def test_pdf_generation_returns_bytes(self):
        """PDF generation should return bytes."""
        output = BytesIO()
        generate_pdf_watermark(output)
        pdf_bytes = output.getvalue()
        self.assertGreater(len(pdf_bytes), 0)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_pdf_has_title_page(self):
        """PDF should contain title page content."""
        output = BytesIO()
        generate_pdf_watermark(output)
        pdf_bytes = output.getvalue()
        pdf_str = pdf_bytes.decode("latin-1", errors="ignore")
        self.assertIn("Operation Guideline", pdf_str)

    def test_pdf_custom_guidelines(self):
        """PDF should support custom guideline list."""
        custom = [
            {
                "code": "TEST1",
                "name": "Test Guideline",
                "purpose": "For testing",
                "template": "Test template",
            }
        ]
        output = BytesIO()
        generate_pdf_watermark(output, guidelines=custom)
        pdf_bytes = output.getvalue()
        self.assertGreater(len(pdf_bytes), 0)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_pdf_multiple_guidelines(self):
        """PDF should handle multiple guidelines."""
        output = BytesIO()
        generate_pdf_watermark(output, guidelines=GUIDELINES)
        pdf_bytes = output.getvalue()
        self.assertGreater(len(pdf_bytes), 0)
        # PDF size should scale with guideline count
        self.assertGreater(len(pdf_bytes), 5000)


class TestMissingReportlab(unittest.TestCase):
    """Test behavior when reportlab is missing."""

    def test_import_error_raises(self):
        """generate_pdf_watermark should raise ImportError if reportlab missing."""
        if HAS_REPORTLAB:
            self.skipTest("reportlab is installed")
        else:
            output = BytesIO()
            with self.assertRaises(ImportError) as cm:
                generate_pdf_watermark(output)
            self.assertIn("reportlab", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
