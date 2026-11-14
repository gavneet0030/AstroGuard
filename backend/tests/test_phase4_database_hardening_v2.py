from __future__ import annotations

import pytest
from sqlalchemy import text

from astroguard_api.database.base import build_engine, normalize_database_url, resolve_database_url
from astroguard_api.secure_config import build_settings


@pytest.mark.parametrize(("source", "expected"), [
    ("postgres://u:p@localhost/db", "postgresql+psycopg://u:p@localhost/db"),
    ("postgresql://u:p@localhost/db", "postgresql+psycopg://u:p@localhost/db"),
    ("postgresql+psycopg2://u:p@localhost/db", "postgresql+psycopg://u:p@localhost/db"),
    ("postgresql+psycopg://u:p@localhost/db", "postgresql+psycopg://u:p@localhost/db"),
    ("sqlite:///./local.db", "sqlite:///./local.db"),
])
def test_url_alias_normalization(source, expected):
    assert normalize_database_url(source) == expected


@pytest.mark.parametrize("bad", ["", " ", None, 42])
def test_invalid_database_url_rejected(bad):
    with pytest.raises(ValueError):
        normalize_database_url(bad)


def test_database_url_precedence_and_legacy_fallback():
    assert resolve_database_url({
        "DATABASE_URL": "postgresql://main:secret@localhost/app",
        "ASTROGUARD_DATABASE_URL": "sqlite:///legacy.db",
    }) == "postgresql+psycopg://main:secret@localhost/app"
    assert resolve_database_url({
        "ASTROGUARD_DATABASE_URL": "postgres://old:secret@localhost/old"
    }) == "postgresql+psycopg://old:secret@localhost/old"


def test_default_database_url_is_sqlite():
    assert resolve_database_url({}).startswith("sqlite:///")


def test_sqlite_engine_smoke():
    engine = build_engine("sqlite://")
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()


def test_secure_settings_use_canonical_precedence():
    settings = build_settings(environ={
        "DATABASE_URL": "postgresql://main:secret@localhost/app",
        "ASTROGUARD_DATABASE_URL": "sqlite:///legacy.db",
    })
    assert settings.database_url.startswith("postgresql://main:")
    assert settings.safe_summary()["database_configured"] is True


def test_secure_settings_legacy_fallback():
    settings = build_settings(environ={"ASTROGUARD_DATABASE_URL": "sqlite:///legacy.db"})
    assert settings.database_url == "sqlite:///legacy.db"