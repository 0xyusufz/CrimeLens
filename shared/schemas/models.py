from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared.schemas.enums import (
    EntityType,
    LeadPriority,
    LeadStatus,
    LeadType,
    PatternType,
    RelationshipStatus,
    RelationshipType,
    ResolutionSignal,
    Severity,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntityMention(ContractModel):
    """Staging/document-level mention. `id` stays an ML mention ID (e.g. mention_001)."""

    id: str = Field(min_length=1, description="ML mention ID, e.g. mention_001")
    type: EntityType
    name: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class Relationship(ContractModel):
    """Extracted source occurrence. Status is stored as-is; never coerce INFERRED/PREDICTED to CONFIRMED.

    Keep this contract compact. amount/currency/transaction_time come from structured
    transaction records; call_time/duration come from structured CDR records.
    """

    id: str = Field(min_length=1, description="ML relationship ID for this extracted occurrence")
    source_entity_id: str = Field(
        min_length=1,
        description="ML mention ID of the source occurrence, not a canonical UUID",
    )
    relationship: RelationshipType
    target_entity_id: str = Field(
        min_length=1,
        description="ML mention ID of the target occurrence, not a canonical UUID",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    status: RelationshipStatus
    source_document_id: Optional[str] = Field(
        default=None,
        description="FIR/document provenance. Backend maps document_id → case_id.",
    )
    source_record_id: Optional[str] = Field(
        default=None,
        description="CDR/transaction provenance, e.g. cdr_000123 or txn_000987",
    )
    evidence_snippet: str = Field(min_length=1)
    extracted_at: datetime

    @model_validator(mode="after")
    def require_provenance(self):
        if not self.source_document_id and not self.source_record_id:
            raise ValueError("relationship requires source_document_id or source_record_id")
        return self


class ExtractionResult(ContractModel):
    """Main Person B → Person A envelope for one processed document."""

    document_id: str = Field(min_length=1)
    entities: list[EntityMention]
    relationships: list[Relationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_relationship_mentions(self):
        mention_ids = {entity.id for entity in self.entities}
        if len(mention_ids) != len(self.entities):
            raise ValueError("duplicate entity mention ids")
        rel_ids = [rel.id for rel in self.relationships]
        if len(set(rel_ids)) != len(rel_ids):
            raise ValueError("duplicate relationship ids")
        for rel in self.relationships:
            if rel.source_entity_id not in mention_ids:
                raise ValueError(f"unknown source_entity_id: {rel.source_entity_id}")
            if rel.target_entity_id not in mention_ids:
                raise ValueError(f"unknown target_entity_id: {rel.target_entity_id}")
            if rel.source_document_id and rel.source_document_id != self.document_id:
                raise ValueError("relationship source_document_id must match document_id")
        return self


class ResolutionProposal(ContractModel):
    """ML proposal only. Backend decides canonicalization.

    Exact phone / exact bank account / agreed strong identifiers may auto-link.
    Name-only fuzzy similarity must never auto-merge.
    """

    canonical_entity_id: str = Field(
        min_length=1,
        description="ML proposal/grouping key only. Backend mints the canonical PostgreSQL UUID.",
    )
    mention_id: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[ResolutionSignal] = Field(min_length=1)


class Pattern(ContractModel):
    """Pattern JSON from Person B. Not a dedicated Pattern table.

    Backend persists validated pattern results as intelligence/lead outputs
    (case insights). severity ≠ status. Status is never coerced.
    """

    id: str = Field(min_length=1)
    type: PatternType
    severity: Severity
    status: RelationshipStatus
    entities: list[str] = Field(
        min_length=1,
        description="ML grouping keys in this JSON; backend maps to canonical UUIDs before graph write",
    )
    explanation: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class Lead(ContractModel):
    """Investigative lead. priority ≠ status. Not a person-level guilt score."""

    id: str = Field(min_length=1)
    type: LeadType
    priority: LeadPriority
    status: LeadStatus = LeadStatus.REVIEW_REQUIRED
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    entity_ids: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    priority_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Lead priority score, never a person criminal-risk score",
    )


Entity = EntityMention
ExtractionEnvelope = ExtractionResult
