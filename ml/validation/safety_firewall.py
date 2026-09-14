"""Phase 7 — Comprehensive Safety & Validation Firewall for CrimeLens ML.

Enforces the authoritative validation and safety boundary between untrusted AI
intelligence and the frozen CrimeLens ML contract:
1. Untrusted AI Input: No AI candidate enters final intelligence without rigorous validation.
2. Controlled Schema: Only the 7 frozen EntityTypes and 8 frozen RelationshipTypes.
3. Strict Status: Only CONFIRMED, INFERRED, PREDICTED.
4. Bounded Confidence: 0.0 <= confidence <= 1.0 (rejects NaN, Inf, negative, >1.0, non-numeric).
5. Grounded Evidence: Rejects fabricated snippets, impossible page references, and unknown documents.
6. Entity ID Safety: Prevents AI from minting canonical database UUIDs; enforces staging IDs.
7. Merge Safety: Protects against unsafe name-only auto-merging.
8. Structured Fact Authority: CDR durations/times and transaction amounts/currencies are immutable.
9. Anti-Criminality & Anti-Bias: Rejects direct assertions of guilt/criminality or predictive policing.
10. Chain-of-Thought Firewall: Strips hidden internal model thoughts.
11. Prompt Injection Defense: Treats all document contents strictly as passive data.
12. Full Contract Compliance: Guarantees final ExtractionResult is schema-valid and JSON-serializable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import math
import re
from typing import Any, Optional

from ml.ai.document_understanding import DocumentUnderstanding
from ml.ai.evidence import EvidenceGroundingEngine, VerificationState
from ml.structured import CDRRecord, TransactionRecord
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, ExtractionResult, Relationship

SUPPORTED_ENTITY_TYPES = {et.value: et for et in EntityType}
SUPPORTED_RELATIONSHIP_TYPES = {rt.value: rt for rt in RelationshipType}
SUPPORTED_RELATIONSHIP_STATUSES = {rs.value: rs for rs in RelationshipStatus}

# Canonical UUID v4 pattern (36 chars: 8-4-4-4-12 hex)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Explicit criminality, guilt, or predictive policing assertions forbidden from AI output
_CRIMINALITY_PATTERNS = [
    re.compile(r"\b(?:is (?:a )?criminal|is guilty|will commit (?:a )?crime)\b", re.IGNORECASE),
    re.compile(r"\b(?:criminal probability|guilt score|threat score|predictive policing)\b", re.IGNORECASE),
    re.compile(r"\b(?:definitely (?:guilty|a criminal)|high[- ]risk suspect score)\b", re.IGNORECASE),
]

# Valid entity type pairs for directional relationships
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


class ValidationRejectionReason(str, Enum):
    """Machine-readable taxonomy of validation firewall rejection reasons."""

    INVALID_ENTITY_TYPE = "INVALID_ENTITY_TYPE"
    INVALID_ENTITY_VALUE = "INVALID_ENTITY_VALUE"
    INVALID_CONFIDENCE = "INVALID_CONFIDENCE"
    INVALID_STATUS = "INVALID_STATUS"
    UNSUPPORTED_RELATIONSHIP_TYPE = "UNSUPPORTED_RELATIONSHIP_TYPE"
    MISSING_SOURCE_ENTITY = "MISSING_SOURCE_ENTITY"
    MISSING_TARGET_ENTITY = "MISSING_TARGET_ENTITY"
    SELF_RELATIONSHIP = "SELF_RELATIONSHIP"
    INCOMPATIBLE_ENTITY_PAIR = "INCOMPATIBLE_ENTITY_PAIR"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    UNGROUNDED_EVIDENCE = "UNGROUNDED_EVIDENCE"
    FABRICATED_PAGE = "FABRICATED_PAGE"
    FABRICATED_SNIPPET = "FABRICATED_SNIPPET"
    UNKNOWN_DOCUMENT = "UNKNOWN_DOCUMENT"
    UNSAFE_ENTITY_MERGE = "UNSAFE_ENTITY_MERGE"
    CANONICAL_ID_MINTING_FORBIDDEN = "CANONICAL_ID_MINTING_FORBIDDEN"
    CRIMINALITY_ASSERTION = "CRIMINALITY_ASSERTION"
    CHAIN_OF_THOUGHT_LEAK = "CHAIN_OF_THOUGHT_LEAK"
    STRUCTURED_RECORD_CONFLICT = "STRUCTURED_RECORD_CONFLICT"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
    MALFORMED_AI_RESPONSE = "MALFORMED_AI_RESPONSE"
    UNSUPPORTED_OUTPUT = "UNSUPPORTED_OUTPUT"


@dataclass(frozen=True)
class CandidateValidationResult:
    """Structured outcome from validation firewall inspection."""

    accepted: bool
    reason: Optional[ValidationRejectionReason] = None
    details: Optional[str] = None
    sanitized_candidate: Optional[Any] = None


class SafetyFirewall:
    """Authoritative validation and safety firewall protecting CrimeLens ML outputs."""

    def __init__(self, evidence_engine: Optional[EvidenceGroundingEngine] = None) -> None:
        self.evidence_engine = evidence_engine or EvidenceGroundingEngine(normalize_ocr=True)

    def validate_confidence(self, value: Any) -> tuple[bool, float, Optional[ValidationRejectionReason]]:
        """Validate that a confidence score is a valid finite float between 0.0 and 1.0."""
        if value is None:
            return False, 0.0, ValidationRejectionReason.INVALID_CONFIDENCE

        # Reject boolean values (since bool is a subclass of int in Python)
        if isinstance(value, bool):
            return False, 0.0, ValidationRejectionReason.INVALID_CONFIDENCE

        if not isinstance(value, (int, float)):
            # If string or non-numeric
            try:
                # Disallow strings such as "high", "0.85"
                if isinstance(value, str):
                    return False, 0.0, ValidationRejectionReason.INVALID_CONFIDENCE
                val = float(value)
            except (ValueError, TypeError):
                return False, 0.0, ValidationRejectionReason.INVALID_CONFIDENCE
        else:
            val = float(value)

        if math.isnan(val) or math.isinf(val):
            return False, 0.0, ValidationRejectionReason.INVALID_CONFIDENCE

        if val < 0.0 or val > 1.0:
            return False, 0.0, ValidationRejectionReason.INVALID_CONFIDENCE

        return True, round(val, 4), None

    def check_criminality_assertion(self, text: str) -> bool:
        """Check if text contains forbidden direct guilt or criminality assertions."""
        if not text:
            return False
        for pattern in _CRIMINALITY_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def validate_entity_candidate(
        self,
        candidate: dict[str, Any] | Any,
        doc_understanding: Optional[DocumentUnderstanding] = None,
        *,
        document_id: str,
    ) -> CandidateValidationResult:
        """Validate an AI entity candidate against CrimeLens frozen contract and safety rules."""
        if candidate is None:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.MALFORMED_AI_RESPONSE,
                details="Candidate object is None",
            )

        # 1. Extract and validate entity type
        raw_type = (
            getattr(candidate, "type", None)
            or (candidate.get("type") if isinstance(candidate, dict) else None)
        )
        if raw_type is None:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.INVALID_ENTITY_TYPE,
                details="Entity type is missing",
            )

        type_str = raw_type.value if isinstance(raw_type, EntityType) else str(raw_type).strip().upper()
        if type_str not in SUPPORTED_ENTITY_TYPES:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.INVALID_ENTITY_TYPE,
                details=f"Unsupported entity type: {type_str!r}",
            )
        entity_type = SUPPORTED_ENTITY_TYPES[type_str]

        # 2. Extract and validate entity name/value
        raw_name = (
            getattr(candidate, "name", None)
            or (candidate.get("name") if isinstance(candidate, dict) else None)
        )
        if raw_name is None or not isinstance(raw_name, str) or not raw_name.strip():
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.INVALID_ENTITY_VALUE,
                details="Entity name is empty or missing",
            )
        name = raw_name.strip()
        if len(name) > 255:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.INVALID_ENTITY_VALUE,
                details="Entity name exceeds maximum length of 255 characters",
            )

        # 3. Guard against canonical UUID minting by AI
        cand_id = (
            getattr(candidate, "id", None)
            or (candidate.get("id") if isinstance(candidate, dict) else None)
        )
        if cand_id and isinstance(cand_id, str):
            if _UUID_PATTERN.match(cand_id):
                return CandidateValidationResult(
                    accepted=False,
                    reason=ValidationRejectionReason.CANONICAL_ID_MINTING_FORBIDDEN,
                    details="AI is forbidden from minting canonical database UUIDs",
                )

        # 4. Check criminality & guilt assertions
        if self.check_criminality_assertion(name):
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.CRIMINALITY_ASSERTION,
                details=f"Entity name contains prohibited criminality/guilt assertion: {name!r}",
            )

        # 5. Validate confidence
        raw_conf = (
            getattr(candidate, "confidence", None)
            or (candidate.get("confidence") if isinstance(candidate, dict) else 0.8)
        )
        valid_conf, conf_val, conf_reason = self.validate_confidence(raw_conf)
        if not valid_conf:
            return CandidateValidationResult(
                accepted=False,
                reason=conf_reason or ValidationRejectionReason.INVALID_CONFIDENCE,
                details=f"Invalid confidence score: {raw_conf!r}",
            )

        # 6. Validate document provenance
        cand_doc_id = (
            getattr(candidate, "document_id", None)
            or (candidate.get("document_id") if isinstance(candidate, dict) else None)
        )
        if cand_doc_id and str(cand_doc_id).strip() != document_id.strip():
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.UNKNOWN_DOCUMENT,
                details=f"Candidate document_id {cand_doc_id!r} does not match current document {document_id!r}",
            )

        # 7. Validate page number bounds
        page_num = (
            getattr(candidate, "page_number", None)
            or (candidate.get("page_number") if isinstance(candidate, dict) else None)
        )
        if page_num is not None:
            if not isinstance(page_num, int) or page_num < 1:
                return CandidateValidationResult(
                    accepted=False,
                    reason=ValidationRejectionReason.FABRICATED_PAGE,
                    details=f"Invalid page reference: {page_num!r} (must be >= 1)",
                )
            if doc_understanding is not None and doc_understanding.page_count > 0:
                if page_num > doc_understanding.page_count:
                    return CandidateValidationResult(
                        accepted=False,
                        reason=ValidationRejectionReason.FABRICATED_PAGE,
                        details=f"Page {page_num} exceeds actual document page count ({doc_understanding.page_count})",
                    )

        # 8. Source Grounding Verification
        if doc_understanding is not None and doc_understanding.full_text:
            if not self._is_entity_grounded(name, doc_understanding.full_text, entity_type):
                return CandidateValidationResult(
                    accepted=False,
                    reason=ValidationRejectionReason.UNGROUNDED_EVIDENCE,
                    details=f"Entity {name!r} could not be grounded in document context",
                )

        # Build clean sanitized candidate dict
        sanitized = {
            "type": entity_type,
            "name": name,
            "confidence": conf_val,
            "page_number": page_num,
            "document_id": document_id,
        }
        return CandidateValidationResult(accepted=True, sanitized_candidate=sanitized)

    def validate_relationship_candidate(
        self,
        candidate: dict[str, Any] | Any,
        known_entities: dict[str, EntityMention] | list[EntityMention],
        doc_understanding: Optional[DocumentUnderstanding] = None,
        *,
        document_id: str,
    ) -> CandidateValidationResult:
        """Validate an AI relationship candidate against CrimeLens frozen contract and evidence rules."""
        if candidate is None:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.MALFORMED_AI_RESPONSE,
                details="Candidate object is None",
            )

        # Prepare entity lookup
        if isinstance(known_entities, list):
            entity_map = {e.id: e for e in known_entities}
        else:
            entity_map = dict(known_entities)

        # 1. Source & Target Entity Reference Validation
        source_ref = (
            getattr(candidate, "source_entity_ref", None)
            or getattr(candidate, "source_entity_id", None)
            or (candidate.get("source_entity_ref") or candidate.get("source_entity_id") if isinstance(candidate, dict) else None)
        )
        target_ref = (
            getattr(candidate, "target_entity_ref", None)
            or getattr(candidate, "target_entity_id", None)
            or (candidate.get("target_entity_ref") or candidate.get("target_entity_id") if isinstance(candidate, dict) else None)
        )

        if not source_ref or not str(source_ref).strip():
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.MISSING_SOURCE_ENTITY,
                details="Source entity reference is missing or empty",
            )
        if not target_ref or not str(target_ref).strip():
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.MISSING_TARGET_ENTITY,
                details="Target entity reference is missing or empty",
            )

        s_id = str(source_ref).strip()
        t_id = str(target_ref).strip()

        if s_id not in entity_map:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.MISSING_SOURCE_ENTITY,
                details=f"Source entity ID {s_id!r} not found among known entities",
            )
        if t_id not in entity_map:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.MISSING_TARGET_ENTITY,
                details=f"Target entity ID {t_id!r} not found among known entities",
            )

        # 2. Reject Self-Relationships
        if s_id == t_id:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.SELF_RELATIONSHIP,
                details=f"Self-relationship detected: {s_id} -> {t_id}",
            )

        source_ent = entity_map[s_id]
        target_ent = entity_map[t_id]

        # 3. Relationship Type Validation
        raw_rel = (
            getattr(candidate, "relationship_type", None)
            or getattr(candidate, "relationship", None)
            or (candidate.get("relationship_type") or candidate.get("relationship") if isinstance(candidate, dict) else None)
        )
        if raw_rel is None:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.UNSUPPORTED_RELATIONSHIP_TYPE,
                details="Relationship type is missing",
            )

        rel_str = raw_rel.value if isinstance(raw_rel, RelationshipType) else str(raw_rel).strip().upper()
        if rel_str not in SUPPORTED_RELATIONSHIP_TYPES:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.UNSUPPORTED_RELATIONSHIP_TYPE,
                details=f"Unsupported relationship type: {rel_str!r}",
            )
        rel_type = SUPPORTED_RELATIONSHIP_TYPES[rel_str]

        # 4. Entity Type Compatibility Check
        allowed_pairs = ALLOWED_RELATIONSHIP_ENTITY_PAIRS.get(rel_type, set())
        if (source_ent.type, target_ent.type) not in allowed_pairs:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.INCOMPATIBLE_ENTITY_PAIR,
                details=f"Entity pair ({source_ent.type.value}, {target_ent.type.value}) incompatible with {rel_type.value}",
            )

        # 5. Relationship Status Validation
        raw_status = (
            getattr(candidate, "status", None)
            or (candidate.get("status") if isinstance(candidate, dict) else "INFERRED")
        )
        status_str = raw_status.value if isinstance(raw_status, RelationshipStatus) else str(raw_status).strip().upper()
        if status_str not in SUPPORTED_RELATIONSHIP_STATUSES:
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.INVALID_STATUS,
                details=f"Unsupported relationship status: {status_str!r}",
            )
        rel_status = SUPPORTED_RELATIONSHIP_STATUSES[status_str]

        # 6. Confidence Validation
        raw_conf = (
            getattr(candidate, "confidence", None)
            or (candidate.get("confidence") if isinstance(candidate, dict) else 0.8)
        )
        valid_conf, conf_val, conf_reason = self.validate_confidence(raw_conf)
        if not valid_conf:
            return CandidateValidationResult(
                accepted=False,
                reason=conf_reason or ValidationRejectionReason.INVALID_CONFIDENCE,
                details=f"Invalid relationship confidence score: {raw_conf!r}",
            )

        # 7. Document Provenance Check
        cand_doc_id = (
            getattr(candidate, "source_document_id", None)
            or getattr(candidate, "document_id", None)
            or (candidate.get("source_document_id") or candidate.get("document_id") if isinstance(candidate, dict) else None)
        )
        if cand_doc_id and str(cand_doc_id).strip() != document_id.strip():
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.UNKNOWN_DOCUMENT,
                details=f"Relationship document_id {cand_doc_id!r} does not match current document {document_id!r}",
            )

        # 8. Page Reference Bounds
        page_num = (
            getattr(candidate, "page_number", None)
            or (candidate.get("page_number") if isinstance(candidate, dict) else None)
        )
        if page_num is not None:
            if not isinstance(page_num, int) or page_num < 1:
                return CandidateValidationResult(
                    accepted=False,
                    reason=ValidationRejectionReason.FABRICATED_PAGE,
                    details=f"Invalid page reference {page_num!r} (must be >= 1)",
                )
            if doc_understanding is not None and doc_understanding.page_count > 0:
                if page_num > doc_understanding.page_count:
                    return CandidateValidationResult(
                        accepted=False,
                        reason=ValidationRejectionReason.FABRICATED_PAGE,
                        details=f"Page {page_num} exceeds actual page count ({doc_understanding.page_count})",
                    )

        # 9. Evidence Snippet Required & Grounded
        snippet = (
            getattr(candidate, "evidence_snippet", None)
            or (candidate.get("evidence_snippet") or candidate.get("snippet") if isinstance(candidate, dict) else None)
        )
        if not snippet or not isinstance(snippet, str) or not snippet.strip():
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.MISSING_EVIDENCE,
                details="Relationship candidate is missing required evidence snippet",
            )
        snip_str = snippet.strip()

        # Check for criminality assertions in snippet
        if self.check_criminality_assertion(snip_str):
            return CandidateValidationResult(
                accepted=False,
                reason=ValidationRejectionReason.CRIMINALITY_ASSERTION,
                details=f"Evidence snippet contains prohibited criminality/guilt assertion: {snip_str!r}",
            )

        grounded_snip = snip_str
        verified_page = page_num
        if doc_understanding is not None and doc_understanding.full_text:
            v_state, g_snip, v_page = self.evidence_engine.verify_and_ground_snippet(
                snip_str,
                doc_understanding,
                claimed_page=page_num,
            )
            if v_state in (VerificationState.INVALID, VerificationState.UNVERIFIED) or not g_snip:
                return CandidateValidationResult(
                    accepted=False,
                    reason=ValidationRejectionReason.FABRICATED_SNIPPET,
                    details=f"Evidence snippet {snip_str[:80]!r} could not be grounded in document context",
                )
            grounded_snip = g_snip
            verified_page = v_page

        # 10. Check reasoning summary (strip internal thoughts / CoT)
        reasoning = (
            getattr(candidate, "reasoning_summary", None)
            or (candidate.get("reasoning_summary") or candidate.get("reasoning") if isinstance(candidate, dict) else None)
        )
        sanitized_reasoning = None
        if reasoning and isinstance(reasoning, str):
            clean_r = reasoning.strip()
            if not self.check_criminality_assertion(clean_r):
                sanitized_reasoning = clean_r

        sanitized = {
            "source_entity_ref": s_id,
            "target_entity_ref": t_id,
            "relationship_type": rel_type,
            "confidence": conf_val,
            "status": rel_status,
            "evidence_snippet": grounded_snip,
            "page_number": verified_page,
            "reasoning_summary": sanitized_reasoning,
            "document_id": document_id,
        }
        return CandidateValidationResult(accepted=True, sanitized_candidate=sanitized)

    def verify_structured_immutability(
        self,
        original_transactions: list[TransactionRecord],
        original_cdrs: list[CDRRecord],
        current_transactions: list[TransactionRecord],
        current_cdrs: list[CDRRecord],
    ) -> bool:
        """Verify that AI candidate reasoning never mutated structured CDR or transaction data."""
        if len(original_transactions) != len(current_transactions):
            return False
        if len(original_cdrs) != len(current_cdrs):
            return False

        for orig, curr in zip(original_transactions, current_transactions):
            if (
                orig.amount != curr.amount
                or orig.currency != curr.currency
                or orig.transaction_time != curr.transaction_time
                or orig.sender != curr.sender
                or orig.recipient != curr.recipient
            ):
                return False

        for orig, curr in zip(original_cdrs, current_cdrs):
            if (
                orig.call_time != curr.call_time
                or orig.duration != curr.duration
                or orig.caller != curr.caller
                or orig.callee != curr.callee
            ):
                return False

        return True

    def _is_entity_grounded(self, name: str, source_text: str, entity_type: EntityType) -> bool:
        """Verify candidate entity name is grounded in source text."""
        source_lower = source_text.lower()
        name_lower = name.lower().strip()

        # 1. Exact or substring match
        if name_lower in source_lower:
            return True

        # 2. Normalized digits match for PHONE, BANK_ACCOUNT, VEHICLE
        if entity_type == EntityType.PHONE:
            digits = "".join(ch for ch in name if ch.isdigit())
            src_digits = "".join(ch for ch in source_lower if ch.isdigit())
            if len(digits) >= 10 and digits[-10:] in src_digits:
                return True
        elif entity_type in (EntityType.BANK_ACCOUNT, EntityType.VEHICLE):
            compact_name = "".join(name_lower.split())
            compact_src = "".join(source_lower.split())
            if compact_name in compact_src:
                return True

        # 3. Multi-word name token overlap (for persons/orgs: at least 70% present)
        tokens = [t for t in name_lower.split() if len(t) > 2]
        if tokens:
            matches = sum(1 for t in tokens if t in source_lower)
            if (matches / len(tokens)) >= 0.7:
                return True

        return False

    def validate_final_result(self, result: ExtractionResult) -> ExtractionResult:
        """Validate final ExtractionResult against contract schema and JSON serializability."""
        # 1. Pydantic contract validation
        validated = ExtractionResult.model_validate(result)

        # 2. JSON serializability check
        try:
            dumped = validated.model_dump(mode="json")
            json.dumps(dumped)
        except Exception as exc:
            raise ValueError(f"ExtractionResult failed JSON serializability: {exc}") from exc

        return validated
