"""F22 `examples` stage: up to 5 example songs per pattern and per top
global transition, preferring songs with a Spotify ID, deterministically
selected. Reads `patterns.parquet` and `transitions.parquet` (both written
by earlier F22 stages) plus `sections.parquet`, and writes
`pattern_examples.parquet`, `transition_examples.parquet`, and
`song_refs.parquet` (only the songs actually referenced by an example).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pipeline.stages.patterns import MAX_LENGTH, MIN_LENGTH, _canonical_rotation

DEFAULT_TOP_TRANSITIONS = 50
DEFAULT_EXAMPLES_PER_KEY = 5
# Stop collecting candidates for a key once we have this many -- comfortably
# more than needed to pick 5 with the Spotify-ID preference, without
# tracking every occurrence of a common pattern across the whole corpus.
MAX_CANDIDATES_PER_KEY = 20


@dataclass
class ExamplesSummary:
    pattern_examples_rows: int = 0
    transition_examples_rows: int = 0
    song_refs_rows: int = 0
    patterns_with_no_example: int = 0
    transitions_with_no_example: int = 0


def run_examples(
    sections_path: str | Path,
    output_dir: str | Path,
    top_transitions: int = DEFAULT_TOP_TRANSITIONS,
    examples_per_key: int = DEFAULT_EXAMPLES_PER_KEY,
    seed: int = 1,
) -> ExamplesSummary:
    import polars as pl

    output_dir = Path(output_dir)
    patterns_frame = pl.read_parquet(output_dir / "patterns.parquet")
    transitions_frame = pl.read_parquet(output_dir / "transitions.parquet")
    sections_frame = pl.read_parquet(sections_path)

    pattern_keys: set[tuple[str, ...]] = {
        tuple(pattern.split(" ")) for pattern in patterns_frame["pattern"].to_list()
    }
    top_transition_rows = (
        transitions_frame.filter(pl.col("context") == "global")
        .sort("count", descending=True)
        .head(top_transitions)
        .to_dicts()
    )
    transition_keys: set[tuple[str, str]] = {
        (row["from_token"], row["to_token"]) for row in top_transition_rows
    }

    pattern_candidates: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    transition_candidates: dict[tuple[str, str], list[dict]] = defaultdict(list)
    song_meta: dict[str, dict] = {}

    for row in sections_frame.select(
        "song_id", "section", "ordinal", "genre", "decade", "spotify_id", "tokens"
    ).iter_rows(named=True):
        song_id = row["song_id"]
        tokens: list[str] = row["tokens"]
        song_meta.setdefault(
            song_id,
            {
                "song_id": song_id,
                "spotify_id": row["spotify_id"],
                "genre": row["genre"],
                "decade": row["decade"],
            },
        )

        for length in range(MIN_LENGTH, min(MAX_LENGTH, len(tokens)) + 1):
            for start in range(0, len(tokens) - length + 1):
                window = tuple(tokens[start : start + length])
                canonical, _ = _canonical_rotation(window)
                if canonical in pattern_keys and len(pattern_candidates[canonical]) < (
                    MAX_CANDIDATES_PER_KEY
                ):
                    pattern_candidates[canonical].append(
                        {
                            "song_id": song_id,
                            "section": row["section"],
                            "ordinal": row["ordinal"],
                            "position": start,
                        }
                    )

        for position, (a, b) in enumerate(zip(tokens, tokens[1:], strict=False)):
            pair = (a, b)
            if pair in transition_keys and len(transition_candidates[pair]) < (
                MAX_CANDIDATES_PER_KEY
            ):
                transition_candidates[pair].append(
                    {
                        "song_id": song_id,
                        "section": row["section"],
                        "ordinal": row["ordinal"],
                        "position": position,
                    }
                )

    summary = ExamplesSummary()
    referenced_songs: set[str] = set()

    pattern_example_rows = _select_examples(
        pattern_candidates,
        song_meta,
        examples_per_key,
        seed,
        key_column="pattern",
        key_to_label=lambda key: " ".join(key),
    )
    summary.patterns_with_no_example = len(pattern_keys) - len(
        {row["pattern"] for row in pattern_example_rows}
    )
    referenced_songs.update(row["song_id"] for row in pattern_example_rows)

    transition_example_rows = _select_examples(
        transition_candidates,
        song_meta,
        examples_per_key,
        seed,
        key_column="transition",
        key_to_label=lambda key: f"{key[0]}->{key[1]}",
    )
    summary.transitions_with_no_example = len(transition_keys) - len(
        {row["transition"] for row in transition_example_rows}
    )
    referenced_songs.update(row["song_id"] for row in transition_example_rows)

    song_refs_rows = [
        song_meta[song_id] for song_id in sorted(referenced_songs) if song_id in song_meta
    ]

    pattern_examples_schema = {
        "pattern": pl.Utf8,
        "song_id": pl.Utf8,
        "section": pl.Utf8,
        "ordinal": pl.Int64,
        "position": pl.Int64,
        "rank": pl.Int64,
    }
    transition_examples_schema = {
        "transition": pl.Utf8,
        "from_token": pl.Utf8,
        "to_token": pl.Utf8,
        "song_id": pl.Utf8,
        "section": pl.Utf8,
        "ordinal": pl.Int64,
        "position": pl.Int64,
        "rank": pl.Int64,
    }
    song_refs_schema = {
        "song_id": pl.Utf8,
        "spotify_id": pl.Utf8,
        "genre": pl.Utf8,
        "decade": pl.Utf8,
    }

    pl.DataFrame(pattern_example_rows, schema=pattern_examples_schema).write_parquet(
        output_dir / "pattern_examples.parquet"
    )
    pl.DataFrame(transition_example_rows, schema=transition_examples_schema).write_parquet(
        output_dir / "transition_examples.parquet"
    )
    pl.DataFrame(song_refs_rows, schema=song_refs_schema).write_parquet(
        output_dir / "song_refs.parquet"
    )

    summary.pattern_examples_rows = len(pattern_example_rows)
    summary.transition_examples_rows = len(transition_example_rows)
    summary.song_refs_rows = len(song_refs_rows)
    return summary


def _select_examples(
    candidates_by_key: dict,
    song_meta: dict[str, dict],
    examples_per_key: int,
    seed: int,
    key_column: str,
    key_to_label,
) -> list[dict]:
    import random

    rows: list[dict] = []
    for key, candidates in candidates_by_key.items():
        # Deterministic: a fixed per-key seed, then sort by (has_spotify_id
        # desc, shuffled tiebreak) so the choice doesn't just default to
        # song_id order but is still 100% reproducible. Seeding with a
        # *string*, not a raw tuple or a hash() of one: random.Random's
        # string seeding is a documented, stable algorithm, unlike
        # built-in hash() on str/tuple, which is randomized per process
        # (PYTHONHASHSEED) and would break the determinism guarantee.
        rng = random.Random(f"{seed}:{key_column}:{key_to_label(key)}")
        shuffled = list(candidates)
        rng.shuffle(shuffled)
        shuffled.sort(key=lambda candidate: song_meta[candidate["song_id"]]["spotify_id"] is None)
        for rank, candidate in enumerate(shuffled[:examples_per_key], start=1):
            rows.append(
                {
                    key_column: key_to_label(key),
                    **(
                        {"from_token": key[0], "to_token": key[1]}
                        if key_column == "transition"
                        else {}
                    ),
                    "song_id": candidate["song_id"],
                    "section": candidate["section"],
                    "ordinal": candidate["ordinal"],
                    "position": candidate["position"],
                    "rank": rank,
                }
            )
    return rows
