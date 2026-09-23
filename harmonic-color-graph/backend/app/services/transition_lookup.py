from app.schemas import (
    ContextUsed,
    NextChordsResponse,
    TransitionCandidate,
    TransitionRecord,
    TransitionStatsResponse,
)

# Which bucket to try, in order, given whether genre and/or section were
# requested. Always ends at "global". A step is only attempted when its
# dimension was actually requested - e.g. a genre-only request never tries
# "section" - so the chain never guesses at a context the caller didn't ask
# for (feature-specs/v2-implementation-plan.md, F04).
_BACKOFF_CHAINS: dict[tuple[bool, bool], list[str]] = {
    (True, True): ["genre_section", "genre", "section", "global"],
    (True, False): ["genre", "global"],
    (False, True): ["section", "global"],
    (False, False): ["global"],
}


def get_next_chords(
    progression: list[str],
    transitions: list[TransitionRecord],
    *,
    mode: str = "major",
    genre: str | None = None,
    section: str | None = None,
) -> NextChordsResponse:
    if not progression:
        return NextChordsResponse(input=[], candidates=[])

    stats = get_transition_stats(
        progression[-1],
        transitions,
        mode=mode,
        genre=genre,
        section=section,
    )
    return NextChordsResponse(
        input=progression,
        candidates=stats.next,
        context_used=stats.context_used,
    )


def get_transition_stats(
    from_roman: str,
    transitions: list[TransitionRecord],
    *,
    mode: str = "major",
    genre: str | None = None,
    section: str | None = None,
) -> TransitionStatsResponse:
    chain = _BACKOFF_CHAINS[(genre is not None, section is not None)]

    tried: list[str] = []
    matches: list[TransitionRecord] = []
    resolved_genre: str | None = None
    resolved_section: str | None = None

    for context_type in chain:
        tried.append(context_type)
        matches = _filter_by_bucket(
            from_roman,
            transitions,
            mode=mode,
            context_type=context_type,
            genre=genre,
            section=section,
        )
        if matches:
            resolved_genre = genre if context_type in ("genre", "genre_section") else None
            resolved_section = section if context_type in ("section", "genre_section") else None
            break

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
        genre=resolved_genre,
        section=resolved_section,
        next=candidates,
        context_used=ContextUsed(
            mode=mode,
            genre=resolved_genre,
            section=resolved_section,
            backoff=tried,
        ),
    )


def _filter_by_bucket(
    from_roman: str,
    transitions: list[TransitionRecord],
    *,
    mode: str,
    context_type: str,
    genre: str | None,
    section: str | None,
) -> list[TransitionRecord]:
    """Rows for exactly one bucket: (from, mode) plus the named context.

    Each bucket is defined by which of genre/section are set - e.g. the
    "genre" bucket is genre=X and section=None, never a row that also
    happens to carry a section. This is what makes the buckets mutually
    exclusive and safe to normalize independently (see
    transition_graph.build_transition_records).
    """
    want_genre = genre if context_type in ("genre", "genre_section") else None
    want_section = section if context_type in ("section", "genre_section") else None

    return [
        transition
        for transition in transitions
        if transition.from_roman == from_roman
        and transition.mode_context == mode
        and transition.genre == want_genre
        and transition.section == want_section
        and transition.decade is None
    ]


def _primary_relationship(transition: TransitionRecord) -> str | None:
    if transition.relationship_labels:
        return transition.relationship_labels[0]
    return None
