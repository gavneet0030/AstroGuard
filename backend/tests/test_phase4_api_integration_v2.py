from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astroguard_api.database.base import Base, get_db
from astroguard_api.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_telemetry_create_and_list(client):
    response = client.post("/api/v1/telemetry/records", json={
        "channel": "a-1",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "phase4-api",
        "payload": {"temperature": 21.5},
    })
    assert response.status_code == 201, response.text
    listed = client.get("/api/v1/telemetry/records?channel=a-1")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_experiment_create_and_list(client):
    response = client.post("/api/v1/experiments", json={
        "channel": "p-1",
        "experiment_name": "phase4-api-integration",
        "configuration": {"seed": 42},
        "notes": "test",
    })
    assert response.status_code == 201, response.text
    assert len(client.get("/api/v1/experiments?channel=p-1").json()) == 1


def test_model_register_and_duplicate_conflict(client):
    payload = {
        "channel": "a-1", "model_name": "isolation_forest", "version": "api-v1",
        "artifact_path": "artifacts/models/test/model.joblib",
        "checksum_sha256": "a" * 64, "metadata_json": {},
    }
    assert client.post("/api/v1/models/register", json=payload).status_code == 201
    assert client.post("/api/v1/models/register", json=payload).status_code == 409
    assert len(client.get("/api/v1/models/registry").json()) == 1


def test_inference_create_and_list(client):
    response = client.post("/api/v1/inference/events", json={
        "channel": "p-1", "model_name": "isolation_forest", "model_version": "v1",
        "prediction": 1, "anomaly_score": 0.83, "input_fingerprint": "api-test",
    })
    assert response.status_code == 201, response.text
    assert len(client.get("/api/v1/inference/events?channel=p-1").json()) == 1


def test_database_health(client):
    response = client.get("/api/v1/system/database/health")
    assert response.status_code == 200
    assert response.json()["status"] == "available"


def test_invalid_timestamp_and_channel_return_422(client):
    no_timezone = client.post("/api/v1/telemetry/records", json={
        "channel": "a-1", "event_timestamp": "2026-11-14T10:00:00",
        "source": "test", "payload": {"x": 1},
    })
    assert no_timezone.status_code == 422
    bad_channel = client.post("/api/v1/telemetry/records", json={
        "channel": "unknown",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test", "payload": {"x": 1},
    })
    assert bad_channel.status_code == 422