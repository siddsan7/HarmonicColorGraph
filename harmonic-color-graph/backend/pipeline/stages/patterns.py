"""F22 `patterns` stage: frequent contiguous token-sequence patterns
(length 3-8), canonicalized by rotation (a loop and its rotations, e.g.
`I V vi IV` and `vi IV I V`, count as the same pattern), with support,
song coverage, and per-context lift.

This stage went through three rounds of real memory incidents against the
real 679K-song corpus before landing on the design below (each is a
distinct lesson, not the same bug repeated -- see pipeline/memory_guard.py
for the structural backstop that now catches whatever the next one turns
out to be):

1. Pass 1 originally tracked a per-pattern song-ID `set()` *and* a
   rotation-offset `set()` for every distinct window, not just ones that
   would matter. At ~10^8 distinct windows (most of them, especially
   length 7-8, occurring exactly once), that is a `set()` object for tens
   of millions of one-off keys -- 15+ GB, 0.3 GB free system-wide. Fixed
   by splitting into two passes: pass 1 tracks *only* a support count
   (`Counter[pattern] -> int`, no per-pattern sets at all); only pass 2,
   restricted to the min_support survivors (`frequent`), pays for
   song/rotation tracking.
2. Pass 1's periodic pruning (delete count<=1 entries every N windows)
   turned out to do nothing for the huge *middle* tier of patterns seen
   dozens to hundreds of times -- confirmed still hit 15+ GB. Fixed by
   real Lossy Counting (Manku & Motwani 2002): buckets of BUCKET_WIDTH
   windows, with the survival bar (current bucket number) rising every
   bucket, bounded memory throughout the whole stream with a formal
   undercounting-error guarantee relative to DEFAULT_MIN_SUPPORT.
3. Pass 2's per-context breakdown (for lift) was keyed by *every* context
   that appears even once, not just ones with enough data to matter --
   still hit 8+ GB even with (1) and (2) fixed. First fix reused
   aggregate's context threshold (2,000): still not enough, crossed
   against ~8,900 frequent patterns that's still ~2,955 contexts' worth
   of per-context counts. Measuring context_counts directly against the
   real corpus showed raising this threshold to 10,000 (matching ngrams'
   own reasoning -- a richer per-context table needs more evidence to be
   worth tracking) cuts it to 680 contexts and ~3.3M entries (~1 GB).
4. Even with all of the above, a handful of extremely common short
   patterns (classic I-IV-V-vi-style loops) each appear in hundreds of
   thousands of the corpus's 679K songs -- still hit 8+ GB. Fixed by
   capping each pattern's tracked song-ID set (MAX_SONGS_TRACKED_PER_PATTERN
   below); `song_count` becomes a floor, not an exact count, once a
   pattern is that common.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from pipeline.manifest import measured_table_mb
from pipeline.stages._context import context_keys

MIN_LENGTH = 3
MAX_LENGTH = 8
# Measured against the real corpus: even a 4.4%-size slice (100K of 679K
# songs) produced 693K distinct windows, and only ~1K of those ever reach
# a count of 500. Raised further, to 2000, to open up room for a much
# smaller BUCKET_WIDTH below without risking undercounting error -- Lossy
# Counting's guaranteed error is bounded by the final bucket count, so it
# needs to stay a small fraction of this threshold for patterns near the
# bar to not be falsely dropped. The "I V vi IV" family and other classic
# progressions this stage's sanity check cares about clear this bar by
# orders of magnitude (their underlying bigrams have counts in the
# millions), so precision at the threshold itself is what matters, not
# these specific patterns' safety margin.
DEFAULT_MIN_SUPPORT = 2000

# Pass 1 memory safety valve: real Lossy Counting (Manku & Motwani 2002),
# not a fixed-threshold heuristic. A first attempt only deleted exact
# singletons (count == 1), which does nothing for the huge middle tier of
# patterns seen dozens to hundreds of times across a corpus this size.
# A second attempt used real Lossy Counting but with BUCKET_WIDTH=5M,
# which only yields ~20-40 buckets over the real corpus's ~10^8 windows --
# the survival bar (current bucket number) never rises past ~40, so the
# entire middle tier (patterns with true counts anywhere up to a few
# hundred) still survives every prune round unpruned. Both attempts still
# drove this stage to 8+ GB against the real corpus.
#
# Real Lossy Counting divides the stream into buckets of BUCKET_WIDTH
# windows; at each bucket boundary it drops every tracked entry whose
# count hasn't exceeded the *current bucket number* yet. The survival bar
# rises every bucket, so the working set stays bounded throughout the
# whole stream (not just at sparse checkpoints), while it provably never
# undercounts an item's true final count by more than the final bucket
# number. At ~150-200M total windows, this bucket width yields roughly
# 150-200 buckets -- comfortably (~10%) below DEFAULT_MIN_SUPPORT above,
# so genuinely-frequent patterns near that bar aren't at real risk, while
# pruning aggressively enough (~150-200 rounds, not ~20-40) to keep the
# working set bounded throughout the whole stream, not just at its start.
BUCKET_WIDTH = 1_000_000

# Pass 2 memory safety valve: even with pass 1 and the context filter both
# bounded, this stage still hit 8+ GB against the real corpus. The
# remaining cause: `songs[pattern]`, a set of every distinct song ID a
# frequent pattern appears in, for popularity ranking / `song_count`. A
# handful of extremely common short patterns (classic I-IV-V-vi-style
# loops) each appear in hundreds of thousands of the corpus's 679K songs,
# and a Python set of that many ints is not free. Capping each pattern's
# tracked song-ID set turns `song_count` into a floor ("at least this
# many songs") rather than an exact count once a pattern is this common --
# an acceptable tradeoff for a popularity metric.
MAX_SONGS_TRACKED_PER_PATTERN = 2_000

# Same idea as ngrams' DEFAULT_MIN_CONTEXT_OBSERVATIONS, and for the same
# reason: reusing aggregate's shared default (2,000) still hit 8+ GB, with
# ~8,900 frequent patterns (at DEFAULT_MIN_SUPPORT above) crossed against
# ~2,955 kept contexts. Measured directly against the real corpus: raising
# this to 10,000 (matching ngrams) cut kept contexts to 680 and let this
# stage run within its own memory budget -- but combined with aggregate's
# and ngrams' output tables, F22's *shared* Postgres budget (the 300MB
# check) was still 706MB (ngrams 270MB + patterns 292MB were most of it).
# Raised to 50,000, measured directly to cut kept contexts to 105.
DEFAULT_MIN_CONTEXT_OBSERVATIONS = 50_000


def _canonical_rotation(window: tuple[str, ...]) -> tuple[tuple[str, ...], int]:
    """The lexicographically smallest rotation of `window`, and the offset
    (number of left-rotations) that reaches it from the original.
    """
    best_index = 0
    best_rotation = window
    for index in range(1, len(window)):
        rotation = window[index:] + window[:index]
        if rotation < best_rotation:
            best_rotation = rotation
            best_index = index
    return best_rotation, best_index


def _iter_windows(tokens: list[str]):
    for length in range(MIN_LENGTH, MAX_LENGTH + 1):
        if length > len(tokens):
            break
        for start in range(0, len(tokens) - length + 1):
            yield tuple(tokens[start : start + length])


@dataclass
class PatternsSummary:
    rows_written: int = 0
    windows_seen: int = 0
    patterns_below_min_support: int = 0
    budget_estimate_mb: float = 0.0


def run_patterns(
    sections_path: str | Path,
    output_path: str | Path,
    min_support: int = DEFAULT_MIN_SUPPORT,
    min_context_observations: int = DEFAULT_MIN_CONTEXT_OBSERVATIONS,
    bucket_width: int = BUCKET_WIDTH,
    max_songs_tracked_per_pattern: int = MAX_SONGS_TRACKED_PER_PATTERN,
) -> PatternsSummary:
    import polars as pl

    frame = pl.read_parquet(sections_path)
    token_lists = frame["tokens"].to_list()
    song_indexes = frame["song_index"].to_list()

    summary = PatternsSummary()

    # Pass 1: support counts only (a plain int per key -- no set allocation
    # for the vast majority of windows that will never clear min_support),
    # bounded via Lossy Counting (see BUCKET_WIDTH above).
    support: Counter[tuple[str, ...]] = Counter()
    bucket_id = 0
    for tokens in token_lists:
        for window in _iter_windows(tokens):
            canonical, _ = _canonical_rotation(window)
            summary.windows_seen += 1
            support[canonical] += 1
            if summary.windows_seen % bucket_width == 0:
                bucket_id += 1
                for pattern in [p for p, count in support.items() if count <= bucket_id]:
                    del support[pattern]

    frequent = {pattern for pattern, count in support.items() if count >= min_support}
    summary.patterns_below_min_support = len(support) - len(frequent)
    del support  # the full (mostly one-off) key set is no longer needed

    # Which contexts are worth a per-context breakdown at all? Same
    # threshold and meaning as aggregate's/ngrams' context filters (a
    # cheap bigram-count proxy, not a full window count -- just enough to
    # rank contexts by size). Without this, context_counts was keyed by
    # *every* context that appears even once (genre/section/decade/
    # genre_section combos number in the thousands), multiplied by
    # `frequent`'s pattern count: the actual cause of this stage hitting
    # 8+ GB even after pass 1 was bounded.
    context_size_proxy: dict[str, int] = defaultdict(int)
    contexts_by_row_for_sizing = frame.select("genre", "section", "decade").iter_rows(named=True)
    for tokens, row in zip(token_lists, contexts_by_row_for_sizing, strict=True):
        for ctx in context_keys(row["genre"], row["section"], row["decade"]):
            context_size_proxy[ctx] += max(len(tokens) - 1, 0)
    kept_contexts = {
        ctx
        for ctx, total in context_size_proxy.items()
        if ctx == "global" or total >= min_context_observations
    }
    del context_size_proxy

    # Pass 2: for the much smaller `frequent` set and `kept_contexts` only,
    # per-context counts (for lift) plus the song-ID and rotation-offset
    # sets that pass 1 deliberately skipped.
    songs: dict[tuple[str, ...], set[int]] = defaultdict(set)
    rotations: dict[tuple[str, ...], set[int]] = defaultdict(set)
    context_counts: dict[str, dict[tuple[str, ...], int]] = defaultdict(lambda: defaultdict(int))
    context_totals: dict[str, int] = defaultdict(int)
    frequent_support: Counter[tuple[str, ...]] = Counter()

    contexts_by_row = frame.select("genre", "section", "decade").iter_rows(named=True)
    for tokens, song_index, row in zip(token_lists, song_indexes, contexts_by_row, strict=True):
        contexts = [
            ctx
            for ctx in context_keys(row["genre"], row["section"], row["decade"])
            if ctx in kept_contexts
        ]
        for window in _iter_windows(tokens):
            canonical, offset = _canonical_rotation(window)
            is_frequent = canonical in frequent
            for ctx in contexts:
                # Every window counts toward the denominator (lift needs
                # the true "share of all windows in this context", not
                # just frequent-pattern windows); only frequent patterns
                # get their own per-context numerator tracked.
                context_totals[ctx] += 1
                if is_frequent:
                    context_counts[ctx][canonical] += 1
            if is_frequent:
                frequent_support[canonical] += 1
                # Capped, not unbounded: a genuinely common 3-token pattern
                # (e.g. a classic I-IV-V-vi loop) can appear in hundreds of
                # thousands of the corpus's 679K songs. This is what
                # actually drove this stage to 8+ GB even after pass 1 was
                # bounded -- a handful of extremely common patterns each
                # holding a set() of hundreds of thousands of song IDs.
                # `song_count` becomes a floor ("at least this many"), not
                # an exact count, once a pattern's set hits the cap; that's
                # an acceptable tradeoff for a popularity/ranking metric,
                # not a value anything downstream needs to be exact.
                if len(songs[canonical]) < max_songs_tracked_per_pattern:
                    songs[canonical].add(song_index)
                rotations[canonical].add(offset)

    global_total = context_totals.get("global", 0)
    rows: list[dict] = []
    for pattern in frequent:
        lifts: dict[str, float] = {}
        global_rate = (context_counts["global"][pattern] / global_total) if global_total else 0.0
        if global_rate > 0:
            for ctx, total in context_totals.items():
                if ctx == "global" or total < min_context_observations:
                    continue
                ctx_rate = context_counts[ctx][pattern] / total
                lifts[ctx] = ctx_rate / global_rate
        rows.append(
            {
                "pattern": " ".join(pattern),
                "length": len(pattern),
                "support": frequent_support[pattern],
                "song_count": len(songs[pattern]),
                "rotations_observed": sorted(rotations[pattern]),
                "context_lifts": json.dumps(lifts, sort_keys=True),
            }
        )

    schema = {
        "pattern": pl.Utf8,
        "length": pl.Int64,
        "support": pl.Int64,
        "song_count": pl.Int64,
        "rotations_observed": pl.List(pl.Int64),
        "context_lifts": pl.Utf8,
    }
    output_frame = pl.DataFrame(rows, schema=schema).sort("support", descending=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.write_parquet(output_path)

    summary.rows_written = output_frame.height
    summary.budget_estimate_mb = measured_table_mb(
        output_frame,
        text_columns=["pattern", "context_lifts"],
        fixed_bytes_per_row=28,  # length/support/song_count (int4x3) + a small rotations list
    )
    return summary
