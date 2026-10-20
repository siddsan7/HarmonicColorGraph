"""Development regressions for explicit directions during parser outages."""

import pytest

from app.ai.state import ParsedIntent
from app.ai.workflow import AssistantWorkflow, heuristic_intent


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        ("darker", {"darker_brighter": -0.7}),
        ("less bright", {"darker_brighter": -0.7}),
        ("more tension", {"tense_relaxed": -0.7}),
        ("less tense", {"tense_relaxed": 0.7}),
        ("simpler", {"simple_complex": -0.7}),
        ("more resolved", {"resolved_open": -0.7}),
        ("smoother", {"smooth": 0.7}),
        ("darker and smoother", {"darker_brighter": -0.7, "smooth": 0.7}),
        ("slightly darker", {"darker_brighter": -0.3}),
        ("much smoother", {"smooth": 1.0}),
        ("not darker", {}),
        ("darker or brighter", {}),
        ("interesting", {}),
        ("if darker is a problem, keep the same character", {}),
        ("if I want more tension", {"tense_relaxed": -0.7}),
        ("neither brighter nor smoother", {}),
        ("unless darker works, keep the same character", {}),
        ("whether darker works is unknown", {}),
    ],
)
@pytest.mark.parametrize(
    ("history", "key"),
    [("D A Bm", "D major"), ("Dm G C", "C major"), ("Am E7", "A minor")],
)
def test_explicit_fallback_directions(words, expected, history, key):
    parsed = heuristic_intent(f"Recommend a {words} next chord after {history} in {key}")
    assert parsed.intent_axes == expected
    assert parsed.chords == history.split()
    assert parsed.key == key


def test_failed_model_keeps_explicit_preferences():
    def fail(_prompt):
        raise TimeoutError("private provider response")

    workflow = AssistantWorkflow(None, intent_model=fail)
    result = workflow._intent_parser(
        {"raw_user_query": "Recommend a darker next chord after D A in D major"}
    )
    assert result["parsed_intent"].intent_axes == {"darker_brighter": -0.7}
    assert result["errors"] == ["intent_model_failed:TimeoutError"]


def test_fallback_does_not_override_valid_model_preferences():
    parsed = ParsedIntent(task_type="recommend", intent_axes={"darker_brighter": -0.2})
    workflow = AssistantWorkflow(None, intent_model=lambda _prompt: parsed)
    result = workflow._intent_parser({"raw_user_query": "Recommend a darker next chord"})
    assert result["parsed_intent"] == parsed
