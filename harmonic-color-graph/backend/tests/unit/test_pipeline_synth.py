"""F20 `synth`: the deterministic synthetic mini corpus generator."""

from pathlib import Path

from app.ingestion.chordonomicon import iter_chordonomicon_rows
from pipeline.synth import CSV_FIELDS, build_mini_corpus, write_mini_corpus


def test_deterministic_for_a_fixed_seed():
    first = build_mini_corpus(song_count=20, seed=1)
    second = build_mini_corpus(song_count=20, seed=1)
    assert first == second


def test_different_seeds_diverge():
    first = build_mini_corpus(song_count=20, seed=1)
    second = build_mini_corpus(song_count=20, seed=2)
    assert first != second


def test_every_chord_token_parses(tmp_path: Path):
    output = write_mini_corpus(tmp_path / "mini_corpus.csv", song_count=30, seed=1)
    for row in iter_chordonomicon_rows(output):
        normalized = row.normalized_progression
        assert not normalized.skipped_tokens, (row.source_song_id, normalized.skipped_tokens)


def test_song_count_and_unique_ids():
    rows = build_mini_corpus(song_count=50, seed=1)
    assert len(rows) == 50
    assert len({row["id"] for row in rows}) == 50


def test_write_mini_corpus_matches_chordonomicon_csv_shape(tmp_path: Path):
    output = write_mini_corpus(tmp_path / "mini_corpus.csv", song_count=10, seed=1)
    header = output.read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",") == CSV_FIELDS
