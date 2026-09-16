"""Explainable case-signal assessment for investigator triage.

This is a case signal, not a person-risk or guilt score.  It is returned only
inside the optional full-analysis result and does not alter existing schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shared.schemas.enums import PatternType, RelationshipStatus, Severity
from shared.schemas.models import Pattern, Relationship


@dataclass(frozen=True)
class SosAssessment:
    level: str
    score: float
    reason_codes: tuple[str, ...]
    supporting_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "score": self.score,
            "reason_codes": list(self.reason_codes),
            "supporting_ids": list(self.supporting_ids),
        }


def assess_sos(
    patterns: Iterable[Pattern] | None = None,
    relationships: Iterable[Relationship] | None = None,
) -> SosAssessment:
    patterns = list(patterns or ())
    relationships = list(relationships or ())
    score = 0.0
    reasons: set[str] = set()
    supporting: set[str] = set()

    severity_weight = {Severity.LOW: 0.20, Severity.MEDIUM: 0.45, Severity.HIGH: 0.70}
    pattern_reason = {
        PatternType.CIRCULAR_TRANSACTION: "CIRCULAR_TRANSACTION",
        PatternType.RAPID_TRANSFER_CHAIN: "RAPID_TRANSFER_CHAIN",
        PatternType.LOCATION_TIME_OVERLAP: "LOCATION_TIME_OVERLAP",
    }
    for pattern in patterns:
        score = max(score, severity_weight.get(pattern.severity, 0.0))
        reason = pattern_reason.get(pattern.type, str(pattern.type))
        reasons.add(reason)
        supporting.add(pattern.id)
        supporting.update(pattern.evidence_ids)

    confirmed = sum(rel.status == RelationshipStatus.CONFIRMED for rel in relationships)
    inferred = sum(rel.status == RelationshipStatus.INFERRED for rel in relationships)
    if confirmed >= 3:
        score = max(score, min(0.85, 0.55 + confirmed * 0.05))
        reasons.add("MULTI_RELATIONSHIP_SUPPORT")
    elif inferred >= 2:
        score = max(score, 0.45)
        reasons.add("INFERRED_NETWORK_SIGNAL")
    supporting.update(rel.id for rel in relationships if rel.status != RelationshipStatus.PREDICTED)

    if score >= 0.80:
        level = "CRITICAL"
    elif score >= 0.60:
        level = "HIGH"
    elif score >= 0.35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return SosAssessment(
        level=level,
        score=round(score, 4),
        reason_codes=tuple(sorted(reasons)),
        supporting_ids=tuple(sorted(supporting)),
    )


__all__ = ["SosAssessment", "assess_sos"]
