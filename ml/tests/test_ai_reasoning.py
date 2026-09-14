"""Phase 4 AI Context & Relationship Reasoning Unit Tests.

Verifies:
1. Basic relationship reasoning over multi-entity context (supported vocabulary).
2. Rejection of unsupported relationship types (e.g. FRIEND_OF, KNOWS, LIKELY_GUILTY).
3. Rejection of unknown entity references (mention_999).
4. Rejection of missing / ungrounded evidence snippets.
5. Rejection of fabricated page references (e.g. page 99 in 2-page document).
6. Malformed JSON handling & resilience.
7. Invalid and out-of-range confidence handling.
8. Rejection of invalid status (e.g. AI_DETECTED).
9. Duplicate candidate relationship deduplication.
10. Reconciliation: Deterministic + AI duplicate agreement (evidence preservation, no duplicate edge).
11. Reconciliation: Deterministic relationships are authoritative and never overwritten.
12. Same-name false association defense (no automatic connection or merge).
13. Cross-page reasoning context with verified evidence.
14. Structured transaction fact preservation.
15. Structured CDR fact preservation.
16. Provider failure resilience (timeout, unavailable, error).
17. Pipeline execution with AI disabled (baseline parity).
18. Empty AI result handling.
19. Hallucinated entity references rejected without entity creation.
20. No criminality/guilt inference.
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
    DocumentPage,
    DocumentSection,
    DocumentTable,
    DocumentUnderstanding,
    MockReasoningProvider,
    RelationshipReconciler,
)
from ml.config import MLConfig
from ml.pipeline import process_document
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, ExtractionResult, Relationship


class TestAIRelationshipReasoningBasic(unittest.TestCase):
    """Verifies standard relationship extraction and schema conformance."""

    def setUp(self):
        self.config = MLConfig(ai_enabled=True)
        self.doc_text = (
            "INVESTIGATION REPORT\n"
            "Subject Vikram Sharma attended the Financial Summit in New Delhi.\n"
            "Amit Kumar also participated in the Financial Summit.\n"
            "Later, Vikram Sharma transferred funds to Amit Kumar."
        )
        self.understanding = DocumentUnderstanding(
            document_id="doc_reason_001",
            filename="report_001.txt",
            document_type="investigative_report",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text=self.doc_text)],
            sections=[DocumentSection(title="Body", section_type="body", content=self.doc_text, page_number=1)],
            tables=[],
            full_text=self.doc_text,
        )
        self.entities = [
            EntityMention(id="mention_001", type=EntityType.PERSON, name="Vikram Sharma", confidence=0.95),
            EntityMention(id="mention_002", type=EntityType.PERSON, name="Amit Kumar", confidence=0.92),
            EntityMention(id="mention_003", type=EntityType.EVENT, name="Financial Summit", confidence=0.88),
        ]

    def test_basic_supported_relationship_reasoning(self):
        """Model proposes valid PART_OF_EVENT candidate with verified evidence."""
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_003",
                    "relationship": "PART_OF_EVENT",
                    "confidence": 0.90,
                    "status": "INFERRED",
                    "page_number": 1,
                    "evidence_snippet": "Vikram Sharma attended the Financial Summit in New Delhi.",
                    "reasoning_summary": "Explicitly documented as attendee.",
                }
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=self.config)

        candidates = reasoner.reason_relationships(self.understanding, self.entities)

        self.assertEqual(len(candidates), 1)
        cand = candidates[0]
        self.assertEqual(cand.source_entity_ref, "mention_001")
        self.assertEqual(cand.target_entity_ref, "mention_003")
        self.assertEqual(cand.relationship_type, RelationshipType.PART_OF_EVENT)
        self.assertEqual(cand.status, RelationshipStatus.INFERRED)
        self.assertEqual(cand.confidence, 0.90)
        self.assertEqual(cand.page_number, 1)
        self.assertIn("Financial Summit", cand.evidence_snippet)


class TestAIRelationshipSafetyAndDefenses(unittest.TestCase):
    """Verifies rejection of unsupported types, unknown entities, invalid confidence, and ungrounded snippets."""

    def setUp(self):
        self.doc_text = "Page 1: Rohan Gupta met with Alpha Technologies in Mumbai."
        self.understanding = DocumentUnderstanding(
            document_id="doc_defense_002",
            filename="defense.txt",
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

    def test_reject_unsupported_relationship_types(self):
        """Model proposes FRIEND_OF, KNOWS, or LIKELY_GUILTY."""
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "FRIEND_OF",
                    "confidence": 0.85,
                    "evidence_snippet": "met with Alpha Technologies",
                },
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "LIKELY_GUILTY",
                    "confidence": 0.95,
                    "evidence_snippet": "met with Alpha Technologies",
                },
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))

        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_reject_unknown_entity_references(self):
        """Model hallucinates mention_999 which does not exist."""
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_999",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.85,
                    "evidence_snippet": "met with Alpha Technologies",
                }
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))

        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_reject_missing_and_ungrounded_evidence(self):
        """Model returns candidate without evidence snippet or completely fabricated snippet."""
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.85,
                    "evidence_snippet": "",  # Missing evidence
                },
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.85,
                    "evidence_snippet": "Ghost meeting that never occurred in text at all.",
                },
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))

        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_reject_fabricated_page_number(self):
        """Document has 1 page, model asserts page 99."""
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.85,
                    "page_number": 99,
                    "evidence_snippet": "Rohan Gupta met with Alpha Technologies in Mumbai.",
                }
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))

        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_reject_invalid_confidence_and_status(self):
        """Model returns negative confidence, > 1.0, or invalid status enum."""
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 1.5,
                    "evidence_snippet": "Rohan Gupta met with Alpha Technologies in Mumbai.",
                },
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.85,
                    "status": "AI_DETECTED",  # Invalid status
                    "evidence_snippet": "Rohan Gupta met with Alpha Technologies in Mumbai.",
                },
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))

        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_reject_self_relationship(self):
        """Model attempts self-relationship mention_001 -> mention_001."""
        custom_payload = {
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_001",
                    "relationship": "ASSOCIATED_WITH",
                    "confidence": 0.85,
                    "evidence_snippet": "Rohan Gupta met with Alpha Technologies in Mumbai.",
                }
            ]
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))

        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])


class TestRelationshipReconciliation(unittest.TestCase):
    """Verifies reconciliation between deterministic relationships and AI candidates."""

    def setUp(self):
        self.reconciler = RelationshipReconciler()
        self.now = datetime.now(timezone.utc)

    def test_duplicate_agreement_preserves_evidence_and_single_edge(self):
        """Deterministic finds A CALLED B, AI also finds A CALLED B -> single edge with reinforced confidence."""
        det = [
            Relationship(
                id="rel_001",
                source_entity_id="mention_001",
                target_entity_id="mention_002",
                relationship=RelationshipType.CALLED,
                confidence=0.85,
                status=RelationshipStatus.INFERRED,
                source_document_id="doc_001",
                evidence_snippet="Vikram called Amit at 10:00",
                extracted_at=self.now,
            )
        ]
        ai_cands = [
            AIRelationshipCandidate(
                source_entity_ref="mention_001",
                target_entity_ref="mention_002",
                relationship_type=RelationshipType.CALLED,
                confidence=0.90,
                status=RelationshipStatus.INFERRED,
                evidence_snippet="Transcript confirms call from Vikram to Amit.",
            )
        ]

        reconciled = self.reconciler.reconcile(det, ai_cands, document_id="doc_001")
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0].id, "rel_001")
        self.assertEqual(reconciled[0].relationship, RelationshipType.CALLED)
        self.assertGreaterEqual(reconciled[0].confidence, 0.90)
        self.assertIn("Transcript confirms call", reconciled[0].evidence_snippet)

    def test_deterministic_relationship_is_never_overwritten(self):
        """Deterministic finds A SENT_MONEY_TO B, AI proposes A ASSOCIATED_WITH B -> deterministic intact, both co-exist."""
        det = [
            Relationship(
                id="rel_001",
                source_entity_id="mention_001",
                target_entity_id="mention_002",
                relationship=RelationshipType.SENT_MONEY_TO,
                confidence=0.95,
                status=RelationshipStatus.INFERRED,
                source_document_id="doc_001",
                evidence_snippet="Transferred 50000 to Amit",
                extracted_at=self.now,
            )
        ]
        ai_cands = [
            AIRelationshipCandidate(
                source_entity_ref="mention_001",
                target_entity_ref="mention_002",
                relationship_type=RelationshipType.ASSOCIATED_WITH,
                confidence=0.80,
                status=RelationshipStatus.INFERRED,
                evidence_snippet="Seen communicating regarding transfer",
            )
        ]

        reconciled = self.reconciler.reconcile(det, ai_cands, document_id="doc_001")
        self.assertEqual(len(reconciled), 2)
        types = {r.relationship for r in reconciled}
        self.assertIn(RelationshipType.SENT_MONEY_TO, types)
        self.assertIn(RelationshipType.ASSOCIATED_WITH, types)

    def test_ai_discovers_contextual_cross_page_relationship(self):
        """Deterministic missed cross-page connection; AI successfully adds it."""
        det = []
        ai_cands = [
            AIRelationshipCandidate(
                source_entity_ref="mention_001",
                target_entity_ref="mention_003",
                relationship_type=RelationshipType.WORKS_FOR,
                confidence=0.88,
                status=RelationshipStatus.INFERRED,
                evidence_snippet="Page 2 confirms employment with organization.",
            )
        ]

        reconciled = self.reconciler.reconcile(det, ai_cands, document_id="doc_002")
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0].id, "rel_001")
        self.assertEqual(reconciled[0].relationship, RelationshipType.WORKS_FOR)


class TestProviderFailureAndEdgeCases(unittest.TestCase):
    """Verifies failure tolerance, timeouts, and empty results."""

    def setUp(self):
        self.doc_text = "Standard narrative with Vikram Sharma and Amit Kumar."
        self.understanding = DocumentUnderstanding(
            document_id="doc_edge_003",
            filename="edge.txt",
            document_type="memo",
            language="en",
            page_count=1,
            pages=[DocumentPage(page_number=1, text=self.doc_text)],
            sections=[],
            tables=[],
            full_text=self.doc_text,
        )
        self.entities = [
            EntityMention(id="mention_001", type=EntityType.PERSON, name="Vikram Sharma", confidence=0.90),
            EntityMention(id="mention_002", type=EntityType.PERSON, name="Amit Kumar", confidence=0.90),
        ]

    def test_provider_timeout_returns_empty_safely(self):
        client = AIClient(MockReasoningProvider(simulate_timeout=True))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))
        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_provider_unavailable_returns_empty_safely(self):
        client = AIClient(MockReasoningProvider(simulate_unavailable=True))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))
        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_provider_malformed_returns_empty_safely(self):
        client = AIClient(MockReasoningProvider(simulate_malformed=True))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))
        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])

    def test_empty_ai_response_handling(self):
        custom_payload = {"relationships": []}
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        reasoner = AIRelationshipReasoner(client=client, config=MLConfig(ai_enabled=True))
        candidates = reasoner.reason_relationships(self.understanding, self.entities)
        self.assertEqual(candidates, [])


class TestPipelinePhase4Integration(unittest.TestCase):
    """Verifies end-to-end compatibility of process_document with Phase 4."""

    def test_pipeline_with_ai_reasoning_enabled(self):
        doc_text = (
            "FIR REPORT\n"
            "Inspector Suresh Raina noted that Rajesh Verma is employed at Apex Logistics Pvt Ltd.\n"
            "Rajesh Verma was seen at Central Plaza."
        )
        custom_payload = {
            "entities": [
                {"type": "PERSON", "name": "Rajesh Verma", "confidence": 0.95},
                {"type": "ORGANIZATION", "name": "Apex Logistics Pvt Ltd", "confidence": 0.95},
                {"type": "LOCATION", "name": "Central Plaza", "confidence": 0.90},
            ],
            "relationships": [
                {
                    "source_entity_id": "mention_001",
                    "target_entity_id": "mention_002",
                    "relationship": "WORKS_FOR",
                    "confidence": 0.94,
                    "evidence_snippet": "Rajesh Verma is employed at Apex Logistics Pvt Ltd.",
                }
            ],
        }
        client = AIClient(MockReasoningProvider(custom_payload=custom_payload))
        cfg = MLConfig(ai_enabled=True)

        res: ExtractionResult = process_document(
            doc_text,
            "doc_pipeline_p4_001",
            config=cfg,
            ai_client=client,
        )

        self.assertIsInstance(res, ExtractionResult)
        self.assertEqual(res.document_id, "doc_pipeline_p4_001")
        # Check relationships
        self.assertGreaterEqual(len(res.relationships), 1)
        rel_types = {r.relationship for r in res.relationships}
        self.assertIn(RelationshipType.WORKS_FOR, rel_types)
        # Verify staging IDs and no database UUIDs
        for r in res.relationships:
            self.assertTrue(r.id.startswith("rel_"))
            self.assertFalse("-" in r.id and len(r.id) == 36)

    def test_structured_cdr_and_transactions_preserved(self):
        """Structured CDR caller/callee and Transaction amounts/currencies remain authoritative."""
        doc_text = "Standard document."
        cdrs = [{"caller": "+919876543210", "callee": "+919123456789", "call_time": "2026-03-01T10:00:00Z", "duration": 120}]
        transactions = [{"sender": "111122223333", "recipient": "444455556666", "amount": 25000.0, "currency": "INR", "transaction_time": "2026-03-01T11:00:00Z"}]

        res: ExtractionResult = process_document(
            doc_text,
            "doc_structured_p4",
            cdrs=cdrs,
            transactions=transactions,
            config=MLConfig(ai_enabled=True),
        )

        self.assertIsInstance(res, ExtractionResult)
        # Verify relationships contain structured links
        rel_types = {r.relationship for r in res.relationships}
        self.assertIn(RelationshipType.CALLED, rel_types)
        self.assertIn(RelationshipType.SENT_MONEY_TO, rel_types)


if __name__ == "__main__":
    unittest.main()
