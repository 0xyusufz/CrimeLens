import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import IntelligenceKind


class IntelligenceOutput(Base):
    """Validated Person B Pattern/Lead JSON stored as case intelligence.

    Not a Pattern table. Payload is the shared contract dump; case_id is backend-derived.
    """

    __tablename__ = "intelligence_outputs"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "kind",
            "source_id",
            name="uq_intelligence_outputs_case_kind_source",
        ),
        Index("ix_intelligence_outputs_case_id", "case_id"),
        Index("ix_intelligence_outputs_source_document_id", "source_document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[IntelligenceKind] = mapped_column(
        Enum(IntelligenceKind, name="intelligence_kind", native_enum=True),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
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

    case: Mapped["Case"] = relationship()
    source_document: Mapped["Document | None"] = relationship()
