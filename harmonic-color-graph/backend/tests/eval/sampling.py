"""F31: deterministic sampling of test positions from a corpus's
`sections.parquet` (any split -- the caller filters).

A "position" is one (preceding tokens, actual next token) pair drawn from
inside a real section: for a section with tokens `[t0, t1, ..., tn-1]`,
position `i` (`1 <= i < n`) has history `tokens[:i]` and actual token
`tokens[i]`. Position 0 (empty history) is excluded -- there's no bigram
for the v1 baseline to use there, and "predict the first chord from
nothing" is a different, less interesting task than continuing a
progression, so every model gets the same, fair position set.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class SampledPosition:
    song_id: str
    section_ordinal: int
    position: int
    genre: str | None
    section: str | None
    mode: str  # "major" | "minor", from the section's local_key
    history: tuple[str, ...]
    actual: str

    @property
    def depth_bucket(self) -> str:
        """How much history was available, capped at the global context's
        max n-gram order (5, i.e. 4 tokens of history) -- more than that
        never changes which orders `KNPredictor` can use."""
        capped = min(self.position, 4)
        return f"{capped}+" if self.position >= 4 else str(capped)


def _mode_of(local_key: str | None) -> str:
    if not local_key:
        return "major"
    return "minor" if local_key.strip().lower().endswith("minor") else "major"


def sample_test_positions(
    rows: list[dict], *, sample_size: int, seed: int
) -> list[SampledPosition]:
    """`rows` are `sections.parquet` records already filtered to the split
    being evaluated (e.g. `split == "test"`), as dicts with at least
    `song_id`, `ordinal`, `genre`, `section`, `local_key`, `tokens`.

    Samples position *indices* first and only slices out the (song,
    position) pairs actually drawn, rather than materializing every
    position's history tuple up front -- a corpus-wide position list is
    O(total tokens), but per-position history slices are O(total
    tokens^2) if built for every position instead of just the sampled
    ones.
    """
    index_pairs = [
        (row_index, token_index)
        for row_index, row in enumerate(rows)
        for token_index in range(1, len(row["tokens"]))
    ]
    rng = random.Random(seed)
    sampled = rng.sample(index_pairs, min(sample_size, len(index_pairs)))

    positions = []
    for row_index, token_index in sampled:
        row = rows[row_index]
        tokens: list[str] = row["tokens"]
        positions.append(
            SampledPosition(
                song_id=row["song_id"],
                section_ordinal=row["ordinal"],
                position=token_index,
                genre=row["genre"],
                section=row["section"],
                mode=_mode_of(row["local_key"]),
                history=tuple(tokens[:token_index]),
                actual=tokens[token_index],
            )
        )
    return positions
