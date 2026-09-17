"""Evidence and graph-quality firewall for extracted relationships.

The firewall is intentionally conservative: invalid candidates are rejected,
not repaired into stronger claims.  Accepted objects remain instances of the
existing ``shared.schemas.Relationship`` model, so backend handoff remains
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ml.intelligence.document_understanding import evidence_is_grounded
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship


_ALLOWED_ENDPOINTS: dict[RelationshipType, set[tuple[EntityType, EntityType]]] = {
    RelationshipType.CALLED: {
        (EntityType.PERSON, EntityType.PERSON),
        (EntityType.PERSON, EntityType.PHONE),
        (EntityType.PHONE, EntityType.PHONE),
    },
    RelationshipType.SENT_MONEY_TO: {
        (EntityType.PERSON, EntityType.PERSON),
        (EntityType.PERSON, EntityType.BANK_ACCOUNT),
        (EntityType.PERSON, EntityType.ORGANIZATION),
        (EntityType.BANK_ACCOUNT, EntityType.BANK_ACCOUNT),
        (EntityType.BANK_ACCOUNT, EntityType.ORGANIZATION),
        (EntityType.ORGANIZATION, EntityType.BANK_ACCOUNT),
        (EntityType.ORGANIZATION, EntityType.ORGANIZATION),
        (EntityType.ORGANIZATION, EntityType.PERSON),
    },
    RelationshipType.OWNS_VEHICLE: {
        (EntityType.PERSON, EntityType.VEHICLE),
        (EntityType.ORGANIZATION, EntityType.VEHICLE),
    },
    RelationshipType.USED_VEHICLE: {(EntityType.PERSON, EntityType.VEHICLE)},
    RelationshipType.WORKS_FOR: {(EntityType.PERSON, EntityType.ORGANIZATION)},
    RelationshipType.LOCATED_AT: {
        (EntityType.PERSON, EntityType.LOCATION),
        (EntityType.ORGANIZATION, EntityType.LOCATION),
        (EntityType.VEHICLE, EntityType.LOCATION),
        (EntityType.EVENT, EntityType.LOCATION),
        (EntityType.BANK_ACCOUNT, EntityType.LOCATION),
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

_STATUS_RANK = {
    RelationshipStatus.PREDICTED: 0,
    RelationshipStatus.INFERRED: 1,
    RelationshipStatus.CONFIRMED: 2,
}


@dataclass
class GraphQualityReport:
    accepted: int = 0
    rejected: int = 0
    duplicate_groups: int = 0
    contradictions: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)

    def reject(self, reason: str) -> None:
        self.rejected += 1
        self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "rejected": self.rejected,
            "duplicate_groups": self.duplicate_groups,
            "contradictions": self.contradictions,
            "rejection_reasons": dict(sorted(self.rejection_reasons.items())),
        }


def _record_ids(records: Iterable[Any] | None) -> set[str]:
    ids: set[str] = set()
    for record in records or ():
        value = getattr(record, "record_id", None)
        if value is None and isinstance(record, dict):
            value = record.get("record_id") or record.get("id")
        if value:
            ids.add(str(value))
    return ids


def _better_relationship(current: Relationship, candidate: Relationship) -> Relationship:
    current_key = (_STATUS_RANK[current.status], current.confidence, current.id)
    candidate_key = (_STATUS_RANK[candidate.status], candidate.confidence, candidate.id)
    return candidate if candidate_key > current_key else current


def apply_graph_quality_firewall(
    relationships: Iterable[Relationship],
    entities: Iterable[EntityMention],
    *,
    source_text: str = "",
    structured_records: Iterable[Any] | None = None,
    min_confidence: float = 0.0,
) -> tuple[list[Relationship], GraphQualityReport]:
    """Validate, deduplicate, and conservatively retain relationship occurrences.

    A source-record relationship is grounded by its record ID; a document
    relationship must contain an exact source-text evidence snippet.  This
    distinction preserves generated structured-record evidence without ever
    allowing an ungrounded AI sentence into the graph.
    """
    entity_map = {entity.id: entity for entity in entities}
    valid_record_ids = _record_ids(structured_records)
    report = GraphQualityReport()
    accepted_by_key: dict[tuple[str, RelationshipType, str], Relationship] = {}

    for rel in relationships:
        source = entity_map.get(rel.source_entity_id)
        target = entity_map.get(rel.target_entity_id)
        if source is None or target is None:
            report.reject("unknown_endpoint")
            continue
        if source.id == target.id:
            report.reject("self_loop")
            continue
        if rel.confidence < min_confidence:
            report.reject("below_confidence_threshold")
            continue
        endpoint_pair = (source.type, target.type)
        if endpoint_pair not in _ALLOWED_ENDPOINTS.get(rel.relationship, set()):
            report.reject("invalid_endpoint_types")
            continue
        if rel.source_record_id:
            if valid_record_ids and str(rel.source_record_id) not in valid_record_ids:
                report.reject("unknown_record_provenance")
                continue
        elif not evidence_is_grounded(rel.evidence_snippet, source_text):
            report.reject("ungrounded_evidence")
            continue

        key = (source.id, rel.relationship, target.id)
        previous = accepted_by_key.get(key)
        if previous is not None:
            report.duplicate_groups += 1
            if previous.status != rel.status:
                report.contradictions += 1
            accepted_by_key[key] = _better_relationship(previous, rel)
        else:
            accepted_by_key[key] = rel

    result = sorted(accepted_by_key.values(), key=lambda item: item.id)
    report.accepted = len(result)
    return result, report


__all__ = ["GraphQualityReport", "apply_graph_quality_firewall"]
