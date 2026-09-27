"""F72 grounding rules: passing and rejecting examples for every rule."""

import pytest

from app.ai.state import Claim, ExplanationDraft
from app.ai.validators import validate_claims, validate_draft

FACTS = {
    "relationship:deceptive:1:2": {"tool": "analyze_progression"},
    "example:abc": {"tool": "get_examples", "source": "corpus"},
}
TOOLS = {
    "analyze_progression": {
        "chords": [{"symbol": "C", "raw_symbol": "C"}, {"symbol": "G7", "raw_symbol": "G7"}],
        "tokens": [
            {"figure": "I", "display_figure": "I", "core": "maj:I"},
            {"figure": "V7", "display_figure": "V7", "core": "maj:V"},
        ],
    }
}


@pytest.mark.parametrize(
    ("text", "facts", "labels", "expected"),
    [
        ("C moves toward G7.", ["relationship:deceptive:1:2"], [], []),
        ("F#7 moves toward G7.", ["relationship:deceptive:1:2"], [], ["chord_provenance"]),
        ("V7 moves toward I.", ["relationship:deceptive:1:2"], [], []),
        ("Imaj9 moves toward V7.", ["relationship:deceptive:1:2"], [], ["figure_provenance"]),
        (
            "Use V99 instead of I.",
            ["relationship:deceptive:1:2"],
            [],
            ["figure_provenance"],
        ),
        ("I think V7 works.", ["relationship:deceptive:1:2"], [], []),
        ("bVII moves toward I.", ["relationship:deceptive:1:2"], [], ["figure_provenance"]),
        ("The change is supported.", ["relationship:deceptive:1:2"], [], []),
        ("The change is supported.", ["invented"], [], ["fact_coverage"]),
        ("The change feels sad.", ["relationship:deceptive:1:2"], [], ["objective_emotion"]),
        ("It makes everyone feel sad.", ["relationship:deceptive:1:2"], [], ["objective_emotion"]),
        (
            "C objectively evokes sadness.",
            ["relationship:deceptive:1:2"],
            [],
            ["objective_emotion"],
        ),
        (
            "C, without doubt, makes every listener sad.",
            ["relationship:deceptive:1:2"],
            [],
            ["objective_emotion"],
        ),
        ("The change may feel sad.", ["relationship:deceptive:1:2"], [], []),
        (
            "It may feel tense. The change is sad.",
            ["relationship:deceptive:1:2"],
            [],
            ["objective_emotion"],
        ),
        ("This song uses C.", ["relationship:deceptive:1:2"], [], ["song_provenance"]),
        ("This song uses C.", ["example:abc"], [], []),
        ("The song key is C major.", ["relationship:deceptive:1:2"], [], []),
        ("The Authentic Cadence follows C.", ["relationship:deceptive:1:2"], [], []),
        ("Let It Be uses C.", ["relationship:deceptive:1:2"], [], ["song_provenance"]),
        ("Yesterday uses C.", ["relationship:deceptive:1:2"], [], ["song_provenance"]),
        ("A deceptive cadence occurs.", ["relationship:deceptive:1:2"], ["deceptive"], []),
        ("A galactic cadence occurs.", ["relationship:deceptive:1:2"], [], ["theory_registry"]),
        ("This is a galactic resolution.", ["relationship:deceptive:1:2"], [], ["theory_registry"]),
        (
            "The transition is a borrowed dominant.",
            ["relationship:deceptive:1:2"],
            [],
            ["theory_registry"],
        ),
        ("This is a cosmic modulation.", ["relationship:deceptive:1:2"], [], ["theory_registry"]),
        (
            "The transition is supported.",
            ["relationship:deceptive:1:2"],
            ["galactic"],
            ["theory_registry"],
        ),
        (
            "The transition is supported.",
            ["relationship:galactic:1:2"],
            [],
            ["fact_coverage", "theory_registry"],
        ),
    ],
)
def test_each_grounding_rule(text, facts, labels, expected):
    claim = Claim(text=text, fact_ids=facts, theory_labels=labels)
    assert [
        issue.rsplit(":", 1)[-1] for issue in validate_claims([claim], FACTS, TOOLS)
    ] == expected


def test_draft_rejects_one_invalid_claim_among_valid_ones():
    draft = ExplanationDraft(
        claims=[
            Claim(text="C moves toward G7.", fact_ids=["relationship:deceptive:1:2"]),
            Claim(text="Add F#7.", fact_ids=["relationship:deceptive:1:2"]),
        ]
    )
    with pytest.raises(ValueError, match="chord_provenance"):
        validate_draft(draft, FACTS, TOOLS)


def test_tool_symbols_cannot_be_smuggled_through_fact_pool():
    claim = Claim(text="F#7 resolves.", fact_ids=["relationship:deceptive:1:2"])
    facts = {**FACTS, "F#7": {"subject": "F#7"}}
    assert "claim:0:chord_provenance" in validate_claims([claim], facts, TOOLS)


def test_unknown_chord_root_is_rejected():
    claim = Claim(text="Add H7 before C.", fact_ids=["relationship:deceptive:1:2"])
    assert "claim:0:chord_provenance" in validate_claims([claim], FACTS, TOOLS)
