"""F40 `voice_leading` stage: top-per-source selection, real voice-leading
metrics on chord-label input, and unparseable-chord handling.
"""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.voice_leading import run_voice_leading  # noqa: E402


def _write_fixture(path: Path, rows: list[dict]) -> Path:
    pl.DataFrame(
        rows, schema={"from_chord": pl.Utf8, "to_chord": pl.Utf8, "count": pl.Int64}
    ).write_parquet(path)
    return path


def test_computes_real_voice_leading_metrics(tmp_path: Path):
    src = _write_fixture(
        tmp_path / "abs_transitions.parquet",
        [{"from_chord": "C:maj", "to_chord": "A:min", "count": 100}],
    )
    summary = run_voice_leading(src, tmp_path / "voice_leads.parquet")
    assert summary.rows_written == 1
    frame = pl.read_parquet(tmp_path / "voice_leads.parquet")
    row = frame.row(0, named=True)
    assert row["from_chord"] == "C:maj"
    assert row["to_chord"] == "A:min"
    assert row["common_tones"] == 2
    assert row["parsimonious"] == "R"
    assert row["total_motion"] >= 0


def test_keeps_only_top_targets_per_source(tmp_path: Path):
    rows = [
        {"from_chord": "C:maj", "to_chord": "F:maj", "count": 50},
        {"from_chord": "C:maj", "to_chord": "G:maj", "count": 40},
        {"from_chord": "C:maj", "to_chord": "A:min", "count": 30},
        {"from_chord": "C:maj", "to_chord": "D:min", "count": 20},
        {"from_chord": "C:maj", "to_chord": "E:min", "count": 10},
        {"from_chord": "C:maj", "to_chord": "B:dim", "count": 5},
    ]
    src = _write_fixture(tmp_path / "abs_transitions.parquet", rows)
    summary = run_voice_leading(src, tmp_path / "voice_leads.parquet", top_per_source=3)
    frame = pl.read_parquet(tmp_path / "voice_leads.parquet")
    assert summary.rows_written == 3
    assert set(frame["to_chord"]) == {"F:maj", "G:maj", "A:min"}


def test_top_targets_are_independent_per_source(tmp_path: Path):
    rows = [
        {"from_chord": "C:maj", "to_chord": "F:maj", "count": 50},
        {"from_chord": "C:maj", "to_chord": "G:maj", "count": 10},
        {"from_chord": "G:maj", "to_chord": "C:maj", "count": 5},
    ]
    src = _write_fixture(tmp_path / "abs_transitions.parquet", rows)
    summary = run_voice_leading(src, tmp_path / "voice_leads.parquet", top_per_source=1)
    frame = pl.read_parquet(tmp_path / "voice_leads.parquet")
    assert summary.rows_written == 2
    assert set(zip(frame["from_chord"], frame["to_chord"], strict=True)) == {
        ("C:maj", "F:maj"),
        ("G:maj", "C:maj"),
    }


def test_unparseable_chords_are_skipped_not_fatal(tmp_path: Path):
    rows = [
        {"from_chord": "C:maj", "to_chord": "A:min", "count": 10},
        {"from_chord": "X:bogus", "to_chord": "C:maj", "count": 5},
    ]
    src = _write_fixture(tmp_path / "abs_transitions.parquet", rows)
    summary = run_voice_leading(src, tmp_path / "voice_leads.parquet")
    assert summary.rows_written == 1
    assert "X:bogus" in summary.unparseable_chords
    frame = pl.read_parquet(tmp_path / "voice_leads.parquet")
    assert frame["from_chord"].to_list() == ["C:maj"]


def test_budget_estimate_scales_with_rows(tmp_path: Path):
    src = _write_fixture(
        tmp_path / "abs_transitions.parquet",
        [{"from_chord": "C:maj", "to_chord": "A:min", "count": 10}],
    )
    summary = run_voice_leading(src, tmp_path / "voice_leads.parquet")
    assert summary.budget_estimate_mb > 0
