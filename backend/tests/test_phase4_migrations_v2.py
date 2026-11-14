from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

TABLES = {
    "audit_events", "experiment_runs", "inference_events",
    "model_artifacts", "telemetry_records",
}


def _config(url: str) -> Config:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(
        root / "backend" / "astroguard_api" / "database" / "migrations"
    ))
    cfg.set_main_option("prepend_sys_path", str(root / "backend"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def test_migration_upgrade_downgrade_upgrade(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ASTROGUARD_DATABASE_URL", raising=False)
    dbfile = tmp_path / "isolated_phase4.db"
    url = f"sqlite:///{dbfile.as_posix()}"
    cfg = _config(url)

    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        assert TABLES.issubset(set(inspect(engine).get_table_names()))
        with engine.connect() as conn:
            revision = conn.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one()
        assert revision == "631d80c15b6b"
    finally:
        engine.dispose()

    command.downgrade(cfg, "base")
    engine = create_engine(url)
    try:
        names = set(inspect(engine).get_table_names())
        assert not (TABLES & names)
        assert "alembic_version" in names
        with engine.connect() as conn:
            remaining_revision = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
        assert remaining_revision is None
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        names = set(inspect(engine).get_table_names())
        assert TABLES.issubset(names)
        assert "alembic_version" in names
    finally:
        engine.dispose()