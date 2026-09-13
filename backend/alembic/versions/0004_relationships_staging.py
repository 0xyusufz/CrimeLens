"""Add relationships_staging.

Revision ID: 0004_relationships_staging
Revises: 0003_entities
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_relationships_staging"
down_revision: Union[str, Sequence[str], None] = "0003_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE relationship_type AS ENUM ("
        "'CALLED', 'SENT_MONEY_TO', 'OWNS_VEHICLE', 'USED_VEHICLE', "
        "'WORKS_FOR', 'LOCATED_AT', 'ASSOCIATED_WITH', 'PART_OF_EVENT')"
    )
    op.execute(
        "CREATE TYPE relationship_status AS ENUM ('CONFIRMED', 'INFERRED', 'PREDICTED')"
    )

    op.create_table(
        "relationships_staging",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_occurrence_id", sa.String(64), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "relationship_type",
            postgresql.ENUM(
                "CALLED",
                "SENT_MONEY_TO",
                "OWNS_VEHICLE",
                "USED_VEHICLE",
                "WORKS_FOR",
                "LOCATED_AT",
                "ASSOCIATED_WITH",
                "PART_OF_EVENT",
                name="relationship_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "CONFIRMED",
                "INFERRED",
                "PREDICTED",
                name="relationship_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_snippet", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["structured_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_relationships_staging_confidence",
        ),
        sa.CheckConstraint(
            "source_document_id IS NOT NULL OR source_record_id IS NOT NULL",
            name="ck_relationships_staging_provenance",
        ),
    )
    op.create_index(
        "uq_rel_staging_doc_occurrence",
        "relationships_staging",
        ["source_document_id", "source_occurrence_id"],
        unique=True,
        postgresql_where=sa.text("source_document_id IS NOT NULL"),
    )
    op.create_index(
        "uq_rel_staging_record_occurrence",
        "relationships_staging",
        ["source_record_id", "source_occurrence_id"],
        unique=True,
        postgresql_where=sa.text("source_record_id IS NOT NULL"),
    )
    op.create_index("ix_relationships_staging_case_id", "relationships_staging", ["case_id"])
    op.create_index(
        "ix_relationships_staging_source_entity_id",
        "relationships_staging",
        ["source_entity_id"],
    )
    op.create_index(
        "ix_relationships_staging_target_entity_id",
        "relationships_staging",
        ["target_entity_id"],
    )
    op.create_index(
        "ix_relationships_staging_relationship_type",
        "relationships_staging",
        ["relationship_type"],
    )
    op.create_index(
        "ix_relationships_staging_source_document_id",
        "relationships_staging",
        ["source_document_id"],
    )
    op.create_index(
        "ix_relationships_staging_source_record_id",
        "relationships_staging",
        ["source_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_relationships_staging_source_record_id", table_name="relationships_staging")
    op.drop_index(
        "ix_relationships_staging_source_document_id",
        table_name="relationships_staging",
    )
    op.drop_index(
        "ix_relationships_staging_relationship_type",
        table_name="relationships_staging",
    )
    op.drop_index("ix_relationships_staging_target_entity_id", table_name="relationships_staging")
    op.drop_index("ix_relationships_staging_source_entity_id", table_name="relationships_staging")
    op.drop_index("ix_relationships_staging_case_id", table_name="relationships_staging")
    op.drop_index("uq_rel_staging_record_occurrence", table_name="relationships_staging")
    op.drop_index("uq_rel_staging_doc_occurrence", table_name="relationships_staging")
    op.drop_table("relationships_staging")
    op.execute("DROP TYPE relationship_status")
    op.execute("DROP TYPE relationship_type")
