"""Add append-only evidence_blocks ledger.

Revision ID: 0007_evidence_blocks
Revises: 0006_audit_logs
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_evidence_blocks"
down_revision: Union[str, Sequence[str], None] = "0006_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_hash", sa.String(64), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("block_hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("block_index", name="uq_evidence_blocks_block_index"),
        sa.UniqueConstraint("evidence_id", name="uq_evidence_blocks_evidence_id"),
    )
    op.create_index("ix_evidence_blocks_case_id", "evidence_blocks", ["case_id"])
    op.create_index("ix_evidence_blocks_timestamp", "evidence_blocks", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_evidence_blocks_timestamp", table_name="evidence_blocks")
    op.drop_index("ix_evidence_blocks_case_id", table_name="evidence_blocks")
    op.drop_table("evidence_blocks")
