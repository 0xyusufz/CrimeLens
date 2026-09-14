"""Lead generation module for CrimeLens ML pipeline.

Translates detected suspicious patterns and evidence-backed investigative signals
into deterministic, explainable Lead recommendations for investigator review.

Core Principles:
1. Leads are investigative recommendations, NOT statements of guilt or accusations.
2. Zero person-level risk scores or criminal predictions.
3. Strict adherence to shared.schemas.Lead:
   - Allowed priorities: LeadPriority.LOW, LeadPriority.MEDIUM, LeadPriority.HIGH
   - Allowed status: LeadStatus.REVIEW_REQUIRED (never DETECTED, never PREDICTED)
   - Extra fields forbidden (no severity, no confidence)
4. Full evidence and entity traceability back to ML staging identifiers.
5. Deterministic sorting and deduplication.
"""

from typing import Any, Optional

from shared.schemas.enums import LeadPriority, LeadStatus, LeadType, PatternType
from shared.schemas.models import Lead, Pattern, Relationship


def generate_leads(
    patterns: Optional[list[dict[str, Any] | Pattern]] = None,
    relationships: Optional[list[dict[str, Any] | Relationship]] = None,
    **kwargs: Any,
) -> list[Lead]:
    """Generate deterministic, explainable investigative leads from patterns and evidence.

    Args:
        patterns: List of Pattern instances or raw pattern dictionaries.
        relationships: Optional list of Relationship instances or dictionaries.
        **kwargs: Additional structured evidence hooks.

    Returns:
        list[Lead]: Validated, deduplicated Lead instances ordered by priority.
    """
    candidate_leads: list[dict[str, Any]] = []
    seen_dedup_keys: set[tuple[LeadType, tuple[str, ...], tuple[str, ...]]] = set()

    # 1. Process Phase 8 Pattern Outputs
    if patterns:
        for p_raw in patterns:
            try:
                p = Pattern.model_validate(p_raw) if not isinstance(p_raw, Pattern) else p_raw
            except Exception:
                continue

            lead_type: Optional[LeadType] = None
            priority: LeadPriority = LeadPriority.LOW
            title: str = ""
            explanation: str = ""
            priority_score: Optional[float] = None

            if p.type == PatternType.CIRCULAR_TRANSACTION:
                lead_type = LeadType.CIRCULAR_TRANSACTION
                priority = LeadPriority.HIGH
                priority_score = 0.90
                nodes_repr = " → ".join(p.entities)
                title = f"Investigate circular transaction cycle ({nodes_repr})"
                explanation = (
                    f"Review the detected fund routing cycle ({nodes_repr}) and supporting "
                    f"transaction records ({', '.join(p.evidence_ids)}) for potential layered routing."
                )

            elif p.type == PatternType.RAPID_TRANSFER_CHAIN:
                lead_type = LeadType.RAPID_TRANSFER_CHAIN
                priority = LeadPriority.HIGH
                priority_score = 0.85
                nodes_repr = " → ".join(p.entities)
                title = f"Investigate rapid fund transfer chain ({nodes_repr})"
                explanation = (
                    f"Review the rapid consecutive fund transfer chain ({nodes_repr}) completed "
                    f"within 48 hours across linked intermediary accounts ({', '.join(p.evidence_ids)})."
                )

            elif p.type == PatternType.LOCATION_TIME_OVERLAP:
                lead_type = LeadType.LOCATION_TIME_OVERLAP
                priority = LeadPriority.MEDIUM
                priority_score = 0.60
                e1 = p.entities[0] if len(p.entities) > 0 else "Entity A"
                e2 = p.entities[1] if len(p.entities) > 1 else "Entity B"
                title = f"Review spatio-temporal co-presence of {e1} and {e2}"
                explanation = (
                    f"Review the temporal and geographic proximity records ({', '.join(p.evidence_ids)}) "
                    f"associating {e1} and {e2} at the same location within 2 hours."
                )

            if lead_type is not None:
                sorted_entities = sorted(p.entities)
                sorted_evidence = sorted(p.evidence_ids)
                dedup_key = (lead_type, tuple(sorted_entities), tuple(sorted_evidence))

                if dedup_key in seen_dedup_keys:
                    continue
                seen_dedup_keys.add(dedup_key)

                candidate_leads.append(
                    {
                        "type": lead_type,
                        "priority": priority,
                        "status": LeadStatus.REVIEW_REQUIRED,
                        "title": title,
                        "explanation": explanation,
                        "entity_ids": list(p.entities),
                        "evidence_ids": list(p.evidence_ids),
                        "priority_score": priority_score,
                    }
                )

    # 2. Sort deterministically: HIGH priority first, then by type, then entities
    priority_order = {LeadPriority.HIGH: 0, LeadPriority.MEDIUM: 1, LeadPriority.LOW: 2}
    candidate_leads.sort(
        key=lambda c: (
            priority_order.get(c["priority"], 99),
            c["type"].value,
            c["entity_ids"],
            c["evidence_ids"],
        )
    )

    # 3. Mint sequential staging IDs and instantiate validated Lead models
    leads: list[Lead] = []
    for idx, cand in enumerate(candidate_leads, start=1):
        leads.append(
            Lead(
                id=f"lead_{idx:03d}",
                type=cand["type"],
                priority=cand["priority"],
                status=cand["status"],
                title=cand["title"],
                explanation=cand["explanation"],
                entity_ids=cand["entity_ids"],
                evidence_ids=cand["evidence_ids"],
                priority_score=cand["priority_score"],
            )
        )

    return leads
