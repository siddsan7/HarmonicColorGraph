from app.schemas import (
    NextChordsResponse,
    TransitionCandidate,
    TransitionRecord,
    TransitionStatsResponse,
)


def get_next_chords(
    progression: list[str],
    transitions: list[TransitionRecord],
    *,
    genre: str | None = None,
    section: str | None = None,
) -> NextChordsResponse:
    if not progression:
        return NextChordsResponse(input=[], candidates=[])

    stats = get_transition_stats(
        progression[-1],
        transitions,
        genre=genre,
        section=section,
    )
    return NextChordsResponse(input=progression, candidates=stats.next)


def get_transition_stats(
    from_roman: str,
    transitions: list[TransitionRecord],
    *,
    genre: str | None = None,
    section: str | None = None,
) -> TransitionStatsResponse:
    matches = _filter_transitions(
        from_roman,
        transitions,
        genre=genre,
        section=section,
    )
    response_genre = genre
    response_section = section

    if not matches and (genre is not None or section is not None):
        matches = _filter_transitions(
            from_roman,
            transitions,
            genre="all",
            section="all",
        )
        response_genre = "all"
        response_section = "all"

    candidates = [
        TransitionCandidate(
            chord=transition.to_roman,
            probability=transition.probability,
            relationship=_primary_relationship(transition),
            count=transition.count,
            relationship_labels=transition.relationship_labels,
        )
        for transition in sorted(
            matches,
            key=lambda item: (-item.probability, -item.count, item.to_roman),
        )
    ]

    return TransitionStatsResponse(
        from_roman=from_roman,
        genre=response_genre,
        section=response_section,
        next=candidates,
    )


def _filter_transitions(
    from_roman: str,
    transitions: list[TransitionRecord],
    *,
    genre: str | None,
    section: str | None,
) -> list[TransitionRecord]:
    return [
        transition
        for transition in transitions
        if transition.from_roman == from_roman
        and (genre is None or transition.genre == genre)
        and (section is None or transition.section == section)
    ]


def _primary_relationship(transition: TransitionRecord) -> str | None:
    if transition.relationship_labels:
        return transition.relationship_labels[0]
    return None
