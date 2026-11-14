from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from astroguard_api.database.base import Base, normalize_database_url
from astroguard_api.database import models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def configured_database_url() -> str | None:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        value = os.getenv("ASTROGUARD_DATABASE_URL", "").strip()
    return normalize_database_url(value) if value else None


database_url = configured_database_url()
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()