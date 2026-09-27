"""F72 grounding rules: passing and rejecting examples for every rule."""

import pytest

from app.ai.state import Claim, ExplanationDraft
from app.ai.validators import _unsupported_theory_phrase, validate_claims, validate_draft
from app.theory.relationships_v2 import RULES

FACTS = {
    "relationship:deceptive:1:2": {"tool": "analyze_progression"},
    "example:abc": {"tool": "get_examples", "source": "corpus"},
}
TOOLS = {
    "analyze_progression": {
        "chords": [
            {"symbol": "C", "raw_symbol": "C"},
            {"symbol": "G", "raw_symbol": "G"},
            {"symbol": "G7", "raw_symbol": "G7"},
        ],
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
        ("A minor third separates the roots.", ["relationship:deceptive:1:2"], [], []),
        ("A minor plagal cadence follows.", ["relationship:deceptive:1:2"], [], []),
        ("A major tonic closes the phrase.", ["relationship:deceptive:1:2"], [], []),
        ("A minor chord follows C.", ["relationship:deceptive:1:2"], [], ["chord_provenance"]),
        ("F#7 moves toward G7.", ["relationship:deceptive:1:2"], [], ["chord_provenance"]),
        ("Add H before C.", ["relationship:deceptive:1:2"], [], ["chord_provenance"]),
        ("The Q chord comes next.", ["relationship:deceptive:1:2"], [], ["chord_provenance"]),
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
            "C may feel sad, but G is objectively sad.",
            ["relationship:deceptive:1:2"],
            [],
            ["objective_emotion"],
        ),
        (
            "C may feel sad while G is objectively sad.",
            ["relationship:deceptive:1:2"],
            [],
            ["objective_emotion"],
        ),
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
        ("Let It Be uses C.", ["example:abc"], [], ["song_provenance"]),
        ("Yesterday uses C.", ["relationship:deceptive:1:2"], [], ["song_provenance"]),
        ("Yesterday is in C.", ["relationship:deceptive:1:2"], [], ["song_provenance"]),
        ("A deceptive cadence occurs.", ["relationship:deceptive:1:2"], ["deceptive"], []),
        ("A galactic cadence occurs.", ["relationship:deceptive:1:2"], [], ["theory_registry"]),
        ("A stellar cadence occurs.", ["relationship:deceptive:1:2"], [], ["theory_registry"]),
        ("This is a galactic resolution.", ["relationship:deceptive:1:2"], [], ["theory_registry"]),
        ("This is galactic resolution.", ["relationship:deceptive:1:2"], [], ["theory_registry"]),
        ("This is a minor third.", ["relationship:deceptive:1:2"], [], []),
        ("The chords form a smooth progression.", ["relationship:deceptive:1:2"], [], []),
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


def test_registered_relationship_templates_are_not_rejected_as_invented_labels():
    for rule in RULES:
        assert not _unsupported_theory_phrase(rule.fact_template), rule.id
        assert not _unsupported_theory_phrase(rule.technical_template), rule.id
    assert not _unsupported_theory_phrase("The prior dominant resolves.")


def test_named_song_must_match_the_cited_example_row():
    claim = Claim(text="Let It Be uses C.", fact_ids=["example:abc"])
    unrelated = {"example:abc": {"tool": "get_examples", "subject": "unrelated-song-123"}}
    assert "claim:0:song_provenance" in validate_claims([claim], unrelated, TOOLS)
    matching = {"example:abc": {"tool": "get_examples", "subject": "Let It Be"}}
    assert validate_claims([claim], matching, TOOLS) == []
