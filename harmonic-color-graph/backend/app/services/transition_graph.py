from collections import Counter
from dataclasses import dataclass

from app.schemas import TransitionRecord
from app.theory.relationships import label_transition


@dataclass(frozen=True)
class ProgressionTransitionInput:
    roman_chords: list[str]
    mode_context: str = "major"
    genre: str | None = None
    subgenre: str | None = None
    section: str | None = None
    decade: int | None = None


# (from_roman, to_roman, mode_context, genre, section, decade)
TransitionKey = tuple[str, str, str, str | None, str | None, int | None]
# (from_roman, mode_context, genre, section, decade)
ContextKey = tuple[str, str, str | None, str | None, int | None]


def extract_transition_edges(
    roman_chords: list[str],
    mode_context: str = "major",
) -> list[TransitionRecord]:
    return [
        label_transition(from_roman, to_roman, mode_context)
        for from_roman, to_roman in zip(roman_chords, roman_chords[1:], strict=False)
    ]


def context_buckets(
    progression: ProgressionTransitionInput,
) -> list[tuple[str | None, str | None, int | None]]:
    """Which (genre, section, decade) buckets a progression's transitions count toward.

    Each bucket varies exactly one dimension at a time (plus the combined
    genre+section bucket) - never a composite of genre, subgenre, section,
    and decade together. That composite key was the F04 bug: two songs that
    share a genre and section but differ in subgenre or decade used to land
    in different buckets, so a genre+section query returned one
    (duplicated, over-confident) candidate per bucket instead of one
    candidate normalized across all of them. subgenre is not an aggregation
    dimension here (feature-specs/v2-implementation-plan.md, F04).
    """
    buckets: list[tuple[str | None, str | None, int | None]] = [(None, None, None)]
    if progression.genre:
        buckets.append((progression.genre, None, None))
    if progression.section:
        buckets.append((None, progression.section, None))
    if progression.decade is not None:
        buckets.append((None, None, progression.decade))
    if progression.genre and progression.section:
        buckets.append((progression.genre, progression.section, None))
    return buckets


def count_transitions(
    counts: Counter[TransitionKey], progression: ProgressionTransitionInput
) -> None:
    """Increment `counts` in place for one progression's transitions.

    Streaming-friendly: callers processing a large corpus row-by-row (see
    app.services.corpus_ingestion) can share one Counter across many calls
    instead of holding every progression in memory at once.
    """
    for from_roman, to_roman in zip(
        progression.roman_chords,
        progression.roman_chords[1:],
        strict=False,
    ):
        for genre, section, decade in context_buckets(progression):
            counts[(from_roman, to_roman, progression.mode_context, genre, section, decade)] += 1


def build_transition_records(counts: Counter[TransitionKey]) -> list[TransitionRecord]:
    """Normalize counts into probabilities, independently within each bucket.

    "Independently" is the fix: the total a count is divided by comes only
    from other rows sharing the exact same (from, mode, genre, section,
    decade) bucket, so probabilities within a bucket always sum to 1
    regardless of how many other buckets exist.
    """
    totals: Counter[ContextKey] = Counter()
    for (from_roman, _to_roman, mode_context, genre, section, decade), count in counts.items():
        totals[(from_roman, mode_context, genre, section, decade)] += count

    transitions = []
    for (from_roman, to_roman, mode_context, genre, section, decade), count in counts.items():
        base = label_transition(from_roman, to_roman, mode_context)
        total = totals[(from_roman, mode_context, genre, section, decade)]
        transitions.append(
            TransitionRecord(
                from_roman=from_roman,
                to_roman=to_roman,
                mode_context=mode_context,  # type: ignore[arg-type]
                count=count,
                probability=count / total if total else 0.0,
                genre=genre,
                section=section,
                decade=decade,
                relationship_labels=base.relationship_labels,
                short_explanation=base.short_explanation,
                technical_explanation=base.technical_explanation,
            )
        )

    return sorted(
        transitions,
        key=lambda transition: (
            transition.genre or "",
            transition.section or "",
            transition.decade or 0,
            transition.from_roman,
            -transition.count,
            transition.to_roman,
        ),
    )


def aggregate_transitions(
    progressions: list[ProgressionTransitionInput],
) -> list[TransitionRecord]:
    counts: Counter[TransitionKey] = Counter()
    for progression in progressions:
        count_transitions(counts, progression)
    return build_transition_records(counts)
