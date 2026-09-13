import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RecordType


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_case_id", "case_id"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
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
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    case: Mapped["Case"] = relationship(back_populates="documents")
    uploader: Mapped["User"] = relationship(back_populates="uploaded_documents")
    structured_records: Mapped[list["StructuredRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class StructuredRecord(Base):
    __tablename__ = "structured_records"
    __table_args__ = (
        Index("ix_structured_records_case_id", "case_id"),
        Index("ix_structured_records_document_id", "document_id"),
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
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    record_type: Mapped[RecordType] = mapped_column(
        Enum(RecordType, name="record_type", native_enum=True),
        nullable=False,
    )
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    case: Mapped["Case"] = relationship(back_populates="structured_records")
    document: Mapped[Document] = relationship(back_populates="structured_records")
