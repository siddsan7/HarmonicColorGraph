"""Explanation lifecycle counters count actual calls and bounded terminal outcomes."""

import pytest

import app.ai.workflow as module
from app.ai.workflow import AssistantWorkflow

VALID = {"claims": [{"text": "Tool evidence is available.", "fact_ids": ["fact:1"]}]}


def _run(monkeypatch, outputs, *, facts=True, model=True, limit=None):
    events = []
    calls = []
    monkeypatch.setattr(
        module, "emit_metric", lambda name, value, **labels: events.append((name, value, labels))
    )
    if limit is not None:
        monkeypatch.setattr(module, "MAIN_MAX_PROMPT_BYTES", limit)

    def explain(prompt):
        calls.append(prompt)
        value = outputs[len(calls) - 1]
        if isinstance(value, Exception):
            raise value
        return value

    result = AssistantWorkflow(None, explanation_model=explain if model else None)._explain(
        {
            "raw_user_query": "private user content",
            "route": "recommend",
            "fact_pool": {"fact:1": {}} if facts else {},
            "tool_results": {},
        }
    )
    lifecycle = [labels for name, _, labels in events if name == "ai_explanation_lifecycle_count"]
    assert all(set(labels) == {"route", "outcome", "kind"} for labels in lifecycle)
    assert all(labels["route"] == "recommend" for labels in lifecycle)
    assert "private" not in str(events)
    return result, calls, events, [(item["outcome"], item["kind"]) for item in lifecycle]


@pytest.mark.parametrize(
    "outputs,expected,calls,fallback",
    [
        ([VALID], [("first_pass_valid", "none")], 1, False),
        ([{}, VALID], [("repair_attempted", "none"), ("repair_succeeded", "none")], 2, False),
        (
            [{}, {}],
            [("repair_attempted", "none"), ("terminal_fallback", "validation_exhausted")],
            2,
            True,
        ),
        (
            [RuntimeError("private provider content")],
            [("provider_error", "none"), ("terminal_fallback", "provider_error")],
            1,
            True,
        ),
        (
            [{}, RuntimeError("private provider content")],
            [
                ("repair_attempted", "none"),
                ("provider_error", "none"),
                ("terminal_fallback", "provider_error"),
            ],
            2,
            True,
        ),
    ],
)
def test_lifecycle_outcomes(monkeypatch, outputs, expected, calls, fallback):
    result, prompts, events, lifecycle = _run(monkeypatch, outputs)
    assert len(prompts) == calls
    assert result["fallback"] is fallback
    assert lifecycle == [("started", "none"), *expected]
    repairs = [event for event in events if event[0] == "ai_repair_attempt_count"]
    assert len(repairs) == calls - 1
    assert (
        sum(
            outcome in {"first_pass_valid", "repair_succeeded", "terminal_fallback"}
            for outcome, _ in lifecycle
        )
        == 1
    )


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"model": False}, "no_model"),
        ({"facts": False}, "no_facts"),
        ({"limit": 1}, "prompt_limit"),
    ],
)
def test_no_call_fallback_lifecycle(monkeypatch, kwargs, reason):
    result, calls, events, lifecycle = _run(monkeypatch, [], **kwargs)
    assert result["fallback"]
    assert not calls
    assert lifecycle == [("started", "none"), ("terminal_fallback", reason)]
    assert not any(name == "ai_repair_attempt_count" for name, _, _ in events)


def test_oversized_repair_does_not_count_provider_attempt(monkeypatch):
    # Keep optional hints constant while making only the appended repair overflow.
    monkeypatch.setattr(module, "explanation_hints", lambda *_: "")
    _, calls, _, _ = _run(monkeypatch, [VALID])
    result, calls, events, lifecycle = _run(monkeypatch, [{}, VALID], limit=len(calls[0].encode()))
    assert result["fallback"]
    assert len(calls) == 1
    assert lifecycle == [("started", "none"), ("terminal_fallback", "prompt_limit")]
    assert not any(name == "ai_repair_attempt_count" for name, _, _ in events)
