
from __future__ import annotations

from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from astroguard_api.database.models import (
    TelemetryRecord,
    ExperimentRun,
    ModelArtifact,
    InferenceEvent,
    AuditEvent,
)


MAX_QUERY_LIMIT = 500
DEFAULT_QUERY_LIMIT = 100


def _limit(value: int | None) -> int:
    if value is None:
        return DEFAULT_QUERY_LIMIT
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Query limit must be an integer.")
    if value < 1 or value > MAX_QUERY_LIMIT:
        raise ValueError(f"Query limit must be between 1 and {MAX_QUERY_LIMIT}.")
    return value


def _add_and_flush(db: Session, item):
    db.add(item)
    db.flush()
    return item


def create_telemetry_record(db: Session, values: dict):
    return _add_and_flush(db, TelemetryRecord(**values))


def list_telemetry_records(db: Session, channel=None, limit=100):
    statement = select(TelemetryRecord).order_by(
        desc(TelemetryRecord.event_timestamp),
        desc(TelemetryRecord.id),
    )
    if channel:
        statement = statement.where(TelemetryRecord.channel == channel)
    return list(db.scalars(statement.limit(_limit(limit))).all())


def create_experiment(db: Session, values: dict):
    return _add_and_flush(db, ExperimentRun(**values))


def list_experiments(db: Session, channel=None, limit=100):
    statement = select(ExperimentRun).order_by(
        desc(ExperimentRun.created_at),
        desc(ExperimentRun.id),
    )
    if channel:
        statement = statement.where(ExperimentRun.channel == channel)
    return list(db.scalars(statement.limit(_limit(limit))).all())


def register_model_artifact(db: Session, values: dict):
    existing = db.scalar(
        select(ModelArtifact).where(
            ModelArtifact.channel == values["channel"],
            ModelArtifact.model_name == values["model_name"],
            ModelArtifact.version == values["version"],
        )
    )

    if existing:
        raise ValueError("Model version already registered.")

    item = ModelArtifact(**values)

    try:
        return _add_and_flush(db, item)
    except IntegrityError as exc:
        # The unique constraint is authoritative under concurrent requests.
        raise ValueError("Model version already registered.") from exc


def list_model_artifacts(db: Session, channel=None, limit=100):
    statement = select(ModelArtifact).order_by(
        desc(ModelArtifact.created_at),
        desc(ModelArtifact.id),
    )
    if channel:
        statement = statement.where(ModelArtifact.channel == channel)
    return list(db.scalars(statement.limit(_limit(limit))).all())


def create_inference_event(db: Session, values: dict):
    return _add_and_flush(db, InferenceEvent(**values))


def list_inference_events(db: Session, channel=None, limit=100):
    statement = select(InferenceEvent).order_by(
        desc(InferenceEvent.created_at),
        desc(InferenceEvent.id),
    )
    if channel:
        statement = statement.where(InferenceEvent.channel == channel)
    return list(db.scalars(statement.limit(_limit(limit))).all())


def create_audit_event(
    db: Session,
    event_type: str,
    resource_type: str,
    resource_id=None,
    details=None,
    actor="system",
):
    item = AuditEvent(
        event_type=event_type,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    return _add_and_flush(db, item)
