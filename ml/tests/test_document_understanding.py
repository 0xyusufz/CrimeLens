"""Phase 2 Multimodal Document Understanding Unit Tests.

Verifies:
1. Input router modality detection (TEXT, IMAGE, PDF, STRUCTURED)
2. Format-agnostic document understanding (Police report, Bank statement, CDR, Witness statement, Seizure memo)
3. Page context preservation across multi-page documents
4. Section identification and tabular data extraction
5. Deterministic fallback when AI provider is disabled, unavailable, or times out
6. Mock provider integration using Phase 1 foundation
7. Security: credential redaction and isolation
8. Full pipeline backward compatibility
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.ai import (
    AIClient,
    AIUnsupportedInputError,
    DocumentModality,
    DocumentPage,
    DocumentRouter,
    DocumentSection,
    DocumentTable,
    DocumentUnderstanding,
    DocumentUnderstandingEngine,
    InputType,
    MockReasoningProvider,
    MultimodalInput,
    RoutedDocument,
)
from ml.config import MLConfig
from ml.pipeline import process_document
from shared.schemas.models import ExtractionResult


class TestDocumentRouter(unittest.TestCase):
    """Verifies that the router classifies inputs accurately without assuming fixed formats."""

    def setUp(self):
        self.router = DocumentRouter()

    def test_route_plain_text_string(self):
        routed = self.router.route("Standard investigative narrative text.")
        self.assertEqual(routed.modality, DocumentModality.TEXT)
        self.assertFalse(routed.is_scanned)
        self.assertFalse(routed.requires_ocr)
        self.assertEqual(routed.multimodal_input.input_type, InputType.TEXT)

    def test_route_image_bytes(self):
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        routed = self.router.route(fake_png, filename="seized_receipt.png")
        self.assertEqual(routed.modality, DocumentModality.IMAGE)
        self.assertTrue(routed.is_scanned)
        self.assertTrue(routed.requires_ocr)
        self.assertEqual(routed.multimodal_input.mime_type, "image/png")

    def test_route_native_pdf_bytes(self):
        # Native PDF with text stream operator BT ... ET
        fake_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nBT\n/F1 12 Tf\n(Incident report) Tj\nET\nendobj"
        routed = self.router.route(fake_pdf, filename="fir_report.pdf")
        self.assertEqual(routed.modality, DocumentModality.PDF)
        self.assertFalse(routed.is_scanned)
        self.assertFalse(routed.requires_ocr)

    def test_route_scanned_pdf_bytes(self):
        # Scanned PDF without text operators
        scanned_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /XObject /Subtype /Image >>\nendobj"
        routed = self.router.route(scanned_pdf, filename="scanned_handwritten.pdf")
        self.assertEqual(routed.modality, DocumentModality.PDF)
        self.assertTrue(routed.is_scanned)
        self.assertTrue(routed.requires_ocr)

    def test_route_structured_json(self):
        json_data = '{"records": [{"id": 1, "target": "ACC-99"}]}'
        routed = self.router.route(json_data, filename="txns.json")
        self.assertEqual(routed.modality, DocumentModality.STRUCTURED)
        self.assertFalse(routed.requires_ocr)

    def test_route_structured_csv(self):
        csv_data = "caller,callee,timestamp,duration\n9876543210,9123456780,2026-09-13T10:00:00,120\n"
        routed = self.router.route(csv_data, filename="cdr.csv")
        self.assertEqual(routed.modality, DocumentModality.STRUCTURED)
        self.assertFalse(routed.requires_ocr)

    def test_route_existing_multimodal_input(self):
        m_input = MultimodalInput.from_text("Evidence note", filename="note.txt")
        routed = self.router.route(m_input)
        self.assertEqual(routed.modality, DocumentModality.TEXT)
        self.assertEqual(routed.filename, "note.txt")

    def test_route_rejects_empty_and_invalid(self):
        with self.assertRaises(AIUnsupportedInputError):
            self.router.route("")

        with self.assertRaises(AIUnsupportedInputError):
            self.router.route("   \n   ")

        with self.assertRaises(AIUnsupportedInputError):
            self.router.route(b"")

        with self.assertRaises(AIUnsupportedInputError):
            self.router.route(12345)  # type: ignore


class TestFormatAgnosticDocumentUnderstanding(unittest.TestCase):
    """Verifies that understanding works across diverse criminal investigation document types."""

    def setUp(self):
        self.engine = DocumentUnderstandingEngine()

    def test_police_report_classification_and_sections(self):
        text = (
            "FIRST INFORMATION REPORT\n"
            "Police Station: Chandrasekharpur, District: Bhubaneswar\n"
            "FIR No: 104/2026, Date: 2026-09-14\n"
            "\n"
            "Incident Details:\n"
            "Complainant reported unauthorized fund transfers to account HDFC-99120.\n"
            "Suspect Vikramaditya was seen at ATM location Nayapalli."
        )
        doc = self.engine.understand(text, filename="fir_104.txt")
        self.assertEqual(doc.document_type, "POLICE_REPORT")
        self.assertGreaterEqual(doc.confidence, 0.85)
        self.assertGreaterEqual(len(doc.sections), 2)
        # Verify incident description section was identified
        incident_sec = doc.get_section("INCIDENT_DESCRIPTION")
        self.assertIsNotNone(incident_sec)
        self.assertIn("HDFC-99120", incident_sec.content)

    def test_bank_statement_with_table(self):
        text = (
            "BANK STATEMENT - HDFC BANK\n"
            "Account Number: 50100998877, IFSC: HDFC0001234\n"
            "\n"
            "Transaction Summary:\n"
            "| Date | Description | Debit | Credit | Balance |\n"
            "| 2026-09-10 | Transfer to Rajesh | 50000 | 0 | 150000 |\n"
            "| 2026-09-11 | Transfer from Priya | 0 | 50000 | 200000 |\n"
        )
        doc = self.engine.understand(text, filename="statement.txt")
        self.assertEqual(doc.document_type, "FINANCIAL_STATEMENT")
        self.assertEqual(len(doc.tables), 1)
        table = doc.tables[0]
        self.assertIn("Debit", table.headers)
        self.assertEqual(len(table.rows), 2)
        self.assertEqual(table.rows[0][0], "2026-09-10")

    def test_call_detail_record(self):
        text = (
            "CALL DETAIL RECORD (CDR) ANALYSIS\n"
            "Target Number: 9876543210, Service Provider: Airtel\n"
            "\n"
            "Communication Log:\n"
            "Caller 9876543210 initiated 15 calls to 9123456780 within 2 hours.\n"
            "Cell Tower ID: LOC-BBSR-04."
        )
        doc = self.engine.understand(text, filename="cdr_target.txt")
        self.assertEqual(doc.document_type, "CALL_DETAIL_RECORD")
        comm_sec = doc.get_section("COMMUNICATION_RECORD")
        self.assertIsNotNone(comm_sec)
        self.assertIn("LOC-BBSR-04", comm_sec.content)

    def test_witness_statement(self):
        text = (
            "STATEMENT OF WITNESS\n"
            "Statement of Ramesh Chandra, age 45, deposes as under:\n"
            "\n"
            "Facts:\n"
            "I witnessed accused Amit Kumar handing over sealed packet to Suresh at 11:30 PM."
        )
        doc = self.engine.understand(text, filename="witness_statement.txt")
        self.assertEqual(doc.document_type, "WITNESS_STATEMENT")
        self.assertGreaterEqual(len(doc.sections), 1)

    def test_seizure_memo(self):
        text = (
            "SEIZURE MEMO / PANCHNAMA\n"
            "Place of Seizure: Railway Station Parking, Cuttack\n"
            "\n"
            "Articles Seized:\n"
            "Two Samsung mobile devices, IMEI: 867530999999999 and cash amount INR 2,50,000."
        )
        doc = self.engine.understand(text, filename="panchnama.txt")
        self.assertEqual(doc.document_type, "SEIZURE_MEMO")
        self.assertIn("867530999999999", doc.full_text)


class TestPageAwareDocumentUnderstanding(unittest.TestCase):
    """Verifies that multi-page documents preserve distinct page context and provenance."""

    def setUp(self):
        self.engine = DocumentUnderstandingEngine()

    def test_multi_page_form_feed_preservation(self):
        page_1 = "CONFIDENTIAL DOSSIER - PAGE 1\nSubject: Operation Falcon overview."
        page_2 = "CONFIDENTIAL DOSSIER - PAGE 2\nSubject details: Primary suspect alias Cobra."
        page_3 = "CONFIDENTIAL DOSSIER - PAGE 3\nFinancial assets: 3 bank accounts in Zurich."

        full_doc = f"{page_1}\f{page_2}\f{page_3}"
        doc = self.engine.understand(full_doc, filename="falcon.txt")

        self.assertEqual(doc.page_count, 3)
        self.assertEqual(len(doc.pages), 3)

        p1 = doc.get_page(1)
        p2 = doc.get_page(2)
        p3 = doc.get_page(3)

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertIsNotNone(p3)

        self.assertIn("PAGE 1", p1.text)
        self.assertIn("alias Cobra", p2.text)
        self.assertIn("Zurich", p3.text)

    def test_multi_page_header_markers(self):
        text = (
            "--- Page 1 ---\n"
            "Case registration details.\n"
            "--- Page 2 ---\n"
            "Forensic call logs analysis.\n"
        )
        doc = self.engine.understand(text, filename="case_multipage.txt")
        self.assertEqual(doc.page_count, 2)
        self.assertIn("Case registration", doc.get_page(1).text)
        self.assertIn("Forensic call logs", doc.get_page(2).text)


class TestAIProviderIntegrationAndFallback(unittest.TestCase):
    """Verifies interaction with Phase 1 AIClient and graceful offline fallback."""

    def test_offline_when_ai_disabled(self):
        config = MLConfig(ai_enabled=False)
        mock_provider = MockReasoningProvider()
        client = AIClient(mock_provider)
        engine = DocumentUnderstandingEngine(client=client, config=config)

        doc = engine.understand("First Information Report content", filename="fir.txt")
        self.assertIsInstance(doc, DocumentUnderstanding)
        self.assertEqual(doc.document_type, "POLICE_REPORT")

    def test_ai_enriched_understanding(self):
        config = MLConfig(ai_enabled=True)
        custom_ai_understanding = {
            "document_understanding": {
                "document_type": "POLICE_REPORT",
                "language": "en",
                "page_count": 1,
                "pages": [{"page_number": 1, "text": "Enriched report", "visual_elements": ["seal"]}],
                "sections": [{"title": "Header", "section_type": "METADATA", "content": "Enriched content", "confidence": 0.98}],
                "tables": [],
                "full_text": "Enriched report",
                "visual_context": {"ai_enhanced": True},
                "metadata": {"custom_model": "reasoner-v2"},
                "confidence": 0.98,
            }
        }
        mock_provider = MockReasoningProvider(custom_payload=custom_ai_understanding)
        client = AIClient(mock_provider)
        engine = DocumentUnderstandingEngine(client=client, config=config)

        doc = engine.understand("Original raw text", filename="raw.txt")
        self.assertEqual(doc.document_type, "POLICE_REPORT")
        self.assertEqual(doc.confidence, 0.98)
        self.assertIn("seal", doc.pages[0].visual_elements)

    def test_ai_provider_timeout_fallback(self):
        """When AI provider times out, engine falls back to deterministic understanding without crash."""
        config = MLConfig(ai_enabled=True)
        timeout_provider = MockReasoningProvider(simulate_timeout=True)
        client = AIClient(timeout_provider, max_retries=0)
        engine = DocumentUnderstandingEngine(client=client, config=config)

        # Must not raise AITimeoutError; falls back to deterministic parsing
        doc = engine.understand("Police Station Chandrasekharpur FIR No 55/2026", filename="fir.txt")
        self.assertIsInstance(doc, DocumentUnderstanding)
        self.assertEqual(doc.document_type, "POLICE_REPORT")


class TestSecurityAndSerialization(unittest.TestCase):
    """Verifies that secrets are not exposed in serialized understanding representations."""

    def test_to_dict_scrubs_secrets(self):
        doc = DocumentUnderstanding(
            document_id="doc_001",
            filename="fir.txt",
            document_type="POLICE_REPORT",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text="Text with sk-1234567890abcdef1234567890 token")],
            sections=[DocumentSection(title="Facts", section_type="NARRATIVE", content="Normal text")],
            tables=[],
            full_text="Text with sk-1234567890abcdef1234567890 token",
            metadata={"api_key": "secret_key_value", "safe_meta": "valid_value"},
        )
        serialized = doc.to_dict()
        self.assertNotIn("sk-1234567890abcdef1234567890", serialized["full_text"])
        self.assertIn("***REDACTED***", serialized["full_text"])
        self.assertNotIn("api_key", serialized["metadata"])
        self.assertEqual(serialized["metadata"]["safe_meta"], "valid_value")

    def test_round_trip_dict_conversion(self):
        doc = DocumentUnderstanding(
            document_id="doc_002",
            filename="statement.txt",
            document_type="FINANCIAL_STATEMENT",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text="Page 1 content")],
            sections=[DocumentSection(title="Summary", section_type="METADATA", content="Content", confidence=0.95)],
            tables=[DocumentTable(title="T1", headers=["A", "B"], rows=[["1", "2"]])],
            full_text="Page 1 content",
        )
        d = doc.to_dict()
        reconstituted = DocumentUnderstanding.from_dict(d)
        self.assertEqual(reconstituted.document_id, "doc_002")
        self.assertEqual(reconstituted.document_type, "FINANCIAL_STATEMENT")
        self.assertEqual(len(reconstituted.tables), 1)
        self.assertEqual(reconstituted.tables[0].headers, ["A", "B"])


class TestPipelineRegressionCompatibility(unittest.TestCase):
    """Verifies that ml.pipeline.process_document continues working without breaking Person A."""

    def test_process_document_default_contract(self):
        res = process_document("doc_reg_01", "Vikramaditya called Amit Kumar on 9876543210.")
        self.assertIsInstance(res, ExtractionResult)
        self.assertEqual(res.document_id, "doc_reg_01")

    def test_process_document_full_analysis_with_understanding(self):
        res = process_document(
            "doc_reg_02",
            "First Information Report under section 420. Suspect withdrew cash.",
            return_full_analysis=True,
            include_understanding=True,
        )
        self.assertIsInstance(res, dict)
        self.assertIn("extraction_result", res)
        self.assertIn("document_understanding", res)
        self.assertIsInstance(res["document_understanding"], DocumentUnderstanding)
        self.assertEqual(res["document_understanding"].document_type, "POLICE_REPORT")


if __name__ == "__main__":
    unittest.main()
