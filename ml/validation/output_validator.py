"""Output validation helpers ensuring ML outputs strictly conform to shared contract schemas.

Validates:
- ExtractionResult
- ResolutionProposal
- Pattern
- Lead
"""

import json
from typing import Any

from shared.schemas.models import (
    EntityMention,
    ExtractionResult,
    Lead,
    Pattern,
    Relationship,
    ResolutionProposal,
)


def validate_json_serializability(data: Any) -> str:
    """Validate that data can be cleanly serialized to standard JSON without errors.

    Raises:
        ValueError: If data cannot be serialized to JSON.
    """
    try:
        if hasattr(data, "model_dump"):
            dumped = data.model_dump(mode="json")
        elif hasattr(data, "to_dict"):
            dumped = data.to_dict()
        else:
            dumped = data
        return json.dumps(dumped, ensure_ascii=False)
    except Exception as exc:
        raise ValueError(f"Object failed JSON serializability: {exc}") from exc


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
    """Validate an extraction result envelope against the shared Pydantic contract and verify JSON serializability."""
    res = data if isinstance(data, ExtractionResult) else ExtractionResult.model_validate(data)
    validate_json_serializability(res)
    return res


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
