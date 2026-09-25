"""F41/F43 `color` stage: corpus percentile norms over a sampled
`sections.parquet` (`run_color`, with and without a real offline F30
predictor), and a color profile for every Function/global-Transition/
Pattern (`run_color_profiles`).
"""

import json
from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.analyze import SECTIONS_SCHEMA  # noqa: E402
from pipeline.stages.color import run_color, run_color_profiles  # noqa: E402


def _section_row(song_index, chords, key="C major", genre=None, section=None):
    return {
        "song_index": song_index,
        "song_id": str(song_index),
        "ordinal": 0,
        "section": section,
        "local_key": key,
        "key_conf": 0.9,
        "ambiguous": False,
        "tokens": [],
        "figures": [],
        "chords": chords,
        "labels": [],
        "genre": genre,
        "decade": None,
        "spotify_id": None,
        "split": "train",
        "repeat_count": 1,
    }


def _write_sections(path: Path, rows: list[dict]) -> Path:
    pl.DataFrame(rows, schema=SECTIONS_SCHEMA).write_parquet(path)
    return path


# A small but harmonically varied fixture -- diatonic, borrowed, applied, and
# dominant-seventh chords across a few keys -- so every axis's transition
# sample has more than one distinct value (std > 0 is checkable without a
# real multi-million-row corpus).
_VARIED_ROWS = [
    _section_row(0, ["C:maj", "G:maj", "A:min", "F:maj"], genre="pop", section="chorus"),
    _section_row(1, ["C:maj", "A:min7", "D:min7", "G:7"], genre="jazz", section="verse"),
    _section_row(2, ["A:maj", "F:min", "G:maj", "C:maj"], key="C major", section="bridge"),
    _section_row(3, ["G:maj", "D:maj", "E:min", "C:maj"], key="G major"),
    _section_row(4, ["D:min", "G:7", "C:maj", "A:min"], genre="pop", section="verse"),
    _section_row(5, ["F:maj7", "E:min7", "D:min7", "C:maj7"]),
    _section_row(6, ["Ab:maj", "Bb:maj", "C:maj"]),
]


def test_run_color_writes_norms_for_every_axis(tmp_path: Path):
    sections = _write_sections(tmp_path / "sections.parquet", _VARIED_ROWS)
    summary = run_color(sections, tmp_path / "missing_ngrams.parquet", tmp_path / "color.parquet")

    assert summary.rows_sampled == len(_VARIED_ROWS)
    assert summary.positions_scored > 0
    assert summary.used_predictor is False

    frame = pl.read_parquet(tmp_path / "color.parquet")
    axes_present = set(frame["axis"].to_list())
    # surprise needs a predictor -- absent here, so no surprise rows at all.
    assert axes_present == {
        "chromaticity",
        "brightness",
        "tension",
        "stability",
        "smoothness",
        "complexity",
        "resolution",
        "finality",
    }
    # smoothness/resolution/finality are transition-only; no "chord" rows.
    transition_only = {"smoothness", "resolution", "finality"}
    for axis in transition_only:
        rows = frame.filter((pl.col("axis") == axis) & (pl.col("subject_type") == "chord"))
        assert rows.height == 0


def test_run_color_percentiles_are_ordered_and_non_degenerate(tmp_path: Path):
    # F41's "std > 0.1 per axis" check needs real-corpus scale to hold for
    # every axis; at this fixture's size, std > 0 (a genuine, non-constant
    # spread, not a data-collection bug) is what's actually checkable.
    sections = _write_sections(tmp_path / "sections.parquet", _VARIED_ROWS)
    run_color(sections, tmp_path / "missing_ngrams.parquet", tmp_path / "color.parquet")
    frame = pl.read_parquet(tmp_path / "color.parquet")
    for row in frame.iter_rows(named=True):
        assert row["p05"] <= row["p25"] <= row["p50"] <= row["p75"] <= row["p95"]
        assert row["count"] > 0
        assert row["std"] > 0.0


def test_run_color_respects_sample_cap(tmp_path: Path):
    rows = [_section_row(i, ["C:maj", "G:maj"]) for i in range(50)]
    sections = _write_sections(tmp_path / "sections.parquet", rows)
    summary = run_color(
        sections, tmp_path / "missing_ngrams.parquet", tmp_path / "color.parquet", sample_rows=10
    )
    assert summary.rows_sampled == 10


def test_run_color_skips_empty_or_keyless_sections(tmp_path: Path):
    rows = [
        _section_row(0, [], key="C major"),
        _section_row(1, ["C:maj", "G:maj"], key=""),
        _section_row(2, ["C:maj", "G:maj"], key="C major"),
    ]
    sections = _write_sections(tmp_path / "sections.parquet", rows)
    summary = run_color(sections, tmp_path / "missing_ngrams.parquet", tmp_path / "color.parquet")
    assert summary.unscored_sections == 2
    assert summary.positions_scored == 2


def test_run_color_uses_a_real_offline_predictor_when_ngrams_exist(tmp_path: Path):
    ngrams_rows = [
        {
            "context": "global",
            "order": 1,
            "history": "",
            "total": 2,
            "distinct_next": 2,
            "next": '{"M:I": 1, "M:V": 1}',
            "cont": "{}",
        },
        {
            "context": "global",
            "order": 2,
            "history": "M:V",
            "total": 10,
            "distinct_next": 1,
            "next": '{"M:I": 10}',
            "cont": '{"M:I": 1}',
        },
    ]
    ngrams_schema = {
        "context": pl.Utf8,
        "order": pl.Int64,
        "history": pl.Utf8,
        "total": pl.Int64,
        "distinct_next": pl.Int64,
        "next": pl.Utf8,
        "cont": pl.Utf8,
    }
    ngrams_path = tmp_path / "ngrams.parquet"
    pl.DataFrame(ngrams_rows, schema=ngrams_schema).write_parquet(ngrams_path)

    sections = _write_sections(tmp_path / "sections.parquet", _VARIED_ROWS)
    summary = run_color(sections, ngrams_path, tmp_path / "color.parquet")

    assert summary.used_predictor is True
    frame = pl.read_parquet(tmp_path / "color.parquet")
    assert "surprise" in set(frame["axis"].to_list())


# --- F43: run_color_profiles -------------------------------------------------


def _write_functions(path: Path, rows: list[dict]) -> Path:
    schema = {"chord": pl.Utf8, "mode": pl.Utf8, "token": pl.Utf8, "count": pl.Int64}
    pl.DataFrame(rows, schema=schema).write_parquet(path)
    return path


def _write_transitions(path: Path, rows: list[dict]) -> Path:
    schema = {
        "context": pl.Utf8,
        "from_token": pl.Utf8,
        "to_token": pl.Utf8,
        "count": pl.Int64,
        "prob": pl.Float64,
        "pmi": pl.Float64,
        "support": pl.Int64,
    }
    pl.DataFrame(rows, schema=schema).write_parquet(path)
    return path


def _write_patterns(path: Path, rows: list[dict]) -> Path:
    schema = {"pattern": pl.Utf8, "length": pl.Int64, "support": pl.Int64}
    pl.DataFrame(rows, schema=schema).write_parquet(path)
    return path


_FUNCTIONS_FIXTURE = [
    {"chord": "C:maj", "mode": "major", "token": "M:I", "count": 10},
    {"chord": "D:maj", "mode": "major", "token": "M:I", "count": 5},
    {"chord": "A:min", "mode": "minor", "token": "m:i", "count": 3},
]
_TRANSITIONS_FIXTURE = [
    {
        "context": "global",
        "from_token": "M:V",
        "to_token": "M:I",
        "count": 100,
        "prob": 0.5,
        "pmi": 0.1,
        "support": 90,
    },
    {
        "context": "genre:pop",
        "from_token": "M:V",
        "to_token": "M:I",
        "count": 20,
        "prob": 0.4,
        "pmi": 0.1,
        "support": 15,
    },
]
_PATTERNS_FIXTURE = [
    {"pattern": "M:I M:V M:vi M:IV", "length": 4, "support": 900},
    {"pattern": "M:bVI M:bVII M:I", "length": 3, "support": 30},
]


def test_run_color_profiles_covers_every_function_transition_and_pattern(tmp_path: Path):
    functions = _write_functions(tmp_path / "functions.parquet", _FUNCTIONS_FIXTURE)
    transitions = _write_transitions(tmp_path / "transitions.parquet", _TRANSITIONS_FIXTURE)
    patterns = _write_patterns(tmp_path / "patterns.parquet", _PATTERNS_FIXTURE)

    summary = run_color_profiles(
        functions,
        transitions,
        patterns,
        tmp_path / "missing_norms.parquet",
        tmp_path / "color_profiles.parquet",
    )

    # Two chords share the M:I function -> one profiled row, not two.
    assert summary.functions_profiled == 2
    # Only the "global" context transition counts, not "genre:pop".
    assert summary.transitions_profiled == 1
    assert summary.patterns_profiled == 2
    assert summary.unrealizable_skipped == 0
    assert summary.rows_written == 5

    frame = pl.read_parquet(tmp_path / "color_profiles.parquet")
    assert frame.height == 5
    assert set(frame["subject_type"].to_list()) == {"function", "transition", "pattern"}
    assert set(frame["subject_id"].to_list()) == {
        "M:I",
        "m:i",
        "M:V>M:I",
        "M:I M:V M:vi M:IV",
        "M:bVI M:bVII M:I",
    }


def test_run_color_profiles_axes_payload_has_raw_and_perceptual_sections(tmp_path: Path):
    functions = _write_functions(tmp_path / "functions.parquet", _FUNCTIONS_FIXTURE[:1])
    transitions = _write_transitions(tmp_path / "transitions.parquet", [])
    patterns = _write_patterns(tmp_path / "patterns.parquet", [])

    run_color_profiles(
        functions,
        transitions,
        patterns,
        tmp_path / "missing_norms.parquet",
        tmp_path / "color_profiles.parquet",
    )
    frame = pl.read_parquet(tmp_path / "color_profiles.parquet")
    row = frame.row(0, named=True)
    payload = json.loads(row["axes"])
    assert set(payload) == {"raw", "raw_normalized", "perceptual"}
    assert payload["raw_normalized"] == {}  # no norms artifact was supplied
    for axis in ("nostalgia", "dreaminess", "melancholy", "warmth", "openness", "cinematic"):
        entry = payload["perceptual"][axis]
        assert set(entry) == {"value", "confidence", "source", "explanation"}


def test_run_color_profiles_normalizes_raw_axes_when_norms_exist(tmp_path: Path):
    functions = _write_functions(tmp_path / "functions.parquet", _FUNCTIONS_FIXTURE[:1])
    transitions = _write_transitions(tmp_path / "transitions.parquet", [])
    patterns = _write_patterns(tmp_path / "patterns.parquet", [])
    norms_rows = [
        {
            "axis": "brightness",
            "subject_type": "chord",
            "count": 1000,
            "p05": -1.0,
            "p25": -0.3,
            "p50": 0.0,
            "p75": 0.3,
            "p95": 1.0,
            "mean": 0.0,
            "std": 0.4,
        }
    ]
    norms_path = tmp_path / "color.parquet"
    pl.DataFrame(norms_rows).write_parquet(norms_path)

    run_color_profiles(
        functions, transitions, patterns, norms_path, tmp_path / "color_profiles.parquet"
    )
    frame = pl.read_parquet(tmp_path / "color_profiles.parquet")
    payload = json.loads(frame.row(0, named=True)["axes"])
    assert "brightness" in payload["raw_normalized"]
    assert 0.0 <= payload["raw_normalized"]["brightness"] <= 1.0


def test_run_color_profiles_skips_unrealizable_tokens(tmp_path: Path):
    functions = _write_functions(
        tmp_path / "functions.parquet",
        [{"chord": "X:weird", "mode": "major", "token": "M:not-a-real-numeral", "count": 1}],
    )
    transitions = _write_transitions(tmp_path / "transitions.parquet", [])
    patterns = _write_patterns(tmp_path / "patterns.parquet", [])

    summary = run_color_profiles(
        functions,
        transitions,
        patterns,
        tmp_path / "missing_norms.parquet",
        tmp_path / "color_profiles.parquet",
    )
    assert summary.functions_profiled == 1
    assert summary.unrealizable_skipped == 1
    assert summary.rows_written == 0
