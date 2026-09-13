import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntityType, RelationshipStatus, RelationshipType


class InvestigationPathNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: uuid.UUID
    type: EntityType
    name: str


class InvestigationPathRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationship_id: uuid.UUID
    relationship: RelationshipType
    confidence: float
    status: RelationshipStatus
    source_document_id: uuid.UUID | None = None
    evidence_snippet: str | None = None
    case_id: uuid.UUID | None = None


class InvestigationPathResult(BaseModel):
    """Explainable shortest path. File bytes and Neo4j internal IDs are never included."""

    model_config = ConfigDict(extra="forbid")

    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    case_id: uuid.UUID
    found: bool
    hop_count: int | None = Field(default=None, ge=0)
    nodes: list[InvestigationPathNode]
    relationships: list[InvestigationPathRelationship]
