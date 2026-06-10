import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

from app.ingestion.chordonomicon import load_chordonomicon_sample
from app.services.analysis import analyze_progression_service
from app.services.transition_graph import ProgressionTransitionInput, aggregate_transitions
from app.theory.roman_analysis import analyze_progression


def build_quality_metrics_report(sample_path: str | Path) -> dict[str, Any]:
    ingestion = load_chordonomicon_sample(sample_path)
    analyses = [
        analyze_progression(row.normalized_progression.raw_input, key=row.key)
        for row in ingestion.rows
    ]
    transition_inputs = [
        ProgressionTransitionInput(
            roman_chords=analysis.roman_chords,
            mode_context=analysis.mode,
            genre=row.genre,
            subgenre=row.subgenre,
            section=row.section,
            decade=_release_decade(row.release_date),
        )
        for row, analysis in zip(ingestion.rows, analyses)
    ]
    transitions = aggregate_transitions(transition_inputs)
    global_transitions = [
        transition
        for transition in transitions
        if transition.genre == "all" and transition.section == "all"
    ]
    labeled_transition_count = sum(
        1 for transition in transitions if transition.relationship_labels
    )
    confidence_values = [analysis.confidence for analysis in analyses]

    return {
        "rows_processed": ingestion.rows_processed,
        "chord_parse_success_rate": ingestion.chord_parse_success_rate,
        "progression_parse_success_rate": (
            ingestion.progression_success_count / ingestion.progressions_loaded
            if ingestion.progressions_loaded
            else 0.0
        ),
        "roman_confidence_distribution": _confidence_distribution(
            confidence_values
        ),
        "normalized_progression_count": ingestion.progressions_loaded,
        "transition_edge_count": sum(
            transition.count for transition in global_transitions
        ),
        "top_global_transitions": _top_transition_rows(global_transitions),
        "top_genre_conditioned_transitions": _top_transition_rows(
            [
                transition
                for transition in transitions
                if transition.genre not in {None, "all"}
            ]
        ),
        "theory_label_coverage": (
            labeled_transition_count / len(transitions) if transitions else 0.0
        ),
        "api_latency_ms": _measure_analysis_latency_ms(ingestion),
        "warning_counts": dict(ingestion.warning_counts),
        "top_unparseable_symbols": [
            [symbol, count] for symbol, count in ingestion.top_failures
        ],
    }


def save_quality_metrics_report(report: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _confidence_distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
    }


def _top_transition_rows(transitions: list) -> list[dict[str, Any]]:
    rows = sorted(
        transitions,
        key=lambda transition: (
            -transition.count,
            transition.from_roman,
            transition.to_roman,
        ),
    )[:100]
    return [
        {
            "from": transition.from_roman,
            "to": transition.to_roman,
            "count": transition.count,
            "probability": transition.probability,
            "genre": transition.genre,
            "section": transition.section,
            "relationship_labels": transition.relationship_labels,
        }
        for transition in rows
    ]


def _measure_analysis_latency_ms(ingestion) -> float:
    if not ingestion.rows:
        return 0.0
    row = ingestion.rows[0]
    start = time.perf_counter()
    analyze_progression_service(row.normalized_progression.raw_input, key=row.key)
    return (time.perf_counter() - start) * 1000


def _release_decade(release_date: str | None) -> int | None:
    if not release_date or len(release_date) < 4:
        return None
    try:
        year = int(release_date[:4])
    except ValueError:
        return None
    return year - (year % 10)

