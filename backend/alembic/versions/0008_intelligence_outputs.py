"""Add intelligence_outputs for validated Pattern/Lead JSON (not a Pattern table).

Revision ID: 0008_intelligence_outputs
Revises: 0007_evidence_blocks
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_intelligence_outputs"
down_revision: Union[str, Sequence[str], None] = "0007_evidence_blocks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE intelligence_kind AS ENUM ('PATTERN', 'LEAD')"
    )
    op.create_table(
        "intelligence_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "kind",
            postgresql.ENUM("PATTERN", "LEAD", name="intelligence_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "case_id",
            "kind",
            "source_id",
            name="uq_intelligence_outputs_case_kind_source",
        ),
    )
    op.create_index("ix_intelligence_outputs_case_id", "intelligence_outputs", ["case_id"])
    op.create_index(
        "ix_intelligence_outputs_source_document_id",
        "intelligence_outputs",
        ["source_document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_intelligence_outputs_source_document_id", table_name="intelligence_outputs")
    op.drop_index("ix_intelligence_outputs_case_id", table_name="intelligence_outputs")
    op.drop_table("intelligence_outputs")
    op.execute("DROP TYPE intelligence_kind")
