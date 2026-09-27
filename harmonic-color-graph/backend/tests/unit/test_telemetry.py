"""Request and database spans must join without exposing SQL or request data."""

import re
from contextlib import nullcontext
from uuid import uuid4

from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from sqlalchemy.orm import Session

from app.ai.workflow import AssistantWorkflow
from app.core import telemetry
from app.core.config import AppSettings
from app.db.session import create_database_engine, get_session
from app.jobs.worker_runtime import JobWorker
from app.main import app
from tests.unit.test_ai_query_v2 import _client
from tests.unit.test_mcp_server import _tools


class CapturingExporter(SpanExporter):
    def __init__(self):
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def test_health_db_trace_correlates_http_and_sql_without_sensitive_fields(caplog):
    exporter = CapturingExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        response = TestClient(app).get("/health/db", headers={"Authorization": "secret-token"})
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    trace_id = response.headers["x-hcg-trace-id"]
    assert response.status_code == 200
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id)
    spans = [span for span in exporter.spans if f"{span.context.trace_id:032x}" == trace_id]
    assert {span.name for span in spans} == {"http.request", "db.query"}
    root = next(span for span in spans if span.name == "http.request")
    database = next(span for span in spans if span.name == "db.query")
    assert database.parent.span_id == root.context.span_id
    assert database.attributes["db.operation.name"] == "SELECT"
    assert "secret-token" not in str(spans) + caplog.text
    assert "select 1" not in str(spans) + caplog.text


def test_workflow_nodes_and_tools_share_parent_trace():
    exporter = CapturingExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    with trace.get_tracer("test").start_as_current_span("test.request") as root:
        result = AssistantWorkflow(_tools()).run("Recommend after C G Am in C major")
    assert result.route == "recommend"
    same_trace = [
        span for span in exporter.spans if span.context.trace_id == root.get_span_context().trace_id
    ]
    names = {span.name for span in same_trace}
    assert "ai.node.intent_parser" in names
    assert "ai.node.validate" in names
    assert "ai.tool.analyze_progression" in names
    assert "ai.tool.recommend_next" in names
    assert all("raw_user_query" not in str(span.attributes) for span in same_trace)


def test_span_omits_exception_message():
    exporter = CapturingExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    try:
        with telemetry.safe_span("sensitive.operation"):
            raise RuntimeError("password=secret-value")
    except RuntimeError:
        pass
    span = exporter.spans[-1]
    assert span.name == "sensitive.operation"
    assert "secret-value" not in str(span.events) + str(span.status)


def test_streamed_ai_nodes_share_http_trace():
    exporter = CapturingExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    client, _factory = _client()
    try:
        response = client.post("/v2/ai/query", json={"query": "Explain C G Am F"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    trace_id = int(response.headers["x-hcg-trace-id"], 16)
    names = {span.name for span in exporter.spans if span.context.trace_id == trace_id}
    assert {"http.request", "ai.node.intent_parser", "ai.tool.analyze_progression"} <= names


def test_langsmith_without_key_keeps_workflow_available(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    workflow = AssistantWorkflow(_tools())
    assert workflow._langsmith_enabled() is False
    assert workflow.run("Explain C G Am F").route == "explain"


def test_worker_creates_trace_for_claimed_job(monkeypatch):
    exporter = CapturingExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    job_id = str(uuid4())
    seen = []

    class Queue:
        def receive(self, timeout):
            return job_id

    class Repository:
        def __init__(self, _session):
            pass

        def claim(self, _job_id, _worker_id):
            return {"type": "evaluation_run", "payload": {}}

        def complete(self, _job_id, _worker_id, _result):
            seen.append("completed")

    monkeypatch.setattr("app.jobs.worker_runtime.JobRepository", Repository)

    def run_job(_kind, _payload, _settings, _progress):
        seen.append(telemetry.current_trace_id())
        return {}

    monkeypatch.setattr("app.jobs.worker_runtime.run_job", run_job)
    worker = JobWorker(lambda: nullcontext(object()), Queue(), AppSettings())
    assert worker.process_one(timeout=0)
    assert seen[-1] == "completed"
    assert re.fullmatch(r"[0-9a-f]{32}", seen[0])
    assert any(
        span.name == "job.process" and f"{span.context.trace_id:032x}" == seen[0]
        for span in exporter.spans
    )
