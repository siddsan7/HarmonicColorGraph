"""Private admin aggregates contain only safe totals and enforce the jobs token."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.logs import ai_query_logs
from app.ai.logs import metadata as ai_metadata
from app.api.admin_metrics_v2 import _redis_snapshot
from app.core import request_metrics, telemetry
from app.core.config import AppSettings, get_settings
from app.core.request_metrics import api_request_logs
from app.core.request_metrics import metadata as request_metadata
from app.db.session import get_session
from app.main import app


def test_admin_metrics_require_token_and_report_aggregates():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.exec_driver_sql("attach database ':memory:' as hcg")
        ai_metadata.create_all(connection)
        request_metadata.create_all(connection)
        connection.exec_driver_sql("create table hcg.jobs (status text not null)")
        connection.exec_driver_sql(
            "create table hcg.job_events (status text not null, created_at timestamp not null)"
        )
        connection.exec_driver_sql("insert into hcg.jobs (status) values ('dead_letter')")
        connection.exec_driver_sql(
            "insert into hcg.job_events (status, created_at) values ('retrying', ?)",
            (now.isoformat(),),
        )
        connection.execute(
            api_request_logs.insert(),
            [
                dict(
                    occurred_at=now - timedelta(minutes=2),
                    trace_id="a" * 32,
                    request_id=uuid4(),
                    route="/v2/ai/query",
                    method="POST",
                    status=status,
                    latency_ms=latency,
                )
                for status, latency in ((200, 10), (500, 50))
            ],
        )
        connection.execute(
            ai_query_logs.insert().values(
                query_id=uuid4(),
                created_at=now - timedelta(minutes=1),
                ip_hash="private-hash",
                user_query="private query text",
                route="recommend",
                tools=["recommend_next"],
                final={"fallback": True},
                model="main-model",
                model_usage={
                    "fast-model": {
                        "calls": 1,
                        "tokens_in": 40,
                        "tokens_out": 5,
                        "cost_usd": "0.025",
                    },
                    "main-model": {
                        "calls": 1,
                        "tokens_in": 60,
                        "tokens_out": 15,
                        "cost_usd": "0.1",
                    },
                },
                tokens_in=100,
                tokens_out=20,
                cost_usd=Decimal("0.125"),
                latency_ms=100,
            )
        )

    settings = AppSettings(HCG_JOBS_ADMIN_TOKEN="test-token", DATABASE_URL="sqlite://")

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = session_override
    try:
        client = TestClient(app)
        assert client.get("/v2/admin/metrics").status_code == 403
        response = client.get("/v2/admin/metrics", headers={"X-HCG-Jobs-Token": "test-token"})
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    data = response.json()["data"]
    assert data["api"]["request_count"] == 2
    assert data["api"]["error_count"] == 1
    assert data["api"]["latency_ms"] == {"p50": 10.0, "p95": 50.0, "p99": 50.0, "sample_count": 2}
    assert data["jobs"]["dead_letter_count"] == 1
    assert data["jobs"]["retry_count"] == 1
    assert data["ai"]["cost_usd"] == 0.125
    assert {row["model"] for row in data["ai"]["models"]} == {"fast-model", "main-model"}
    assert sum(row["cost_usd"] for row in data["ai"]["models"]) == 0.125
    assert data["ai"]["tools"] == [{"tool": "recommend_next", "count": 1}]
    assert data["ai"]["fallback_rate"] == 1.0
    assert "private query text" not in response.text
    assert "private-hash" not in response.text


def test_http_request_metric_is_persisted_with_response_trace_id(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.exec_driver_sql("attach database ':memory:' as hcg")
        request_metadata.create_all(connection)
    factory = sessionmaker(bind=engine)
    settings = SimpleNamespace(database_url="postgresql://test")
    monkeypatch.setattr(telemetry, "get_settings", lambda: settings)
    monkeypatch.setattr(request_metrics, "get_settings", lambda: settings)
    monkeypatch.setattr(request_metrics, "_default_session_factory", lambda: factory)
    test_app = FastAPI()
    test_app.add_middleware(telemetry.TelemetryMiddleware)

    @test_app.get("/v2/test")
    def ok():
        return {"ok": True}

    response = TestClient(test_app).get("/v2/test")
    with Session(engine) as session:
        row = session.execute(select(api_request_logs)).one()._mapping
    engine.dispose()
    assert response.status_code == 200
    assert row["trace_id"] == response.headers["x-hcg-trace-id"]
    assert row["route"] == "/v2/test"
    assert row["status"] == 200


def test_queue_depth_remains_visible_when_redis_info_is_unsupported(monkeypatch):
    class FakeRedis:
        def llen(self, _key):
            return 3

        def info(self, _section):
            raise ValueError("unsupported")

        def close(self):
            pass

    monkeypatch.setattr(
        "app.api.admin_metrics_v2.Redis.from_url", lambda *_args, **_kw: FakeRedis()
    )
    snapshot = _redis_snapshot("redis://unused")
    assert snapshot["queue_depth"] == 3
    assert snapshot["hit_rate"] is None
