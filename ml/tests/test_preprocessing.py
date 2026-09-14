"""Phase 2 Document Preprocessing tests.

Covers:
- TEST 1: Basic text input & determinism
- TEST 2: Whitespace normalization (tabs, CRLF, multi-space, blank lines)
- TEST 3: Identifier preservation (phone, bank account, vehicle)
- TEST 4: Transaction information preservation (amounts, dates, times)
- TEST 5: Multilingual / Unicode preservation (non-ASCII, currency symbols)
- TEST 6: Empty and whitespace-only input handling
- TEST 7: Normalizer idempotence
- TEST 8: Evidence preservation (source phrasing fidelity)
- Scanned document boundary test (Phase 3 OCR handoff)
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.preprocessing import (
    is_scanned_file,
    load_document,
    normalize_text,
    preprocess_text,
)


class TestDocumentPreprocessing(unittest.TestCase):
    def test_1_basic_text_input(self):
        """TEST 1: Basic multi-line document loading and deterministic normalization."""
        doc = (
            "FIRST INFORMATION REPORT\n"
            "Police Station: Central Cyber Cell\n"
            "Complainant: Suresh Verma"
        )
        loaded = load_document(doc)
        normalized = normalize_text(loaded)

        self.assertEqual(loaded, doc)
        self.assertIn("FIRST INFORMATION REPORT", normalized)
        self.assertIn("Police Station: Central Cyber Cell", normalized)
        self.assertIn("Complainant: Suresh Verma", normalized)
        # Deterministic
        self.assertEqual(normalize_text(loaded), normalize_text(loaded))

    def test_2_whitespace_normalization(self):
        """TEST 2: Formatting noise cleanup (CRLF, tabs, multi-spaces, blank lines)."""
        noisy_text = (
            "  Case Report:\t\tCyber Fraud   \r\n"
            "\r\n"
            "\r\n"
            "\r\n"
            "Suspect identified    at     terminal.   \r\n"
            "\t\tLocation:    Mumbai Central    \r\n"
        )
        cleaned = normalize_text(noisy_text)
        expected = (
            "Case Report: Cyber Fraud\n\n"
            "Suspect identified at terminal.\n"
            "Location: Mumbai Central"
        )
        self.assertEqual(cleaned, expected)

    def test_3_identifier_preservation(self):
        """TEST 3: Key identifiers remain intact and recoverable."""
        raw = (
            "Contact info:\n"
            "PHONE: +91-98765-43210\n"
            "ACCOUNT: 123456789012\n"
            "VEHICLE: DL 01 AB 1234"
        )
        cleaned = normalize_text(raw)
        self.assertIn("+91-98765-43210", cleaned)
        self.assertIn("123456789012", cleaned)
        self.assertIn("DL 01 AB 1234", cleaned)

    def test_4_transaction_information_preservation(self):
        """TEST 4: Amounts, dates, and times remain fully preserved."""
        raw = (
            "Transaction record:\n"
            "Amount: ₹50,000\n"
            "Date: 2026-01-15\n"
            "Time: 14:30\n"
            "Remarks: NEFT transfer to vendor"
        )
        cleaned = normalize_text(raw)
        self.assertIn("₹50,000", cleaned)
        self.assertIn("2026-01-15", cleaned)
        self.assertIn("14:30", cleaned)
        self.assertIn("NEFT transfer", cleaned)

    def test_5_multilingual_unicode_preservation(self):
        """TEST 5: Non-ASCII characters, Hindi, accents, and currency symbols."""
        raw = (
            "प्राथमिकी विवरण: संदिग्ध व्यक्ति अमित कुमार\n"
            "स्थान: भुवनेश्वर, ओडिशा\n"
            "Amount: €1,200 / ₹1,00,000\n"
            "Café Meeting noted."
        )
        cleaned = normalize_text(raw)
        self.assertIn("प्राथमिकी विवरण: संदिग्ध व्यक्ति अमित कुमार", cleaned)
        self.assertIn("स्थान: भुवनेश्वर, ओडिशा", cleaned)
        self.assertIn("€1,200", cleaned)
        self.assertIn("₹1,00,000", cleaned)
        self.assertIn("Café Meeting noted.", cleaned)

    def test_6_empty_and_whitespace_input(self):
        """TEST 6: Empty and whitespace-only input handling without producing fake content."""
        self.assertEqual(load_document(""), "")
        self.assertEqual(load_document("   \n\t   "), "   \n\t   ")

        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text("    "), "")
        self.assertEqual(normalize_text("\n\n\t\r\n   "), "")

        preprocessed = preprocess_text("   \n\t  ")
        self.assertEqual(preprocessed.normalized_text, "")
        self.assertEqual(preprocessed.char_count, 0)
        self.assertEqual(preprocessed.line_count, 0)

        # Non-string input raises TypeError
        with self.assertRaises(TypeError):
            load_document(12345)  # type: ignore

        with self.assertRaises(TypeError):
            normalize_text(None)  # type: ignore

    def test_7_idempotence(self):
        """TEST 7: Normalizing an already-normalized string yields the identical string."""
        sample = (
            "INCIDENT MEMORANDUM\n\n"
            "Officer: Insp. K. Sharma\n"
            "Suspect called Amit Kumar regarding transfer of ₹25,000.\n"
            "Vehicle: KA 03 MH 9999 observed at scene."
        )
        first_pass = normalize_text(sample)
        second_pass = normalize_text(first_pass)
        third_pass = normalize_text(second_pass)

        self.assertEqual(first_pass, second_pass)
        self.assertEqual(second_pass, third_pass)

    def test_8_evidence_preservation(self):
        """TEST 8: Original phrasing remains exact substring for evidence snippets."""
        snippet = "Rahul Sharma handed over the counterfeit currency near City Park gate."
        raw_report = f"  POLICE DIARY ENTRY \n\n   {snippet}   \n\n End of entry.  "
        cleaned = normalize_text(raw_report)

        self.assertIn(snippet, cleaned)

    def test_scanned_file_boundary(self):
        """Verify loader flags/rejects scanned documents requiring Phase 3 OCR."""
        self.assertTrue(is_scanned_file("sample_fir.pdf"))
        self.assertTrue(is_scanned_file("evidence_scan.png"))
        self.assertTrue(is_scanned_file("cheque.jpg"))
        self.assertFalse(is_scanned_file("report.txt"))

        with self.assertRaises(ValueError) as ctx:
            load_document("evidence_scan.png")
        self.assertIn("Phase 3", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
