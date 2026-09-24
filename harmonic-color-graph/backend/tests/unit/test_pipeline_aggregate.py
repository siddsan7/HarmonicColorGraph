"""F22 `aggregate` stage: per-context transition probabilities, PMI,
support, FUNCTIONS_AS, ABS_TRANSITIONS_TO, and the budget estimator.
"""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.aggregate import run_aggregate  # noqa: E402
from pipeline.stages.analyze import SECTIONS_SCHEMA  # noqa: E402


def _section_row(
    song_index,
    song_id,
    tokens,
    chords,
    genre="pop",
    section="verse",
    decade="2020",
):
    return {
        "song_index": song_index,
        "song_id": song_id,
        "ordinal": 0,
        "section": section,
        "local_key": "C major",
        "key_conf": 0.9,
        "ambiguous": False,
        "tokens": tokens,
        "figures": tokens,
        "chords": chords,
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


def test_per_context_from_probabilities_sum_to_one(tmp_path: Path):
    rows = [
        _section_row(i, str(i), ["M:I", "M:IV", "M:V", "M:I"], ["C:maj", "F:maj", "G:maj", "C:maj"])
        for i in range(5)
    ] + [
        _section_row(i, str(i), ["M:I", "M:V", "M:vi"], ["C:maj", "G:maj", "A:min"], genre="rock")
        for i in range(5, 8)
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_dir = tmp_path / "out"

    run_aggregate(sections_path, output_dir, min_context_transitions=1)

    transitions = pl.read_parquet(output_dir / "transitions.parquet")
    totals = transitions.group_by(["context", "from_token"]).agg(
        pl.col("prob").sum().alias("total_prob")
    )
    for value in totals["total_prob"]:
        assert value == pytest.approx(1.0)


def test_small_contexts_are_dropped_global_always_kept(tmp_path: Path):
    rows = [_section_row(0, "0", ["M:I", "M:V"], ["C:maj", "G:maj"], genre="obscure")]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_dir = tmp_path / "out"

    summary = run_aggregate(sections_path, output_dir, min_context_transitions=2000)

    assert "global" in summary.contexts_kept
    assert "genre:obscure" in summary.contexts_dropped_small
    transitions = pl.read_parquet(output_dir / "transitions.parquet")
    assert set(transitions["context"].unique().to_list()) == {"global"}


def test_support_counts_distinct_songs(tmp_path: Path):
    rows = [
        _section_row(0, "song-a", ["M:V", "M:I"], ["G:maj", "C:maj"]),
        _section_row(0, "song-a", ["M:V", "M:I"], ["G:maj", "C:maj"]),  # same song, repeated
        _section_row(1, "song-b", ["M:V", "M:I"], ["G:maj", "C:maj"]),
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_dir = tmp_path / "out"

    run_aggregate(sections_path, output_dir, min_context_transitions=1)

    transitions = pl.read_parquet(output_dir / "transitions.parquet")
    row = transitions.filter(
        (pl.col("context") == "global")
        & (pl.col("from_token") == "M:V")
        & (pl.col("to_token") == "M:I")
    ).to_dicts()[0]
    assert row["count"] == 3
    assert row["support"] == 2  # 2 distinct song_index values, not 3 occurrences


def test_functions_and_abs_transitions(tmp_path: Path):
    rows = [_section_row(i, str(i), ["M:I", "M:IV"], ["C:maj", "F:maj"]) for i in range(25)]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_dir = tmp_path / "out"

    run_aggregate(sections_path, output_dir, min_context_transitions=1)

    functions = pl.read_parquet(output_dir / "functions.parquet")
    assert {"chord": "C:maj", "mode": "major", "token": "M:I", "count": 25} in functions.to_dicts()

    abs_transitions = pl.read_parquet(output_dir / "abs_transitions.parquet")
    assert abs_transitions.to_dicts() == [{"from_chord": "C:maj", "to_chord": "F:maj", "count": 25}]


def test_abs_transitions_below_threshold_are_dropped(tmp_path: Path):
    rows = [_section_row(0, "0", ["M:I", "M:IV"], ["C:maj", "F:maj"])]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_dir = tmp_path / "out"

    run_aggregate(sections_path, output_dir, min_context_transitions=1)

    abs_transitions = pl.read_parquet(output_dir / "abs_transitions.parquet")
    assert abs_transitions.height == 0


def test_budget_estimate_present_and_positive(tmp_path: Path):
    rows = [
        _section_row(i, str(i), ["M:I", "M:IV", "M:V"], ["C:maj", "F:maj", "G:maj"])
        for i in range(3)
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_dir = tmp_path / "out"

    summary = run_aggregate(sections_path, output_dir, min_context_transitions=1)

    assert summary.budget_estimate_mb["total"] > 0
    assert summary.budget_estimate_mb["total"] == pytest.approx(
        sum(v for k, v in summary.budget_estimate_mb.items() if k != "total")
    )
