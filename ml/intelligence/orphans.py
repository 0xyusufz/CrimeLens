"""Explain disconnected graph nodes without fabricating a relationship."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shared.schemas.models import EntityMention, Relationship


@dataclass(frozen=True)
class OrphanExplanation:
    mention_id: str
    name: str
    entity_type: str
    accepted_degree: int
    candidate_degree: int
    reason: str


def analyze_orphans(
    entities: Iterable[EntityMention],
    accepted_relationships: Iterable[Relationship],
    candidate_relationships: Iterable[Relationship] = (),
) -> list[OrphanExplanation]:
    accepted_degree: dict[str, int] = {}
    candidate_degree: dict[str, int] = {}
    for relation in accepted_relationships:
        accepted_degree[relation.source_entity_id] = accepted_degree.get(relation.source_entity_id, 0) + 1
        accepted_degree[relation.target_entity_id] = accepted_degree.get(relation.target_entity_id, 0) + 1
    for relation in candidate_relationships:
        candidate_degree[relation.source_entity_id] = candidate_degree.get(relation.source_entity_id, 0) + 1
        candidate_degree[relation.target_entity_id] = candidate_degree.get(relation.target_entity_id, 0) + 1

    output: list[OrphanExplanation] = []
    for entity in entities:
        accepted = accepted_degree.get(entity.id, 0)
        if accepted:
            continue
        candidates = candidate_degree.get(entity.id, 0)
        output.append(
            OrphanExplanation(
                mention_id=entity.id,
                name=entity.name,
                entity_type=entity.type.value,
                accepted_degree=accepted,
                candidate_degree=candidates,
                reason=(
                    "candidate_relationship_pending_review"
                    if candidates
                    else "no_evidence_backed_relationship_found"
                ),
            )
        )
    return output


__all__ = ["OrphanExplanation", "analyze_orphans"]
