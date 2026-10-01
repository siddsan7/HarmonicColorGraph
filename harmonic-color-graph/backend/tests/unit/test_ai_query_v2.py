"""F73 SSE, rate, budget, and audit behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.logs import AIQueryStore, ai_query_logs, metadata
from app.ai.state import ParsedIntent
from app.ai.usage import UsageMeter, request_cost_bound
from app.ai.workflow import AssistantWorkflow
from app.api.ai_v2 import AIQueryRuntime, get_ai_runtime
from app.main import app
from tests.unit.test_mcp_server import _tools

NOW = datetime(2026, 9, 27, 8, 0, tzinfo=UTC)


def _client(workflow_factory=None, budget=Decimal("2.00")):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    ).execution_options(schema_translate_map={"hcg": None})
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    runtime = AIQueryRuntime(
        session_factory=factory,
        workflow_factory=workflow_factory or (lambda _session, _meter: AssistantWorkflow(_tools())),
        budget_usd=budget,
        reservation_usd=Decimal("0.25"),
        now=lambda: NOW,
    )
    app.dependency_overrides[get_ai_runtime] = lambda: runtime
    return TestClient(app), factory


def _events(response):
    return [line[7:] for line in response.text.splitlines() if line.startswith("event: ")]


def test_sse_returns_steps_validated_partial_and_final_with_success_log():
    client, factory = _client()
    try:
        response = client.post("/v2/ai/query", json={"query": "Explain C G Am F"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _events(response)
        assert events[0] == "step"
        assert "partial" in events
        assert events[-1] == "final"
        with factory() as session:
            row = session.execute(select(ai_query_logs)).one()._mapping
            assert row["route"] == "explain"
            assert row["final"]["route"] == "explain"
            assert row["parsed_intent"]["chords"] == ["C", "G", "Am", "F"]
            assert row["error_category"] is None
    finally:
        app.dependency_overrides.clear()


def test_twenty_first_query_in_hour_is_rejected_and_logged():
    client, factory = _client()
    try:
        for _ in range(20):
            response = client.post("/v2/ai/query", json={"query": "Explain C G Am F"})
            assert response.status_code == 200
        response = client.post("/v2/ai/query", json={"query": "Explain C G Am F"})
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert int(response.headers["retry-after"]) > 0
        with factory() as session:
            count = session.execute(select(func.count()).select_from(ai_query_logs)).scalar_one()
            assert count == 21
            rejected = session.execute(
                select(func.count())
                .select_from(ai_query_logs)
                .where(ai_query_logs.c.error_category == "ip_rate_limit")
            ).scalar_one()
            assert rejected == 1
    finally:
        app.dependency_overrides.clear()


def test_daily_budget_uses_logged_cost_and_records_rejection():
    client, factory = _client()
    try:
        with factory() as session:
            AIQueryStore(session).write(
                query_id=uuid4(),
                created_at=NOW,
                ip_hash="prior",
                user_query="previous",
                cost_usd=Decimal("2.01"),
            )
            session.commit()
        response = client.post("/v2/ai/query", json={"query": "Explain C G Am F"})
        assert response.status_code == 429
        assert "daily budget" in response.json()["error"]["message"]
        with factory() as session:
            categories = session.execute(select(ai_query_logs.c.error_category)).scalars().all()
            assert "daily_budget" in categories
    finally:
        app.dependency_overrides.clear()


def test_next_request_is_blocked_after_a_metered_query_spends_the_budget():
    class Raw:
        usage_metadata = {"input_tokens": 50_000, "output_tokens": 0}

    def metered_workflow(_session, meter):
        meter.record(Raw(), "claude-sonnet-5")
        return AssistantWorkflow(_tools())

    client, factory = _client(workflow_factory=metered_workflow, budget=Decimal("0.30"))
    try:
        assert client.post("/v2/ai/query", json={"query": "Explain C G"}).status_code == 200
        response = client.post("/v2/ai/query", json={"query": "Explain C G"})
        assert response.status_code == 429
        with factory() as session:
            costs = session.execute(select(ai_query_logs.c.cost_usd)).scalars().all()
            assert Decimal("0.10") in costs
    finally:
        app.dependency_overrides.clear()


def test_pending_reservation_blocks_concurrent_spend_and_releases_on_completion():
    _client_unused, factory = _client()
    runtime = AIQueryRuntime(
        session_factory=factory,
        workflow_factory=lambda _session, _meter: AssistantWorkflow(_tools()),
        budget_usd=Decimal("0.30"),
        reservation_usd=Decimal("0.25"),
        now=lambda: NOW,
    )
    first = uuid4()
    second = uuid4()
    third = uuid4()
    try:
        assert runtime.preflight(query="Explain C G", ip_hash="first", query_id=first) is None
        denied = runtime.preflight(query="Explain C G", ip_hash="second", query_id=second)
        assert denied is not None and denied.status_code == 429
        assert list(runtime.events(query="Explain C G", query_id=first))[-1].startswith(
            "event: final"
        )
        assert runtime.preflight(query="Explain C G", ip_hash="third", query_id=third) is None
    finally:
        app.dependency_overrides.clear()


def test_stream_failure_emits_error_and_writes_failure_log():
    class BrokenWorkflow:
        def stream(self, _query):
            yield "step", {"node": "intent_parser", "status": "started"}
            raise RuntimeError("provider secret must never reach the client")

    client, factory = _client(workflow_factory=lambda _session, _meter: BrokenWorkflow())
    try:
        response = client.post("/v2/ai/query", json={"query": "Explain C G"})
        assert response.status_code == 200
        assert _events(response) == ["step", "error"]
        assert "provider secret" not in response.text
        with factory() as session:
            row = session.execute(select(ai_query_logs)).one()._mapping
            assert row["error_category"] == "workflow_failed"
            assert row["final"] is None
    finally:
        app.dependency_overrides.clear()


def test_usage_meter_counts_both_models_and_estimates_cost():
    class Raw:
        usage_metadata = {"input_tokens": 1000, "output_tokens": 100}

    meter = UsageMeter()
    meter.record(Raw(), "claude-haiku-4-5-20251001")
    meter.record(Raw(), "claude-sonnet-5")
    assert meter.tokens_in == 2000
    assert meter.tokens_out == 200
    assert meter.cost_usd == Decimal("0.0045")
    assert meter.as_log()["model_usage"] == {
        "claude-haiku-4-5-20251001": {
            "calls": 1,
            "tokens_in": 1000,
            "tokens_out": 100,
            "cost_usd": "0.0015",
        },
        "claude-sonnet-5": {"calls": 1, "tokens_in": 1000, "tokens_out": 100, "cost_usd": "0.003"},
    }


def test_missing_provider_usage_gets_conservative_charge():
    meter = UsageMeter()
    meter.record(object(), "claude-sonnet-5")
    assert meter.cost_usd == Decimal("0.25")


def test_model_timeout_fallback_retains_budget_reservation():
    def timed_out(_prompt):
        raise TimeoutError("provider outcome unknown")

    client, factory = _client(
        workflow_factory=lambda _session, _meter: AssistantWorkflow(
            _tools(), intent_model=timed_out
        ),
        budget=Decimal("0.40"),
    )
    try:
        response = client.post("/v2/ai/query", json={"query": "Explain C G"})
        assert response.status_code == 200
        assert _events(response)[-1] == "final"
        with factory() as session:
            row = session.execute(select(ai_query_logs)).one()._mapping
            assert any("model_failed" in code for code in row["validation_errors"])
            assert row["cost_usd"] == Decimal("0.25")
        assert client.post("/v2/ai/query", json={"query": "Explain C G"}).status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_workflow_timeout_retains_budget_reservation():
    class TimedOutWorkflow:
        def stream(self, _query):
            yield "step", {"stage": "model"}
            raise TimeoutError("provider outcome unknown")

    client, factory = _client(
        workflow_factory=lambda _session, _meter: TimedOutWorkflow(), budget=Decimal("0.40")
    )
    try:
        response = client.post("/v2/ai/query", json={"query": "Explain C G"})
        assert _events(response)[-1] == "error"
        with factory() as session:
            row = session.execute(select(ai_query_logs)).one()._mapping
            assert row["error_category"] == "timeout"
            assert row["cost_usd"] == Decimal("0.25")
        assert client.post("/v2/ai/query", json={"query": "Explain C G"}).status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_missing_usage_retains_full_request_bound():
    def missing_usage(_session, meter):
        meter.record(object(), "claude-sonnet-5")
        return AssistantWorkflow(_tools())

    client, factory = _client(workflow_factory=missing_usage, budget=Decimal("1.40"))
    app.dependency_overrides[get_ai_runtime]().reservation_usd = Decimal("0.90")
    try:
        assert client.post("/v2/ai/query", json={"query": "Explain C G"}).status_code == 200
        with factory() as session:
            assert session.execute(select(ai_query_logs.c.cost_usd)).scalar_one() == Decimal("0.90")
        assert client.post("/v2/ai/query", json={"query": "Explain C G"}).status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_request_reservation_bounds_three_model_calls(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    assert Decimal("0.75") <= request_cost_bound() <= Decimal("2")


def test_oversized_explanation_prompt_falls_back_before_model_call():
    calls = 0

    def explain(_prompt):
        nonlocal calls
        calls += 1
        return {"claims": [{"text": "Unsupported", "fact_ids": ["fact:1"]}]}

    workflow = AssistantWorkflow(_tools(), explanation_model=explain)
    result = workflow._explain(
        {
            "raw_user_query": "Explain C G",
            "route": "explain",
            "parsed_intent": ParsedIntent(task_type="explain", chords=["C", "G"]),
            "fact_pool": {"fact:1": {"subject": "x" * 100_000}},
            "tool_results": {},
        }
    )
    assert calls == 0
    assert result["fallback"]


def test_production_requires_private_ip_hash_secret(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("HCG_IP_HASH_SECRET", raising=False)
    client, factory = _client()
    try:
        response = client.post("/v2/ai/query", json={"query": "Explain C G"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "ai_configuration_error"
        with factory() as session:
            assert (
                session.execute(select(func.count()).select_from(ai_query_logs)).scalar_one() == 0
            )
    finally:
        app.dependency_overrides.clear()


def test_production_accepts_configured_ip_hash_secret(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("HCG_IP_HASH_SECRET", "test-only-private-value")
    client, _factory = _client()
    try:
        response = client.post("/v2/ai/query", json={"query": "Explain C G"})
        assert response.status_code == 200
        assert _events(response)[-1] == "final"
    finally:
        app.dependency_overrides.clear()


def test_blank_query_is_rejected_before_rate_counter_changes():
    client, factory = _client()
    try:
        response = client.post("/v2/ai/query", json={"query": "  "})
        assert response.status_code == 422
        with factory() as session:
            assert (
                session.execute(select(func.count()).select_from(ai_query_logs)).scalar_one() == 0
            )
    finally:
        app.dependency_overrides.clear()


def test_disconnect_retains_reservation():
    _client_instance, factory = _client(budget=Decimal("0.40"))
    runtime = app.dependency_overrides[get_ai_runtime]()
    query_id = uuid4()
    try:
        assert runtime.preflight(query="Explain C G", ip_hash="test", query_id=query_id) is None
        events = runtime.events(query="Explain C G", query_id=query_id)
        assert next(events).startswith("event: step")
        events.close()
        with factory() as session:
            row = session.execute(select(ai_query_logs)).one()._mapping
            assert row["error_category"] == "client_disconnected"
            assert row["cost_usd"] == Decimal("0.25")
        assert (
            runtime.preflight(query="Explain C G", ip_hash="test", query_id=uuid4()).status_code
            == 429
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "usage",
    [
        {"total_tokens": 123},
        {"input_tokens": 100},
        {"input_tokens": -1000, "output_tokens": 0},
        {"input_tokens": True, "output_tokens": 0},
        {"input_tokens": "100", "output_tokens": 0},
        {"input_tokens": 0, "output_tokens": 0.5},
        [100, 0],
    ],
)
def test_malformed_usage_retains_reservation(usage):
    class Raw:
        usage_metadata = usage

    def malformed_usage(_session, meter):
        meter.record(Raw(), "claude-sonnet-5")
        assert meter.unknown_usage_calls == 1
        assert meter.tokens_in == meter.tokens_out == 0
        return AssistantWorkflow(_tools())

    client, factory = _client(workflow_factory=malformed_usage, budget=Decimal("1.40"))
    app.dependency_overrides[get_ai_runtime]().reservation_usd = Decimal("0.90")
    try:
        assert client.post("/v2/ai/query", json={"query": "Explain C G"}).status_code == 200
        with factory() as session:
            assert session.execute(select(ai_query_logs.c.cost_usd)).scalar_one() == Decimal("0.90")
        assert client.post("/v2/ai/query", json={"query": "Explain C G"}).status_code == 429
    finally:
        app.dependency_overrides.clear()
