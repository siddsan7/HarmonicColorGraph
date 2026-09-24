"""F21 `corpus-report`: histogram, ambiguity/modulation/label-coverage
rates, top tokens, and the musician spot-check sample, over a small
`sections.parquet` fixture.
"""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.analyze import SECTIONS_SCHEMA  # noqa: E402
from pipeline.stages.corpus_report import (  # noqa: E402
    _display_chord,
    build_corpus_report,
    render_corpus_report_markdown,
)


def _section_row(
    song_id,
    ordinal,
    section,
    local_key,
    key_conf,
    ambiguous,
    tokens,
    figures,
    chords,
    labels,
    genre="pop",
    decade="2020",
):
    return {
        "song_index": int(song_id),
        "song_id": song_id,
        "ordinal": ordinal,
        "section": section,
        "local_key": local_key,
        "key_conf": key_conf,
        "ambiguous": ambiguous,
        "tokens": tokens,
        "figures": figures,
        "chords": chords,
        "labels": labels,
        "genre": genre,
        "decade": decade,
        "spotify_id": None,
        "split": "train",
        "repeat_count": 1,
    }


def _write_sections_fixture(path: Path, rows: list[dict]) -> Path:
    frame = pl.DataFrame(rows, schema=SECTIONS_SCHEMA)
    frame.write_parquet(path)
    return path


def test_display_chord_converts_canonical_symbol():
    assert _display_chord("C:maj") == "C"
    assert _display_chord("F:min7") == "Fm7"
    assert _display_chord("G:dom7/B") == "G7/B"


def test_build_corpus_report_metrics(tmp_path: Path):
    rows = [
        _section_row(
            "1",
            0,
            "verse",
            "C major",
            0.97,
            False,
            ["M:I", "M:IV", "M:V", "M:I"],
            ["I", "IV", "V", "I"],
            ["C:maj", "F:maj", "G:maj", "C:maj"],
            ["rule:cadence"],
        ),
        _section_row(
            "1",
            1,
            "chorus",
            "G major",
            0.4,
            False,
            ["M:I", "M:V"],
            ["I", "V"],
            ["G:maj", "D:maj"],
            [],
        ),
        _section_row(
            "2",
            0,
            "verse",
            "A minor",
            0.6,
            True,
            ["m:i", "m:iv"],
            ["i", "iv"],
            ["A:min", "D:min"],
            [],
        ),
    ]
    sections_path = _write_sections_fixture(tmp_path / "sections.parquet", rows)

    report = build_corpus_report(
        sections_path,
        version="cv-test",
        sample_seed=1,
        sample_size=2,
        top_n=10,
        external_parse_rate=0.999683,
        external_parse_rate_source="docs/eval/vocab.md",
    )

    assert report.songs == 2
    assert report.sections == 3
    assert report.tokens == 8
    assert report.ambiguous_song_rate == 0.5  # song "2" is ambiguous, song "1" is not
    assert report.modulation_song_rate == 0.5  # song "1" has two distinct local keys
    assert report.label_coverage_rate == pytest.approx(1 / 3)
    assert ("M:I", 3) in report.top_core_tokens
    assert len(report.sample_songs) == 2

    markdown = render_corpus_report_markdown(report)
    assert "cv-test" in markdown
    assert "99.9683%" in markdown
    assert "Spot-check sample (2 songs)" in markdown
