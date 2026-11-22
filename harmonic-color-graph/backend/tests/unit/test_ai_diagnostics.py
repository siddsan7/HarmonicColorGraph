"""Profiling preserves failures, cost reservations and route denominators."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from tests.eval.ai import load_cases, run
from tests.eval.ai_diagnostics import RequestDiagnostics, route_diagnostics


def test_model_diagnostics_record_failed_calls_without_content():
    def fail(prompt):
        raise TimeoutError("secret provider content")

    workflow = SimpleNamespace(intent_model=fail, explanation_model=None)
    diagnostics = RequestDiagnostics()
    diagnostics.attach(workflow)
    with pytest.raises(TimeoutError):
        workflow.intent_model("private query")
    record = diagnostics.finish()
    assert len(record["model_calls"]) == 1
    call = record["model_calls"][0]
    assert call["stage"] == "intent"
    assert call["outcome"] == "error"
    assert call["prompt_bytes"] == 13
    assert "private" not in str(record) and "secret" not in str(record)


def test_route_summary_counts_misroutes_and_failed_requests():
    def row(duration, **extra):
        return {
            "expected_route": "recommend",
            "actual_route": "generate",
            "fallback": True,
            "accounted_cost_usd": "0.75",
            "model_usage": {"model": {"calls": 1, "tokens_in": 10, "tokens_out": 5}},
            "diagnostics": {
                "workflow_completion_ms": duration,
                "first_validated_text_ms": None,
                "repair_calls": 0,
            },
            **extra,
        }

    summary = route_diagnostics([row(10), row(30), row(100, error="TimeoutError")])
    result = summary["recommend"]
    assert result["attempts"] == 3
    assert result["completed"] == 2
    assert result["request_failures"] == 1
    assert result["p50_workflow_ms"] == 20
    assert result["p95_workflow_ms"] == 30
    assert result["p50_first_validated_text_ms"] is None
    assert result["model_calls"] == 3
    assert result["tokens_in"] == 30
    assert result["cost_per_completed_request_usd"] == "1.125"


def test_offline_profile_has_stage_and_tool_boundaries_without_models():
    report = run(cases=load_cases()[:1], live=False, fixture=True, max_cost_usd=Decimal(1))
    row = report["cases"][0]
    assert row["diagnostics"]["model_calls"] == []
    assert row["diagnostics"]["repair_calls"] == 0
    assert set(row["diagnostics"]["node_ms"]) >= {"retrieve", "rank", "explain", "final"}
    assert row["diagnostics"]["tools"]
    assert row["model_usage"] == {}
    assert row["unknown_usage_calls"] == 0
    summary = report["route_diagnostics"]["recommend"]
    assert summary["model_call_attempts"] == summary["usage_recorded_calls"] == 0
    assert summary["tokens_in_per_known_usage_call"] is None
    assert row["accounted_cost_usd"] == "0"
    assert report["reproducibility"]["corpus_version"] == "ai-eval-v1"
    assert report["reproducibility"]["models"] == {}
    assert report["route_diagnostics"]["recommend"]["completed"] == 1
