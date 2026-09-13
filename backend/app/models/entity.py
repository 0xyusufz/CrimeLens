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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EntityType


class Entity(Base):
    """Canonical entity. PK is a backend UUID, never an ML mention ID."""

    __tablename__ = "entities"
    __table_args__ = (Index("ix_entities_type", "type"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type", native_enum=True),
        nullable=False,
    )
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    mentions: Mapped[list["EntityMention"]] = relationship(back_populates="entity")
    case_links: Mapped[list["EntityCaseLink"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    outgoing_staged_relationships: Mapped[list["RelationshipStaging"]] = relationship(
        back_populates="source_entity",
        foreign_keys="RelationshipStaging.source_entity_id",
    )
    incoming_staged_relationships: Mapped[list["RelationshipStaging"]] = relationship(
        back_populates="target_entity",
        foreign_keys="RelationshipStaging.target_entity_id",
    )


class EntityMention(Base):
    """Document-level mention. mention_id is the ML staging ID."""

    __tablename__ = "entity_mentions"
    __table_args__ = (
        UniqueConstraint("document_id", "mention_id", name="uq_entity_mentions_doc_mention"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_entity_mentions_confidence",
        ),
        Index("ix_entity_mentions_document_id", "document_id"),
        Index("ix_entity_mentions_entity_id", "entity_id"),
        Index("ix_entity_mentions_mention_id", "mention_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    mention_id: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type", native_enum=True, create_constraint=False),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="entity_mentions")
    entity: Mapped[Entity | None] = relationship(back_populates="mentions")


class EntityCaseLink(Base):
    """Canonical entity membership in a case. Entities have no single case_id."""

    __tablename__ = "entity_case_links"
    __table_args__ = (
        UniqueConstraint("entity_id", "case_id", name="uq_entity_case_links_entity_case"),
        Index("ix_entity_case_links_entity_id", "entity_id"),
        Index("ix_entity_case_links_case_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    entity: Mapped[Entity] = relationship(back_populates="case_links")
    case: Mapped["Case"] = relationship(back_populates="entity_links")
