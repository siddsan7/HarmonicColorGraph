import json
from pathlib import Path
from uuid import uuid4

from app.services.quality_metrics import (
    build_quality_metrics_report,
    save_quality_metrics_report,
)


def test_build_quality_metrics_report_from_local_sample():
    sample_path = _sample_path()
    _write_sample(sample_path)

    report = build_quality_metrics_report(sample_path)

    assert report["rows_processed"] == 30
    assert report["chord_parse_success_rate"] > 0.9
    assert report["progression_parse_success_rate"] > 0.9
    assert report["normalized_progression_count"] == 30
    assert report["transition_edge_count"] > 0
    assert report["top_global_transitions"]
    assert report["roman_confidence_distribution"]["min"] > 0
    assert report["theory_label_coverage"] > 0
    assert report["api_latency_ms"] >= 0
    assert report["top_unparseable_symbols"][0] == ["not a chord", 1]


def test_save_quality_metrics_report_writes_json():
    sample_path = _sample_path()
    output_path = _sample_path().with_suffix(".report.json")
    _write_sample(sample_path)
    report = build_quality_metrics_report(sample_path)

    save_quality_metrics_report(report, output_path)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["rows_processed"] == report["rows_processed"]
    assert saved["top_global_transitions"] == report["top_global_transitions"]


def _sample_path() -> Path:
    directory = Path(__file__).resolve().parents[1] / ".tmp" / "metrics-tests"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"chordonomicon_metrics_{uuid4().hex}.jsonl"


def _write_sample(path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for index in range(30):
            chords = ["C", "G", "Am", "F"]
            if index == 0:
                chords = ["C", "not a chord", "G"]
            handle.write(
                json.dumps(
                    {
                        "song_id": f"song_{index}",
                        "genre": "pop",
                        "section": "chorus",
                        "key": "C major",
                        "chords": chords,
                    }
                )
                + "\n"
            )

