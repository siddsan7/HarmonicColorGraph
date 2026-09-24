"""F22 `aggregate` stage: TRANSITIONS_TO counts per context, FUNCTIONS_AS
(chord -> token per mode), and ABS_TRANSITIONS_TO (global, absolute chords).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.manifest import INDEX_OVERHEAD_FACTOR
from pipeline.stages._context import MIN_CONTEXT_OBSERVATIONS, context_keys

MIN_CONTEXT_TRANSITIONS = MIN_CONTEXT_OBSERVATIONS
MIN_ABS_TRANSITION_COUNT = 20

TRANSITIONS_SCHEMA_TYPES = {
    # column -> (postgres type, estimated bytes for the budget estimator)
    "context": ("text", 24),
    "from_token": ("text", 12),
    "to_token": ("text", 12),
    "count": ("int", 4),
    "prob": ("real", 4),
    "pmi": ("real", 4),
    "support": ("int", 4),
}
FUNCTIONS_SCHEMA_TYPES = {
    "chord": ("text", 12),
    "mode": ("text", 6),
    "token": ("text", 12),
    "count": ("int", 4),
}
ABS_TRANSITIONS_SCHEMA_TYPES = {
    "from_chord": ("text", 12),
    "to_chord": ("text", 12),
    "count": ("int", 4),
}


@dataclass
class AggregateSummary:
    contexts_kept: list[str] = field(default_factory=list)
    contexts_dropped_small: list[str] = field(default_factory=list)
    transitions_rows: int = 0
    functions_rows: int = 0
    abs_transitions_rows: int = 0
    budget_estimate_mb: dict[str, float] = field(default_factory=dict)


def _estimate_table_mb(row_count: int, columns: dict[str, tuple[str, int]]) -> float:
    bytes_per_row = sum(size for _, size in columns.values())
    total_bytes = row_count * bytes_per_row * INDEX_OVERHEAD_FACTOR
    return total_bytes / (1024 * 1024)


def run_aggregate(
    sections_path: str | Path,
    output_dir: str | Path,
    min_context_transitions: int = MIN_CONTEXT_TRANSITIONS,
) -> AggregateSummary:
    import polars as pl

    frame = pl.read_parquet(sections_path)

    # context -> (from, to) -> count
    bigram_counts: dict[str, dict[tuple[str, str], int]] = defaultdict(lambda: defaultdict(int))
    # context -> from -> total outgoing bigrams (the P(to|from) denominator)
    from_marginal: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # context -> to -> total incoming bigrams (the PMI marginal for `to`)
    to_marginal: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # context -> (from, to) -> distinct song_index set, for `support`
    support: dict[str, dict[tuple[str, str], set[int]]] = defaultdict(lambda: defaultdict(set))

    function_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    abs_bigram_counts: dict[tuple[str, str], int] = defaultdict(int)

    for row in frame.select(
        "song_index", "genre", "section", "decade", "tokens", "chords"
    ).iter_rows(named=True):
        tokens: list[str] = row["tokens"]
        chords: list[str] = row["chords"]
        song_index: int = row["song_index"]
        contexts = context_keys(row["genre"], row["section"], row["decade"])

        for token, chord in zip(tokens, chords, strict=True):
            mode = "major" if token.startswith("M:") else "minor"
            function_counts[(chord, mode, token)] += 1

        for a, b in zip(chords, chords[1:], strict=False):
            abs_bigram_counts[(a, b)] += 1

        for a, b in zip(tokens, tokens[1:], strict=False):
            for ctx in contexts:
                bigram_counts[ctx][(a, b)] += 1
                from_marginal[ctx][a] += 1
                to_marginal[ctx][b] += 1
                support[ctx][(a, b)].add(song_index)

    summary = AggregateSummary()
    transition_rows: list[dict] = []
    for ctx, pairs in bigram_counts.items():
        total = sum(pairs.values())
        if ctx != "global" and total < min_context_transitions:
            summary.contexts_dropped_small.append(ctx)
            continue
        summary.contexts_kept.append(ctx)
        for (from_token, to_token), count in pairs.items():
            prob = count / from_marginal[ctx][from_token]
            pmi = math.log(
                (count * total) / (from_marginal[ctx][from_token] * to_marginal[ctx][to_token])
            )
            transition_rows.append(
                {
                    "context": ctx,
                    "from_token": from_token,
                    "to_token": to_token,
                    "count": count,
                    "prob": prob,
                    "pmi": pmi,
                    "support": len(support[ctx][(from_token, to_token)]),
                }
            )
    summary.transitions_rows = len(transition_rows)

    function_rows = [
        {"chord": chord, "mode": mode, "token": token, "count": count}
        for (chord, mode, token), count in function_counts.items()
    ]
    summary.functions_rows = len(function_rows)

    abs_transition_rows = [
        {"from_chord": a, "to_chord": b, "count": count}
        for (a, b), count in abs_bigram_counts.items()
        if count >= MIN_ABS_TRANSITION_COUNT
    ]
    summary.abs_transitions_rows = len(abs_transition_rows)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    transitions_schema = {
        "context": pl.Utf8,
        "from_token": pl.Utf8,
        "to_token": pl.Utf8,
        "count": pl.Int64,
        "prob": pl.Float64,
        "pmi": pl.Float64,
        "support": pl.Int64,
    }
    functions_schema = {"chord": pl.Utf8, "mode": pl.Utf8, "token": pl.Utf8, "count": pl.Int64}
    abs_transitions_schema = {"from_chord": pl.Utf8, "to_chord": pl.Utf8, "count": pl.Int64}
    pl.DataFrame(transition_rows, schema=transitions_schema).write_parquet(
        output_dir / "transitions.parquet"
    )
    pl.DataFrame(function_rows, schema=functions_schema).write_parquet(
        output_dir / "functions.parquet"
    )
    pl.DataFrame(abs_transition_rows, schema=abs_transitions_schema).write_parquet(
        output_dir / "abs_transitions.parquet"
    )

    summary.budget_estimate_mb = {
        "transitions": _estimate_table_mb(summary.transitions_rows, TRANSITIONS_SCHEMA_TYPES),
        "functions": _estimate_table_mb(summary.functions_rows, FUNCTIONS_SCHEMA_TYPES),
        "abs_transitions": _estimate_table_mb(
            summary.abs_transitions_rows, ABS_TRANSITIONS_SCHEMA_TYPES
        ),
    }
    summary.budget_estimate_mb["total"] = sum(summary.budget_estimate_mb.values())

    return summary
