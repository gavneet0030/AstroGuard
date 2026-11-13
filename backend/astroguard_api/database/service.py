
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from astroguard_api.database import repository


class DatabaseConflictError(ValueError):
    """A deterministic database uniqueness or state conflict."""


def database_health(db: Session):
    db.execute(text("SELECT 1"))
    return {
        "status": "available",
        "database": "connected",
    }


def _save_atomically(
    db: Session,
    creator,
    values: dict,
    event_type: str,
    resource_type: str,
    details_factory,
):
    """
    Persist the business record and its audit event in one transaction.

    Repository methods only add/flush. This service owns commit/rollback.
    """
    try:
        item = creator(db, values)

        repository.create_audit_event(
            db,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=item.id,
            details=details_factory(item),
        )

        db.flush()
        db.commit()
        return item

    except Exception:
        db.rollback()
        raise


def save_telemetry(db: Session, values: dict):
    return _save_atomically(
        db,
        repository.create_telemetry_record,
        values,
        "telemetry.record.created",
        "telemetry_record",
        lambda item: {
            "channel": item.channel,
            "source": item.source,
        },
    )


def save_experiment(db: Session, values: dict):
    return _save_atomically(
        db,
        repository.create_experiment,
        values,
        "experiment.created",
        "experiment_run",
        lambda item: {
            "channel": item.channel,
            "experiment_name": item.experiment_name,
        },
    )


def save_model_artifact(db: Session, values: dict):
    try:
        return _save_atomically(
            db,
            repository.register_model_artifact,
            values,
            "model_artifact.registered",
            "model_artifact",
            lambda item: {
                "channel": item.channel,
                "model_name": item.model_name,
                "version": item.version,
            },
        )
    except (IntegrityError, ValueError) as exc:
        db.rollback()
        raise DatabaseConflictError(
            "Model version already registered."
        ) from exc


def save_inference_event(db: Session, values: dict):
    return _save_atomically(
        db,
        repository.create_inference_event,
        values,
        "inference.event.created",
        "inference_event",
        lambda item: {
            "channel": item.channel,
            "model_name": item.model_name,
            "prediction": item.prediction,
        },
    )
