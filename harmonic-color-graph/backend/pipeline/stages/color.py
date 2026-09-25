"""F41 `color` stage: corpus percentile norms for the measurable color axes
(`app/color/features.py`) over a bounded, seeded sample of sections.

Bounded and seeded for the same reason as `corpus_report.py`'s sampling: this
stage re-derives a `CanonicalChord`/`RomanToken` pair per sampled chord (the
`analyze` stage already paid that cost once, across a worker pool, to write
`sections.parquet`), and percentile breakpoints don't need every row in the
corpus to be stable -- only a large-enough, unbiased sample. Redoing the full
corpus serially here just to compute norms would be slow and wasteful.

When `ngrams_path` points at a real `ngrams` stage artifact (it runs earlier
in `STAGE_ORDER`), `surprise` and `resolution`'s forward-looking term are
computed against a real (in-memory, offline) predictor built from that
artifact -- no database involved. Without it, those two axes fall back to
their predictor-free definitions (`resolution` still uses F13 cadence
strength; `surprise` stays `None` and is excluded from its norms).
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.color.features import AXES
from pipeline.manifest import INDEX_OVERHEAD_FACTOR

# Enough sampled sections for stable percentile breakpoints without paying
# to re-run Roman/key analysis over the full multi-million-row corpus.
DEFAULT_SAMPLE_ROWS = 20_000
DEFAULT_SEED = 20260925

_SUBJECT_TYPES = ("chord", "transition")

NORMS_SCHEMA_TYPES = {
    # column -> (postgres type, estimated bytes for the budget estimator)
    "axis": ("text", 16),
    "subject_type": ("text", 12),
    "count": ("int", 4),
    "p05": ("float8", 8),
    "p25": ("float8", 8),
    "p50": ("float8", 8),
    "p75": ("float8", 8),
    "p95": ("float8", 8),
    "mean": ("float8", 8),
    "std": ("float8", 8),
}


@dataclass
class ColorSummary:
    rows_sampled: int = 0
    positions_scored: int = 0
    unscored_sections: int = 0
    axes_written: int = 0
    used_predictor: bool = False
    budget_estimate_mb: float = 0.0
    stds: dict[str, float] = field(default_factory=dict)


def _estimate_table_mb(row_count: int) -> float:
    bytes_per_row = sum(size for _, size in NORMS_SCHEMA_TYPES.values())
    return row_count * bytes_per_row * INDEX_OVERHEAD_FACTOR / (1024 * 1024)


def _to_symbol(chord_label: str) -> str:
    """`root:quality[/bass]` node-label form (as `sections.parquet`'s
    `chords` column stores it) -> a `normalize_chord`-ready symbol. Same
    conversion, for the same reason, as
    `pipeline/stages/voice_leading.py`'s helper of the same name."""
    return chord_label.replace(":", "", 1)


def run_color(
    sections_path: str | Path,
    ngrams_path: str | Path,
    output_path: str | Path,
    *,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
    seed: int = DEFAULT_SEED,
) -> ColorSummary:
    import polars as pl

    from app.color.features import compute_chord_color
    from app.predict.ngram import InMemoryNgramStore, KNPredictor
    from app.theory.roman import analyze_v2

    predictor = None
    ngrams_file = Path(ngrams_path)
    if ngrams_file.is_file():
        predictor = KNPredictor(store=InMemoryNgramStore.from_parquet(str(ngrams_file)))

    frame = pl.read_parquet(sections_path)
    total_rows = frame.height
    rng = random.Random(seed)
    take = min(total_rows, sample_rows)
    indices = sorted(rng.sample(range(total_rows), k=take)) if take else []
    sampled = frame[indices] if indices else frame.head(0)

    summary = ColorSummary(rows_sampled=sampled.height, used_predictor=predictor is not None)
    samples: dict[tuple[str, str], list[float]] = defaultdict(list)

    for row in sampled.iter_rows(named=True):
        chord_symbols = row["chords"]
        local_key = row["local_key"]
        if not chord_symbols or not local_key:
            summary.unscored_sections += 1
            continue
        try:
            analysis = analyze_v2([_to_symbol(c) for c in chord_symbols], local_key)
        except ValueError:
            summary.unscored_sections += 1
            continue

        history: list[str] = []
        for index, (chord, token) in enumerate(zip(analysis.chords, analysis.tokens, strict=True)):
            previous_chord = analysis.chords[index - 1] if index else None
            previous_token = analysis.tokens[index - 1] if index else None
            subject_type = "chord" if index == 0 else "transition"
            raw = compute_chord_color(
                chord,
                token,
                local_key,
                previous_chord=previous_chord,
                previous_token=previous_token,
                predictor=predictor,
                history=tuple(history),
                genre=row["genre"],
                section=row["section"],
            )
            summary.positions_scored += 1
            for axis in AXES:
                value = getattr(raw, axis)
                if value is not None:
                    samples[(axis, subject_type)].append(value)
            history.append(token.core)

    output_rows: list[dict] = []
    for axis in AXES:
        for subject_type in _SUBJECT_TYPES:
            values = sorted(samples.get((axis, subject_type), []))
            if not values:
                continue
            series = pl.Series(values)
            output_rows.append(
                {
                    "axis": axis,
                    "subject_type": subject_type,
                    "count": len(values),
                    "p05": series.quantile(0.05, interpolation="linear"),
                    "p25": series.quantile(0.25, interpolation="linear"),
                    "p50": series.quantile(0.50, interpolation="linear"),
                    "p75": series.quantile(0.75, interpolation="linear"),
                    "p95": series.quantile(0.95, interpolation="linear"),
                    "mean": series.mean(),
                    "std": series.std() or 0.0,
                }
            )
            if subject_type == "transition":
                summary.stds[axis] = series.std() or 0.0

    summary.axes_written = len(output_rows)
    summary.budget_estimate_mb = _estimate_table_mb(summary.axes_written)

    schema = {
        "axis": pl.Utf8,
        "subject_type": pl.Utf8,
        "count": pl.Int64,
        "p05": pl.Float64,
        "p25": pl.Float64,
        "p50": pl.Float64,
        "p75": pl.Float64,
        "p95": pl.Float64,
        "mean": pl.Float64,
        "std": pl.Float64,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(output_rows, schema=schema).write_parquet(output_path)

    return summary
