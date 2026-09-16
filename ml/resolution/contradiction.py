"""Detect conflicting evidence without discarding either source occurrence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship


@dataclass(frozen=True)
class Contradiction:
    entity_id: str
    relationship: RelationshipType
    conflicting_targets: tuple[str, str]
    relationship_ids: tuple[str, str]
    reason: str


def detect_contradictions(
    relationships: Iterable[Relationship],
    entities: Iterable[EntityMention],
) -> list[Contradiction]:
    """Find coexisting, incompatible location assertions for review.

    A location can legitimately change over time, so this reports a review
    signal rather than rejecting or overwriting either evidence item.
    """
    entity_map = {entity.id: entity for entity in entities}
    by_source: dict[str, list[Relationship]] = {}
    for relation in relationships:
        if relation.relationship != RelationshipType.LOCATED_AT:
            continue
        if relation.status == RelationshipStatus.PREDICTED:
            continue
        target = entity_map.get(relation.target_entity_id)
        if target is None or target.type != EntityType.LOCATION:
            continue
        by_source.setdefault(relation.source_entity_id, []).append(relation)

    contradictions: list[Contradiction] = []
    for source_id, items in sorted(by_source.items()):
        for index, left in enumerate(items):
            for right in items[index + 1:]:
                if left.target_entity_id == right.target_entity_id:
                    continue
                contradictions.append(
                    Contradiction(
                        entity_id=source_id,
                        relationship=RelationshipType.LOCATED_AT,
                        conflicting_targets=(left.target_entity_id, right.target_entity_id),
                        relationship_ids=(left.id, right.id),
                        reason="multiple_supported_locations_require_temporal_review",
                    )
                )
    return contradictions


__all__ = ["Contradiction", "detect_contradictions"]
