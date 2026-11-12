"""Routing regressions preserve missing-context clarification without extra tools."""

import pytest

from app.ai.state import AssistantResponse, ParsedIntent
from app.ai.workflow import AssistantWorkflow, heuristic_intent
from tests.eval.ai import RecordingTools, _measure, load_cases
from tests.eval.fixtures import seeded_tools


@pytest.mark.parametrize("case_id", ["similar-03", "clarify-01", "clarify-02"])
def test_offline_routing_and_tool_regressions(case_id):
    case = next(case for case in load_cases() if case["id"] == case_id)
    tools = RecordingTools(seeded_tools())
    workflow = AssistantWorkflow(tools)
    final = next(payload for event, payload in workflow.stream(case["input"]) if event == "final")
    response = AssistantResponse.model_validate(final["response"])
    row = _measure(
        case, response, ParsedIntent.model_validate(final["parsed_intent"]), tools.called
    )
    assert row["routing"]
    assert row["tool_correct"]
    if case_id.startswith("clarify"):
        assert tools.called == []
        assert response.candidates == []


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("Find chord progressions like Am E F Dm in A minor", "similar"),
        ("Show a progression like D A Bm G in D major", "similar"),
        ("I'd like a brighter next chord after D A Bm in D major", "recommend"),
        ("Recommend a next chord in D major", "clarify"),
        ("Find similar progressions", "clarify"),
        ("I need a comparison before I choose the sequences", "clarify"),
        ("Compare two progressions", "clarify"),
        ("Create a bright progression in D major", "generate"),
    ],
)
def test_fallback_routing_paraphrases_and_missing_context(query, route):
    assert heuristic_intent(query).task_type == route


@pytest.mark.parametrize("route", ["recommend", "similar", "compare"])
def test_model_routes_without_required_input_clarify_without_tools(route):
    tools = RecordingTools(seeded_tools())
    response = AssistantWorkflow(tools, intent_model=lambda _: ParsedIntent(task_type=route)).run(
        "Please help with these chords"
    )
    assert response.route == "clarify"
    assert tools.called == []
    assert response.candidates == []


def test_model_generation_without_chords_stays_generation():
    workflow = AssistantWorkflow(None)
    assert workflow._router({"parsed_intent": ParsedIntent(task_type="generate")}) == {
        "route": "generate"
    }
