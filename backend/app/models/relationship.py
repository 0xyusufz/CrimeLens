import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RelationshipStatus, RelationshipType


class RelationshipStaging(Base):
    """Extracted relationship occurrence. Status is stored as-is; never coerced.

    Financial/CDR extras live on structured_records, not here.
    """

    __tablename__ = "relationships_staging"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_relationships_staging_confidence",
        ),
        CheckConstraint(
            "source_document_id IS NOT NULL OR source_record_id IS NOT NULL",
            name="ck_relationships_staging_provenance",
        ),
        Index(
            "uq_rel_staging_doc_occurrence",
            "source_document_id",
            "source_occurrence_id",
            unique=True,
            postgresql_where=text("source_document_id IS NOT NULL"),
        ),
        Index(
            "uq_rel_staging_record_occurrence",
            "source_record_id",
            "source_occurrence_id",
            unique=True,
            postgresql_where=text("source_record_id IS NOT NULL"),
        ),
        Index("ix_relationships_staging_case_id", "case_id"),
        Index("ix_relationships_staging_source_entity_id", "source_entity_id"),
        Index("ix_relationships_staging_target_entity_id", "target_entity_id"),
        Index("ix_relationships_staging_relationship_type", "relationship_type"),
        Index("ix_relationships_staging_source_document_id", "source_document_id"),
        Index("ix_relationships_staging_source_record_id", "source_record_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_occurrence_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="ML relationship ID for this extracted occurrence, e.g. rel_001",
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        Enum(RelationshipType, name="relationship_type", native_enum=True),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[RelationshipStatus] = mapped_column(
        Enum(RelationshipStatus, name="relationship_status", native_enum=True),
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("structured_records.id", ondelete="RESTRICT"),
        nullable=True,
    )
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )

    case: Mapped["Case"] = relationship(back_populates="staged_relationships")
    source_entity: Mapped["Entity"] = relationship(
        foreign_keys=[source_entity_id],
        back_populates="outgoing_staged_relationships",
    )
    target_entity: Mapped["Entity"] = relationship(
        foreign_keys=[target_entity_id],
        back_populates="incoming_staged_relationships",
    )
    source_document: Mapped["Document | None"] = relationship(
        back_populates="staged_relationships",
    )
    source_record: Mapped["StructuredRecord | None"] = relationship(
        back_populates="staged_relationships",
    )
