
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


EXPECTED_ALEMBIC_REVISION = "631d80c15b6b"

EXPECTED_TABLES = {
    "audit_events",
    "experiment_runs",
    "inference_events",
    "model_artifacts",
    "telemetry_records",
}


class Base(DeclarativeBase):
    pass


def resolve_database_url() -> str:
    configured = os.getenv("ASTROGUARD_DATABASE_URL", "").strip()

    if configured:
        return configured

    project_root = Path(__file__).resolve().parents[3]
    database_dir = project_root / "artifacts" / "database"
    database_dir.mkdir(parents=True, exist_ok=True)

    database_file = database_dir / "astroguard.db"
    return f"sqlite:///{database_file.as_posix()}"


def build_engine(database_url: str | None = None):
    url = database_url or resolve_database_url()

    options = {"pool_pre_ping": True}

    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}

        if ":memory:" in url:
            options["poolclass"] = StaticPool

    return create_engine(url, **options)


DATABASE_URL = resolve_database_url()
engine = build_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)

_schema_lock = threading.Lock()
_schema_verified = False


def initialize_schema() -> None:
    """
    Verify an Alembic-managed database.

    Deliberately does not call Base.metadata.create_all().
    Schema changes must be applied through Alembic.
    """
    global _schema_verified

    if _schema_verified:
        return

    with _schema_lock:
        if _schema_verified:
            return

        from astroguard_api.database import models  # noqa: F401

        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names())

        missing = EXPECTED_TABLES - actual_tables
        if missing:
            raise RuntimeError(
                f"Database schema is incomplete; missing tables: {sorted(missing)}"
            )

        if "alembic_version" not in actual_tables:
            raise RuntimeError(
                "Alembic version table is missing. Run the approved migration workflow."
            )

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()

        if revision != EXPECTED_ALEMBIC_REVISION:
            raise RuntimeError(
                "Database migration revision mismatch. "
                f"Expected {EXPECTED_ALEMBIC_REVISION}; got {revision!r}."
            )

        _schema_verified = True


def get_db() -> Generator[Session, None, None]:
    initialize_schema()
    db = SessionLocal()

    try:
        yield db
    finally:
        if db.in_transaction():
            db.rollback()
        db.close()
