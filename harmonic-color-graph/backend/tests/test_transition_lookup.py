from app.schemas import TransitionRecord
from app.services.transition_lookup import get_next_chords, get_transition_stats


def sample_transitions() -> list[TransitionRecord]:
    return [
        TransitionRecord(
            from_roman="V",
            to_roman="I",
            mode_context="major",
            genre="all",
            section="all",
            count=30,
            probability=0.6,
            relationship_labels=["authentic cadence"],
        ),
        TransitionRecord(
            from_roman="V",
            to_roman="vi",
            mode_context="major",
            genre="all",
            section="all",
            count=20,
            probability=0.4,
            relationship_labels=["deceptive cadence"],
        ),
        TransitionRecord(
            from_roman="V",
            to_roman="vi",
            mode_context="major",
            genre="pop",
            section="chorus",
            count=8,
            probability=0.8,
            relationship_labels=["deceptive cadence"],
        ),
        TransitionRecord(
            from_roman="V",
            to_roman="I",
            mode_context="major",
            genre="pop",
            section="chorus",
            count=2,
            probability=0.2,
            relationship_labels=["authentic cadence"],
        ),
    ]


def test_get_next_chords_uses_last_roman_and_filter_context():
    response = get_next_chords(
        ["I", "V"],
        sample_transitions(),
        genre="pop",
        section="chorus",
    )

    assert response.input == ["I", "V"]
    assert [candidate.chord for candidate in response.candidates] == ["vi", "I"]
    assert response.candidates[0].probability == 0.8
    assert response.candidates[0].relationship_labels == ["deceptive cadence"]


def test_get_next_chords_falls_back_to_global_context():
    response = get_next_chords(
        ["I", "V"],
        sample_transitions(),
        genre="jazz",
        section="bridge",
    )

    assert [candidate.chord for candidate in response.candidates] == ["I", "vi"]
    assert response.candidates[0].count == 30


def test_get_transition_stats_returns_ranked_candidates():
    response = get_transition_stats(
        "V",
        sample_transitions(),
        genre="all",
        section="all",
    )

    assert response.from_roman == "V"
    assert response.genre == "all"
    assert [candidate.chord for candidate in response.next] == ["I", "vi"]

