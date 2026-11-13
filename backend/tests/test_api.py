from fastapi.testclient import TestClient

from astroguard_api.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "AstroGuard"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_system_information():
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["backend_language"] == "Python"
    assert data["native_language"] == "C++20"
    assert data["safety_classification"] == "research_prototype_only"