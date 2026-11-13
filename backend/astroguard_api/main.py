"""
AstroGuard FastAPI application.

Research prototype only.
Not an operational spacecraft flight-safety system.

Security:
- Configuration is loaded through the centralized settings module.
- Startup logs contain safe metadata only.
- No environment values or credential-bearing URLs are logged.
- No request bodies, authorization headers, or query strings are logged.
- Existing public API response contracts are preserved.
"""

from __future__ import annotations

import logging

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from astroguard_api.settings import settings


logger = logging.getLogger("astroguard.application")


def _log_startup_configuration() -> None:
    """
    Emit safe configuration metadata only.

    Never log os.environ, settings.secure, database URLs,
    tokens, API keys, or complete settings representations.
    """
    logger.info(
        "AstroGuard application startup configuration: %s",
        settings.safe_summary(),
    )

    for warning in settings.configuration_warnings:
        logger.warning(
            "AstroGuard configuration warning: %s",
            warning,
        )


@asynccontextmanager
async def lifespan(
    application: FastAPI,
) -> AsyncIterator[None]:
    """
    Application lifecycle.

    Configuration is already validated during settings import.
    The startup phase emits only non-secret metadata.
    """
    _log_startup_configuration()

    logger.info(
        "AstroGuard API startup completed."
    )

    yield

    logger.info(
        "AstroGuard API shutdown completed."
    )


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "AstroGuard research prototype. "
        "Not an operational spacecraft flight-safety system."
    ),
    debug=settings.debug,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict:
    """
    Root metadata endpoint.

    Preserve the original response shape.
    """
    return {
        "name": "AstroGuard",
        "service": "astroguard-api",
        "status": "online",
        "environment": settings.app_env,
    }


@app.get("/health", tags=["health"])
def health() -> dict:
    """
    Lightweight liveness endpoint.

    Does not disclose internal secrets or infrastructure credentials.
    """
    return {
        "status": "ok",
        "service": "astroguard-api",
    }


@app.get("/ready", tags=["health"])
def ready() -> dict:
    """
    Database-backed readiness endpoint.

    A successful SELECT 1 confirms database connectivity.
    initialize_schema() enforces the application's existing
    migration/schema readiness guard.
    """
    database_status = "unavailable"

    try:
        from sqlalchemy import text
        from astroguard_api.database.base import engine, initialize_schema

        initialize_schema()

        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            value = result.scalar_one()

        if value == 1:
            database_status = "available"

    except Exception:
        database_status = "unavailable"

    return {
        "status": "ready" if database_status == "available" else "not_ready",
        "database": database_status,
        "native_engine": "phase_1_available",
    }


@app.get(
    f"{settings.api_v1_prefix}/system/info",
    tags=["system"],
)
def system_info() -> dict:
    """
    Public system metadata.

    Deliberately excludes:
    - API keys
    - database URLs
    - Redis URLs
    - JWT secrets
    - cloud credentials
    - private service credentials
    """
    return {
        "name": "AstroGuard",
        "version": "0.1.0",
        "backend_language": "Python",
        "native_language": "C++20",
        "mode": "historical_telemetry_replay",
        "safety_classification": "research_prototype_only",
    }

# AstroGuard Phase 3 ML inference integration
from pathlib import Path as _MLPath
from astroguard_api.ml_engine.inference.router import create_ml_router as _create_ml_router

app.include_router(
    _create_ml_router(_MLPath(__file__).resolve().parents[2])
)

# astroguard_phase4_database_router
from astroguard_api.database.router import router as astroguard_database_router
app.include_router(astroguard_database_router, prefix="/api/v1")
