"""Synthetic intent candidates: validation, dedupe, data boundary and cost cap."""

import json
from decimal import Decimal

from tests.eval.synthetic_intent import (
    STYLE_EXAMPLES,
    build_prompt,
    generate,
    normalize,
    valid_case,
)


def _eval_dir(tmp_path):
    for name in STYLE_EXAMPLES:
        (tmp_path / name).write_text(
            json.dumps({"input": f"Example from {name}", "route": "generate", "axes": {}}) + "\n",
            encoding="utf-8",
        )
    (tmp_path / "intent_next_chord_validation.jsonl").write_text(
        json.dumps({"input": "Held-out VALIDATION request!", "route": "generate"}) + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_valid_case_rules():
    assert valid_case(
        {
            "input": "Next chord after C G, a bit darker",
            "route": "recommend",
            "axes": {"darker_brighter": -0.3},
        }
    )
    assert not valid_case(
        {"input": "Next chord after C G", "route": "recommend", "axes": {"darker_brighter": -0.5}}
    )
    assert not valid_case(
        {"input": "Next chord after C G", "route": "recommend", "axes": {"spicy": 0.7}}
    )
    assert not valid_case(
        {"input": "Explain C G Am F", "route": "explain", "axes": {"dreamy": 0.7}}
    )
    assert not valid_case({"input": "Hi", "route": "explain", "axes": {}})


def test_generation_dedupes_and_never_prompts_with_held_out_sets(tmp_path):
    eval_dir = _eval_dir(tmp_path)
    prompts = []

    def call(prompt):
        prompts.append(prompt)
        return (
            [
                {
                    "input": "held-out validation request",
                    "route": "generate",
                    "axes": {},
                    "category": "dup",
                },
                {
                    "input": "Write a progression in F# minor",
                    "route": "generate",
                    "axes": {},
                    "category": "plain",
                },
                {
                    "input": "Write a progression in F# minor!",
                    "route": "generate",
                    "axes": {},
                    "category": "dup",
                },
                {
                    "input": "Next chord after C G, much tenser",
                    "route": "recommend",
                    "axes": {"tense_relaxed": -1.0},
                    "category": "magnitude",
                },
                {
                    "input": "Next chord after C G",
                    "route": "recommend",
                    "axes": {"tense_relaxed": -0.4},
                    "category": "bad",
                },
            ],
            1000,
            2000,
        )

    result = generate(count=2, max_cost_usd=Decimal("5"), call=call, eval_dir=eval_dir)
    assert result["accepted"] == 2 and result["rejected"] == {"duplicate": 2, "invalid": 1}
    assert [row["review"] for row in result["rows"]] == ["pending", "pending"]
    assert "Held-out VALIDATION" not in prompts[0]
    assert "Example from intent_next_chord_development.jsonl" in prompts[0]
    assert Decimal(result["metered_cost_usd"]) == Decimal("0.055")


def test_generation_stops_before_exceeding_cap(tmp_path):
    calls = []
    result = generate(
        count=10,
        max_cost_usd=Decimal("0.01"),
        call=lambda prompt: calls.append(prompt) or ([], 0, 0),
        eval_dir=_eval_dir(tmp_path),
    )
    assert calls == [] and result["stopped_reason"] == "cost_cap_reached"


def test_prompt_and_normalize():
    assert normalize("  Next chord: C#m, F#!") == "next chord c#m f#"
    assert "Write exactly 5 cases." in build_prompt(5, "{}", [])
