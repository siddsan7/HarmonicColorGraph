"""Fresh frozen fallback-routing regressions; no model or corpus calls."""

import json
from pathlib import Path

import pytest

from app.ai.workflow import AssistantWorkflow, heuristic_intent


def _cases():
    root = Path(__file__).parents[1] / "eval"
    return [
        json.loads(line)
        for split in ("development", "validation")
        for line in (root / f"intent_next_chord_{split}.jsonl").read_text().splitlines()
    ]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_frozen_next_chord_cases(case):
    parsed = heuristic_intent(case["input"])
    assert parsed.task_type == case["route"]
    assert parsed.intent_axes == case["axes"]


def test_valid_model_intent_remains_authoritative():
    expected = {"task_type": "generate", "key": "Eb major", "intent_axes": {}}
    workflow = AssistantWorkflow(None, intent_model=lambda _: expected)
    result = workflow._intent_parser({"raw_user_query": _cases()[0]["input"]})
    assert result["parsed_intent"].task_type == "generate"
    assert result["parsed_intent"].intent_axes == {}


def test_failed_model_recovers_direct_next_chord():
    def fail(_):
        raise TimeoutError("not user visible")

    result = AssistantWorkflow(None, intent_model=fail)._intent_parser(
        {"raw_user_query": _cases()[0]["input"]}
    )
    assert result["parsed_intent"].task_type == "recommend"
    assert result["parsed_intent"].intent_axes == {"darker_brighter": 0.3}
