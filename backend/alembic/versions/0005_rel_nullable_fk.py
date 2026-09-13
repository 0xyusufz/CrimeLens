"""Allow unresolved relationship staging endpoints.

Revision ID: 0005_rel_nullable_fk
Revises: 0004_relationships_staging
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_rel_nullable_fk"
down_revision: Union[str, Sequence[str], None] = "0004_relationships_staging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "relationships_staging",
        "source_entity_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "relationships_staging",
        "target_entity_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "relationships_staging",
        "target_entity_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "relationships_staging",
        "source_entity_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
