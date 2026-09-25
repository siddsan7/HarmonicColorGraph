"""F40 `voice_leading` stage: materializes `VOICE_LEADS_TO` edges for the
top absolute chord transitions, using music theory (not corpus statistics)
to compute the minimal-motion voicing pair between each source and target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pipeline.manifest import INDEX_OVERHEAD_FACTOR

# Bounds storage: `abs_transitions.parquet` can carry tens of thousands of
# distinct global chord pairs, but every chord that appears as a source only
# needs its handful of most common destinations annotated with voice-leading
# metrics. Mirrors the "top-N evidence per key" pattern already used by the
# F26 examples and F30 n-gram stages.
TOP_TARGETS_PER_SOURCE = 5

VOICE_LEADS_SCHEMA_TYPES = {
    # column -> (postgres type, estimated bytes for the budget estimator)
    "from_chord": ("text", 12),
    "to_chord": ("text", 12),
    "total_motion": ("int", 4),
    "max_voice_motion": ("int", 4),
    "common_tones": ("int", 4),
    "bass_motion": ("int", 4),
    "parallel_perfects": ("int", 4),
    "parsimonious": ("text", 4),
}


@dataclass
class VoiceLeadingSummary:
    rows_written: int = 0
    pairs_considered: int = 0
    unparseable_chords: list[str] = field(default_factory=list)
    budget_estimate_mb: float = 0.0


def _estimate_table_mb(row_count: int) -> float:
    bytes_per_row = sum(size for _, size in VOICE_LEADS_SCHEMA_TYPES.values())
    return row_count * bytes_per_row * INDEX_OVERHEAD_FACTOR / (1024 * 1024)


def _to_symbol(chord_label: str) -> str:
    """`root:quality[/bass]` node-label form -> a `normalize_chord`-ready symbol."""
    return chord_label.replace(":", "", 1)


def run_voice_leading(
    abs_transitions_path: str | Path,
    output_path: str | Path,
    top_per_source: int = TOP_TARGETS_PER_SOURCE,
) -> VoiceLeadingSummary:
    import polars as pl

    from app.theory.voice_leading import transition_metrics, voice_lead

    frame = pl.read_parquet(abs_transitions_path)
    summary = VoiceLeadingSummary()

    taken_per_source: dict[str, int] = {}
    rows: list[dict] = []
    unparseable: set[str] = set()
    for row in frame.sort("count", descending=True).iter_rows(named=True):
        from_chord, to_chord = row["from_chord"], row["to_chord"]
        taken = taken_per_source.get(from_chord, 0)
        if taken >= top_per_source:
            continue
        summary.pairs_considered += 1
        from_symbol, to_symbol = _to_symbol(from_chord), _to_symbol(to_chord)
        try:
            source_voicing, target_voicing = voice_lead([from_symbol, to_symbol])
            metrics = transition_metrics(source_voicing, target_voicing, from_symbol, to_symbol)
        except ValueError:
            unparseable.update(
                symbol for symbol in (from_chord, to_chord) if symbol not in unparseable
            )
            continue
        taken_per_source[from_chord] = taken + 1
        rows.append(
            {
                "from_chord": from_chord,
                "to_chord": to_chord,
                "total_motion": metrics.total_motion,
                "max_voice_motion": metrics.max_voice_motion,
                "common_tones": metrics.common_tones,
                "bass_motion": metrics.bass_motion,
                "parallel_perfects": metrics.parallel_perfects,
                "parsimonious": metrics.parsimonious,
            }
        )

    summary.rows_written = len(rows)
    summary.unparseable_chords = sorted(unparseable)
    summary.budget_estimate_mb = _estimate_table_mb(summary.rows_written)

    schema = {
        "from_chord": pl.Utf8,
        "to_chord": pl.Utf8,
        "total_motion": pl.Int64,
        "max_voice_motion": pl.Int64,
        "common_tones": pl.Int64,
        "bass_motion": pl.Int64,
        "parallel_perfects": pl.Int64,
        "parsimonious": pl.Utf8,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows, schema=schema).write_parquet(output_path)

    return summary
