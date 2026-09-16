"""Conservative propagation of OCR uncertainty to downstream candidates."""

from __future__ import annotations

from typing import Any, Iterable

from shared.schemas.models import EntityMention, Relationship


def _block_confidence_for_name(name: str, blocks: Iterable[dict[str, Any]]) -> float | None:
    matches: list[float] = []
    for block in blocks:
        text = str(block.get("text") or "")
        if name.casefold() not in text.casefold():
            continue
        try:
            matches.append(max(0.0, min(1.0, float(block.get("confidence")))))
        except (TypeError, ValueError):
            continue
    return max(matches) if matches else None


def apply_ocr_confidence_to_entities(
    entities: Iterable[EntityMention],
    blocks: Iterable[dict[str, Any]],
) -> list[EntityMention]:
    """Lower a mention's confidence when its source OCR is uncertain."""
    block_list = list(blocks)
    adjusted: list[EntityMention] = []
    for entity in entities:
        ocr_confidence = _block_confidence_for_name(entity.name, block_list)
        if ocr_confidence is None:
            adjusted.append(entity)
            continue
        # Preserve a usable floor for contextual corroboration while making
        # low-quality OCR visibly weaker.  54% OCR turns 0.95 into ~0.73.
        multiplier = 0.5 + (0.5 * ocr_confidence)
        adjusted.append(entity.model_copy(update={"confidence": round(entity.confidence * multiplier, 4)}))
    return adjusted


def apply_ocr_confidence_to_relationships(
    relationships: Iterable[Relationship],
    entities: Iterable[EntityMention],
) -> list[Relationship]:
    by_id = {entity.id: entity for entity in entities}
    adjusted: list[Relationship] = []
    for relationship in relationships:
        source = by_id.get(relationship.source_entity_id)
        target = by_id.get(relationship.target_entity_id)
        if source is None or target is None:
            adjusted.append(relationship)
            continue
        endpoint_confidence = min(source.confidence, target.confidence)
        # Never strengthen an edge; only cap it by its least-certain endpoint.
        adjusted.append(
            relationship.model_copy(
                update={"confidence": round(min(relationship.confidence, endpoint_confidence), 4)}
            )
        )
    return adjusted


__all__ = ["apply_ocr_confidence_to_entities", "apply_ocr_confidence_to_relationships"]
