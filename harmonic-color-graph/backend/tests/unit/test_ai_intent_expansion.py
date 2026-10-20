"""Frozen development cases for narrow explicit-language recovery."""

import json
from pathlib import Path

import pytest

from app.ai.workflow import AssistantWorkflow, heuristic_intent

CASES = [
    json.loads(line)
    for line in (Path(__file__).parents[1] / "eval" / "intent_expansion_development.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_expansion_development(case):
    assert heuristic_intent(case["input"]).intent_axes == case["expected_axes"]


def test_model_success_preserves_nondefault_strength_for_new_phrases():
    expected = {"task_type": "recommend", "intent_axes": {"tense_relaxed": -0.15}}
    workflow = AssistantWorkflow(None, intent_model=lambda _prompt: expected)
    actual = workflow._intent_parser({"raw_user_query": "Recommend a tenser chord after C G"})
    assert actual["parsed_intent"].intent_axes == expected["intent_axes"]


def test_failed_model_recovers_new_explicit_language():
    def fail(_prompt):
        raise TimeoutError("private provider detail")

    workflow = AssistantWorkflow(None, intent_model=fail)
    actual = workflow._intent_parser(
        {"raw_user_query": "Recommend a little bit tenser next chord after C G"}
    )
    assert actual["parsed_intent"].intent_axes == {"tense_relaxed": -0.3}
    assert actual["errors"] == ["intent_model_failed:TimeoutError"]
