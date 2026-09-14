"""AI Context & Relationship Reasoning for CrimeLens (Phase 4).

Consumes:
- Phase 2 DocumentUnderstanding context (pages, sections, tables, text)
- Phase 3 extracted EntityMention candidates
- Existing deterministic relationships
- Structured records (Transactions, CDRs)

Produces:
- Supported, evidence-grounded candidate relationships
- Reconciled against deterministic relationships without blind overwriting

CRITICAL SAFETY & CONTRACT RULES:
1. AI output is strictly UNTRUSTED candidate intelligence.
2. Grounded: Every candidate requires genuine evidence grounded in source context.
3. Strict Schema: Rejects unsupported relationship types (e.g. FRIEND_OF, KNOWS, LIKELY_GUILTY).
4. Strict Status: Only supports CONFIRMED, INFERRED, PREDICTED (no AI_DETECTED).
5. Valid Entities: References only existing ML mention IDs (mention_001, etc.).
6. Isolated: Zero database UUIDs, zero case IDs, zero Neo4j/PostgreSQL access.
7. Directional: Preserves relationship direction (A CALLED B != B CALLED A).
8. No Self-Edges: Rejects A -> A where logically invalid.
9. No Guilt/Risk: Never generates guilt, criminality, or threat scores.
10. Additive: AI failure never destroys deterministic extraction/pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Optional

from ml.ai.client.client import AIClient
from ml.ai.document_understanding import DocumentUnderstanding
from ml.ai.errors import AIError
from ml.ai.types import MultimodalInput
from ml.config import MLConfig, default_config
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship

SUPPORTED_RELATIONSHIP_TYPES = {rt.value: rt for rt in RelationshipType}
SUPPORTED_RELATIONSHIP_STATUSES = {rs.value: rs for rs in RelationshipStatus}

# Valid entity type pairs for directional CrimeLens relationships
ALLOWED_RELATIONSHIP_ENTITY_PAIRS: dict[RelationshipType, set[tuple[EntityType, EntityType]]] = {
    RelationshipType.CALLED: {
        (EntityType.PERSON, EntityType.PERSON),
        (EntityType.PERSON, EntityType.PHONE),
        (EntityType.PHONE, EntityType.PHONE),
    },
    RelationshipType.SENT_MONEY_TO: {
        (EntityType.PERSON, EntityType.PERSON),
        (EntityType.PERSON, EntityType.BANK_ACCOUNT),
        (EntityType.BANK_ACCOUNT, EntityType.BANK_ACCOUNT),
    },
    RelationshipType.OWNS_VEHICLE: {
        (EntityType.PERSON, EntityType.VEHICLE),
        (EntityType.ORGANIZATION, EntityType.VEHICLE),
    },
    RelationshipType.USED_VEHICLE: {
        (EntityType.PERSON, EntityType.VEHICLE),
    },
    RelationshipType.WORKS_FOR: {
        (EntityType.PERSON, EntityType.ORGANIZATION),
    },
    RelationshipType.LOCATED_AT: {
        (EntityType.PERSON, EntityType.LOCATION),
        (EntityType.ORGANIZATION, EntityType.LOCATION),
        (EntityType.VEHICLE, EntityType.LOCATION),
    },
    RelationshipType.ASSOCIATED_WITH: {
        (EntityType.PERSON, EntityType.PERSON),
        (EntityType.PERSON, EntityType.ORGANIZATION),
        (EntityType.PERSON, EntityType.PHONE),
        (EntityType.ORGANIZATION, EntityType.ORGANIZATION),
    },
    RelationshipType.PART_OF_EVENT: {
        (EntityType.PERSON, EntityType.EVENT),
        (EntityType.ORGANIZATION, EntityType.EVENT),
    },
}


@dataclass(frozen=True)
class AIRelationshipCandidate:
    """Candidate relationship proposed by AI reasoning model before reconciliation."""

    source_entity_ref: str
    target_entity_ref: str
    relationship_type: RelationshipType
    confidence: float
    status: RelationshipStatus
    evidence_snippet: str
    page_number: Optional[int] = None
    reasoning_summary: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_entity_ref or not self.source_entity_ref.strip():
            raise ValueError("source_entity_ref cannot be empty")
        if not self.target_entity_ref or not self.target_entity_ref.strip():
            raise ValueError("target_entity_ref cannot be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if not self.evidence_snippet or not self.evidence_snippet.strip():
            raise ValueError("evidence_snippet cannot be empty")


class AIRelationshipReasoner:
    """Performs contextual relationship reasoning using Phase 1 client and Phase 2/3 context."""

    def __init__(
        self,
        client: Optional[AIClient] = None,
        config: Optional[MLConfig] = None,
    ) -> None:
        self.client = client
        self.config = config or default_config

    def reason_relationships(
        self,
        doc_understanding: DocumentUnderstanding,
        entities: list[EntityMention],
        *,
        existing_relationships: Optional[list[Relationship]] = None,
        structured_records: Optional[list[Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> list[AIRelationshipCandidate]:
        """Propose grounded relationship candidates connecting known entities.

        Args:
            doc_understanding: Normalized Phase 2 DocumentUnderstanding.
            entities: Staging EntityMention instances (must have >= 2 to form relationships).
            existing_relationships: Deterministic relationships already extracted.
            structured_records: Optional CDR or transaction records.
            context: Additional caller context.

        Returns:
            list[AIRelationshipCandidate]: Validated, evidence-grounded candidate relationships.
        """
        if not self.config.ai_enabled or self.client is None or not self.client.provider.is_available:
            return []

        if len(entities) < 2:
            return []

        # Construct controlled, structured reasoning context
        reasoning_context = self._build_reasoning_context(
            doc_understanding=doc_understanding,
            entities=entities,
            existing_relationships=existing_relationships or [],
            structured_records=structured_records or [],
            extra_context=context or {},
        )

        m_input = MultimodalInput.from_text(
            doc_understanding.full_text or "Empty document",
            filename=doc_understanding.filename,
            metadata=reasoning_context,
        )

        try:
            response = self.client.analyze(m_input, context=reasoning_context)
        except AIError:
            # Controlled fallback: return empty candidates, letting deterministic pipeline proceed
            return []

        raw_candidates = response.get_candidate_relationships()
        return self._parse_and_validate_candidates(raw_candidates, entities, doc_understanding)

    def _build_reasoning_context(
        self,
        doc_understanding: DocumentUnderstanding,
        entities: list[EntityMention],
        existing_relationships: list[Relationship],
        structured_records: list[Any],
        extra_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Construct a bounded reasoning prompt context omitting secrets."""
        entity_summaries = [
            {"id": e.id, "type": e.type.value, "name": e.name, "confidence": e.confidence}
            for e in entities
        ]
        rel_summaries = [
            {
                "source": r.source_entity_id,
                "target": r.target_entity_id,
                "relationship": r.relationship.value,
                "status": r.status.value,
            }
            for r in existing_relationships
        ]

        return {
            **extra_context,
            "task": "relationship_reasoning",
            "document_id": doc_understanding.document_id,
            "filename": doc_understanding.filename,
            "page_count": doc_understanding.page_count,
            "known_entities": entity_summaries,
            "existing_relationships": rel_summaries,
            "structured_record_count": len(structured_records),
            "allowed_relationship_types": list(SUPPORTED_RELATIONSHIP_TYPES.keys()),
        }

    def _parse_and_validate_candidates(
        self,
        raw_candidates: list[dict[str, Any]],
        entities: list[EntityMention],
        doc: DocumentUnderstanding,
    ) -> list[AIRelationshipCandidate]:
        valid_candidates: list[AIRelationshipCandidate] = []
        entity_map = {e.id: e for e in entities}
        full_text_lower = doc.full_text.lower()

        for raw in raw_candidates:
            if not isinstance(raw, dict):
                continue

            # 1. Source and Target entity reference checks (must reference known mentions)
            s_id = str(raw.get("source_entity_id") or raw.get("source_entity_ref", "")).strip()
            t_id = str(raw.get("target_entity_id") or raw.get("target_entity_ref", "")).strip()

            if not s_id or not t_id or s_id not in entity_map or t_id not in entity_map:
                # Reject unknown entity references
                continue

            # 2. Self-relationship check (no self-loops)
            if s_id == t_id:
                continue

            source_entity = entity_map[s_id]
            target_entity = entity_map[t_id]

            # 3. Relationship Type validation (must be in frozen CrimeLens taxonomy)
            raw_type = str(raw.get("relationship", "") or raw.get("relationship_type", "")).strip().upper()
            if raw_type not in SUPPORTED_RELATIONSHIP_TYPES:
                # Reject unsupported relationship types (e.g. FRIEND_OF, KNOWS, LIKELY_GUILTY)
                continue

            rel_type = SUPPORTED_RELATIONSHIP_TYPES[raw_type]

            # 4. Type compatibility check (source and target EntityTypes must match taxonomy)
            allowed_pairs = ALLOWED_RELATIONSHIP_ENTITY_PAIRS.get(rel_type, set())
            if (source_entity.type, target_entity.type) not in allowed_pairs:
                # Type incompatibility (e.g., PERSON WORKS_FOR PERSON or BANK_ACCOUNT CALLED LOCATION)
                continue

            # 5. Status validation (strictly CONFIRMED, INFERRED, PREDICTED)
            raw_status = str(raw.get("status", "INFERRED")).strip().upper()
            if raw_status not in SUPPORTED_RELATIONSHIP_STATUSES:
                # Reject unsupported status (e.g. AI_DETECTED, SUSPECTED)
                continue

            rel_status = SUPPORTED_RELATIONSHIP_STATUSES[raw_status]

            # 6. Confidence validation (strictly bounded between 0.0 and 1.0)
            try:
                conf = float(raw.get("confidence", 0.8))
                if conf < 0.0 or conf > 1.0:
                    continue
            except (ValueError, TypeError):
                continue

            # 7. Evidence validation & grounding (Phase 5 EvidenceGroundingEngine)
            raw_snippet = str(raw.get("evidence_snippet", "") or raw.get("snippet", "")).strip()
            if not raw_snippet:
                # Evidence is required; cannot accept ungrounded assertions
                continue

            page_num = raw.get("page_number") or raw.get("page")
            claimed_page: Optional[int] = page_num if isinstance(page_num, int) else None

            # Verify grounding using Phase 5 EvidenceGroundingEngine
            from ml.ai.evidence import EvidenceGroundingEngine, VerificationState
            engine = EvidenceGroundingEngine(normalize_ocr=True)
            v_state, grounded_snip, verified_page = engine.verify_and_ground_snippet(
                raw_snippet,
                doc,
                claimed_page=claimed_page,
            )

            if v_state in (VerificationState.INVALID, VerificationState.UNVERIFIED) or not grounded_snip:
                # Reject ungrounded, fabricated, or page-invalid evidence
                continue

            reasoning = str(raw.get("reasoning_summary", "") or raw.get("reasoning", "")).strip()

            valid_candidates.append(
                AIRelationshipCandidate(
                    source_entity_ref=s_id,
                    target_entity_ref=t_id,
                    relationship_type=rel_type,
                    confidence=round(conf, 4),
                    status=rel_status,
                    evidence_snippet=grounded_snip,
                    page_number=verified_page,
                    reasoning_summary=reasoning if reasoning else None,
                    metadata=raw.get("metadata", {}),
                )
            )

        return valid_candidates

    def _is_snippet_grounded(self, snippet: str, doc_text_lower: str) -> bool:
        """Verify that the evidence snippet is grounded in the document text."""
        snip_lower = snippet.lower().strip()
        if snip_lower in doc_text_lower:
            return True

        # Check significant token overlap (>= 60% of keywords present)
        tokens = [t for t in snip_lower.split() if len(t) > 3]
        if not tokens:
            return snip_lower in doc_text_lower

        matches = sum(1 for t in tokens if t in doc_text_lower)
        return (matches / len(tokens)) >= 0.6


class RelationshipReconciler:
    """Reconciles deterministic relationships and AI candidate relationships."""

    def reconcile(
        self,
        deterministic_relationships: list[Relationship],
        ai_candidates: list[AIRelationshipCandidate],
        *,
        document_id: Optional[str] = None,
        min_confidence: float = 0.5,
    ) -> list[Relationship]:
        """Merge, deduplicate, and assign sequential relationship IDs.

        Preserves:
        - Deterministic relationships are authoritative and never overwritten.
        - AI duplicate proposals reinforce confidence and preserve evidence.
        - Valid non-duplicate AI candidates are safely appended.
        - Sequential staging IDs (rel_001, rel_002, ...) are minted.

        Returns:
            list[Relationship]: Unified, schema-compliant Relationship instances.
        """
        reconciled: dict[tuple[str, str, RelationshipType], dict[str, Any]] = {}

        # 1. Ingest deterministic relationships (authoritative baseline)
        for r in deterministic_relationships:
            if r.confidence < min_confidence:
                continue
            key = (r.source_entity_id, r.target_entity_id, r.relationship)
            reconciled[key] = {
                "source": r.source_entity_id,
                "target": r.target_entity_id,
                "relationship": r.relationship,
                "confidence": r.confidence,
                "status": r.status,
                "evidence_snippet": r.evidence_snippet,
                "source_document_id": r.source_document_id or document_id,
                "source_record_id": r.source_record_id,
                "extracted_at": r.extracted_at,
                "method": "deterministic",
            }

        # 2. Ingest AI candidates
        now = datetime.now(timezone.utc)
        for cand in ai_candidates:
            if cand.confidence < min_confidence:
                continue

            key = (cand.source_entity_ref, cand.target_entity_ref, cand.relationship_type)
            if key in reconciled:
                # Existing deterministic relationship: reinforce confidence slightly, preserve deterministic status
                existing = reconciled[key]
                combined_conf = max(existing["confidence"], cand.confidence)
                combined_conf = min(1.0, combined_conf + 0.02)
                existing["confidence"] = round(combined_conf, 4)
                # Keep evidence comprehensive
                if cand.evidence_snippet not in existing["evidence_snippet"]:
                    existing["evidence_snippet"] += f" | {cand.evidence_snippet}"
            else:
                # New contextual relationship discovered by AI reasoning
                reconciled[key] = {
                    "source": cand.source_entity_ref,
                    "target": cand.target_entity_ref,
                    "relationship": cand.relationship_type,
                    "confidence": cand.confidence,
                    "status": cand.status,
                    "evidence_snippet": cand.evidence_snippet,
                    "source_document_id": document_id,
                    "source_record_id": None,
                    "extracted_at": now,
                    "method": "ai",
                }

        # 3. Format as schema-compliant Relationship objects with sequential staging IDs
        final_relationships: list[Relationship] = []
        for idx, item in enumerate(reconciled.values(), start=1):
            rel_id = f"rel_{idx:03d}"
            final_relationships.append(
                Relationship(
                    id=rel_id,
                    source_entity_id=item["source"],
                    target_entity_id=item["target"],
                    relationship=item["relationship"],
                    confidence=item["confidence"],
                    status=item["status"],
                    source_document_id=item["source_document_id"],
                    source_record_id=item["source_record_id"],
                    evidence_snippet=item["evidence_snippet"],
                    extracted_at=item["extracted_at"],
                )
            )

        return final_relationships
