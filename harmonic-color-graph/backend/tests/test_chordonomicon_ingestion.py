import json
from pathlib import Path
from uuid import uuid4

from app.ingestion.chordonomicon import load_chordonomicon_sample


def test_load_chordonomicon_sample_reports_ingestion_metrics():
    sample_path = _sample_path()
    with sample_path.open("w", encoding="utf-8") as handle:
        for index in range(1000):
            chords = ["C", "G", "Am", "F"]
            if index % 100 == 0:
                chords = ["C", "not a chord", "G"]
            handle.write(
                json.dumps(
                    {
                        "song_id": f"song_{index}",
                        "title": f"Fixture Song {index}",
                        "artist": "Fixture Artist",
                        "spotify_id": f"spotify_{index}",
                        "genre": "pop",
                        "subgenre": "fixture-pop",
                        "section": "chorus",
                        "release_date": "2012",
                        "key": "C major",
                        "chords": chords,
                    }
                )
                + "\n"
            )

    summary = load_chordonomicon_sample(sample_path)

    assert summary.rows_processed == 1000
    assert summary.progressions_loaded == 1000
    assert summary.progression_success_count == 990
    assert summary.chord_parse_success_rate > 0.99
    assert summary.warning_counts["unparseable_chord"] == 10
    assert summary.top_failures[0] == ("not a chord", 10)
    assert summary.rows[0].source_song_id == "song_0"
    assert summary.rows[0].genre == "pop"


def test_load_chordonomicon_sample_supports_limit():
    sample_path = _sample_path()
    with sample_path.open("w", encoding="utf-8") as handle:
        for index in range(20):
            handle.write(
                json.dumps(
                    {
                        "song_id": f"song_{index}",
                        "genre": "rock",
                        "section": "verse",
                        "key": "G major",
                        "chords": ["G", "D", "Em", "C"],
                    }
                )
                + "\n"
            )

    summary = load_chordonomicon_sample(sample_path, limit=5)

    assert summary.rows_processed == 5
    assert summary.progressions_loaded == 5
    assert all(row.source == "Chordonomicon" for row in summary.rows)


def _sample_path() -> Path:
    directory = Path(__file__).resolve().parents[1] / ".tmp" / "ingestion-tests"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"chordonomicon_sample_{uuid4().hex}.jsonl"
