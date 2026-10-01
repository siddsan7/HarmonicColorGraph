"""F20 `analyze` stage: per-song key/Roman/relationship analysis over
ingest's deduped sections, run single-process and via a multiprocessing pool.
"""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.manifest import content_hash  # noqa: E402
from pipeline.stages.analyze import run_analyze  # noqa: E402
from pipeline.stages.ingest import INGEST_SCHEMA  # noqa: E402


def _write_ingest_fixture(path: Path, rows: list[dict]) -> Path:
    frame = pl.DataFrame(rows, schema=INGEST_SCHEMA)
    frame.write_parquet(path)
    return path


def _row(song_index, song_id, ordinal, section, chords, repeat_count=1, split="train"):
    return {
        "song_index": song_index,
        "song_id": song_id,
        "ordinal": ordinal,
        "section": section,
        "chords": chords,
        "genre": "pop",
        "subgenre": None,
        "decade": "2020",
        "spotify_id": None,
        "split": split,
        "repeat_count": repeat_count,
    }


def test_analyzes_a_simple_song(tmp_path: Path):
    ingest_path = _write_ingest_fixture(
        tmp_path / "ingest.parquet",
        [_row(0, "1", 0, "verse", "C F G C", repeat_count=2)],
    )
    output_path = tmp_path / "sections.parquet"

    summary = run_analyze(ingest_path, output_path)

    assert summary.songs_analyzed == 1
    assert summary.sections_written == 1
    row = pl.read_parquet(output_path).to_dicts()[0]
    assert row["local_key"] == "C major"
    assert row["tokens"] == ["M:I", "M:IV", "M:V", "M:I"]
    assert row["chords"] == ["C:maj", "F:maj", "G:maj", "C:maj"]
    assert row["repeat_count"] == 2
    assert 0.0 <= row["key_conf"] <= 1.0
    assert isinstance(row["ambiguous"], bool)
    assert isinstance(row["labels"], list)


def test_internal_regions_preserve_source_and_split_metadata(tmp_path: Path):
    text = "E B7 E A E Ab Eb7 Ab Db Ab C G7 C F C"
    ingest = _write_ingest_fixture(
        tmp_path / "ingest.parquet",
        [
            _row(0, "1", 7, None, text, repeat_count=3, split="test"),
            _row(0, "1", 9, "outro", "C F G C", split="test"),
        ],
    )
    output = tmp_path / "sections.parquet"
    summary = run_analyze(ingest, output)
    rows = pl.read_parquet(output).to_dicts()
    assert summary.tokens_total == 19
    assert [r["ordinal"] for r in rows] == [0, 1, 2, 3]
    assert [r["source_ordinal"] for r in rows] == [7, 7, 7, 9]
    assert [r["start_chord_index"] for r in rows] == [0, 5, 10, 0]
    assert [r["local_key"] for r in rows] == ["E major", "Ab major", "C major", "C major"]
    assert all(r["split"] == "test" for r in rows)
    assert all(r["repeat_count"] == 3 for r in rows[:3])
    assert all(r["figures"] == ["I", "V7", "I", "IV", "I"] for r in rows[:3])


def test_skips_song_with_no_parseable_chords(tmp_path: Path):
    ingest_path = _write_ingest_fixture(
        tmp_path / "ingest.parquet",
        [_row(0, "1", 0, "verse", "notachord alsonotachord")],
    )
    output_path = tmp_path / "sections.parquet"

    summary = run_analyze(ingest_path, output_path)

    assert summary.songs_analyzed == 0
    assert summary.songs_skipped_no_chords == 1
    assert pl.read_parquet(output_path).height == 0


def test_multiple_sections_preserve_order_and_song_grouping(tmp_path: Path):
    ingest_path = _write_ingest_fixture(
        tmp_path / "ingest.parquet",
        [
            _row(0, "1", 0, "verse", "C F G C"),
            _row(0, "1", 1, "chorus", "Am F C G"),
            _row(1, "2", 0, "verse", "G C D G"),
        ],
    )
    output_path = tmp_path / "sections.parquet"

    run_analyze(ingest_path, output_path)

    rows = pl.read_parquet(output_path).sort(["song_index", "ordinal"]).to_dicts()
    assert [(r["song_id"], r["ordinal"]) for r in rows] == [
        ("1", 0),
        ("1", 1),
        ("2", 0),
    ]


def test_single_process_and_pool_agree(tmp_path: Path):
    rows = [
        _row(index, str(index), 0, "verse", "C F G C" if index % 2 == 0 else "G C D G")
        for index in range(6)
    ]
    ingest_path = _write_ingest_fixture(tmp_path / "ingest.parquet", rows)
    output_single = tmp_path / "single.parquet"
    output_pool = tmp_path / "pool.parquet"

    run_analyze(ingest_path, output_single, workers=1)
    run_analyze(ingest_path, output_pool, workers=2)

    assert content_hash(pl.read_parquet(output_single)) == content_hash(
        pl.read_parquet(output_pool)
    )


def test_batched_writing_matches_single_batch(tmp_path: Path):
    # flush_every_rows=1 forces a flush after almost every song, exercising
    # the multi-batch ParquetWriter path; output must match one big flush.
    rows = [
        _row(index, str(index), 0, "verse", "C F G C" if index % 2 == 0 else "G C D G")
        for index in range(10)
    ]
    ingest_path = _write_ingest_fixture(tmp_path / "ingest.parquet", rows)
    output_batched = tmp_path / "batched.parquet"
    output_unbatched = tmp_path / "unbatched.parquet"

    summary_batched = run_analyze(ingest_path, output_batched, flush_every_rows=1)
    summary_unbatched = run_analyze(ingest_path, output_unbatched, flush_every_rows=10_000)

    assert summary_batched.sections_written == summary_unbatched.sections_written == 10
    assert content_hash(pl.read_parquet(output_batched)) == content_hash(
        pl.read_parquet(output_unbatched)
    )
