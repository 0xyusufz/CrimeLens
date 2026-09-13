import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RelationshipStatus, RelationshipType


class RelationshipEvidenceRead(BaseModel):
    """Provenance for one staged relationship. File bytes and paths are never included."""

    model_config = ConfigDict(extra="forbid")

    relationship_id: uuid.UUID
    case_id: uuid.UUID
    relationship: RelationshipType
    source_entity_id: uuid.UUID | None = None
    target_entity_id: uuid.UUID | None = None
    confidence: float
    status: RelationshipStatus
    source_document_id: uuid.UUID | None = None
    source_record_id: uuid.UUID | None = None
    evidence_snippet: str | None = None
    extracted_at: datetime
