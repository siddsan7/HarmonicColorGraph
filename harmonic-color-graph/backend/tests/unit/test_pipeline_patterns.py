"""F22 `patterns` stage: rotation canonicalization, support/song-count,
the min-support prune, and per-context lift.
"""

import json
from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.analyze import SECTIONS_SCHEMA  # noqa: E402
from pipeline.stages.patterns import _canonical_rotation, run_patterns  # noqa: E402


def _section_row(song_index, tokens, genre=None, section=None, decade=None):
    return {
        "song_index": song_index,
        "song_id": str(song_index),
        "ordinal": 0,
        "section": section,
        "local_key": "C major",
        "key_conf": 0.9,
        "ambiguous": False,
        "tokens": tokens,
        "figures": tokens,
        "chords": ["C:maj"] * len(tokens),
        "labels": [],
        "genre": genre,
        "decade": decade,
        "spotify_id": None,
        "split": "train",
        "repeat_count": 1,
    }


def _write_fixture(path: Path, rows: list[dict]) -> Path:
    pl.DataFrame(rows, schema=SECTIONS_SCHEMA).write_parquet(path)
    return path


def test_canonical_rotation_picks_lexicographically_smallest():
    # "I" < "IV" (string comparison: a prefix sorts before the longer
    # string it's a prefix of), so this loop's own first rotation is
    # already its lexicographically smallest form.
    canonical, offset = _canonical_rotation(("I", "V", "vi", "IV"))
    assert canonical == ("I", "V", "vi", "IV")
    assert offset == 0
    # every rotation of the same loop must canonicalize to the same form,
    # each via the offset that reaches it from that specific rotation
    for rotated, expected_offset in [
        (("I", "V", "vi", "IV"), 0),
        (("V", "vi", "IV", "I"), 3),
        (("vi", "IV", "I", "V"), 2),
        (("IV", "I", "V", "vi"), 1),
    ]:
        assert _canonical_rotation(rotated) == (canonical, expected_offset)


def test_rotations_of_a_loop_merge_into_one_pattern_row(tmp_path: Path):
    rows = [
        _section_row(0, ["I", "V", "vi", "IV"]),
        _section_row(1, ["V", "vi", "IV", "I"]),
        _section_row(2, ["vi", "IV", "I", "V"]),
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "patterns.parquet"

    run_patterns(sections_path, output_path, min_support=1)

    frame = pl.read_parquet(output_path)
    matches = frame.filter(pl.col("length") == 4)
    assert matches.height == 1
    row = matches.to_dicts()[0]
    assert row["support"] == 3
    assert row["song_count"] == 3
    # song0's window is already canonical (offset 0); song1 and song2's
    # rotations need offset 3 and 2 respectively to reach the same form.
    assert sorted(row["rotations_observed"]) == [0, 2, 3]


def test_song_count_is_capped_not_unbounded(tmp_path: Path):
    # 20 distinct songs all containing "A B C", with the per-pattern
    # song-ID tracking capped at 5: song_count must report the cap (a
    # floor, "at least this many"), not silently keep growing past it.
    rows = [_section_row(i, ["A", "B", "C"]) for i in range(20)]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "patterns.parquet"

    summary = run_patterns(
        sections_path, output_path, min_support=1, max_songs_tracked_per_pattern=5
    )

    assert summary.rows_written == 1
    frame = pl.read_parquet(output_path)
    row = frame.filter(pl.col("pattern") == "A B C").to_dicts()[0]
    assert row["support"] == 20  # support itself is never capped, only song_count
    assert row["song_count"] == 5


def test_min_support_prunes_rare_patterns(tmp_path: Path):
    rows = [_section_row(0, ["I", "V", "vi", "IV"])]  # each 4-window occurs once
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "patterns.parquet"

    summary = run_patterns(sections_path, output_path, min_support=2)

    assert summary.rows_written == 0
    assert summary.patterns_below_min_support > 0


def test_lossy_counting_preserves_a_frequent_pattern_across_many_prunes(tmp_path: Path):
    # 25 occurrences of "A B C" interleaved with 25 never-repeating filler
    # sections, with a tiny bucket_width (10) so pruning fires 5 times
    # during accumulation. "A B C" must survive every prune round (its
    # count always outpaces the current bucket threshold) with its exact,
    # un-undercounted total -- not just an approximation.
    rows = []
    for i in range(25):
        rows.append(_section_row(2 * i, ["A", "B", "C"]))
        rows.append(_section_row(2 * i + 1, [f"F{i}a", f"F{i}b", f"F{i}c"]))
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "patterns.parquet"

    summary = run_patterns(sections_path, output_path, min_support=20, bucket_width=10)

    assert summary.windows_seen == 50
    frame = pl.read_parquet(output_path)
    row = frame.filter(pl.col("pattern") == "A B C").to_dicts()[0]
    assert row["support"] == 25
    assert row["song_count"] == 25
    # every filler pattern occurred once, nowhere near min_support=20
    assert frame.height == 1


def test_window_lengths_are_3_to_8(tmp_path: Path):
    tokens = [f"t{i}" for i in range(10)]
    rows = [_section_row(0, tokens)]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "patterns.parquet"

    run_patterns(sections_path, output_path, min_support=1)

    frame = pl.read_parquet(output_path)
    assert frame["length"].min() >= 3
    assert frame["length"].max() <= 8


def test_context_lift_above_one_when_pattern_is_enriched_in_a_context(tmp_path: Path):
    # "A B C" appears in every rock section but only a minority of pop
    # sections, so its lift for genre:rock should exceed 1.
    rock_rows = [_section_row(i, ["A", "B", "C"], genre="rock") for i in range(30)]
    pop_rows = [_section_row(30 + i, ["A", "B", "C"], genre="pop") for i in range(2)] + [
        _section_row(32 + i, ["X", "Y", "Z"], genre="pop") for i in range(28)
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rock_rows + pop_rows)
    output_path = tmp_path / "patterns.parquet"

    run_patterns(sections_path, output_path, min_support=1, min_context_observations=10)

    frame = pl.read_parquet(output_path)
    row = frame.filter(pl.col("pattern") == "A B C").to_dicts()[0]
    lifts = json.loads(row["context_lifts"])
    assert lifts["genre:rock"] > 1.0
    assert lifts["genre:pop"] < 1.0


def test_lift_denominator_counts_all_windows_not_just_frequent_ones(tmp_path: Path):
    # Regression test: context_totals (the lift denominator) must count
    # every window in a context, not just windows belonging to a pattern
    # that cleared min_support. A first attempt at bounding pass 2's
    # memory gated context_totals by frequency too, which silently
    # produced identical (wrong) lift values for both genres below.
    light_rows = [_section_row(i, ["A", "B", "C"], genre="light") for i in range(5)]
    heavy_rows = [_section_row(5 + i, ["A", "B", "C"], genre="heavy") for i in range(5)] + [
        # Each filler section is unique, so every filler window has
        # support 1 -- well below min_support -- but still contributes
        # windows to genre:heavy's total.
        _section_row(10 + i, [f"P{i}", f"Q{i}", f"R{i}", f"S{i}"], genre="heavy")
        for i in range(3)
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", light_rows + heavy_rows)
    output_path = tmp_path / "patterns.parquet"

    run_patterns(sections_path, output_path, min_support=5, min_context_observations=1)

    frame = pl.read_parquet(output_path)
    row = frame.filter(pl.col("pattern") == "A B C").to_dicts()[0]
    lifts = json.loads(row["context_lifts"])
    # Same "A B C" numerator (5 occurrences) in both genres, but
    # genre:heavy has extra non-frequent filler windows diluting its
    # denominator, so its lift must be strictly lower than light's.
    assert lifts["genre:light"] > lifts["genre:heavy"]


def test_budget_estimate_is_measured_not_zero(tmp_path: Path):
    rows = [_section_row(i, ["I", "V", "vi", "IV"]) for i in range(3)]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "patterns.parquet"

    summary = run_patterns(sections_path, output_path, min_support=1)

    assert summary.budget_estimate_mb > 0
