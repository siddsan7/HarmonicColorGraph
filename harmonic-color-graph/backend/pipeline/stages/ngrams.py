"""F22 `ngrams` stage: one row per (context, order, history) with raw
next-token counts and, for orders below a context's max, Kneser-Ney
continuation counts (`N1+(*h w)`: the number of distinct one-token-longer
histories ending in `h` that were followed by `w`) for backoff smoothing.

`order` follows n-gram convention: order 1 is the unigram (empty history,
0 preceding tokens), order n has n-1 preceding tokens as history. Orders
1-5 for `global`, 1-3 for every other context.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.ngram_contract import HISTORY_SEP, MAX_ORDER_GLOBAL, MAX_ORDER_OTHER
from pipeline.manifest import measured_table_mb
from pipeline.stages._context import context_keys

# Minimum `total` to keep a (context, order, history) row, by order.
# Orders 1-2 are never pruned (they're the KN backoff floor). The plan's
# literal defaults (3/5/8) came from before this stage had run against the
# real corpus; at real scale they produced a table alone worth ~270-450MB,
# blowing the F22 acceptance check's 300MB *total* Postgres budget (which
# aggregate's tables already use ~145MB of). Retuned empirically against
# the real corpus (see progress-tracker.md's F22 Completed entry) to fit
# with headroom for `patterns`. Tunable in a future pipeline/params.yaml
# (F22 lists that file; not needed until another stage also wants it).
PRUNE_MIN_TOTAL = {3: 30, 4: 48, 5: 75}

# Same idea as aggregate's context threshold (both come from
# _context.MIN_CONTEXT_OBSERVATIONS by default), but ngrams needs a
# stricter bar: each context can carry up to 5 orders' worth of history
# rows, vastly more than aggregate's one row per (from, to) pair, so a
# context that's "worth modeling" for a handful of bigram transitions
# isn't necessarily worth a full n-gram table. First calibrated to 10,000
# against the real corpus, which brought this stage itself comfortably
# under budget alone -- but combined with aggregate's and patterns' tables
# the *shared* Postgres budget (F22's 300MB check) was still 706MB.
# Raised to 50,000, which cuts kept contexts from 680 to 105 (measured
# directly: see patterns.py's own threshold, tuned the same way).
DEFAULT_MIN_CONTEXT_OBSERVATIONS = 50_000


@dataclass
class NgramsSummary:
    rows_written: int = 0
    rows_pruned: int = 0
    contexts: list[str] = field(default_factory=list)
    budget_estimate_mb: float = 0.0


def _max_order(context: str) -> int:
    return MAX_ORDER_GLOBAL if context == "global" else MAX_ORDER_OTHER


def run_ngrams(
    sections_path: str | Path,
    output_path: str | Path,
    min_context_observations: int = DEFAULT_MIN_CONTEXT_OBSERVATIONS,
    prune_min_total: dict[int, int] | None = None,
) -> NgramsSummary:
    import polars as pl

    prune_min_total = PRUNE_MIN_TOTAL if prune_min_total is None else prune_min_total
    frame = pl.read_parquet(sections_path)
    rows = list(frame.select("genre", "section", "decade", "tokens").iter_rows(named=True))

    # Pass 1: which contexts have enough bigram-level observations to be
    # worth modeling at all? Same threshold and meaning as aggregate's
    # TRANSITIONS_TO context filter -- "contexts worth modeling" means the
    # same thing everywhere. Without this, ngrams was building full n-gram
    # tables for every context that appears even once (e.g. a genre_section
    # combo seen twice), ballooning row count and the Postgres budget for
    # no signal: on the full corpus this dropped context count from 34,017
    # to roughly aggregate's ~2,955 kept contexts.
    context_totals: dict[str, int] = defaultdict(int)
    for row in rows:
        for ctx in context_keys(row["genre"], row["section"], row["decade"]):
            context_totals[ctx] += max(len(row["tokens"]) - 1, 0)
    kept_contexts = {
        ctx
        for ctx, total in context_totals.items()
        if ctx == "global" or total >= min_context_observations
    }

    # Pass 2: context -> order -> history (tuple) -> next_token -> count
    raw: dict[str, dict[int, dict[tuple[str, ...], dict[str, int]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )

    for row in rows:
        tokens: list[str] = row["tokens"]
        contexts = [
            ctx
            for ctx in context_keys(row["genre"], row["section"], row["decade"])
            if ctx in kept_contexts
        ]
        for ctx in contexts:
            max_order = _max_order(ctx)
            for order in range(1, max_order + 1):
                history_len = order - 1
                for i in range(history_len, len(tokens)):
                    history = tuple(tokens[i - history_len : i])
                    raw[ctx][order][history][tokens[i]] += 1

    output_rows: list[dict] = []
    summary = NgramsSummary(contexts=sorted(raw.keys()))
    for ctx, by_order in raw.items():
        max_order = _max_order(ctx)
        for order, histories in by_order.items():
            # Continuation counts (order < max_order only) come from the
            # UNPRUNED order+1 histories: KN continuation counts distinct
            # contexts, not frequency, so pruning the source first would
            # undercount it.
            continuations: dict[tuple[str, ...], dict[str, int]] = defaultdict(
                lambda: defaultdict(int)
            )
            if order < max_order:
                for higher_history, next_counts in by_order.get(order + 1, {}).items():
                    suffix = higher_history[1:]
                    for token in next_counts:
                        continuations[suffix][token] += 1

            min_total = prune_min_total.get(order, 0)
            for history, next_counts in histories.items():
                total = sum(next_counts.values())
                if total < min_total:
                    summary.rows_pruned += 1
                    continue
                output_rows.append(
                    {
                        "context": ctx,
                        "order": order,
                        "history": HISTORY_SEP.join(history),
                        "total": total,
                        "distinct_next": len(next_counts),
                        "next": json.dumps(next_counts, sort_keys=True),
                        "cont": json.dumps(continuations.get(history, {}), sort_keys=True),
                    }
                )

    schema = {
        "context": pl.Utf8,
        "order": pl.Int64,
        "history": pl.Utf8,
        "total": pl.Int64,
        "distinct_next": pl.Int64,
        "next": pl.Utf8,
        "cont": pl.Utf8,
    }
    output_frame = pl.DataFrame(output_rows, schema=schema).sort(["context", "order", "history"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.write_parquet(output_path)

    summary.rows_written = output_frame.height
    summary.budget_estimate_mb = measured_table_mb(
        output_frame,
        text_columns=["context", "history", "next", "cont"],
        fixed_bytes_per_row=16,  # order + total + distinct_next (int4 x 3, rounded up)
    )
    return summary
