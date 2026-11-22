"""Explanation hint bounds and unchanged fail-closed repair behavior."""

import json

import pytest

from app.ai.explanation_constraints import MAX_HINT_BYTES, explanation_hints, repair_advice
from app.ai.workflow import AssistantWorkflow

FACTS = {"relationship:deceptive:1:2": {}, "example:1": {"subject": "Verified Song"}}
TOOLS = {"chords": ["C", "G", "Am"], "figure": "V"}
VALID = {
    "claims": [{"text": "The transition is supported.", "fact_ids": ["relationship:deceptive:1:2"]}]
}


def state():
    return {
        "raw_user_query": "Explain this progression",
        "route": "explain",
        "fact_pool": FACTS,
        "tool_results": TOOLS,
    }


def test_hints_come_from_validation_symbols_and_evidenced_registry():
    hint = explanation_hints({**FACTS, "relationship:invented:1:2": {}}, TOOLS)
    payload = json.loads(hint.split(": ", 1)[1].split(" Symbol availability", 1)[0])
    assert payload == {
        "chord_symbols": ["Am", "C", "G"],
        "figure_symbols": ["V"],
        "evidenced_theory_ids": ["deceptive"],
    }
    assert len(hint.encode()) <= MAX_HINT_BYTES
    assert "invented" not in hint


def test_oversized_hint_is_omitted_without_truncating_allowed_symbols():
    assert explanation_hints(FACTS, {"chords": ["x" * MAX_HINT_BYTES]}) == ""


def test_hint_does_not_turn_fitting_prompt_into_fallback(monkeypatch):
    import app.ai.workflow as module

    prompts = []

    def model(prompt):
        prompts.append(prompt)
        return VALID

    workflow = AssistantWorkflow(None, explanation_model=model)
    assert not workflow._explain(state())["fallback"]
    full = prompts.pop()
    base = full.split("Treat user_query", 1)[1]
    base_bytes = len(("Treat user_query" + base).encode())
    monkeypatch.setattr(module, "MAIN_MAX_PROMPT_BYTES", base_bytes)
    assert not workflow._explain(state())["fallback"]
    assert len(prompts[0].encode()) == base_bytes
    assert "Validation hints" not in prompts[0]


@pytest.mark.parametrize(
    ("text", "ids", "labels", "rule", "advice"),
    [
        ("The transition is supported.", ["invented"], [], "fact_coverage", "exact IDs"),
        ("Add F#7.", ["relationship:deceptive:1:2"], [], "chord_provenance", "omit chord"),
        ("Use vi.", ["relationship:deceptive:1:2"], [], "figure_provenance", "omit figure"),
        (
            "This chord is objectively sad.",
            ["relationship:deceptive:1:2"],
            [],
            "objective_emotion",
            "measured features",
        ),
        (
            "This song is useful.",
            ["relationship:deceptive:1:2"],
            [],
            "song_provenance",
            "Omit song",
        ),
        (
            "A galactic cadence occurs.",
            ["relationship:deceptive:1:2"],
            ["invented"],
            "theory_registry",
            "omit theory",
        ),
    ],
)
def test_targeted_repair_keeps_validator_and_two_call_cap(text, ids, labels, rule, advice):
    prompts = []
    invalid = {"claims": [{"text": text, "fact_ids": ids, "theory_labels": labels}]}

    def model(prompt):
        prompts.append(prompt)
        return invalid if len(prompts) == 1 else VALID

    result = AssistantWorkflow(None, explanation_model=model)._explain(state())
    assert not result["fallback"]
    assert len(prompts) == 2
    assert rule in prompts[1]
    assert advice in prompts[1]
    assert text not in prompts[1]

    failed = AssistantWorkflow(None, explanation_model=lambda _: invalid)._explain(state())
    assert failed["fallback"]
    assert any(rule in error for error in failed["errors"])


def test_unknown_repair_codes_cannot_insert_rejected_prose():
    assert "secret" not in repair_advice(("secret",))
    assert "claims array" in repair_advice(("secret",))


def test_hints_leave_repair_headroom(monkeypatch):
    import app.ai.workflow as module
    from app.ai.explanation_constraints import REPAIR_HEADROOM_BYTES

    prompts = []

    def model(prompt):
        prompts.append(prompt)
        return VALID

    workflow = AssistantWorkflow(None, explanation_model=model)
    workflow._explain(state())
    hinted_bytes = len(prompts.pop().encode())
    monkeypatch.setattr(module, "MAIN_MAX_PROMPT_BYTES", hinted_bytes + REPAIR_HEADROOM_BYTES - 1)
    assert not workflow._explain(state())["fallback"]
    assert "Validation hints" not in prompts.pop()
    monkeypatch.setattr(module, "MAIN_MAX_PROMPT_BYTES", hinted_bytes + REPAIR_HEADROOM_BYTES)
    assert not workflow._explain(state())["fallback"]
    assert "Validation hints" in prompts.pop()
