from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories import HarmonicRepository
from app.ingestion.chordonomicon import load_chordonomicon_sample
from app.services.transition_graph import ProgressionTransitionInput, aggregate_transitions
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
) -> CorpusIngestionReport:
    ingestion = load_chordonomicon_sample(sample_path, limit=limit)
    repository = HarmonicRepository(session)
    transition_inputs: list[ProgressionTransitionInput] = []
    confidence_values: list[float] = []
    progressions_persisted = 0

    for row in ingestion.rows:
        roman = analyze_progression(row.normalized_progression.raw_input, key=row.key)
        confidence_values.append(roman.confidence)
        absolute_chords = [
            chord.symbol for chord in row.normalized_progression.chords
        ]

        for chord in row.normalized_progression.chords:
            repository.upsert_chord(chord)

        if row.source_song_id:
            repository.upsert_song(
                source_id=row.source_song_id,
                title=row.title,
                artist=row.artist,
                spotify_id=row.spotify_id,
                genre=row.genre,
                release_date=row.release_date,
            )

        progression = repository.insert_progression(
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
        for index, absolute_chord in enumerate(absolute_chords):
            repository.insert_progression_chord(
                progression_id=progression.id,
                position=index,
                absolute_chord=absolute_chord,
                roman_chord=(
                    roman.roman_chords[index]
                    if index < len(roman.roman_chords)
                    else None
                ),
            )

        transition_inputs.append(
            ProgressionTransitionInput(
                roman_chords=roman.roman_chords,
                mode_context=roman.mode,
                genre=row.genre,
                subgenre=row.subgenre,
                section=row.section,
                decade=_release_decade(row.release_date),
            )
        )
        progressions_persisted += 1

    transitions = aggregate_transitions(transition_inputs)
    for transition in transitions:
        repository.insert_transition(transition)

    session.commit()
    metrics = {
        "rows_processed": ingestion.rows_processed,
        "progressions_loaded": ingestion.progressions_loaded,
        "progressions_persisted": progressions_persisted,
        "progression_parse_success_rate": (
            ingestion.progression_success_count / ingestion.progressions_loaded
            if ingestion.progressions_loaded
            else 0.0
        ),
        "chord_parse_success_rate": ingestion.chord_parse_success_rate,
        "roman_confidence_distribution": _confidence_distribution(confidence_values),
        "transition_records_persisted": len(transitions),
        "warning_counts": dict(ingestion.warning_counts),
        "top_unparseable_symbols": [
            [symbol, count] for symbol, count in ingestion.top_failures
        ],
    }

    return CorpusIngestionReport(
        rows_processed=ingestion.rows_processed,
        progressions_persisted=progressions_persisted,
        transitions_persisted=len(transitions),
        metrics=metrics,
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
