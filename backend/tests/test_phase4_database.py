from datetime import datetime, timezone

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astroguard_api.database.base import Base

from astroguard_api.database import repository, service

from astroguard_api.database.models import AuditEvent


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


def test_database_health(db_session):

    result = service.database_health(db_session)

    assert result["status"] == "available"


def test_telemetry_persistence(db_session):

    item = service.save_telemetry(
        db_session,
        {
            "channel": "a-1",
            "event_timestamp": datetime.now(timezone.utc),
            "source": "pytest",
            "payload": {
                "temperature": 22.5,
                "voltage": 5.2,
            },
        },
    )

    assert item.id
    assert item.channel == "a-1"

    records = repository.list_telemetry_records(
        db_session,
        "a-1",
    )

    assert len(records) == 1


def test_experiment_persistence(db_session):

    item = service.save_experiment(
        db_session,
        {
            "channel": "p-1",
            "experiment_name": "phase4-test",
            "configuration": {
                "seed": 42,
            },
            "notes": "Test experiment",
        },
    )

    assert item.status == "created"
    assert item.configuration["seed"] == 42


def test_model_registry(db_session):

    item = service.save_model_artifact(
        db_session,
        {
            "channel": "a-1",
            "model_name": "isolation_forest",
            "version": "phase4-test-v1",
            "artifact_path": "artifacts/models/test/model.joblib",
            "checksum_sha256": "a" * 64,
            "metadata_json": {
                "feature_count": 69,
            },
        },
    )

    assert item.is_active
    assert len(item.checksum_sha256) == 64


def test_duplicate_model_version_rejected(db_session):

    values = {
        "channel": "a-1",
        "model_name": "isolation_forest",
        "version": "duplicate-test",
        "artifact_path": "test.joblib",
        "checksum_sha256": "a" * 64,
        "metadata_json": {},
    }

    repository.register_model_artifact(db_session, values)

    with pytest.raises(ValueError):
        repository.register_model_artifact(db_session, values)


def test_inference_persistence(db_session):

    item = service.save_inference_event(
        db_session,
        {
            "channel": "p-1",
            "model_name": "isolation_forest",
            "model_version": "v1",
            "prediction": 1,
            "anomaly_score": 0.83,
            "input_fingerprint": "test-fingerprint",
        },
    )

    assert item.prediction == 1
    assert item.anomaly_score == pytest.approx(0.83)


def test_audit_event_creation(db_session):

    service.save_experiment(
        db_session,
        {
            "channel": "a-1",
            "experiment_name": "audit-test",
            "configuration": {},
            "notes": None,
        },
    )

    events = list(
        db_session.scalars(
            select(AuditEvent)
        ).all()
    )

    assert len(events) == 1
    assert events[0].event_type == "experiment.created"


def test_channel_filtering(db_session):

    for channel in ["a-1", "p-1"]:

        repository.create_telemetry_record(
            db_session,
            {
                "channel": channel,
                "event_timestamp": datetime.now(timezone.utc),
                "source": "test",
                "payload": {"value": 1},
            },
        )

    a = repository.list_telemetry_records(db_session, "a-1")
    p = repository.list_telemetry_records(db_session, "p-1")

    assert len(a) == 1
    assert len(p) == 1


def test_telemetry_timezone_contract():

    from astroguard_api.database.schemas import TelemetryRecordCreate

    with pytest.raises(Exception):

        TelemetryRecordCreate(
            channel="a-1",
            event_timestamp="2026-11-12T10:00:00",
            source="test",
            payload={"value": 1},
        )


def test_model_checksum_contract():

    from astroguard_api.database.schemas import ModelArtifactCreate

    with pytest.raises(Exception):

        ModelArtifactCreate(
            channel="a-1",
            model_name="isolation_forest",
            version="v1",
            artifact_path="model.joblib",
            checksum_sha256="invalid",
            metadata_json={},
        )