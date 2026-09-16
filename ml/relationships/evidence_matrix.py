"""Relationship evidence matrix and evidence-group consolidation.

The shared ``Relationship`` contract represents one source occurrence.  This
module preserves those occurrences while producing an internal grouped view:
one logical relationship can have many independent evidence records without
collapsing provenance into a fabricated snippet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ml.intelligence.document_understanding import evidence_is_grounded
from shared.schemas.enums import RelationshipStatus
from shared.schemas.models import EntityMention, Relationship


class EvidenceStrength(str, Enum):
    STRUCTURED = "STRUCTURED"
    EXPLICIT = "EXPLICIT"
    CONTEXTUAL = "CONTEXTUAL"
    UNGROUNDED = "UNGROUNDED"


@dataclass(frozen=True)
class EvidenceAssessment:
    relationship_id: str
    strength: EvidenceStrength
    grounded: bool
    independent_source_key: str


@dataclass(frozen=True)
class RelationshipEvidenceGroup:
    source_entity_id: str
    relationship: str
    target_entity_id: str
    relationship_ids: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    independent_source_count: int
    calibrated_confidence: float
    strongest_status: str


_STATUS_WEIGHT = {
    RelationshipStatus.PREDICTED: 0,
    RelationshipStatus.INFERRED: 1,
    RelationshipStatus.CONFIRMED: 2,
}


def assess_evidence(
    relationship: Relationship,
    *,
    source_text: str,
    known_record_ids: Iterable[str] = (),
) -> EvidenceAssessment:
    known_records = {str(item) for item in known_record_ids}
    if relationship.source_record_id:
        grounded = not known_records or relationship.source_record_id in known_records
        strength = EvidenceStrength.STRUCTURED if grounded else EvidenceStrength.UNGROUNDED
        source_key = f"record:{relationship.source_record_id}"
    else:
        grounded = evidence_is_grounded(relationship.evidence_snippet, source_text)
        strength = EvidenceStrength.EXPLICIT if grounded else EvidenceStrength.UNGROUNDED
        source_key = f"document:{relationship.source_document_id or 'unknown'}:{relationship.id}"
    return EvidenceAssessment(
        relationship_id=relationship.id,
        strength=strength,
        grounded=grounded,
        independent_source_key=source_key,
    )


def consolidate_relationship_evidence(
    relationships: Iterable[Relationship],
) -> list[RelationshipEvidenceGroup]:
    """Build a read-only canonical edge view without discarding occurrences."""
    buckets: dict[tuple[str, str, str], list[Relationship]] = {}
    for relationship in relationships:
        key = (
            relationship.source_entity_id,
            relationship.relationship.value,
            relationship.target_entity_id,
        )
        buckets.setdefault(key, []).append(relationship)

    groups: list[RelationshipEvidenceGroup] = []
    for (source_id, relation, target_id), items in sorted(buckets.items()):
        ordered = sorted(items, key=lambda item: item.id)
        source_keys = {
            f"record:{item.source_record_id}"
            if item.source_record_id
            else f"document:{item.source_document_id or 'unknown'}:{item.evidence_snippet.strip()}"
            for item in ordered
        }
        # Independent records/sources strengthen confidence, but copies of the
        # same evidence do not. The cap deliberately leaves human review room.
        max_confidence = max(item.confidence for item in ordered)
        independent = len(source_keys)
        calibrated = min(0.99, max_confidence + 0.03 * max(0, independent - 1))
        strongest = max(ordered, key=lambda item: (_STATUS_WEIGHT[item.status], item.confidence, item.id))
        groups.append(
            RelationshipEvidenceGroup(
                source_entity_id=source_id,
                relationship=relation,
                target_entity_id=target_id,
                relationship_ids=tuple(item.id for item in ordered),
                evidence_sources=tuple(sorted(source_keys)),
                independent_source_count=independent,
                calibrated_confidence=round(calibrated, 4),
                strongest_status=strongest.status.value,
            )
        )
    return groups


__all__ = [
    "EvidenceAssessment",
    "EvidenceStrength",
    "RelationshipEvidenceGroup",
    "assess_evidence",
    "consolidate_relationship_evidence",
]
