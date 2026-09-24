"""F20 `ingest` stage: within-song dedupe, split assignment, determinism."""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.manifest import content_hash  # noqa: E402
from pipeline.stages.ingest import assign_split, run_ingest  # noqa: E402

CSV_HEADER = (
    "id,chords,release_date,genres,decade,rock_genre,artist_id,"
    "main_genre,spotify_song_id,spotify_artist_id\n"
)


def _write_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(CSV_HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_dedupes_identical_sections_within_a_song(tmp_path: Path):
    source = _write_csv(
        tmp_path / "source.csv",
        [
            "1,<verse_1> C F G C <verse_2> C F G C <chorus_1> Am F C G,,,,,artist_1,pop,,",
        ],
    )
    output = tmp_path / "ingest.parquet"

    summary = run_ingest(source, output)

    assert summary.songs_processed == 1
    assert summary.sections_total == 3
    assert summary.sections_after_dedupe == 2

    frame = pl.read_parquet(output)
    rows = frame.sort("ordinal").to_dicts()
    assert [row["section"] for row in rows] == ["verse", "chorus"]
    assert rows[0]["repeat_count"] == 2
    assert rows[1]["repeat_count"] == 1


def test_split_assignment_is_deterministic_and_covers_all_buckets():
    splits = {assign_split(f"song-{i}") for i in range(200)}
    assert splits == {"train", "dev", "test"}
    assert assign_split("song-42") == assign_split("song-42")


def test_split_filter_train_only(tmp_path: Path):
    source = _write_csv(
        tmp_path / "source.csv",
        [f"{i},<verse_1> C F G C,,,,,artist_{i},pop,," for i in range(1, 21)],
    )
    output_all = tmp_path / "all.parquet"
    output_train = tmp_path / "train.parquet"

    summary_all = run_ingest(source, output_all, split_filter="all")
    summary_train = run_ingest(source, output_train, split_filter="train")

    assert summary_train.songs_processed < summary_all.songs_processed
    assert set(pl.read_parquet(output_train)["split"].unique().to_list()) == {"train"}


def test_run_twice_yields_identical_content_hash(tmp_path: Path):
    source = _write_csv(
        tmp_path / "source.csv",
        [f"{i},<verse_1> C F G C <chorus_1> Am F C G,,,,,artist_{i},pop,," for i in range(1, 11)],
    )
    output_a = tmp_path / "a.parquet"
    output_b = tmp_path / "b.parquet"

    run_ingest(source, output_a)
    run_ingest(source, output_b)

    assert content_hash(pl.read_parquet(output_a)) == content_hash(pl.read_parquet(output_b))


def test_limit_caps_song_count_not_section_count(tmp_path: Path):
    source = _write_csv(
        tmp_path / "source.csv",
        [
            f"{i},<verse_1> C F <chorus_1> Am G <bridge_1> F G,,,,,artist_{i},pop,,"
            for i in range(1, 6)
        ],
    )
    output = tmp_path / "ingest.parquet"

    summary = run_ingest(source, output, limit=2)

    assert summary.songs_processed == 2
    frame = pl.read_parquet(output)
    assert frame["song_id"].n_unique() == 2
