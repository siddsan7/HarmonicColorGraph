from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ingestion.chordonomicon import iter_chordonomicon_rows
from app.schemas import TransitionRecord
from app.services.transition_graph import (
    ContextKey,
    ProgressionTransitionInput,
    TransitionKey,
)
from app.theory.relationships import label_transition
from app.theory.roman_analysis import analyze_progression


@dataclass(frozen=True)
class CorpusIngestionReport:
    rows_processed: int
    progressions_persisted: int
    transitions_persisted: int
    metrics: dict[str, Any]


def ingest_chordonomicon_corpus(
    sample_path: str | Path,
    *,
    session: Session,
    limit: int | None = None,
    batch_size: int = 1000,
    transition_only: bool = False,
) -> CorpusIngestionReport:
    from app.models.harmony import (
        ChordModel,
        ProgressionModel,
        SongModel,
        TransitionModel,
    )

    batch_size = max(1, batch_size)
    transition_counts: Counter[TransitionKey] = Counter()
    confidence_values: list[float] = []
    warning_counts: Counter[str] = Counter()
    skipped_tokens: Counter[str] = Counter()
    total_tokens = 0
    parsed_tokens = 0
    progression_success_count = 0
    rows_processed = 0
    progressions_persisted = 0
    seen_chords: set[str] = set()
    seen_song_ids: set[str] = set()
    progression_batch: list[tuple[Any, list[str], list[str]]] = []

    for row in iter_chordonomicon_rows(sample_path, limit=limit):
        normalized = row.normalized_progression
        rows_processed += 1
        total_tokens += len(normalized.chords) + len(normalized.skipped_tokens)
        parsed_tokens += len(normalized.chords)
        if normalized.success:
            progression_success_count += 1
        for warning in normalized.warnings:
            warning_counts[warning.code] += 1
        for token in normalized.skipped_tokens:
            skipped_tokens[token] += 1

        roman = analyze_progression(row.normalized_progression.raw_input, key=row.key)
        confidence_values.append(roman.confidence)
        absolute_chords = [
            chord.symbol for chord in row.normalized_progression.chords
        ]

        for chord in row.normalized_progression.chords:
            if chord.symbol in seen_chords:
                continue
            session.add(
                ChordModel(
                    symbol=chord.symbol,
                    root=chord.root,
                    quality=chord.quality,
                    pitch_classes=chord.pitch_classes,
                    intervals=chord.intervals,
                )
            )
            seen_chords.add(chord.symbol)

        if (
            not transition_only
            and row.source_song_id
            and row.source_song_id not in seen_song_ids
        ):
            session.add(
                SongModel(
                    source_id=row.source_song_id,
                    title=row.title,
                    artist=row.artist,
                    spotify_id=row.spotify_id,
                    genre=row.genre,
                    release_date=row.release_date,
                )
            )
            seen_song_ids.add(row.source_song_id)

        if not transition_only:
            progression = ProgressionModel(
                source=row.source,
                source_song_id=row.source_song_id,
                key=roman.key,
                mode=roman.mode,
                genre=row.genre,
                subgenre=row.subgenre,
                section=row.section,
                absolute_chords=absolute_chords,
                roman_chords=roman.roman_chords,
                analysis_confidence=roman.confidence,
                parse_warnings=[
                    f"{warning.code}:{warning.raw_value or ''}"
                    for warning in row.normalized_progression.warnings + roman.warnings
                ],
            )
            session.add(progression)
            progression_batch.append(
                (progression, absolute_chords, roman.roman_chords)
            )

        _count_transitions(
            transition_counts,
            ProgressionTransitionInput(
                roman_chords=roman.roman_chords,
                mode_context=roman.mode,
                genre=row.genre,
                subgenre=row.subgenre,
                section=row.section,
                decade=_release_decade(row.release_date),
            ),
        )
        if not transition_only:
            progressions_persisted += 1

        if not transition_only and len(progression_batch) >= batch_size:
            _flush_progression_batch(session, progression_batch)

    if not transition_only:
        _flush_progression_batch(session, progression_batch)

    transitions = _build_transition_records(transition_counts)
    session.add_all(
        TransitionModel(
            from_roman=transition.from_roman,
            to_roman=transition.to_roman,
            mode_context=transition.mode_context,
            genre=transition.genre,
            subgenre=transition.subgenre,
            section=transition.section,
            decade=transition.decade,
            count=transition.count,
            probability=transition.probability,
            relationship_labels=transition.relationship_labels,
        )
        for transition in transitions
    )

    session.commit()
    metrics = {
        "rows_processed": rows_processed,
        "progressions_loaded": rows_processed,
        "progressions_persisted": progressions_persisted,
        "progression_parse_success_rate": (
            progression_success_count / rows_processed
            if rows_processed
            else 0.0
        ),
        "chord_parse_success_rate": parsed_tokens / total_tokens if total_tokens else 0.0,
        "roman_confidence_distribution": _confidence_distribution(confidence_values),
        "transition_records_persisted": len(transitions),
        "warning_counts": dict(warning_counts),
        "top_unparseable_symbols": [
            [symbol, count] for symbol, count in skipped_tokens.most_common(10)
        ],
    }

    return CorpusIngestionReport(
        rows_processed=rows_processed,
        progressions_persisted=progressions_persisted,
        transitions_persisted=len(transitions),
        metrics=metrics,
    )


def _flush_progression_batch(
    session: Session,
    batch: list[tuple[Any, list[str], list[str]]],
) -> None:
    from app.models.harmony import ProgressionChordModel

    if not batch:
        return

    session.flush()
    progression_chords = []
    for progression, absolute_chords, roman_chords in batch:
        progression_chords.extend(
            ProgressionChordModel(
                progression_id=progression.id,
                position=index,
                absolute_chord=absolute_chord,
                roman_chord=(
                    roman_chords[index] if index < len(roman_chords) else None
                ),
            )
            for index, absolute_chord in enumerate(absolute_chords)
        )
    session.add_all(progression_chords)
    batch.clear()


def _count_transitions(
    counts: Counter[TransitionKey],
    progression: ProgressionTransitionInput,
) -> None:
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


def _build_transition_records(
    counts: Counter[TransitionKey],
) -> list[TransitionRecord]:
    totals_by_context: Counter[ContextKey] = Counter()
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


def _confidence_distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def _release_decade(release_date: str | None) -> int | None:
    if not release_date or len(release_date) < 4:
        return None
    try:
        year = int(release_date[:4])
    except ValueError:
        return None
    return year - (year % 10)
