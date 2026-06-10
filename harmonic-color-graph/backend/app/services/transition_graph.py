from collections import Counter, defaultdict
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


ContextKey = tuple[str, str, str, str | None, str | None, int | None]
TransitionKey = tuple[str, str, str, str, str | None, str | None, int | None]


def extract_transition_edges(
    roman_chords: list[str],
    mode_context: str = "major",
) -> list[TransitionRecord]:
    return [
        label_transition(from_roman, to_roman, mode_context)
        for from_roman, to_roman in zip(roman_chords, roman_chords[1:])
    ]


def aggregate_transitions(
    progressions: list[ProgressionTransitionInput],
) -> list[TransitionRecord]:
    counts: Counter[TransitionKey] = Counter()

    for progression in progressions:
        for from_roman, to_roman in zip(
            progression.roman_chords,
            progression.roman_chords[1:],
        ):
            counts[
                (
                    from_roman,
                    to_roman,
                    progression.mode_context,
                    "all",
                    None,
                    "all",
                    None,
                )
            ] += 1

            if progression.genre or progression.section:
                counts[
                    (
                        from_roman,
                        to_roman,
                        progression.mode_context,
                        progression.genre or "all",
                        progression.subgenre,
                        progression.section or "all",
                        progression.decade,
                    )
                ] += 1

    totals_by_context: defaultdict[ContextKey, int] = defaultdict(int)
    for (
        from_roman,
        _to_roman,
        mode_context,
        genre,
        subgenre,
        section,
        decade,
    ), count in counts.items():
        totals_by_context[
            (from_roman, mode_context, genre, subgenre, section, decade)
        ] += count

    transitions = []
    for (
        from_roman,
        to_roman,
        mode_context,
        genre,
        subgenre,
        section,
        decade,
    ), count in counts.items():
        base = label_transition(from_roman, to_roman, mode_context)
        total = totals_by_context[
            (from_roman, mode_context, genre, subgenre, section, decade)
        ]
        transitions.append(
            TransitionRecord(
                from_roman=from_roman,
                to_roman=to_roman,
                mode_context=mode_context,  # type: ignore[arg-type]
                count=count,
                probability=count / total if total else 0.0,
                genre=genre,
                subgenre=subgenre,
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
            transition.from_roman,
            -transition.count,
            transition.to_roman,
        ),
    )
