from uuid import UUID

from pydantic import BaseModel, ConfigDict

from shared.schemas import Lead, Pattern


class CaseInsights(BaseModel):
    """Case-scoped Person B intelligence. File bytes and secrets are never included."""

    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    patterns: list[Pattern]
    leads: list[Lead]
