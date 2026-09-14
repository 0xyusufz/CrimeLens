"""Phase 6 — ML + AI Pipeline Integration & Orchestration Coordinator.

Integrates Phase 1–5 AI capabilities (Foundation, Document Understanding,
Entity Extraction, Relationship Reasoning, Evidence Grounding & Provenance)
into the authoritative CrimeLens deterministic ML pipeline.

CRITICAL INVARIANTS:
1. AI proposes intelligence; deterministic ML validates, reconciles, and controls it.
2. AI failure (timeout, 500 error, malformed output) NEVER destroys deterministic extraction.
3. No criminality/guilt scoring, predictive policing, or chain-of-thought storage.
4. Structured CDR and transaction data remain authoritative: amounts, currencies,
   durations, and timestamps are immutable.
5. Deterministic patterns (CIRCULAR_TRANSACTION, RAPID_TRANSFER_CHAIN,
   LOCATION_TIME_OVERLAP) and leads remain authoritative.
6. Zero database/Neo4j access or writes; zero database UUID minting.
7. Pure ML layer: provider-agnostic, backward-compatible, testable with mocks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
from typing import Any, Optional

from ml.ai.client.client import AIClient
from ml.ai.document_understanding import DocumentUnderstanding, DocumentUnderstandingEngine
from ml.ai.errors import AIError
from ml.ai.evidence import (
    EvidenceGroundingEngine,
    EvidenceReference,
    ProvenanceTracker,
    VerificationState,
)
from ml.ai.extraction import (
    AIEntityCandidate,
    AIEntityExtractor,
    EntityReconciler,
)
from ml.ai.providers.mock import MockReasoningProvider
from ml.ai.reasoning import (
    AIRelationshipCandidate,
    AIRelationshipReasoner,
    RelationshipReconciler,
)
from ml.config import MLConfig, default_config
from ml.structured import CDRRecord, TransactionRecord
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship

logger = logging.getLogger("ml.ai.pipeline_integration")


@dataclass
class AITraceabilityMetrics:
    """Internal observability and execution metrics for Phase 6 pipeline integration."""

    ai_enabled: bool = False
    ai_attempted: bool = False
    ai_fallback_occurred: bool = False
    fallback_reason: Optional[str] = None
    document_modality: Optional[str] = None
    deterministic_entities_count: int = 0
    ai_entity_candidates_proposed: int = 0
    ai_entity_candidates_accepted: int = 0
    ai_entity_candidates_rejected: int = 0
    reconciled_entities_count: int = 0
    deterministic_relationships_count: int = 0
    ai_relationship_candidates_proposed: int = 0
    ai_relationship_candidates_accepted: int = 0
    ai_relationship_candidates_rejected: int = 0
    relationships_merged_count: int = 0
    reconciled_relationships_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to clean serializable dictionary."""
        return asdict(self)


class AIPipelineCoordinator:
    """Coordinates AI integration into CrimeLens document analysis pipeline.

    Provides bounded, isolated AI execution with deterministic fallbacks,
    preventing any AI failure from breaking core intelligence processing.
    """

    def __init__(
        self,
        client: Optional[AIClient] = None,
        config: Optional[MLConfig] = None,
    ) -> None:
        self.config = config or default_config
        self.client = client
        self.metrics = AITraceabilityMetrics(ai_enabled=self.config.ai_enabled)
        self.evidence_engine = EvidenceGroundingEngine(normalize_ocr=True)
        self.provenance_tracker = ProvenanceTracker()
        self._doc_understanding: Optional[DocumentUnderstanding] = None

    def _ensure_client(self) -> AIClient:
        """Get or initialize AIClient safely using configured or mock provider."""
        if self.client is not None:
            return self.client

        # Provider resolution based on config
        provider_name = (self.config.ai_provider or "mock").lower()
        if provider_name == "mock":
            provider = MockReasoningProvider()
        else:
            # For non-mock providers without credentials, fallback safely to mock
            if not self.config.ai_api_key:
                logger.info("No AI API key found for provider %s; falling back to MockReasoningProvider", provider_name)
                provider = MockReasoningProvider()
            else:
                try:
                    # Dynamically instantiate provider if supported
                    if provider_name == "gemini":
                        from ml.ai.providers.gemini import GeminiReasoningProvider
                        provider = GeminiReasoningProvider(api_key=self.config.ai_api_key, model_name=self.config.ai_model)
                    elif provider_name == "openai":
                        from ml.ai.providers.openai import OpenAIReasoningProvider
                        provider = OpenAIReasoningProvider(api_key=self.config.ai_api_key, model_name=self.config.ai_model)
                    elif provider_name == "claude":
                        from ml.ai.providers.claude import ClaudeReasoningProvider
                        provider = ClaudeReasoningProvider(api_key=self.config.ai_api_key, model_name=self.config.ai_model)
                    else:
                        logger.warning("Unrecognized provider %s; using mock", provider_name)
                        provider = MockReasoningProvider()
                except Exception as exc:
                    logger.warning("Could not initialize provider %s: %s; using mock", provider_name, exc)
                    provider = MockReasoningProvider()

        self.client = AIClient(
            provider,
            timeout_seconds=self.config.ai_timeout_seconds,
            max_retries=self.config.ai_max_retries,
            max_input_bytes=self.config.ai_max_input_bytes,
        )
        return self.client

    def understand_document(
        self,
        raw_input: str | bytes,
        *,
        filename: str,
        document_id: str,
    ) -> Optional[DocumentUnderstanding]:
        """Perform multimodal document understanding once and cache the representation.

        Returns None if understanding fails, safely logging the error and updating metrics.
        """
        if not self.config.ai_enabled:
            return None

        self.metrics.ai_attempted = True
        try:
            client = self._ensure_client()
            engine = DocumentUnderstandingEngine(client=client, config=self.config)
            doc_understanding = engine.understand(
                raw_input,
                filename=filename,
                document_id=document_id,
            )
            self._doc_understanding = doc_understanding
            self.metrics.document_modality = doc_understanding.document_type
            if getattr(client, "last_error", None) is not None:
                self.metrics.ai_fallback_occurred = True
                self.metrics.fallback_reason = f"Document understanding failure: {type(client.last_error).__name__}"
            return doc_understanding
        except Exception as exc:
            logger.warning("AI document understanding failed: %s; falling back to deterministic processing", exc)
            self.metrics.ai_fallback_occurred = True
            self.metrics.fallback_reason = f"Document understanding failure: {type(exc).__name__}"
            return None

    def reconcile_entities(
        self,
        doc_understanding: Optional[DocumentUnderstanding],
        deterministic_entities: list[EntityMention],
        *,
        min_confidence: Optional[float] = None,
    ) -> list[EntityMention]:
        """Extract AI candidate entities and reconcile with deterministic baseline.

        Preserves:
        - Deterministic extraction remains authoritative.
        - Exact duplicate candidates are reconciled without duplicates.
        - Name-only fuzzy matching never auto-merges mentions.
        - Bounded confidence [0.0, 1.0].
        - AI failure falls back cleanly to deterministic entities.
        """
        self.metrics.deterministic_entities_count = len(deterministic_entities)
        conf_threshold = min_confidence if min_confidence is not None else self.config.min_entity_confidence

        if not self.config.ai_enabled or doc_understanding is None:
            self.metrics.reconciled_entities_count = len(deterministic_entities)
            return deterministic_entities

        try:
            client = self._ensure_client()
            extractor = AIEntityExtractor(client=client, config=self.config)
            ai_candidates = extractor.extract_candidates(doc_understanding)
            self.metrics.ai_entity_candidates_proposed = len(ai_candidates)

            if getattr(client, "last_error", None) is not None:
                self.metrics.ai_fallback_occurred = True
                self.metrics.fallback_reason = f"Entity extraction failure: {type(client.last_error).__name__}"

            if not ai_candidates:
                self.metrics.reconciled_entities_count = len(deterministic_entities)
                return deterministic_entities

            reconciler = EntityReconciler()
            reconciled = reconciler.reconcile(
                deterministic_entities,
                ai_candidates,
                min_confidence=conf_threshold,
            )

            # Calculate accepted vs rejected AI candidates
            # An AI candidate is accepted if its normalized name & type exist in the reconciled output
            existing_det_keys = {(e.type, reconciler._normalize_candidate_name(e.type, e.name)) for e in deterministic_entities}
            reconciled_keys = {(e.type, reconciler._normalize_candidate_name(e.type, e.name)) for e in reconciled}

            accepted_count = 0
            rejected_count = 0
            for cand in ai_candidates:
                cand_key = (cand.type, reconciler._normalize_candidate_name(cand.type, cand.name))
                if cand_key in reconciled_keys:
                    accepted_count += 1
                else:
                    rejected_count += 1

            self.metrics.ai_entity_candidates_accepted = accepted_count
            self.metrics.ai_entity_candidates_rejected = rejected_count
            self.metrics.reconciled_entities_count = len(reconciled)
            return reconciled

        except Exception as exc:
            logger.warning("AI entity extraction failed: %s; retaining deterministic entities", exc)
            self.metrics.ai_fallback_occurred = True
            self.metrics.fallback_reason = f"Entity extraction failure: {type(exc).__name__}"
            self.metrics.reconciled_entities_count = len(deterministic_entities)
            return deterministic_entities

    def reconcile_relationships(
        self,
        doc_understanding: Optional[DocumentUnderstanding],
        entities: list[EntityMention],
        deterministic_relationships: list[Relationship],
        structured_records: Optional[list[Any]] = None,
        *,
        document_id: str,
        min_confidence: Optional[float] = None,
    ) -> list[Relationship]:
        """Reason AI contextual relationships, ground evidence, and reconcile with deterministic baseline.

        Preserves:
        - Deterministic structured relationships (CDR, transactions) remain authoritative.
        - Unverified or fabricated evidence is strictly rejected.
        - Unsupported relationship types and statuses are rejected.
        - Duplicate relationships are unified with preserved provenance.
        - AI failure falls back cleanly to deterministic relationships.
        """
        self.metrics.deterministic_relationships_count = len(deterministic_relationships)
        conf_threshold = min_confidence if min_confidence is not None else self.config.min_relationship_confidence

        if not self.config.ai_enabled or doc_understanding is None or len(entities) < 2:
            self.metrics.reconciled_relationships_count = len(deterministic_relationships)
            return deterministic_relationships

        try:
            client = self._ensure_client()
            reasoner = AIRelationshipReasoner(client=client, config=self.config)
            ai_candidates = reasoner.reason_relationships(
                doc_understanding,
                entities=entities,
                existing_relationships=deterministic_relationships,
                structured_records=structured_records,
            )
            self.metrics.ai_relationship_candidates_proposed = len(ai_candidates)

            if getattr(client, "last_error", None) is not None:
                self.metrics.ai_fallback_occurred = True
                self.metrics.fallback_reason = f"Relationship reasoning failure: {type(client.last_error).__name__}"

            if not ai_candidates:
                self.metrics.reconciled_relationships_count = len(deterministic_relationships)
                return deterministic_relationships

            # Ground and filter candidates against Phase 5 evidence rules
            verified_candidates: list[AIRelationshipCandidate] = []
            for cand in ai_candidates:
                v_state, grounded_snip, verified_page = self.evidence_engine.verify_and_ground_snippet(
                    cand.evidence_snippet,
                    doc_understanding,
                    claimed_page=cand.page_number,
                )
                if v_state in (VerificationState.INVALID, VerificationState.UNVERIFIED) or not grounded_snip:
                    # Ungrounded, fabricated snippet or invalid page number
                    continue

                # Valid, grounded candidate
                verified_cand = AIRelationshipCandidate(
                    source_entity_ref=cand.source_entity_ref,
                    target_entity_ref=cand.target_entity_ref,
                    relationship_type=cand.relationship_type,
                    confidence=cand.confidence,
                    status=cand.status,
                    evidence_snippet=grounded_snip,
                    page_number=verified_page,
                    reasoning_summary=cand.reasoning_summary,
                    metadata=cand.metadata,
                )
                verified_candidates.append(verified_cand)

            self.metrics.ai_relationship_candidates_accepted = len(verified_candidates)
            self.metrics.ai_relationship_candidates_rejected = len(ai_candidates) - len(verified_candidates)

            # Reconcile verified AI candidates with deterministic relationships
            reconciler = RelationshipReconciler()
            reconciled = reconciler.reconcile(
                deterministic_relationships,
                verified_candidates,
                document_id=document_id,
                min_confidence=conf_threshold,
            )

            # Count merged relationships (where both deterministic and AI agreed on source, target, type)
            det_keys = {(r.source_entity_id, r.target_entity_id, r.relationship) for r in deterministic_relationships}
            ai_keys = {(c.source_entity_ref, c.target_entity_ref, c.relationship_type) for c in verified_candidates}
            merged_keys = det_keys.intersection(ai_keys)
            self.metrics.relationships_merged_count = len(merged_keys)
            self.metrics.reconciled_relationships_count = len(reconciled)

            return reconciled

        except Exception as exc:
            logger.warning("AI relationship reasoning failed: %s; retaining deterministic relationships", exc)
            self.metrics.ai_fallback_occurred = True
            self.metrics.fallback_reason = f"Relationship reasoning failure: {type(exc).__name__}"
            self.metrics.reconciled_relationships_count = len(deterministic_relationships)
            return deterministic_relationships

    def verify_structured_integrity(
        self,
        original_transactions: list[TransactionRecord],
        original_cdrs: list[CDRRecord],
        current_transactions: list[TransactionRecord],
        current_cdrs: list[CDRRecord],
    ) -> bool:
        """Verify that structured transaction and CDR fields were never mutated by AI reasoning."""
        if len(original_transactions) != len(current_transactions):
            return False
        if len(original_cdrs) != len(current_cdrs):
            return False

        for orig, curr in zip(original_transactions, current_transactions):
            if orig.amount != curr.amount or orig.currency != curr.currency or orig.transaction_time != curr.transaction_time:
                return False

        for orig, curr in zip(original_cdrs, current_cdrs):
            if orig.call_time != curr.call_time or orig.duration != curr.duration:
                return False

        return True
