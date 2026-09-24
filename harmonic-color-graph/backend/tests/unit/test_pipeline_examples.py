"""F22 `examples` stage: up to 5 example songs per pattern/top transition,
preferring a Spotify ID, deterministic across runs; song_refs contains only
referenced songs.
"""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.analyze import SECTIONS_SCHEMA  # noqa: E402
from pipeline.stages.examples import run_examples  # noqa: E402


def _section_row(song_index, song_id, tokens, spotify_id=None, genre="pop", decade="2020"):
    return {
        "song_index": song_index,
        "song_id": song_id,
        "ordinal": 0,
        "section": "verse",
        "local_key": "C major",
        "key_conf": 0.9,
        "ambiguous": False,
        "tokens": tokens,
        "figures": tokens,
        "chords": ["C:maj"] * len(tokens),
        "labels": [],
        "genre": genre,
        "decade": decade,
        "spotify_id": spotify_id,
        "split": "train",
        "repeat_count": 1,
    }


def _write(path: Path, rows: list[dict], schema: dict) -> Path:
    pl.DataFrame(rows, schema=schema).write_parquet(path)
    return path


PATTERNS_SCHEMA = {
    "pattern": pl.Utf8,
    "length": pl.Int64,
    "support": pl.Int64,
    "song_count": pl.Int64,
    "rotations_observed": pl.List(pl.Int64),
    "context_lifts": pl.Utf8,
}
TRANSITIONS_SCHEMA = {
    "context": pl.Utf8,
    "from_token": pl.Utf8,
    "to_token": pl.Utf8,
    "count": pl.Int64,
    "prob": pl.Float64,
    "pmi": pl.Float64,
    "support": pl.Int64,
}


def _setup(tmp_path: Path, section_rows, pattern_rows, transition_rows) -> Path:
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    sections_path = _write(output_dir / "sections.parquet", section_rows, SECTIONS_SCHEMA)
    _write(output_dir / "patterns.parquet", pattern_rows, PATTERNS_SCHEMA)
    _write(output_dir / "transitions.parquet", transition_rows, TRANSITIONS_SCHEMA)
    return sections_path, output_dir


def _pattern_row(pattern, support=10):
    return {
        "pattern": pattern,
        "length": len(pattern.split(" ")),
        "support": support,
        "song_count": support,
        "rotations_observed": [0],
        "context_lifts": "{}",
    }


def _transition_row(a, b, count, context="global"):
    return {
        "context": context,
        "from_token": a,
        "to_token": b,
        "count": count,
        "prob": 1.0,
        "pmi": 0.0,
        "support": count,
    }


def test_prefers_songs_with_spotify_id(tmp_path: Path):
    tokens = ["M:I", "M:IV", "M:V"]
    section_rows = [
        _section_row(0, "no-spotify-1", tokens, spotify_id=None),
        _section_row(1, "no-spotify-2", tokens, spotify_id=None),
        _section_row(2, "has-spotify-1", tokens, spotify_id="abc123"),
    ]
    sections_path, output_dir = _setup(
        tmp_path,
        section_rows,
        [_pattern_row("M:I M:IV M:V")],
        [],
    )

    run_examples(sections_path, output_dir, examples_per_key=2)

    pattern_examples = pl.read_parquet(output_dir / "pattern_examples.parquet")
    song_ids = pattern_examples.filter(pl.col("pattern") == "M:I M:IV M:V")["song_id"].to_list()
    assert "has-spotify-1" in song_ids
    assert len(song_ids) == 2  # capped at examples_per_key


def test_song_refs_only_contains_referenced_songs(tmp_path: Path):
    tokens_a = ["M:I", "M:IV", "M:V"]
    tokens_b = ["M:vi", "M:ii", "M:iii"]  # not in any pattern/transition of interest
    section_rows = [
        _section_row(0, "referenced", tokens_a),
        _section_row(1, "not-referenced", tokens_b),
    ]
    sections_path, output_dir = _setup(
        tmp_path,
        section_rows,
        [_pattern_row("M:I M:IV M:V")],
        [],
    )

    run_examples(sections_path, output_dir)

    song_refs = pl.read_parquet(output_dir / "song_refs.parquet")
    assert song_refs["song_id"].to_list() == ["referenced"]


def test_transition_examples_use_top_global_transitions(tmp_path: Path):
    section_rows = [_section_row(0, "song-0", ["M:V", "M:I", "M:IV"])]
    sections_path, output_dir = _setup(
        tmp_path,
        section_rows,
        [],
        [_transition_row("M:V", "M:I", count=100), _transition_row("M:I", "M:IV", count=50)],
    )

    run_examples(sections_path, output_dir, top_transitions=1)

    transition_examples = pl.read_parquet(output_dir / "transition_examples.parquet")
    # only the top-1 transition (M:V -> M:I, count 100) should have examples
    assert set(transition_examples["transition"].to_list()) == {"M:V->M:I"}


def test_deterministic_across_repeated_runs(tmp_path: Path):
    tokens = ["M:I", "M:IV", "M:V"]
    section_rows = [
        _section_row(i, f"song-{i}", tokens, spotify_id=f"sp{i}" if i % 2 == 0 else None)
        for i in range(8)
    ]
    sections_path, output_dir_a = _setup(tmp_path, section_rows, [_pattern_row("M:I M:IV M:V")], [])
    output_dir_b = tmp_path / "artifacts-b"
    output_dir_b.mkdir()
    _write(output_dir_b / "sections.parquet", section_rows, SECTIONS_SCHEMA)
    _write(output_dir_b / "patterns.parquet", [_pattern_row("M:I M:IV M:V")], PATTERNS_SCHEMA)
    _write(output_dir_b / "transitions.parquet", [], TRANSITIONS_SCHEMA)

    run_examples(sections_path, output_dir_a, examples_per_key=3)
    run_examples(output_dir_b / "sections.parquet", output_dir_b, examples_per_key=3)

    a = pl.read_parquet(output_dir_a / "pattern_examples.parquet").sort("rank")
    b = pl.read_parquet(output_dir_b / "pattern_examples.parquet").sort("rank")
    assert a.to_dicts() == b.to_dicts()
