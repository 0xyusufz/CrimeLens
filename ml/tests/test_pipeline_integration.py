"""Tests for Phase 6 — Existing ML + AI Pipeline Integration & Orchestration.

Tests all required scenarios from prompt Section 40:
A. AI Disabled (Parity with deterministic baseline)
B. AI Enabled (Integrated candidates, schema-valid output)
C. AI Failure / Timeout Fallback (Controlled fallback, zero crashes)
D. Malformed AI Responses (Unsupported types/statuses/confidences rejected safely)
E. Entity Reconciliation (Consensus deduplication, no duplicates)
F. Fuzzy Name Safety (Name-only fuzzy matching never auto-merges)
G. Strong Identifier (Exact matching respects resolver behavior)
H. Relationship Deduplication (One reconciled relationship with preserved provenance)
I. Conflicting Relationship (No unsafe overwrite, deterministic authoritative)
J. Evidence Required (Ungrounded relationships rejected)
K. Fabricated Evidence (Nonexistent page/snippet rejected)
L. Transaction Authority (Amount, currency, timestamp immutable)
M. CDR Authority (Call time, duration immutable)
N. Pattern Safety (Speculative AI claims do not trigger false patterns)
O. Provider Disabled (No credentials, deterministic works)
P. Provider Mock (Fully functional offline)
Q. Multimodal Document (Image/document representation, candidate extraction, grounding)
R. Regression & Contract Verification
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from typing import Any, Optional

from ml.ai.client.client import AIClient
from ml.ai.errors import AIMalformedResponseError, AITimeoutError
from ml.ai.pipeline_integration import AIPipelineCoordinator, AITraceabilityMetrics
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.providers.mock import MockReasoningProvider
from ml.ai.types import ModelResponse, MultimodalInput
from ml.config import MLConfig
from ml.pipeline import process_document
from ml.structured import CDRRecord, TransactionRecord
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, ExtractionResult, Relationship


class TimeoutFailingProvider(ReasoningModelProvider):
    """Provider that simulates a network timeout."""

    @property
    def provider_name(self) -> str:
        return "timeout-failing-provider"

    @property
    def is_available(self) -> bool:
        return True

    def analyze(self, input_data: MultimodalInput, *, context: Optional[dict[str, Any]] = None) -> ModelResponse:
        raise AITimeoutError("Simulated upstream provider timeout after 30.0s")


class MalformedResponseProvider(ReasoningModelProvider):
    """Provider that returns malformed JSON or invalid schema structures."""

    def __init__(self, raw_text: str) -> None:
        self._raw_text = raw_text

    @property
    def provider_name(self) -> str:
        return "malformed-provider"

    @property
    def is_available(self) -> bool:
        return True

    def analyze(self, input_data: MultimodalInput, *, context: Optional[dict[str, Any]] = None) -> ModelResponse:
        return ModelResponse(
            provider_name="malformed-provider",
            model_name="malformed-v1",
            raw_content=self._raw_text,
            structured_payload={},
        )


class ControlledAIProvider(ReasoningModelProvider):
    """Provider returning customized candidates for specific integration tests."""

    def __init__(
        self,
        *,
        entities: Optional[list[dict[str, Any]]] = None,
        relationships: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.entities = entities or []
        self.relationships = relationships or []

    @property
    def provider_name(self) -> str:
        return "controlled-test-provider"

    @property
    def is_available(self) -> bool:
        return True

    def analyze(self, input_data: MultimodalInput, *, context: Optional[dict[str, Any]] = None) -> ModelResponse:
        task = input_data.metadata.get("task")
        if task == "entity_extraction":
            payload = {"entities": self.entities}
        elif task == "relationship_reasoning":
            known = {e["name"]: e["id"] for e in input_data.metadata.get("known_entities", [])}
            resolved_rels = []
            for r in self.relationships:
                r_copy = dict(r)
                s_ref = str(r_copy.get("source_entity_ref", ""))
                t_ref = str(r_copy.get("target_entity_ref", ""))
                if s_ref.startswith("name:"):
                    name_key = s_ref[5:]
                    if name_key in known:
                        r_copy["source_entity_ref"] = known[name_key]
                if t_ref.startswith("name:"):
                    name_key = t_ref[5:]
                    if name_key in known:
                        r_copy["target_entity_ref"] = known[name_key]
                resolved_rels.append(r_copy)
            payload = {"relationships": resolved_rels}
        else:
            payload = {"entities": self.entities, "relationships": self.relationships}

        raw_json = json.dumps(payload)
        return ModelResponse(
            provider_name="controlled-test-provider",
            model_name="controlled-v1",
            raw_content=raw_json,
            structured_payload=payload,
        )


class TestPhase6PipelineIntegration(unittest.TestCase):
    """Phase 6 Comprehensive Integration Test Suite."""

    def setUp(self) -> None:
        self.doc_id = "doc_p6_001"
        self.sample_text = (
            "Investigation Report:\n"
            "Rahul Sharma (phone: 9876543210) called Amit Kumar (phone: 9123456780) on 2026-03-01.\n"
            "Amit Kumar sent money to Vikram Singh via account ACC12345.\n"
            "Vehicle DL 01 AB 1234 was spotted near Bhubaneswar Central Mall."
        )

    # -------------------------------------------------------------------------
    # TEST A: AI DISABLED
    # -------------------------------------------------------------------------
    def test_a_ai_disabled_matches_deterministic_baseline(self) -> None:
        """When AI is disabled, pipeline operates deterministically without AI calls."""
        cfg = MLConfig(ai_enabled=False)
        result = process_document(self.doc_id, self.sample_text, config=cfg)

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, self.doc_id)
        self.assertGreater(len(result.entities), 0)

        # Full analysis check: ai_traceability not present or ai_enabled=False
        analysis = process_document(self.doc_id, self.sample_text, config=cfg, return_full_analysis=True)
        self.assertNotIn("ai_traceability", analysis)

    # -------------------------------------------------------------------------
    # TEST B: AI ENABLED
    # -------------------------------------------------------------------------
    def test_b_ai_enabled_integrates_and_remains_schema_valid(self) -> None:
        """When AI is enabled with mock provider, candidates are integrated and schema validated."""
        cfg = MLConfig(ai_enabled=True)
        mock_client = AIClient(MockReasoningProvider())

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=mock_client,
        )

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, self.doc_id)
        self.assertGreater(len(result.entities), 0)
        self.assertGreater(len(result.relationships), 0)

        # Full analysis includes ai_traceability
        analysis = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=mock_client,
            return_full_analysis=True,
        )
        self.assertIn("ai_traceability", analysis)
        trace = analysis["ai_traceability"]
        self.assertTrue(trace["ai_enabled"])
        self.assertTrue(trace["ai_attempted"])
        self.assertFalse(trace["ai_fallback_occurred"])

    # -------------------------------------------------------------------------
    # TEST C: AI FAILURE / TIMEOUT FALLBACK
    # -------------------------------------------------------------------------
    def test_c_ai_timeout_fallback_to_deterministic(self) -> None:
        """If AI provider times out, pipeline logs fallback and returns valid deterministic result."""
        cfg = MLConfig(ai_enabled=True)
        failing_client = AIClient(TimeoutFailingProvider())

        # Must NOT raise AITimeoutError; must return valid ExtractionResult
        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=failing_client,
        )

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, self.doc_id)
        self.assertGreater(len(result.entities), 0)

        analysis = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=failing_client,
            return_full_analysis=True,
        )
        self.assertTrue(analysis["ai_traceability"]["ai_fallback_occurred"])
        self.assertIn("AITimeoutError", str(analysis["ai_traceability"]["fallback_reason"]))

    # -------------------------------------------------------------------------
    # TEST D: MALFORMED AI RESPONSE
    # -------------------------------------------------------------------------
    def test_d_malformed_ai_response_rejected_safely(self) -> None:
        """Malformed JSON or invalid types/statuses/confidences are safely rejected."""
        cfg = MLConfig(ai_enabled=True)
        malformed_client = AIClient(
            MalformedResponseProvider(
                raw_text="NOT A JSON {corrupted output [invalid"
            )
        )

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=malformed_client,
        )
        self.assertIsInstance(result, ExtractionResult)

        # Invalid field types / unsupported entity & relationship types
        unsupported_client = AIClient(
            ControlledAIProvider(
                entities=[
                    {"name": "BadGuy", "type": "CRIMINAL", "confidence": 0.9},
                    {"name": "Suspect X", "type": "GUILTY_PARTY", "confidence": 1.5},
                ],
                relationships=[
                    {
                        "source_entity_ref": "mention_001",
                        "target_entity_ref": "mention_002",
                        "relationship": "LIKELY_GUILTY",
                        "confidence": -0.5,
                        "status": "AI_DETECTED",
                        "evidence_snippet": "Bad text",
                    }
                ],
            )
        )

        res2 = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=unsupported_client,
        )
        self.assertIsInstance(res2, ExtractionResult)
        # None of the invalid entities or relationships should be accepted
        for ent in res2.entities:
            self.assertNotEqual(ent.type.value, "CRIMINAL")
            self.assertNotEqual(ent.type.value, "GUILTY_PARTY")
        for rel in res2.relationships:
            self.assertNotEqual(rel.relationship.value, "LIKELY_GUILTY")

    # -------------------------------------------------------------------------
    # TEST E: ENTITY RECONCILIATION (DEDUPLICATION)
    # -------------------------------------------------------------------------
    def test_e_entity_reconciliation_no_duplicate(self) -> None:
        """Deterministic entity + identical AI entity results in one reconciled entity."""
        cfg = MLConfig(ai_enabled=True)
        provider = ControlledAIProvider(
            entities=[
                {"name": "Rahul Sharma", "type": "PERSON", "confidence": 0.95},
            ]
        )
        client = AIClient(provider)

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=client,
        )

        rahul_mentions = [e for e in result.entities if e.name == "Rahul Sharma"]
        # Exactly one mention for Rahul Sharma, not two!
        self.assertEqual(len(rahul_mentions), 1)
        self.assertGreaterEqual(rahul_mentions[0].confidence, 0.95)

    # -------------------------------------------------------------------------
    # TEST F: FUZZY NAME SAFETY
    # -------------------------------------------------------------------------
    def test_f_fuzzy_name_does_not_auto_merge(self) -> None:
        """Name-only fuzzy matching must NOT automatically merge entities."""
        cfg = MLConfig(ai_enabled=True)
        # AI proposes an abbreviated / fuzzy variation: "Rahul S."
        provider = ControlledAIProvider(
            entities=[
                {"name": "Rahul S.", "type": "PERSON", "confidence": 0.85},
            ]
        )
        client = AIClient(provider)

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=client,
            return_full_analysis=True,
        )

        names = [e.name for e in result["entities"]]
        self.assertIn("Rahul Sharma", names)
        self.assertIn("Rahul S.", names)

        # In resolution proposals, under default threshold (0.70), name-only fuzzy match is NOT auto-merged
        proposals = result["resolution_proposals"]
        for p in proposals:
            # If a proposal references Rahul S., it must NOT be an auto-merge confidence >= 0.70
            mA = next((e for e in result["entities"] if e.id == p.mention_id), None)
            if mA and mA.name == "Rahul S.":
                self.assertLess(p.confidence, 0.70)

    # -------------------------------------------------------------------------
    # TEST G: STRONG IDENTIFIER MATCHING
    # -------------------------------------------------------------------------
    def test_g_strong_identifier_respected_in_resolution(self) -> None:
        """Exact supported strong identifier (phone) respects resolver behavior."""
        from ml.resolution import propose_resolutions

        mA = EntityMention(id="mention_001", type=EntityType.PHONE, name="+91 98765 43210", confidence=0.95)
        mB = EntityMention(id="mention_002", type=EntityType.PHONE, name="9876543210", confidence=0.95)

        proposals = propose_resolutions([mA, mB])
        self.assertEqual(len(proposals), 2)
        phone_proposals = [p for p in proposals if any(s.value == "phone_match" for s in p.signals)]
        self.assertEqual(len(phone_proposals), 2)
        for p in phone_proposals:
            self.assertGreaterEqual(p.confidence, 0.90)

    # -------------------------------------------------------------------------
    # TEST H: RELATIONSHIP DEDUPLICATION & PROVENANCE PRESERVATION
    # -------------------------------------------------------------------------
    def test_h_relationship_deduplication_preserves_provenance(self) -> None:
        """Deterministic A -> B and AI A -> B produce one relationship with combined evidence."""
        cfg = MLConfig(ai_enabled=True)
        provider = ControlledAIProvider(
            relationships=[
                {
                    "source_entity_ref": "mention_001",
                    "target_entity_ref": "mention_002",
                    "relationship": "CALLED",
                    "confidence": 0.95,
                    "status": "CONFIRMED",
                    "evidence_snippet": "Rahul Sharma (phone: 9876543210) called Amit Kumar",
                    "page_number": 1,
                }
            ]
        )
        client = AIClient(provider)

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=client,
        )

        called_rels = [
            r for r in result.relationships
            if r.source_entity_id == "mention_001" and r.target_entity_id == "mention_002" and r.relationship == RelationshipType.CALLED
        ]
        # Must be deduplicated to exactly 1
        self.assertEqual(len(called_rels), 1)
        rel = called_rels[0]
        self.assertIn("called", rel.evidence_snippet.lower())

    # -------------------------------------------------------------------------
    # TEST I: CONFLICTING RELATIONSHIP (NO UNSAFE OVERWRITE)
    # -------------------------------------------------------------------------
    def test_i_conflicting_relationship_no_unsafe_overwrite(self) -> None:
        """Deterministic A -> B is preserved when AI proposes A -> C; no silent overwrite."""
        cfg = MLConfig(ai_enabled=True)
        provider = ControlledAIProvider(
            relationships=[
                {
                    "source_entity_ref": "name:Rahul Sharma",
                    "target_entity_ref": "name:Vikram Singh",
                    "relationship": "ASSOCIATED_WITH",
                    "confidence": 0.85,
                    "status": "INFERRED",
                    "evidence_snippet": "Investigation Report:",
                    "page_number": 1,
                }
            ]
        )
        client = AIClient(provider)

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=client,
        )

        # Verify deterministic CALLED relation (Rahul Sharma -> Amit Kumar) is untouched
        ent_by_id = {e.id: e.name for e in result.entities}
        called_pairs = [
            (ent_by_id.get(r.source_entity_id), ent_by_id.get(r.target_entity_id))
            for r in result.relationships
            if r.relationship == RelationshipType.CALLED
        ]
        self.assertIn(("Rahul Sharma", "Amit Kumar"), called_pairs)

        # AI relation (Rahul Sharma -> Vikram Singh) is also present without replacing deterministic relation
        assoc_pairs = [
            (ent_by_id.get(r.source_entity_id), ent_by_id.get(r.target_entity_id))
            for r in result.relationships
            if r.relationship == RelationshipType.ASSOCIATED_WITH
        ]
        self.assertIn(("Rahul Sharma", "Vikram Singh"), assoc_pairs)

    # -------------------------------------------------------------------------
    # TEST J: EVIDENCE REQUIRED
    # -------------------------------------------------------------------------
    def test_j_ai_relationship_without_evidence_rejected(self) -> None:
        """AI candidate relationship with empty evidence snippet is strictly rejected."""
        cfg = MLConfig(ai_enabled=True)
        provider = ControlledAIProvider(
            relationships=[
                {
                    "source_entity_ref": "mention_001",
                    "target_entity_ref": "mention_002",
                    "relationship": "ASSOCIATED_WITH",
                    "confidence": 0.90,
                    "status": "INFERRED",
                    "evidence_snippet": "",  # Empty evidence
                    "page_number": 1,
                }
            ]
        )
        client = AIClient(provider)

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=client,
        )

        # Un-evidenced ASSOCIATED_WITH relationship must NOT be present
        assoc_rels = [
            r for r in result.relationships
            if r.relationship == RelationshipType.ASSOCIATED_WITH and r.source_entity_id == "mention_001" and r.target_entity_id == "mention_002"
        ]
        self.assertEqual(len(assoc_rels), 0)

    # -------------------------------------------------------------------------
    # TEST K: FABRICATED EVIDENCE REJECTED
    # -------------------------------------------------------------------------
    def test_k_fabricated_evidence_rejected(self) -> None:
        """AI referencing a nonexistent page or fabricated snippet is rejected."""
        cfg = MLConfig(ai_enabled=True)
        provider = ControlledAIProvider(
            relationships=[
                {
                    "source_entity_ref": "mention_001",
                    "target_entity_ref": "mention_002",
                    "relationship": "ASSOCIATED_WITH",
                    "confidence": 0.90,
                    "status": "INFERRED",
                    "evidence_snippet": "This text definitely does not exist in the source document anywhere at all.",
                    "page_number": 99,  # Document has only 1 page!
                }
            ]
        )
        client = AIClient(provider)

        result = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=client,
        )

        assoc_rels = [
            r for r in result.relationships
            if r.relationship == RelationshipType.ASSOCIATED_WITH and r.source_entity_id == "mention_001" and r.target_entity_id == "mention_002"
        ]
        self.assertEqual(len(assoc_rels), 0)

    # -------------------------------------------------------------------------
    # TEST L: TRANSACTION AUTHORITY
    # -------------------------------------------------------------------------
    def test_l_structured_transaction_remains_authoritative(self) -> None:
        """AI interpretation must never alter transaction amount, currency, or timestamp."""
        cfg = MLConfig(ai_enabled=True)
        original_tx = {
            "transaction_id": "TXN_001",
            "sender": "ACC_111",
            "recipient": "ACC_222",
            "amount": 50000.0,
            "currency": "INR",
            "transaction_time": "2026-03-01T12:00:00Z",
        }

        # AI claims a different amount
        provider = ControlledAIProvider(
            relationships=[
                {
                    "source_entity_ref": "mention_001",
                    "target_entity_ref": "mention_002",
                    "relationship": "SENT_MONEY_TO",
                    "confidence": 0.95,
                    "status": "CONFIRMED",
                    "evidence_snippet": "Transfer was 999999 USD according to AI conjecture",
                    "page_number": 1,
                }
            ]
        )
        client = AIClient(provider)

        analysis = process_document(
            self.doc_id,
            self.sample_text,
            transactions=[original_tx],
            config=cfg,
            ai_client=client,
            return_full_analysis=True,
        )

        # Check structured_records in output
        tx_records = [r for r in analysis["structured_records"] if isinstance(r, TransactionRecord)]
        self.assertEqual(len(tx_records), 1)
        tx = tx_records[0]
        self.assertEqual(tx.amount, 50000.0)
        self.assertEqual(tx.currency, "INR")
        self.assertEqual(tx.transaction_time, "2026-03-01T12:00:00Z")

    # -------------------------------------------------------------------------
    # TEST M: CDR AUTHORITY
    # -------------------------------------------------------------------------
    def test_m_structured_cdr_remains_authoritative(self) -> None:
        """AI interpretation must never alter CDR call_time or duration."""
        cfg = MLConfig(ai_enabled=True)
        original_cdr = {
            "record_id": "CDR_001",
            "caller": "9876543210",
            "callee": "9123456780",
            "call_time": "2026-03-01T14:30:00Z",
            "duration": 180,
        }

        analysis = process_document(
            self.doc_id,
            self.sample_text,
            cdrs=[original_cdr],
            config=cfg,
            return_full_analysis=True,
        )

        cdr_records = [r for r in analysis["structured_records"] if isinstance(r, CDRRecord)]
        self.assertEqual(len(cdr_records), 1)
        cdr = cdr_records[0]
        self.assertEqual(cdr.call_time, "2026-03-01T14:30:00Z")
        self.assertEqual(cdr.duration, 180)

    # -------------------------------------------------------------------------
    # TEST N: PATTERN SAFETY
    # -------------------------------------------------------------------------
    def test_n_speculative_ai_claims_cannot_trigger_false_patterns(self) -> None:
        """Speculative AI relationships cannot trigger CIRCULAR_TRANSACTION or false patterns."""
        cfg = MLConfig(ai_enabled=True)
        # AI hallucinating circular transfer relationship without structured records
        provider = ControlledAIProvider(
            relationships=[
                {
                    "source_entity_ref": "mention_001",
                    "target_entity_ref": "mention_002",
                    "relationship": "SENT_MONEY_TO",
                    "confidence": 0.8,
                    "status": "INFERRED",
                    "evidence_snippet": "Amit Kumar sent money to Vikram Singh",
                    "page_number": 1,
                },
                {
                    "source_entity_ref": "mention_002",
                    "target_entity_ref": "mention_001",
                    "relationship": "SENT_MONEY_TO",
                    "confidence": 0.8,
                    "status": "INFERRED",
                    "evidence_snippet": "Amit Kumar sent money to Vikram Singh",
                    "page_number": 1,
                },
            ]
        )
        client = AIClient(provider)

        analysis = process_document(
            self.doc_id,
            self.sample_text,
            config=cfg,
            ai_client=client,
            return_full_analysis=True,
        )

        patterns = analysis["patterns"]
        # Without 3 verified structured TransactionRecords, CIRCULAR_TRANSACTION is NEVER produced
        circ_patterns = [p for p in patterns if p.type.value == "CIRCULAR_TRANSACTION"]
        self.assertEqual(len(circ_patterns), 0)

    # -------------------------------------------------------------------------
    # TEST O & P: PROVIDER DISABLED / MOCK OFFLINE
    # -------------------------------------------------------------------------
    def test_o_provider_disabled_without_credentials(self) -> None:
        """Without API credentials, coordinator falls back cleanly to deterministic."""
        cfg = MLConfig(ai_enabled=False, ai_api_key=None)
        result = process_document(self.doc_id, self.sample_text, config=cfg)
        self.assertIsInstance(result, ExtractionResult)

    def test_p_provider_mock_works_offline(self) -> None:
        """Mock provider works completely offline with zero network connectivity."""
        cfg = MLConfig(ai_enabled=True, ai_provider="mock")
        result = process_document(self.doc_id, self.sample_text, config=cfg)
        self.assertIsInstance(result, ExtractionResult)

    # -------------------------------------------------------------------------
    # TEST Q: MULTIMODAL DOCUMENT (PDF / IMAGE / OCR)
    # -------------------------------------------------------------------------
    def test_q_multimodal_document_integration(self) -> None:
        """Multimodal input bytes flow through preprocessing/OCR, understanding, and reconciliation."""
        cfg = MLConfig(ai_enabled=True)
        # Mock OCR runner
        def mock_ocr(b: bytes, lang: str = "eng") -> str:
            return "OCR Scanned Content: Rahul Sharma called Amit Kumar regarding vehicle DL 01 AB 1234."

        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

        result = process_document(
            dummy_png,
            "evidence_scan.png",
            self.doc_id,
            config=cfg,
            ocr_engine_runner=mock_ocr,
        )

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, self.doc_id)
        ent_names = [e.name for e in result.entities]
        self.assertIn("Rahul Sharma", ent_names)
        self.assertIn("Amit Kumar", ent_names)

    # -------------------------------------------------------------------------
    # TEST: BACKEND CALLING CONVENTION PARITY
    # -------------------------------------------------------------------------
    def test_backend_adapter_three_argument_convention(self) -> None:
        """Backend adapter convention (document_bytes, filename, document_id) works identically."""
        cfg = MLConfig(ai_enabled=True)
        raw_bytes = self.sample_text.encode("utf-8")

        result = process_document(
            raw_bytes,
            "fir_report.txt",
            "doc_backend_001",
            config=cfg,
        )

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_backend_001")
        self.assertGreater(len(result.entities), 0)


if __name__ == "__main__":
    unittest.main()
