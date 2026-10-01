"""Maintenance rejects work before handlers can write, while probes remain available."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.maintenance import MaintenanceMiddleware


def test_maintenance_blocks_reads_and_writes_before_handler():
    app = FastAPI()
    calls = []

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    def handler(path: str):
        calls.append(path)
        return {"status": "ok"}

    app.add_middleware(MaintenanceMiddleware, enabled=True)
    with TestClient(app) as client:
        for method, path in [
            ("GET", "/v2/neighborhood"),
            ("POST", "/v2/jobs"),
            ("POST", "/v2/ai/query"),
        ]:
            response = client.request(method, path)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "maintenance"
            assert response.headers["retry-after"] == "60"
            assert response.headers["cache-control"] == "no-store"
        assert not calls
        for path in ["/health", "/health/db", "/health/redis"]:
            assert client.get(path).status_code == 200
        assert len(calls) == 3


def test_maintenance_disabled_preserves_routes():
    app = FastAPI()

    @app.post("/v2/jobs")
    def handler():
        return {"queued": True}

    app.add_middleware(MaintenanceMiddleware)
    with TestClient(app) as client:
        assert client.post("/v2/jobs").json() == {"queued": True}
