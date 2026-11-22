"""Exact provenance repair scope; validation and full-draft acceptance stay strict."""

import json

from app.ai.explanation_constraints import (
    MAX_HINT_BYTES,
    REPAIR_HEADROOM_BYTES,
    repair_advice,
    song_reference_hints,
)
from app.ai.state import Claim
from app.ai.validators import validate_claims
from app.ai.workflow import AssistantWorkflow


def test_repair_maps_identity_to_its_own_fact_without_inferred_names():
    facts = {"example:12": {"subject": "Sample Anchor"}, "example:27": {"subject": "198294"}}
    tools = {"example": {"fact_id": "example:12", "song_id": "sample-12"}, "chords": ["C"]}
    hint = song_reference_hints(facts, tools)
    identities = json.loads(hint.split(": ", 1)[1])
    assert identities == {"example:12": ["sample anchor", "sample-12"], "example:27": ["198294"]}
    assert (
        validate_claims(
            [Claim(text="Sample Anchor uses C.", fact_ids=["example:12"])], facts, tools
        )
        == []
    )
    assert "claim:0:song_provenance" in validate_claims(
        [Claim(text="Sample Anchor uses C.", fact_ids=["example:27"])], facts, tools
    )
    # A cited full title does not authorize its suffix or an unrelated subject.
    for text in ("Anchor uses C.", "Sample Anchor uses C. Unknown uses C."):
        assert "claim:0:song_provenance" in validate_claims(
            [Claim(text=text, fact_ids=["example:12"])], facts, tools
        )
    advice = repair_advice(("claim:0:song_provenance",), facts=facts, tool_results=tools)
    assert "opaque song/database ID does not establish a title" in advice
    assert hint in advice


def test_oversized_identity_scope_is_omitted_whole_and_stays_bounded():
    hint = song_reference_hints({"example:long": {"subject": "x" * 5000}}, {})
    assert len(hint.encode()) <= MAX_HINT_BYTES
    assert "omitted for size" in hint
    assert "x" * 100 not in hint


def test_full_rule_diagnostics_and_near_limit_identity_map_fit_repair_headroom():
    rules = (
        "fact_coverage",
        "chord_provenance",
        "figure_provenance",
        "objective_emotion",
        "song_provenance",
        "theory_registry",
    )
    codes = tuple(f"claim:{index}:{rule}" for index in range(8) for rule in rules)
    facts = {"example:limit": {"subject": "x" * 1900}}
    detail = ",".join(codes)
    advice = repair_advice(codes, facts=facts)
    repair = (
        f"\nRepair attempt 1: {detail}. Return one short claim. "
        "Use only listed facts, symbols, and registered theory labels. " + advice
    )
    assert len(repair.encode()) <= REPAIR_HEADROOM_BYTES


def test_provenance_repair_has_matching_scope_and_never_accepts_invalid_second_draft():
    facts = {"example:47": {"subject": "stable-song-47"}, "fact:chords": {}}
    tools = {"chords": ["C", "F", "G"]}
    invalid = {"claims": [{"text": "Unverified Anthem uses C.", "fact_ids": ["example:47"]}]}
    prompts = []

    def rejected(prompt):
        prompts.append(prompt)
        return invalid

    state = {
        "raw_user_query": "Explain C F G",
        "route": "recommend",
        "fact_pool": facts,
        "tool_results": tools,
    }
    result = AssistantWorkflow(None, explanation_model=rejected)._explain(state)
    assert result["fallback"] and len(prompts) == 2
    assert '"example:47":["stable-song-47"]' in prompts[1]
    assert "Unverified Anthem" not in prompts[1]
    assert "song_provenance" in result["errors"][-1]


def test_valid_cited_repair_succeeds_without_changing_original_draft_policy():
    facts = {"example:48": {"subject": "stable-song-48"}, "fact:chords": {}}
    tools = {"chords": ["C", "F", "G"]}
    calls = []
    outputs = [
        {"claims": [{"text": "Unverified Anthem uses C.", "fact_ids": ["example:48"]}]},
        {"claims": [{"text": "C moves toward F.", "fact_ids": ["fact:chords"]}]},
    ]

    def repaired(prompt):
        calls.append(prompt)
        return outputs[len(calls) - 1]

    result = AssistantWorkflow(None, explanation_model=repaired)._explain(
        {
            "raw_user_query": "Explain C F G",
            "route": "recommend",
            "fact_pool": facts,
            "tool_results": tools,
        }
    )
    assert not result["fallback"] and len(calls) == 2
    assert result["explanation"].claims[0].text == "C moves toward F."
