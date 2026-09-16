"""Case-memory resolution helpers with no database dependency.

The backend remains the canonical-identity authority.  This module consumes an
optional snapshot of already-known case entities and returns explainable link
proposals for review/persistence by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ml.resolution.resolver import compare_mentions
from shared.schemas.enums import EntityType, ResolutionSignal
from shared.schemas.models import EntityMention


@dataclass(frozen=True)
class CaseEntityReference:
    canonical_entity_id: str
    mention: EntityMention


@dataclass(frozen=True)
class CaseMemoryProposal:
    mention_id: str
    canonical_entity_id: str
    confidence: float
    signals: tuple[ResolutionSignal, ...]
    requires_review: bool


def _reference_from_raw(index: int, raw: Any) -> CaseEntityReference | None:
    if isinstance(raw, CaseEntityReference):
        return raw
    if isinstance(raw, EntityMention):
        return CaseEntityReference(f"case_entity_{index:03d}", raw)
    if not isinstance(raw, dict):
        return None
    canonical_id = str(raw.get("canonical_entity_id") or raw.get("entity_id") or "").strip()
    try:
        mention = EntityMention(
            id=str(raw.get("mention_id") or raw.get("id") or f"case_mention_{index:03d}"),
            type=EntityType(str(raw.get("type") or "")),
            name=str(raw.get("name") or raw.get("canonical_name") or "").strip(),
            confidence=float(raw.get("confidence", 1.0)),
        )
    except (TypeError, ValueError):
        return None
    return CaseEntityReference(canonical_id or f"case_entity_{index:03d}", mention)


def propose_case_memory_links(
    mentions: Iterable[EntityMention],
    case_memory: Iterable[Any] | None,
) -> list[CaseMemoryProposal]:
    """Compare new mentions against a caller-supplied canonical case snapshot."""
    references = [
        reference
        for index, raw in enumerate(case_memory or (), start=1)
        if (reference := _reference_from_raw(index, raw)) is not None
    ]
    proposals: list[CaseMemoryProposal] = []
    for mention in mentions:
        for reference in references:
            match = compare_mentions(mention, reference.mention, allow_fuzzy_name=True)
            if match is None:
                continue
            confidence, signals = match
            strong = any(
                signal
                in {
                    ResolutionSignal.PHONE_MATCH,
                    ResolutionSignal.ACCOUNT_MATCH,
                    ResolutionSignal.VEHICLE_MATCH,
                }
                for signal in signals
            )
            proposals.append(
                CaseMemoryProposal(
                    mention_id=mention.id,
                    canonical_entity_id=reference.canonical_entity_id,
                    confidence=round(confidence, 4),
                    signals=tuple(signals),
                    requires_review=not strong,
                )
            )
    return sorted(
        proposals,
        key=lambda item: (item.mention_id, -item.confidence, item.canonical_entity_id),
    )


__all__ = ["CaseEntityReference", "CaseMemoryProposal", "propose_case_memory_links"]
