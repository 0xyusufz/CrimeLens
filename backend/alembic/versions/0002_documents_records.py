"""Add documents and structured_records.

Revision ID: 0002_documents_records
Revises: 0001_users_cases
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_documents_records"
down_revision: Union[str, Sequence[str], None] = "0001_users_cases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE record_type AS ENUM ('CDR', 'TRANSACTION')")

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])

    op.create_table(
        "structured_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "record_type",
            postgresql.ENUM("CDR", "TRANSACTION", name="record_type", create_type=False),
            nullable=False,
        ),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_structured_records_case_id", "structured_records", ["case_id"])
    op.create_index(
        "ix_structured_records_document_id",
        "structured_records",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_structured_records_document_id", table_name="structured_records")
    op.drop_index("ix_structured_records_case_id", table_name="structured_records")
    op.drop_table("structured_records")
    op.drop_index("ix_documents_uploaded_by", table_name="documents")
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_table("documents")
    op.execute("DROP TYPE record_type")
