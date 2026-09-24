"""F27 API → durable ledger → queue → worker → completed job."""

import os
from collections import deque

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import AppSettings, get_settings
from app.db.session import create_session_factory, get_session
from app.jobs.worker_runtime import JobWorker
from app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


class MemoryQueue:
    def __init__(self):
        self.ids: deque[str] = deque()

    def enqueue(self, job_id: str, *, force: bool = False) -> None:
        self.ids.append(job_id)

    def receive(self, timeout: int = 5) -> str | None:
        return self.ids.popleft() if self.ids else None

    def close(self) -> None:
        pass


def test_job_survives_api_session_and_worker_completes(monkeypatch):
    factory = create_session_factory(TEST_DATABASE_URL)
    settings = AppSettings(
        DATABASE_URL=TEST_DATABASE_URL,
        REDIS_URL="redis://unused:6379",
        HCG_JOBS_ADMIN_TOKEN="test-job-token",
    )
    queue = MemoryQueue()

    def session_dependency():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("app.api.jobs_v2.JobQueue.from_url", lambda _: queue)

    def fake_handler(kind, payload, worker_settings, progress):
        assert kind == "evaluation_run"
        assert payload == {"suite": "keys", "song_limit": 3}
        assert worker_settings is settings
        progress(0.5, "evaluating", 1, 3)
        return {"report": "passed"}

    monkeypatch.setattr("app.jobs.worker_runtime.run_job", fake_handler)
    job_id = None
    try:
        with TestClient(app) as client:
            headers = {"X-HCG-Jobs-Token": "test-job-token"}
            assert (
                client.post(
                    "/v2/jobs",
                    json={"type": "unknown", "payload": {}},
                    headers=headers,
                ).status_code
                == 422
            )
            submitted = client.post(
                "/v2/jobs",
                json={"type": "evaluation_run", "payload": {"suite": "keys", "song_limit": 3}},
                headers=headers,
            )
            assert submitted.status_code == 202
            job_id = submitted.json()["data"]["job_id"]
            assert (
                client.get(f"/v2/jobs/{job_id}", headers=headers).json()["data"]["status"]
                == "queued"
            )

            assert JobWorker(factory, queue, settings, worker_id="integration-worker").process_one()
            completed = client.get(f"/v2/jobs/{job_id}", headers=headers)
            assert completed.status_code == 200
            assert completed.json()["data"]["status"] == "completed"
            assert completed.json()["data"]["result"] == {"report": "passed"}
            assert completed.json()["data"]["attempt"] == 1
            events = client.get(f"/v2/jobs/{job_id}/events", headers=headers)
            assert events.status_code == 200
            assert [item["status"] for item in events.json()["data"]] == [
                "queued",
                "running",
                "running",
                "completed",
            ]
    finally:
        app.dependency_overrides.clear()
        if job_id:
            with factory() as session:
                session.execute(
                    text("delete from hcg.jobs where id = cast(:id as uuid)"), {"id": job_id}
                )
                session.commit()
