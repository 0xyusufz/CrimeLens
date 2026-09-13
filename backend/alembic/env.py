from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import postgres_url
from app.db.base import Base
from app.models import (  # noqa: F401
    Case,
    CaseMember,
    Document,
    Entity,
    EntityCaseLink,
    EntityMention,
    RelationshipStaging,
    StructuredRecord,
    User,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=postgres_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(postgres_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
