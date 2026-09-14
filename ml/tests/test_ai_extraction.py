"""Phase 3 AI-Assisted Entity & Information Extraction Unit Tests.

Verifies:
1. Candidate entity extraction across all 7 frozen CrimeLens categories:
   - PERSON, ORGANIZATION, PHONE, BANK_ACCOUNT, VEHICLE, LOCATION, EVENT
2. Multimodal context consumption (Phase 2 DocumentUnderstanding with text, pages, sections, tables)
3. Page context and evidence snippet preservation
4. Hallucination defenses:
   - Rejection of ungrounded candidate entities (not present in source document)
   - Rejection of unsupported types (CRIMINAL, SUSPECT, GANG_MEMBER, THREAT_LEVEL, etc.)
   - Handling of invalid / out-of-range / malformed confidence values
5. Controlled failure handling:
   - Provider unavailable, timeout, or malformed responses fall back safely
6. Reconciliation cases (deterministic + AI):
   - Case A: Deterministic & AI consensus (reinforce candidate, deduplicate)
   - Case B: Distinct entities preserved without blind overwrite
   - Case C: AI discovers contextual entity missed by regex/NER
   - Case D: Unsupported AI types safely ignored/rejected
7. Pipeline integration:
   - ml.pipeline.process_document compatibility with Phase 3 extraction
8. Strict isolation:
   - No database UUIDs, no case IDs, no guilt scoring, no real PII
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
    AIEntityCandidate,
    AIEntityExtractor,
    DocumentPage,
    DocumentSection,
    DocumentTable,
    DocumentUnderstanding,
    DocumentUnderstandingEngine,
    EntityReconciler,
    MockReasoningProvider,
)
from ml.config import MLConfig
from ml.pipeline import process_document
from shared.schemas.enums import EntityType
from shared.schemas.models import EntityMention, ExtractionResult


class TestAIEntityExtractionCategories(unittest.TestCase):
    """Verifies extraction of all 7 frozen CrimeLens entity categories."""

    def setUp(self):
        self.config = MLConfig(ai_enabled=True)
        # Synthetic document context
        self.doc_text = (
            "INVESTIGATION MEMORANDUM\n"
            "Subject Officer Inspector Rajesh Verma interviewed witness Sunita Rao.\n"
            "The witness was employed at Apex Logistics Pvt Ltd.\n"
            "She reported a suspicious call from mobile +91 98765 43210.\n"
            "Funds were remitted to bank account 112233445566 at Central Plaza branch.\n"
            "The suspect was seen driving black sedan DL 01 AB 1234 near Connaught Place.\n"
            "The briefing meeting occurred during the Annual Conference event."
        )
        self.pages = [
            DocumentPage(
                page_number=1,
                text=self.doc_text,
            )
        ]
        self.understanding = DocumentUnderstanding(
            document_id="doc_synth_001",
            filename="memo_001.txt",
            document_type="investigative_memo",
            language="en",
            page_count=1,
            pages=self.pages,
            sections=[
                DocumentSection(
                    title="Narrative",
                    section_type="body",
                    content=self.doc_text,
                    page_number=1,
                )
            ],
            tables=[],
            full_text=self.doc_text,
        )

    def test_extract_all_seven_supported_categories(self):
        custom_payload = {
            "entities": [
                {"type": "PERSON", "name": "Rajesh Verma", "confidence": 0.95, "page_number": 1},
                {"type": "ORGANIZATION", "name": "Apex Logistics Pvt Ltd", "confidence": 0.92, "page_number": 1},
                {"type": "PHONE", "name": "+91 98765 43210", "confidence": 0.98, "page_number": 1},
                {"type": "BANK_ACCOUNT", "name": "112233445566", "confidence": 0.94, "page_number": 1},
                {"type": "VEHICLE", "name": "DL 01 AB 1234", "confidence": 0.91, "page_number": 1},
                {"type": "LOCATION", "name": "Connaught Place", "confidence": 0.89, "page_number": 1},
                {"type": "EVENT", "name": "Annual Conference", "confidence": 0.85, "page_number": 1},
            ]
        }
        mock_provider = MockReasoningProvider(custom_payload=custom_payload)
        client = AIClient(mock_provider)
        extractor = AIEntityExtractor(client=client, config=self.config)

        candidates = extractor.extract_candidates(self.understanding)

        extracted_types = {c.type for c in candidates}
        self.assertEqual(len(candidates), 7)
        self.assertIn(EntityType.PERSON, extracted_types)
        self.assertIn(EntityType.ORGANIZATION, extracted_types)
        self.assertIn(EntityType.PHONE, extracted_types)
        self.assertIn(EntityType.BANK_ACCOUNT, extracted_types)
        self.assertIn(EntityType.VEHICLE, extracted_types)
        self.assertIn(EntityType.LOCATION, extracted_types)
        self.assertIn(EntityType.EVENT, extracted_types)

        # Validate structure of candidate
        person_cand = next(c for c in candidates if c.type == EntityType.PERSON)
        self.assertEqual(person_cand.name, "Rajesh Verma")
        self.assertEqual(person_cand.page_number, 1)
        self.assertEqual(person_cand.extraction_method, "ai")
        self.assertIsNotNone(person_cand.evidence_snippet)
        self.assertIn("Rajesh Verma", person_cand.evidence_snippet)


class TestMultimodalContextExtraction(unittest.TestCase):
    """Verifies that extraction consumes Phase 2 document representations with pages, sections, tables."""

    def test_multi_page_context_preserves_page_numbers(self):
        page1_text = "Page 1: Witness Vikram Joshi appeared at the Cyber Cell."
        page2_text = "Page 2: Phone number +91 91234 56789 was used to transfer money."
        understanding = DocumentUnderstanding(
            document_id="doc_multipage_002",
            filename="report.pdf",
            document_type="pdf_report",
            language="en",
            page_count=2,
            pages=[
                DocumentPage(page_number=1, text=page1_text),
                DocumentPage(page_number=2, text=page2_text),
            ],
            sections=[
                DocumentSection(title="Witness", section_type="body", content=page1_text, page_number=1),
                DocumentSection(title="Evidence", section_type="body", content=page2_text, page_number=2),
            ],
            tables=[],
            full_text=f"{page1_text}\n{page2_text}",
        )

        custom_payload = {
            "entities": [
                {"type": "PERSON", "name": "Vikram Joshi", "confidence": 0.93},
                {"type": "PHONE", "name": "+91 91234 56789", "confidence": 0.97},
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(understanding)
        self.assertEqual(len(candidates), 2)

        person = next(c for c in candidates if c.type == EntityType.PERSON)
        phone = next(c for c in candidates if c.type == EntityType.PHONE)

        # Page numbers automatically grounded and preserved
        self.assertEqual(person.page_number, 1)
        self.assertEqual(phone.page_number, 2)

    def test_table_understanding_extraction(self):
        table_text = "Seized Assets: Car plate MH 02 CD 5678 registered to Horizon Tech."
        understanding = DocumentUnderstanding(
            document_id="doc_table_003",
            filename="scan_table.png",
            document_type="image_scan",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text=table_text)],
            sections=[DocumentSection(title="Table Section", section_type="table", content=table_text, page_number=1)],
            tables=[
                DocumentTable(
                    title="Seized Assets",
                    headers=["Asset", "Registration", "Owner"],
                    rows=[["Car", "MH 02 CD 5678", "Horizon Tech"]],
                    page_number=1,
                )
            ],
            full_text=table_text,
            is_scanned=True,
        )

        custom_payload = {
            "entities": [
                {"type": "VEHICLE", "name": "MH 02 CD 5678", "confidence": 0.96, "page_number": 1},
                {"type": "ORGANIZATION", "name": "Horizon Tech", "confidence": 0.88, "page_number": 1},
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(understanding)
        self.assertEqual(len(candidates), 2)
        vehicle = next(c for c in candidates if c.type == EntityType.VEHICLE)
        org = next(c for c in candidates if c.type == EntityType.ORGANIZATION)
        self.assertEqual(vehicle.name, "MH 02 CD 5678")
        self.assertEqual(org.name, "Horizon Tech")


class TestHallucinationAndSafetyDefenses(unittest.TestCase):
    """Verifies that ungrounded candidates, unsupported types, and invalid confidence are rejected."""

    def setUp(self):
        self.source_text = "Complainant Ananya Roy reported an incident at South Park Mall."
        self.understanding = DocumentUnderstanding(
            document_id="doc_safety_004",
            filename="incident.txt",
            document_type="narrative",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text=self.source_text)],
            sections=[],
            tables=[],
            full_text=self.source_text,
        )

    def test_reject_ungrounded_hallucinated_candidate(self):
        """Model hallucinates an entity completely absent from the source text."""
        custom_payload = {
            "entities": [
                {"type": "PERSON", "name": "Ananya Roy", "confidence": 0.95},
                {"type": "PERSON", "name": "Ghost Hallucination Name", "confidence": 0.99},
                {"type": "PHONE", "name": "+91 99999 88888", "confidence": 0.90},  # Absent phone
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(self.understanding)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].name, "Ananya Roy")

    def test_reject_unsupported_entity_types(self):
        """Model proposes unsupported types like CRIMINAL, SUSPECT, GANG_MEMBER, THREAT_LEVEL."""
        custom_payload = {
            "entities": [
                {"type": "CRIMINAL", "name": "Ananya Roy", "confidence": 0.95},
                {"type": "SUSPECT", "name": "Ananya Roy", "confidence": 0.90},
                {"type": "GANG_MEMBER", "name": "Ananya Roy", "confidence": 0.85},
                {"type": "THREAT_LEVEL", "name": "HIGH", "confidence": 0.80},
                {"type": "PERSON", "name": "Ananya Roy", "confidence": 0.95},
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(self.understanding)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].type, EntityType.PERSON)

    def test_reject_invalid_and_out_of_range_confidence(self):
        """Model outputs negative, > 1.0, or non-numeric confidence."""
        custom_payload = {
            "entities": [
                {"type": "PERSON", "name": "Ananya Roy", "confidence": -0.5},
                {"type": "PERSON", "name": "Ananya Roy", "confidence": 2.5},
                {"type": "PERSON", "name": "Ananya Roy", "confidence": "very_high"},
                {"type": "LOCATION", "name": "South Park Mall", "confidence": 0.88},
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(self.understanding)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].name, "South Park Mall")
        self.assertEqual(candidates[0].confidence, 0.88)


class TestProviderFailureResilience(unittest.TestCase):
    """Verifies that provider failures do not crash extraction or ML processing."""

    def setUp(self):
        self.understanding = DocumentUnderstanding(
            document_id="doc_fail_005",
            filename="test.txt",
            document_type="text",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text="Sample text with Rahul Sharma.")],
            sections=[],
            tables=[],
            full_text="Sample text with Rahul Sharma.",
        )

    def test_provider_unavailable_returns_empty_candidates_safely(self):
        provider = MockReasoningProvider(simulate_unavailable=True)
        client = AIClient(provider)
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(self.understanding)
        self.assertEqual(candidates, [])

    def test_provider_timeout_returns_empty_candidates_safely(self):
        provider = MockReasoningProvider(simulate_timeout=True)
        client = AIClient(provider)
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(self.understanding)
        self.assertEqual(candidates, [])

    def test_provider_malformed_returns_empty_candidates_safely(self):
        provider = MockReasoningProvider(simulate_malformed=True)
        client = AIClient(provider)
        extractor = AIEntityExtractor(client=client, config=MLConfig(ai_enabled=True))

        candidates = extractor.extract_candidates(self.understanding)
        self.assertEqual(candidates, [])


class TestCandidateReconciliation(unittest.TestCase):
    """Verifies reconciliation between deterministic extraction and AI candidates."""

    def setUp(self):
        self.reconciler = EntityReconciler()

    def test_case_a_consensus_between_deterministic_and_ai(self):
        """Deterministic and AI both find same entity -> reinforce confidence, deduplicate, single mention."""
        deterministic = [
            EntityMention(id="mention_001", type=EntityType.PERSON, name="Rahul Sharma", confidence=0.85)
        ]
        ai_candidates = [
            AIEntityCandidate(
                type=EntityType.PERSON,
                name="Rahul Sharma",
                confidence=0.90,
                page_number=1,
            )
        ]

        reconciled = self.reconciler.reconcile(deterministic, ai_candidates)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0].id, "mention_001")
        self.assertEqual(reconciled[0].name, "Rahul Sharma")
        # Consensus slight boost
        self.assertGreaterEqual(reconciled[0].confidence, 0.90)

    def test_case_b_distinct_entities_preserved_without_overwrite(self):
        """Deterministic finds Rahul Sharma, AI finds Sunita Rao -> both preserved."""
        deterministic = [
            EntityMention(id="mention_001", type=EntityType.PERSON, name="Rahul Sharma", confidence=0.85)
        ]
        ai_candidates = [
            AIEntityCandidate(
                type=EntityType.PERSON,
                name="Sunita Rao",
                confidence=0.88,
                page_number=1,
            )
        ]

        reconciled = self.reconciler.reconcile(deterministic, ai_candidates)
        self.assertEqual(len(reconciled), 2)
        names = {r.name for r in reconciled}
        self.assertIn("Rahul Sharma", names)
        self.assertIn("Sunita Rao", names)
        self.assertEqual(reconciled[0].id, "mention_001")
        self.assertEqual(reconciled[1].id, "mention_002")

    def test_case_c_ai_discovers_contextual_entity_missed_by_deterministic(self):
        """Deterministic extracted only phone, AI extracted organization missed by regex/NER."""
        deterministic = [
            EntityMention(id="mention_001", type=EntityType.PHONE, name="+91 98765 43210", confidence=0.95)
        ]
        ai_candidates = [
            AIEntityCandidate(
                type=EntityType.ORGANIZATION,
                name="Alpha Logistics",
                confidence=0.87,
                page_number=1,
            )
        ]

        reconciled = self.reconciler.reconcile(deterministic, ai_candidates)
        self.assertEqual(len(reconciled), 2)
        types = {r.type for r in reconciled}
        self.assertIn(EntityType.PHONE, types)
        self.assertIn(EntityType.ORGANIZATION, types)

    def test_case_d_phone_normalization_deduplication(self):
        """Deterministic has raw spaces, AI has compact phone -> reconciled into single phone mention."""
        deterministic = [
            EntityMention(id="mention_001", type=EntityType.PHONE, name="+91 98765 43210", confidence=0.90)
        ]
        ai_candidates = [
            AIEntityCandidate(
                type=EntityType.PHONE,
                name="+91 9876543210",
                confidence=0.95,
                page_number=1,
            )
        ]

        reconciled = self.reconciler.reconcile(deterministic, ai_candidates)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0].type, EntityType.PHONE)


class TestPipelinePhase3Integration(unittest.TestCase):
    """Verifies that ml.pipeline.process_document seamlessly coordinates Phase 3."""

    def test_process_document_with_ai_enabled_and_custom_mock(self):
        doc_text = (
            "FIRST INFORMATION REPORT\n"
            "Complainant Vikram Patel reported fraud at Cyber City.\n"
            "Contact number +91 98765 43210 was utilized in the scam."
        )
        custom_payload = {
            "entities": [
                {"type": "PERSON", "name": "Vikram Patel", "confidence": 0.94, "page_number": 1},
                {"type": "LOCATION", "name": "Cyber City", "confidence": 0.88, "page_number": 1},
                {"type": "PHONE", "name": "+91 98765 43210", "confidence": 0.98, "page_number": 1},
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        cfg = MLConfig(ai_enabled=True)

        res: ExtractionResult = process_document(
            doc_text,
            "doc_pipeline_p3_001",
            config=cfg,
            ai_client=client,
        )

        self.assertIsInstance(res, ExtractionResult)
        self.assertEqual(res.document_id, "doc_pipeline_p3_001")
        # Check entities
        entity_names = {e.name for e in res.entities}
        self.assertIn("Vikram Patel", entity_names)
        self.assertIn("Cyber City", entity_names)
        self.assertIn("+91 98765 43210", entity_names)

        # Confirm sequential IDs are schema-compliant staging IDs (mention_001, ...)
        for e in res.entities:
            self.assertTrue(e.id.startswith("mention_"))
            self.assertFalse("-" in e.id and len(e.id) == 36)  # No database UUIDs

    def test_process_document_backward_compatibility_when_ai_disabled(self):
        """When AI is disabled (default), process_document functions identically to baseline."""
        doc_text = "Phone: +91 98765 43210. Person: Amit Kumar."
        res: ExtractionResult = process_document(doc_text, "doc_baseline_001")

        self.assertIsInstance(res, ExtractionResult)
        self.assertGreaterEqual(len(res.entities), 1)


if __name__ == "__main__":
    unittest.main()
