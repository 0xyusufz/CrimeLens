"""Add entities, entity_mentions, and entity_case_links.

Revision ID: 0003_entities
Revises: 0002_documents_records
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_entities"
down_revision: Union[str, Sequence[str], None] = "0002_documents_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ENTITY_TYPE = postgresql.ENUM(
    "PERSON",
    "PHONE",
    "BANK_ACCOUNT",
    "VEHICLE",
    "ORGANIZATION",
    "LOCATION",
    "EVENT",
    name="entity_type",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE entity_type AS ENUM "
        "('PERSON', 'PHONE', 'BANK_ACCOUNT', 'VEHICLE', 'ORGANIZATION', 'LOCATION', 'EVENT')"
    )

    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("type", ENTITY_TYPE, nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_entities_type", "entities", ["type"])

    op.create_table(
        "entity_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mention_id", sa.String(64), nullable=False),
        sa.Column("entity_type", ENTITY_TYPE, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_snippet", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("document_id", "mention_id", name="uq_entity_mentions_doc_mention"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_entity_mentions_confidence",
        ),
    )
    op.create_index("ix_entity_mentions_document_id", "entity_mentions", ["document_id"])
    op.create_index("ix_entity_mentions_entity_id", "entity_mentions", ["entity_id"])
    op.create_index("ix_entity_mentions_mention_id", "entity_mentions", ["mention_id"])

    op.create_table(
        "entity_case_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("entity_id", "case_id", name="uq_entity_case_links_entity_case"),
    )
    op.create_index("ix_entity_case_links_entity_id", "entity_case_links", ["entity_id"])
    op.create_index("ix_entity_case_links_case_id", "entity_case_links", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_entity_case_links_case_id", table_name="entity_case_links")
    op.drop_index("ix_entity_case_links_entity_id", table_name="entity_case_links")
    op.drop_table("entity_case_links")
    op.drop_index("ix_entity_mentions_mention_id", table_name="entity_mentions")
    op.drop_index("ix_entity_mentions_entity_id", table_name="entity_mentions")
    op.drop_index("ix_entity_mentions_document_id", table_name="entity_mentions")
    op.drop_table("entity_mentions")
    op.drop_index("ix_entities_type", table_name="entities")
    op.drop_table("entities")
    op.execute("DROP TYPE entity_type")
