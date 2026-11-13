
from datetime import datetime, timezone

import pytest

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astroguard_api.database.base import Base
from astroguard_api.database import repository, service
from astroguard_api.database.models import (
    AuditEvent,
    TelemetryRecord,
    ExperimentRun,
    ModelArtifact,
    InferenceEvent,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    with factory() as session:
        yield session

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def telemetry_values():
    return {
        "channel": "a-1",
        "event_timestamp": datetime.now(timezone.utc),
        "source": "phase4-test",
        "payload": {"temperature": 22.5},
    }


def experiment_values():
    return {
        "channel": "p-1",
        "experiment_name": "atomicity-test",
        "configuration": {"seed": 42},
        "notes": None,
    }


def model_values(version="atomic-v1"):
    return {
        "channel": "a-1",
        "model_name": "isolation_forest",
        "version": version,
        "artifact_path": "artifacts/models/test/model.joblib",
        "checksum_sha256": "a" * 64,
        "metadata_json": {},
    }


def inference_values():
    return {
        "channel": "p-1",
        "model_name": "isolation_forest",
        "model_version": "v1",
        "prediction": 1,
        "anomaly_score": 0.83,
        "input_fingerprint": "test-fingerprint",
    }


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_health_query(db_session):
    assert service.database_health(db_session)["status"] == "available"


def test_telemetry_and_audit_commit_together(db_session):
    item = service.save_telemetry(db_session, telemetry_values())

    assert item.id
    assert count(db_session, TelemetryRecord) == 1
    assert count(db_session, AuditEvent) == 1


def test_experiment_and_audit_commit_together(db_session):
    item = service.save_experiment(db_session, experiment_values())

    assert item.status == "created"
    assert count(db_session, ExperimentRun) == 1
    assert count(db_session, AuditEvent) == 1


def test_model_registration_and_audit_commit_together(db_session):
    item = service.save_model_artifact(db_session, model_values())

    assert item.is_active
    assert count(db_session, ModelArtifact) == 1
    assert count(db_session, AuditEvent) == 1


def test_inference_and_audit_commit_together(db_session):
    item = service.save_inference_event(db_session, inference_values())

    assert item.prediction == 1
    assert count(db_session, InferenceEvent) == 1
    assert count(db_session, AuditEvent) == 1


def test_audit_failure_rolls_back_business_record(db_session, monkeypatch):
    def fail_audit(*args, **kwargs):
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(repository, "create_audit_event", fail_audit)

    with pytest.raises(RuntimeError, match="injected audit failure"):
        service.save_experiment(db_session, experiment_values())

    assert count(db_session, ExperimentRun) == 0
    assert count(db_session, AuditEvent) == 0


def test_duplicate_model_version_conflict(db_session):
    service.save_model_artifact(db_session, model_values("duplicate-v1"))

    with pytest.raises(service.DatabaseConflictError):
        service.save_model_artifact(db_session, model_values("duplicate-v1"))

    assert count(db_session, ModelArtifact) == 1
    assert count(db_session, AuditEvent) == 1


def test_repository_does_not_commit_telemetry(db_session):
    repository.create_telemetry_record(db_session, telemetry_values())

    # Repository must leave the transaction under service ownership.
    assert db_session.in_transaction()

    db_session.rollback()

    assert count(db_session, TelemetryRecord) == 0


def test_query_limit_validation(db_session):
    with pytest.raises(ValueError):
        repository.list_telemetry_records(db_session, limit=0)

    with pytest.raises(ValueError):
        repository.list_telemetry_records(db_session, limit=501)


def test_channel_filtering_and_deterministic_lists(db_session):
    for channel in ("a-1", "p-1"):
        values = telemetry_values()
        values["channel"] = channel
        repository.create_telemetry_record(db_session, values)

    assert len(repository.list_telemetry_records(db_session, "a-1")) == 1
    assert len(repository.list_telemetry_records(db_session, "p-1")) == 1
    db_session.rollback()


def test_repository_flushes_without_committing(db_session):
    item = repository.create_experiment(db_session, experiment_values())

    assert item.id
    assert db_session.in_transaction()
    db_session.rollback()
    assert count(db_session, ExperimentRun) == 0


def test_schema_contracts_remain_enforced():
    from astroguard_api.database.schemas import (
        TelemetryRecordCreate,
        ModelArtifactCreate,
    )

    with pytest.raises(Exception):
        TelemetryRecordCreate(
            channel="a-1",
            event_timestamp="2026-11-12T10:00:00",
            source="test",
            payload={"value": 1},
        )

    with pytest.raises(Exception):
        ModelArtifactCreate(
            channel="a-1",
            model_name="isolation_forest",
            version="v1",
            artifact_path="model.joblib",
            checksum_sha256="invalid",
            metadata_json={},
        )
