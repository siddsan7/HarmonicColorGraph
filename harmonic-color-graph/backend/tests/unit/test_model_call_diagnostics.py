"""Model efficiency reports retain failed attempts and unknown token usage."""

from types import SimpleNamespace

import pytest

from app.ai.usage import UsageMeter
from tests.eval.ai_diagnostics import RequestDiagnostics, route_diagnostics
from tests.eval.model_call_diagnostics import model_call_summary


def test_attempts_and_usage_records_have_different_failure_boundaries():
    meter = UsageMeter()
    replies = iter(["parse_error", "timeout", "valid", "missing_usage"])

    def explain(_prompt):
        reply = next(replies)
        if reply == "timeout":
            raise TimeoutError("private provider error")
        meter.record(
            SimpleNamespace(
                usage_metadata={"input_tokens": 10, "output_tokens": 2}
                if reply != "missing_usage"
                else {}
            ),
            "test",
        )
        if reply == "parse_error":
            raise ValueError("private parse error")
        return {"claims": []}

    diagnostics = RequestDiagnostics()
    workflow = SimpleNamespace(intent_model=None, explanation_model=explain)
    diagnostics.attach(workflow)
    for _ in range(2):
        with pytest.raises((ValueError, TimeoutError)):
            workflow.explanation_model("é")
    workflow.explanation_model("é")
    workflow.explanation_model("é")
    row = {
        "expected_route": "explain",
        "accounted_cost_usd": "1",
        "model_usage": meter.as_log()["model_usage"],
        "unknown_usage_calls": meter.unknown_usage_calls,
        "diagnostics": diagnostics.finish(),
    }
    result = route_diagnostics([row])["explain"]
    assert result["model_call_attempts"] == 4
    assert result["model_callable_returned"] == 2
    assert result["model_callable_failed"] == 2
    assert result["usage_recorded_calls"] == result["model_calls"] == 3
    assert result["unknown_usage_calls"] == 1
    assert result["known_usage_calls"] == 2
    assert result["tokens_in_per_known_usage_call"] == 10
    assert result["tokens_out_per_known_usage_call"] == 2
    assert result["attempted_prompt_bytes"] == 8
    assert result["model_calls_by_stage"]["explanation"] == {
        "attempts": 4,
        "callable_returned": 2,
        "callable_failed": 2,
        "prompt_bytes": 8,
    }
    assert result["repair_calls"] == 3
    assert "private" not in str(result)


def test_offline_zero_and_unknown_legacy_denominators():
    row = {"model_usage": {}, "diagnostics": {"model_calls": []}, "unknown_usage_calls": 0}
    summary = model_call_summary([row])
    assert summary["model_call_attempts"] == summary["known_usage_calls"] == 0
    assert summary["tokens_in_per_known_usage_call"] is None
    assert summary["tokens_out_per_known_usage_call"] is None
    assert summary["model_calls_by_stage"] == {}
    assert summary["attempted_prompt_bytes"] == 0
    del row["unknown_usage_calls"]
    del row["diagnostics"]["model_calls"]
    summary = model_call_summary([row])
    for key in (
        "model_call_attempts",
        "model_callable_returned",
        "model_callable_failed",
        "unknown_usage_calls",
        "known_usage_calls",
        "attempted_prompt_bytes",
        "model_calls_by_stage",
    ):
        assert summary[key] is None
    assert summary["usage_recorded_calls"] == 0


def test_missing_usage_is_not_treated_as_zero_token_average():
    summary = model_call_summary(
        [
            {
                "model_usage": {"test": {"calls": 1, "tokens_in": 0, "tokens_out": 0}},
                "diagnostics": {"model_calls": []},
                "unknown_usage_calls": 1,
            }
        ]
    )
    assert summary["known_usage_calls"] == 0
    assert summary["tokens_in_per_known_usage_call"] is None
