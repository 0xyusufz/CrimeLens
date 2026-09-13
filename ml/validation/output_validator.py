"""Output validation helpers ensuring ML outputs strictly conform to shared contract schemas.

Validates:
- ExtractionResult
- ResolutionProposal
- Pattern
- Lead
"""

from typing import Any

from shared.schemas.models import (
    EntityMention,
    ExtractionResult,
    Lead,
    Pattern,
    Relationship,
    ResolutionProposal,
)


def validate_entity_mention(data: dict[str, Any] | EntityMention) -> EntityMention:
    """Validate an entity mention against the shared Pydantic contract."""
    if isinstance(data, EntityMention):
        return data
    return EntityMention.model_validate(data)


def validate_relationship(data: dict[str, Any] | Relationship) -> Relationship:
    """Validate a relationship against the shared Pydantic contract."""
    if isinstance(data, Relationship):
        return data
    return Relationship.model_validate(data)


def validate_extraction_result(data: dict[str, Any] | ExtractionResult) -> ExtractionResult:
    """Validate an extraction result envelope against the shared Pydantic contract."""
    if isinstance(data, ExtractionResult):
        return data
    return ExtractionResult.model_validate(data)


def validate_resolution_proposal(
    data: dict[str, Any] | ResolutionProposal,
) -> ResolutionProposal:
    """Validate a resolution proposal against the shared Pydantic contract."""
    if isinstance(data, ResolutionProposal):
        return data
    return ResolutionProposal.model_validate(data)


def validate_pattern(data: dict[str, Any] | Pattern) -> Pattern:
    """Validate a pattern detection result against the shared Pydantic contract."""
    if isinstance(data, Pattern):
        return data
    return Pattern.model_validate(data)


def validate_lead(data: dict[str, Any] | Lead) -> Lead:
    """Validate an investigative lead against the shared Pydantic contract."""
    if isinstance(data, Lead):
        return data
    return Lead.model_validate(data)
