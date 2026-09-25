"""F41 `color` stage: corpus percentile norms over a sampled `sections.parquet`,
with and without a real (offline, in-memory) F30 predictor.
"""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.analyze import SECTIONS_SCHEMA  # noqa: E402
from pipeline.stages.color import run_color  # noqa: E402


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
