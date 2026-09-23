"""Reproduces and fixes the transition lookup bug from docs/roadmap-v2.md §2.2.

Five fixture progressions, all sharing a genre=pop/section=chorus transition
from "vi", but recorded under different subgenre/decade combinations. The v1
bug keyed contextual rows by (genre, subgenre, section, decade) together, so
each distinct subgenre/decade combination became its own normalized bucket -
querying genre=pop/section=chorus then returned one "IV" candidate per
bucket (duplicates, each at probability 1.0) instead of one candidate
normalized across all matching rows (feature-specs/v2-implementation-plan.md,
F04).
"""

from app.services.transition_graph import ProgressionTransitionInput, aggregate_transitions
from app.services.transition_lookup import get_transition_stats

FIXTURE_PROGRESSIONS = [
    ProgressionTransitionInput(
        roman_chords=["I", "V", "vi", "IV"],
        genre="pop",
        subgenre="dance-pop",
        section="chorus",
        decade=2010,
    ),
    ProgressionTransitionInput(
        roman_chords=["I", "V", "vi", "IV"],
        genre="pop",
        subgenre="synth-pop",
        section="chorus",
        decade=1980,
    ),
    ProgressionTransitionInput(
        roman_chords=["I", "V", "vi", "IV"],
        genre="pop",
        subgenre="teen-pop",
        section="chorus",
        decade=2000,
    ),
    ProgressionTransitionInput(
        roman_chords=["I", "V", "vi", "ii"],
        genre="pop",
        subgenre="power-pop",
        section="chorus",
        decade=1990,
    ),
    ProgressionTransitionInput(
        roman_chords=["I", "V", "vi", "iii"],
        genre="rock",
        section="bridge",
        decade=2005,
    ),
]


def test_genre_section_query_has_no_duplicate_candidates_and_sums_to_one():
    transitions = aggregate_transitions(FIXTURE_PROGRESSIONS)

    stats = get_transition_stats("vi", transitions, genre="pop", section="chorus")

    chords = [candidate.chord for candidate in stats.next]
    assert len(chords) == len(set(chords)), f"duplicate candidates: {chords}"

    total_probability = sum(candidate.probability for candidate in stats.next)
    assert abs(total_probability - 1.0) < 1e-9

    by_chord = {candidate.chord: candidate for candidate in stats.next}
    assert by_chord["IV"].count == 3
    assert by_chord["IV"].probability == 3 / 4
    assert by_chord["ii"].count == 1
    assert by_chord["ii"].probability == 1 / 4
    assert "iii" not in by_chord, "rock/bridge data must not leak into a pop/chorus query"


def test_unfiltered_query_uses_only_the_global_bucket_and_sums_to_one():
    transitions = aggregate_transitions(FIXTURE_PROGRESSIONS)

    stats = get_transition_stats("vi", transitions)

    chords = [candidate.chord for candidate in stats.next]
    assert len(chords) == len(set(chords)), f"duplicate candidates: {chords}"

    total_probability = sum(candidate.probability for candidate in stats.next)
    assert abs(total_probability - 1.0) < 1e-9

    by_chord = {candidate.chord: candidate for candidate in stats.next}
    assert by_chord["IV"].count == 3
    assert by_chord["ii"].count == 1
    assert by_chord["iii"].count == 1


def test_mode_is_part_of_the_lookup_key():
    transitions = aggregate_transitions(
        [
            ProgressionTransitionInput(roman_chords=["V", "I"], mode_context="major"),
            ProgressionTransitionInput(roman_chords=["V", "I"], mode_context="major"),
            ProgressionTransitionInput(roman_chords=["V", "i"], mode_context="minor"),
        ]
    )

    major_stats = get_transition_stats("V", transitions, mode="major")
    minor_stats = get_transition_stats("V", transitions, mode="minor")

    assert [c.chord for c in major_stats.next] == ["I"]
    assert major_stats.next[0].count == 2
    assert [c.chord for c in minor_stats.next] == ["i"]
    assert minor_stats.next[0].count == 1
