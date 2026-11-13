# AstroGuard Phase 4.0 — Database Foundation

## Architecture

SQLAlchemy 2.x ORM.
SQLite local database.
PostgreSQL-compatible URL configuration.
Alembic migration configuration.
FastAPI database router.
Repository and service layers.

## Persistent entities

1. TelemetryRecord
2. ExperimentRun
3. ModelArtifact
4. InferenceEvent
5. AuditEvent

## Local database

artifacts/database/astroguard.db

Environment override:

ASTROGUARD_DATABASE_URL

## API routes

GET  /api/v1/system/database/health

POST /api/v1/telemetry/records
GET  /api/v1/telemetry/records

POST /api/v1/experiments
GET  /api/v1/experiments

POST /api/v1/models/register
GET  /api/v1/models/registry

POST /api/v1/inference/events
GET  /api/v1/inference/events

## Migration commands

python -m alembic revision --autogenerate -m "description"

python -m alembic upgrade head

python -m alembic downgrade -1

## Security limitations

Authentication and authorization are not implemented in this phase.
Production secrets management is not implemented.
Database backup/restore automation is not implemented.
SQLite is a local development database.

## Phase 3 carry-forward

A-1 rolling detector has zero training score variation.
P-1 rolling detector recall remains low.
Supervised training remains skipped because genuine training labels are unavailable.

These are known limitations, not successful detection results.