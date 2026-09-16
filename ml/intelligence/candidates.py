"""Candidate-first normalization for optional AI provider output.

Providers are allowed to suggest names and edges, but only candidates with
valid vocabulary, known/exactly grounded evidence, and valid endpoint types are
handed to the frozen relationship contract.  The provider can therefore fail
softly without weakening deterministic extraction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from ml.intelligence.document_understanding import evidence_is_grounded
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship


def _raw_items(value: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if isinstance(value, dict):
        return list(value.get("entities") or []), list(value.get("relationships") or [])
    if isinstance(value, tuple) and len(value) == 2:
        return list(value[0] or []), list(value[1] or [])
    return [], []


def _confidence(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def integrate_ai_candidates(
    entities: Iterable[EntityMention],
    provider_output: Any,
    *,
    document_id: str,
    source_text: str,
    min_confidence: float = 0.5,
    relationship_id_prefix: str = "rel_ai",
) -> tuple[list[EntityMention], list[Relationship], dict[str, int]]:
    """Merge optional provider candidates into deterministic document mentions.

    Returns ``(entities, relationships, telemetry)``.  The telemetry is
    internal and intentionally small so it can be returned in full analysis
    without changing the default API envelope.
    """
    raw_entities, raw_relationships = _raw_items(provider_output)
    result_entities = list(entities)
    by_name_type = {(item.type, item.name.casefold()): item for item in result_entities}
    telemetry = {"entities_seen": len(raw_entities), "entities_added": 0, "relationships_seen": len(raw_relationships), "relationships_accepted": 0, "relationships_rejected": 0}

    next_id = len(result_entities) + 1
    for raw in raw_entities:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        try:
            entity_type = EntityType(str(raw.get("type") or "").upper())
        except ValueError:
            continue
        confidence = _confidence(raw.get("confidence"), 0.75)
        if not name or confidence < min_confidence:
            continue
        key = (entity_type, name.casefold())
        if key in by_name_type:
            continue
        mention = EntityMention(
            id=f"mention_{next_id:03d}",
            type=entity_type,
            name=name,
            confidence=round(confidence, 4),
        )
        next_id += 1
        result_entities.append(mention)
        by_name_type[key] = mention
        telemetry["entities_added"] += 1

    # Build an exact name index after provider entities have been added.  No
    # substring matching is used: it can silently map two different people.
    by_name: dict[str, EntityMention] = {}
    for entity in result_entities:
        by_name.setdefault(entity.name.casefold(), entity)

    relationships: list[Relationship] = []
    for index, raw in enumerate(raw_relationships, start=1):
        if not isinstance(raw, dict):
            telemetry["relationships_rejected"] += 1
            continue
        source = by_name.get(str(raw.get("source") or raw.get("source_entity") or "").strip().casefold())
        target = by_name.get(str(raw.get("target") or raw.get("target_entity") or "").strip().casefold())
        evidence = str(raw.get("evidence") or raw.get("evidence_snippet") or "").strip()
        try:
            rel_type = RelationshipType(str(raw.get("type") or raw.get("relationship") or "").upper())
        except ValueError:
            telemetry["relationships_rejected"] += 1
            continue
        if source is None or target is None or source.id == target.id or not evidence:
            telemetry["relationships_rejected"] += 1
            continue
        if not evidence_is_grounded(evidence, source_text):
            telemetry["relationships_rejected"] += 1
            continue
        relationships.append(
            Relationship(
                id=f"{relationship_id_prefix}_{index:03d}",
                source_entity_id=source.id,
                relationship=rel_type,
                target_entity_id=target.id,
                confidence=round(_confidence(raw.get("confidence"), 0.65), 4),
                status=RelationshipStatus.PREDICTED,
                source_document_id=document_id,
                evidence_snippet=evidence,
                extracted_at=datetime.now(timezone.utc),
            )
        )
        telemetry["relationships_accepted"] += 1

    return result_entities, relationships, telemetry


__all__ = ["integrate_ai_candidates"]
