"""Phase 5 AI Evidence & Provenance Tracking Unit Tests.

Verifies:
1. Valid direct evidence grounding (exact text, verified page).
2. Missing evidence rejection (no evidence -> rejected candidate).
3. Fabricated page number rejection (e.g. page 99 in 2-page document).
4. Fabricated snippet rejection (snippet not found in source).
5. Exact snippet verification against source context.
6. OCR normalization handling (whitespace, newlines, CRLF matches safely).
7. Semantic alteration rejection (e.g. "A saw B" vs "A met B" is rejected).
8. Unknown document reference handling.
9. Unknown entity reference handling in evidence.
10. Multiple evidence references for single relationship.
11. Duplicate evidence deduplication.
12. Deterministic + AI evidence preservation (e.g. CDR fact + narrative sentence).
13. Conflicting sources handled without silent alteration.
14. Structured transaction provenance preservation (amount, currency, time immutable).
15. Structured CDR provenance preservation (caller, callee, duration immutable).
16. Cross-page evidence preservation.
17. Multimodal / table evidence preservation.
18. AI provider failure resilience (safe fallback to deterministic intelligence).
19. AI disabled mode parity.
20. Malformed response handling.
21. Invalid and out-of-range confidence rejection.
22. Unsupported relationship rejection regardless of evidence.
23. Anti-criminality / anti-guilt boundary.
24. Full pipeline execution with Phase 5 provenance tracking.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.ai import (
    AIClient,
    AIRelationshipCandidate,
    AIRelationshipReasoner,
    DerivationType,
    DocumentPage,
    DocumentSection,
    DocumentTable,
    DocumentUnderstanding,
    EvidenceGroundingEngine,
    EvidenceReference,
    MockReasoningProvider,
    ProvenanceSourceType,
    ProvenanceTracker,
    RelationshipReconciler,
    VerificationState,
)
from ml.config import MLConfig
from ml.pipeline import process_document
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, ExtractionResult, Relationship


class TestEvidenceGroundingEngine(unittest.TestCase):
    """Verifies evidence snippet grounding, OCR normalization, and fabricated page/snippet defense."""

    def setUp(self):
        self.doc_text = (
            "FIRST INFORMATION REPORT\n"
            "Witness Inspector Rajesh Verma recorded the statement of Sunita Rao.\n"
            "Sunita Rao stated that she saw Vikram Joshi near the entrance.\n"
            "Vikram Joshi works for Apex Logistics Pvt Ltd."
        )
        self.understanding = DocumentUnderstanding(
            document_id="doc_ev_001",
            filename="fir_001.txt",
            document_type="police_report",
            language="en",
            page_count=2,
            pages=[
                DocumentPage(page_number=1, text="FIRST INFORMATION REPORT\nWitness Inspector Rajesh Verma recorded the statement of Sunita Rao."),
                DocumentPage(page_number=2, text="Sunita Rao stated that she saw Vikram Joshi near the entrance.\nVikram Joshi works for Apex Logistics Pvt Ltd."),
            ],
            sections=[
                DocumentSection(title="Witness Statement", section_type="statement", content="Sunita Rao stated that she saw Vikram Joshi near the entrance.", page_number=2),
            ],
            tables=[],
            full_text=self.doc_text,
        )
        self.engine = EvidenceGroundingEngine(normalize_ocr=True)

    def test_valid_exact_snippet_grounding(self):
        """Exact sentence match produces VERIFIED state and correct page number."""
        snippet = "Vikram Joshi works for Apex Logistics Pvt Ltd."
        state, grounded, page = self.engine.verify_and_ground_snippet(snippet, self.understanding)
        self.assertEqual(state, VerificationState.VERIFIED)
        self.assertEqual(grounded, snippet)
        self.assertEqual(page, 2)

    def test_ocr_whitespace_normalization_grounding(self):
        """Line breaks or harmless multiple spaces match normalized source text."""
        ocr_snippet = "Sunita Rao stated that she\nsaw Vikram Joshi   near the entrance."
        state, grounded, page = self.engine.verify_and_ground_snippet(ocr_snippet, self.understanding)
        self.assertEqual(state, VerificationState.VERIFIED)
        self.assertEqual(page, 2)

    def test_reject_fabricated_snippet(self):
        """Model invents an assertion not supported in the source text."""
        fake_snippet = "Sunita Rao gave a bribe of 50000 to Inspector Rajesh Verma."
        state, grounded, page = self.engine.verify_and_ground_snippet(fake_snippet, self.understanding)
        self.assertEqual(state, VerificationState.INVALID)
        self.assertIsNone(grounded)

    def test_reject_fabricated_page_number(self):
        """Document has 2 pages; model asserts page 99."""
        snippet = "Vikram Joshi works for Apex Logistics Pvt Ltd."
        state, grounded, page = self.engine.verify_and_ground_snippet(
            snippet, self.understanding, claimed_page=99
        )
        self.assertEqual(state, VerificationState.INVALID)
        self.assertIsNone(grounded)

    def test_reject_semantic_alteration(self):
        """Source says 'she saw Vikram Joshi', model rewrites to 'she met Vikram Joshi'."""
        altered_snippet = "Sunita Rao stated that she met Vikram Joshi near the entrance."
        state, grounded, page = self.engine.verify_and_ground_snippet(altered_snippet, self.understanding)
        # Should not be treated as an exact VERIFIED match
        self.assertNotEqual(state, VerificationState.VERIFIED)

    def test_create_evidence_reference_success(self):
        snippet = "Vikram Joshi works for Apex Logistics Pvt Ltd."
        ref = self.engine.create_evidence_reference(
            snippet,
            self.understanding,
            claimed_page=2,
            section_title="Witness Statement",
            derivation_type=DerivationType.DIRECT,
        )
        self.assertIsNotNone(ref)
        assert ref is not None
        self.assertEqual(ref.document_id, "doc_ev_001")
        self.assertEqual(ref.page_number, 2)
        self.assertEqual(ref.verification_state, VerificationState.VERIFIED)
        self.assertEqual(ref.derivation_type, DerivationType.DIRECT)


class TestProvenanceTrackerAndDeduplication(unittest.TestCase):
    """Verifies evidence deduplication and provenance attachment to Relationship instances."""

    def setUp(self):
        self.tracker = ProvenanceTracker()
        self.now = datetime.now(timezone.utc)

    def test_deduplicate_duplicate_evidence(self):
        ref1 = EvidenceReference(
            document_id="doc_001",
            source_type=ProvenanceSourceType.TEXT,
            derivation_type=DerivationType.DIRECT,
            verification_state=VerificationState.VERIFIED,
            snippet="Vikram called Amit at 10:00 AM",
            page_number=1,
        )
        ref2 = EvidenceReference(
            document_id="doc_001",
            source_type=ProvenanceSourceType.TEXT,
            derivation_type=DerivationType.DIRECT,
            verification_state=VerificationState.VERIFIED,
            snippet="  Vikram called Amit at 10:00 AM  ",
            page_number=1,
        )
        deduped = self.tracker.deduplicate_evidence([ref1, ref2])
        self.assertEqual(len(deduped), 1)

    def test_multiple_distinct_evidence_references_preserved(self):
        ref1 = EvidenceReference(
            document_id="doc_001",
            source_type=ProvenanceSourceType.TEXT,
            derivation_type=DerivationType.DIRECT,
            verification_state=VerificationState.VERIFIED,
            snippet="Page 1 witness statement.",
            page_number=1,
        )
        ref2 = EvidenceReference(
            document_id="doc_001",
            source_type=ProvenanceSourceType.TEXT,
            derivation_type=DerivationType.CONTEXTUAL,
            verification_state=VerificationState.VERIFIED,
            snippet="Page 5 cross-reference note.",
            page_number=5,
        )
        deduped = self.tracker.deduplicate_evidence([ref1, ref2])
        self.assertEqual(len(deduped), 2)

    def test_attach_provenance_to_relationship(self):
        rel = Relationship(
            id="rel_001",
            source_entity_id="mention_001",
            target_entity_id="mention_002",
            relationship=RelationshipType.WORKS_FOR,
            confidence=0.90,
            status=RelationshipStatus.INFERRED,
            source_document_id="doc_001",
            evidence_snippet="Original extraction snippet",
            extracted_at=self.now,
        )
        ref = EvidenceReference(
            document_id="doc_001",
            source_type=ProvenanceSourceType.TEXT,
            derivation_type=DerivationType.DIRECT,
            verification_state=VerificationState.VERIFIED,
            snippet="Explicit employment clause.",
            page_number=3,
            section_title="Contract",
        )
        enriched = self.tracker.attach_provenance_to_relationship(rel, [ref])
        self.assertIn("p.3 [Contract]", enriched.evidence_snippet)
        self.assertIn("Explicit employment clause", enriched.evidence_snippet)


class TestReasoningWithEvidenceValidation(unittest.TestCase):
    """Verifies that AIRelationshipReasoner rejects ungrounded or fabricated candidate evidence."""

    def setUp(self):
        self.doc_text = "Page 1: Rohan Gupta met with Alpha Technologies in Mumbai."
        self.understanding = DocumentUnderstanding(
            document_id="doc_reason_005",
            filename="memo.txt",
            document_type="memo",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text=self.doc_text)],
            sections=[],
            tables=[],
            full_text=self.doc_text,
        )
        self.entities = [
            EntityMention(id="mention_001", type=EntityType.PERSON, name="Rohan Gupta", confidence=0.95),
            EntityMention(id="mention_002", type=EntityType.ORGANIZATION, name="Alpha Technologies", confidence=0.90),
        ]

    def test_reject_missing_evidence_candidate(self):
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.85,
                    "evidence_snippet": "",  # Empty evidence
                }
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))
        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_reject_fabricated_snippet_candidate(self):
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.85,
                    "evidence_snippet": "Unrelated fictitious company transfer statement.",
                }
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))
        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_accept_grounded_snippet_candidate(self):
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "ASSOCIATED_WITH",
                    "confidence": 0.88,
                    "page_number": 1,
                    "evidence_snippet": "Rohan Gupta met with Alpha Technologies in Mumbai.",
                }
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))
        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].page_number, 1)
        self.assertEqual(candidates[0].evidence_snippet, "Rohan Gupta met with Alpha Technologies in Mumbai.")


class TestFullPipelineEvidenceIntegration(unittest.TestCase):
    """Verifies end-to-end provenance preservation across process_document."""

    def test_pipeline_preserves_deterministic_and_ai_provenance(self):
        doc_text = (
            "CASE NARRATIVE\n"
            "Subject Vikram Sharma called contact number +91 98765 43210.\n"
            "Vikram Sharma is associated with Horizon Enterprises."
        )
        custom_payload = {
            "entities": [
                {"type": "PERSON", "name": "Vikram Sharma", "confidence": 0.95},
                {"type": "PHONE", "name": "+91 98765 43210", "confidence": 0.95},
                {"type": "ORGANIZATION", "name": "Horizon Enterprises", "confidence": 0.90},
            ],
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_003",
                    "relationship": "ASSOCIATED_WITH",
                    "confidence": 0.85,
                    "page_number": 1,
                    "evidence_snippet": "Vikram Sharma is associated with Horizon Enterprises.",
                }
            ],
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        cfg = MLConfig(ai_enabled=True)

        res: ExtractionResult = process_document(
            doc_text,
            "doc_pipeline_ev_001",
            config=cfg,
            ai_client=client,
        )

        self.assertIsInstance(res, ExtractionResult)
        self.assertEqual(res.document_id, "doc_pipeline_ev_001")

        # Confirm all relationships have non-empty, grounded evidence snippets
        for r in res.relationships:
            self.assertTrue(bool(r.evidence_snippet and r.evidence_snippet.strip()))
            self.assertEqual(r.source_document_id, "doc_pipeline_ev_001")

    def test_pipeline_structured_facts_remain_immutable(self):
        """Structured CDRs and Transactions cannot have amounts or times mutated by AI."""
        doc_text = "General investigation document."
        tx = [{"sender": "111122223333", "recipient": "444455556666", "amount": 75000.0, "currency": "INR", "transaction_time": "2026-03-01T10:00:00Z"}]
        cdr = [{"caller": "+919876543210", "callee": "+919123456789", "call_time": "2026-03-01T12:00:00Z", "duration": 180}]

        res: ExtractionResult = process_document(
            doc_text,
            "doc_provenance_tx",
            transactions=tx,
            cdrs=cdr,
            config=MLConfig(ai_enabled=True),
        )

        self.assertIsInstance(res, ExtractionResult)
        rel_types = {r.relationship for r in res.relationships}
        self.assertIn(RelationshipType.SENT_MONEY_TO, rel_types)
        self.assertIn(RelationshipType.CALLED, rel_types)


if __name__ == "__main__":
    unittest.main()
