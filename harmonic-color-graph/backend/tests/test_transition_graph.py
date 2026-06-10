from app.services.transition_graph import (
    ProgressionTransitionInput,
    aggregate_transitions,
    extract_transition_edges,
)


def test_extract_transition_edges_from_roman_progression():
    edges = extract_transition_edges(["I", "V", "vi", "IV"], mode_context="major")

    assert [(edge.from_roman, edge.to_roman) for edge in edges] == [
        ("I", "V"),
        ("V", "vi"),
        ("vi", "IV"),
    ]


def test_aggregate_transitions_counts_and_normalizes_probabilities():
    transitions = aggregate_transitions(
        [
            ProgressionTransitionInput(roman_chords=["I", "V", "vi", "IV"]),
            ProgressionTransitionInput(roman_chords=["I", "V", "vi", "IV"]),
            ProgressionTransitionInput(roman_chords=["I", "V", "I"]),
        ]
    )
    by_pair = {
        (transition.from_roman, transition.to_roman): transition
        for transition in transitions
        if transition.genre == "all" and transition.section == "all"
    }

    assert by_pair[("I", "V")].count == 3
    assert by_pair[("I", "V")].probability == 1.0
    assert by_pair[("V", "vi")].count == 2
    assert by_pair[("V", "vi")].probability == 2 / 3
    assert by_pair[("V", "I")].count == 1
    assert by_pair[("V", "I")].probability == 1 / 3
    assert "deceptive cadence" in by_pair[("V", "vi")].relationship_labels


def test_aggregate_transitions_includes_contextual_counts():
    transitions = aggregate_transitions(
        [
            ProgressionTransitionInput(
                roman_chords=["I", "V", "vi"],
                genre="pop",
                section="chorus",
            ),
            ProgressionTransitionInput(
                roman_chords=["I", "IV"],
                genre="rock",
                section="verse",
            ),
        ]
    )

    pop_edges = [
        transition
        for transition in transitions
        if transition.genre == "pop" and transition.section == "chorus"
    ]

    assert [(edge.from_roman, edge.to_roman) for edge in pop_edges] == [
        ("I", "V"),
        ("V", "vi"),
    ]
    assert all(edge.probability == 1.0 for edge in pop_edges)

