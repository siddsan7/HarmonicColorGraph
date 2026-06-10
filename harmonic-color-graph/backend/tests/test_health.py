from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_backend_status():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "harmonic-color-graph-backend",
        "phase": "phase-1",
    }

