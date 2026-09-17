import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntityType, RelationshipStatus, RelationshipType


class EntityCaseRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: uuid.UUID
    case_number: str


class EntityAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aliases: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    vehicles: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    occupations: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    source_documents: list[str] = Field(default_factory=list)


class EntityRead(BaseModel):
    """Canonical entity plus cases the current user is allowed to see and rich attributes."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    type: EntityType
    canonical_name: str
    cases: list[EntityCaseRef]
    attributes: EntityAttributes = Field(default_factory=EntityAttributes)


class EntityConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: uuid.UUID
    type: EntityType
    name: str
    relationship: RelationshipType
    relationship_id: uuid.UUID
    confidence: float
    status: RelationshipStatus
    source_document_id: uuid.UUID | None = None
    evidence_snippet: str | None = None
    case_id: uuid.UUID | None = None


class EntityConnectionsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: uuid.UUID
    connections: list[EntityConnection]


class CaseGraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: uuid.UUID
    type: EntityType
    name: str


class CaseGraphRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationship_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship: RelationshipType
    confidence: float
    status: RelationshipStatus
    source_document_id: uuid.UUID | None = None
    evidence_snippet: str | None = None


class CaseGraphResult(BaseModel):
    """Case-scoped subgraph. File bytes and Neo4j internal IDs are never included."""

    model_config = ConfigDict(extra="forbid")

    case_id: uuid.UUID
    nodes: list[CaseGraphNode]
    relationships: list[CaseGraphRelationship]
    truncated: bool = Field(
        default=False,
        description="True when more case relationships exist than the response limit.",
    )
