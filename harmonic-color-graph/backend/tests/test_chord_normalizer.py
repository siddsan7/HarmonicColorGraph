import json
from pathlib import Path

from app.theory.chord_normalizer import normalize_chord


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "samples"
    / "chord_normalization_cases.json"
)


def test_normalize_chord_matches_fixture_cases():
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for case in cases:
        result = normalize_chord(case["raw_symbol"])

        if case["expected"] is None:
            assert result.chord is None
            assert result.success is False
            assert [warning.code for warning in result.warnings] == [
                warning["code"] for warning in case["warnings"]
            ]
            continue

        assert result.success is True
        assert result.chord is not None
        assert result.chord.symbol == case["expected"]["symbol"]
        assert result.chord.root == case["expected"]["root"]
        assert result.chord.quality == case["expected"]["quality"]
        assert result.chord.bass == case["expected"]["bass"]
        assert result.chord.pitch_classes == case["expected"]["pitch_classes"]
        assert result.chord.intervals == case["expected"]["intervals"]
        assert [warning.code for warning in result.warnings] == [
            warning["code"] for warning in case["warnings"]
        ]


def test_normalize_chord_preserves_original_raw_symbol():
    result = normalize_chord(" C Maj7 ")

    assert result.success is True
    assert result.chord is not None
    assert result.chord.raw_symbol == " C Maj7 "
    assert result.chord.symbol == "C:maj7"

