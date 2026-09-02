import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import Base
from backend.config import get_settings

# Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_db_url() -> str:
    """Derive synchronous database URL for Alembic migrations."""
    db_url = get_settings().database_url
    if "sqlite+aiosqlite" in db_url:
        return db_url.replace("sqlite+aiosqlite", "sqlite")
    if "postgresql+asyncpg" in db_url:
        return db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_sync_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    sync_url = get_sync_db_url()
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True if "sqlite" in sync_url else False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
