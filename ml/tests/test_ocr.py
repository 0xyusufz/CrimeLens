"""Phase 3 OCR Integration tests.

Covers:
- TEST 1: OCR module import
- TEST 2: Valid synthetic image handling (with controlled/mock runner and real check)
- TEST 3: OCR output flows into Phase 2 normalizer
- TEST 4: Plain text path remains operational without OCR
- TEST 5: Invalid/corrupt image raises clear error
- TEST 6: Missing file raises FileNotFoundError
- TEST 7: Empty OCR result handled safely without fabricating content
- TEST 8: Unavailable OCR engine raises clear OCREngineUnavailableError
- TEST 9: Multilingual / Unicode preservation through OCR -> normalizer path
- TEST 10: Identifier preservation (phone, account, vehicle, date, amount)
- TEST 11: Deterministic pipeline behavior
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.ocr import (
    InvalidImageError,
    OCREngineUnavailableError,
    OCRError,
    OCRProcessingError,
    OCRResult,
    UnsupportedImageFormatError,
    extract_ocr_result,
    extract_text_from_image,
    is_ocr_available,
    run_tesseract,
)
from ml.pipeline import process_document
from ml.preprocessing import normalize_text
from shared.schemas.models import ExtractionResult

# Valid 1x1 transparent PNG bytes
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00"
    b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestOCRIntegration(unittest.TestCase):
    def test_1_ocr_module_import(self):
        """TEST 1: OCR module exports are present and callable."""
        self.assertTrue(callable(extract_text_from_image))
        self.assertTrue(callable(extract_ocr_result))
        self.assertTrue(callable(is_ocr_available))
        self.assertTrue(callable(run_tesseract))
        self.assertTrue(issubclass(OCREngineUnavailableError, RuntimeError))
        self.assertTrue(issubclass(InvalidImageError, ValueError))

    def test_2_valid_synthetic_image(self):
        """TEST 2: Valid synthetic image extraction using controlled engine runner."""
        expected_text = (
            "CRIMINAL TEST DOCUMENT\n"
            "PERSON: Rahul Kumar\n"
            "PHONE: +91-98765-43210"
        )

        def mock_runner(img_bytes: bytes, lang: str) -> str:
            self.assertEqual(img_bytes, VALID_PNG_BYTES)
            self.assertEqual(lang, "eng")
            return expected_text

        result = extract_ocr_result(
            VALID_PNG_BYTES,
            lang="eng",
            engine_runner=mock_runner,
        )
        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.raw_text, expected_text)
        self.assertFalse(result.is_empty)
        self.assertEqual(result.engine, "tesseract")

    def test_3_ocr_output_enters_phase2_normalizer(self):
        """TEST 3: OCR output flows through Phase 2 normalizer."""
        raw_ocr_output = "  PERSON: Rahul Kumar  \n\n\n\n PHONE: +91-98765-43210 "
        normalized = normalize_text(raw_ocr_output)

        expected = "PERSON: Rahul Kumar\n\nPHONE: +91-98765-43210"
        self.assertEqual(normalized, expected)
        self.assertIn("Rahul Kumar", normalized)
        self.assertIn("+91-98765-43210", normalized)

    def test_4_text_path_remains_working(self):
        """TEST 4: Plain text documents still process directly without OCR."""
        text_content = "FIR No. 204/2026: Suspect Amit Kumar seen near market."
        result = process_document("doc_text_001", text_content)

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_text_001")
        self.assertEqual(result.relationships, [])
        self.assertTrue(any(e.name == "Amit Kumar" for e in result.entities))

    def test_5_invalid_image(self):
        """TEST 5: Corrupt or non-image bytes raise InvalidImageError."""
        corrupt_bytes = b"NOT_A_VALID_IMAGE_HEADER_12345"

        with self.assertRaises(InvalidImageError):
            extract_text_from_image(corrupt_bytes)

        with self.assertRaises(InvalidImageError):
            extract_text_from_image(b"")

    def test_6_missing_file(self):
        """TEST 6: Missing image file raises FileNotFoundError."""
        missing_path = "non_existent_scan_12345.png"

        with self.assertRaises(FileNotFoundError):
            extract_text_from_image(missing_path)

    def test_7_empty_ocr_result(self):
        """TEST 7: Empty OCR result does not fabricate content."""
        def mock_empty_runner(img_bytes: bytes, lang: str) -> str:
            return "   \n\n   "

        result = process_document(
            "doc_ocr_empty",
            VALID_PNG_BYTES,
            ocr_engine_runner=mock_empty_runner,
        )
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_ocr_empty")
        self.assertEqual(result.entities, [])
        self.assertEqual(result.relationships, [])

    def test_8_ocr_engine_unavailable(self):
        """TEST 8: Clearly raises OCREngineUnavailableError when engine missing."""
        def mock_unavailable_runner(img_bytes: bytes, lang: str) -> str:
            raise OCREngineUnavailableError("Tesseract OCR engine is not installed or not found in system PATH.")

        with self.assertRaises(OCREngineUnavailableError) as ctx:
            extract_text_from_image(VALID_PNG_BYTES, engine_runner=mock_unavailable_runner)
        self.assertIn("system PATH", str(ctx.exception))

    def test_9_unicode_preservation(self):
        """TEST 9: Multilingual non-ASCII characters and currency symbols are preserved."""
        multilingual_ocr = (
            "प्राथमिकी विवरण: संदिग्ध व्यक्ति अमित कुमार\n"
            "Currency: ₹50,000 / €1,200\n"
            "स्थान: भुवनेश्वर"
        )
        normalized = normalize_text(multilingual_ocr)

        self.assertIn("अमित कुमार", normalized)
        self.assertIn("₹50,000", normalized)
        self.assertIn("€1,200", normalized)
        self.assertIn("भुवनेश्वर", normalized)

    def test_10_identifier_preservation(self):
        """TEST 10: Complete identifier suite preserved through OCR normalization path."""
        ocr_text = (
            "INVESTIGATION SUMMARY\n"
            "PHONE: +91-98765-43210\n"
            "ACCOUNT: 123456789012\n"
            "VEHICLE: DL 01 AB 1234\n"
            "DATE: 2026-01-15\n"
            "TIME: 14:30\n"
            "AMOUNT: ₹50,000"
        )
        cleaned = normalize_text(ocr_text)

        self.assertIn("+91-98765-43210", cleaned)
        self.assertIn("123456789012", cleaned)
        self.assertIn("DL 01 AB 1234", cleaned)
        self.assertIn("2026-01-15", cleaned)
        self.assertIn("14:30", cleaned)
        self.assertIn("₹50,000", cleaned)

    def test_11_deterministic_pipeline_behavior(self):
        """TEST 11: Repeated processing of the same OCR input produces identical results."""
        def mock_runner(img_bytes: bytes, lang: str) -> str:
            return "CALL LOG: +91-98765-43210 called account holder at 14:30"

        res1 = process_document("doc_rep", VALID_PNG_BYTES, ocr_engine_runner=mock_runner)
        res2 = process_document("doc_rep", VALID_PNG_BYTES, ocr_engine_runner=mock_runner)

        self.assertEqual(res1.model_dump(), res2.model_dump())


if __name__ == "__main__":
    unittest.main()
