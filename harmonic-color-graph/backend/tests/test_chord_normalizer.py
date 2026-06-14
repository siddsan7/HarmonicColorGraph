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


def test_normalize_chord_accepts_chordonomicon_sharp_alias():
    result = normalize_chord("A/Cs")

    assert result.success is True
    assert result.chord is not None
    assert result.chord.symbol == "A:maj/C#"


def test_normalize_chord_disambiguates_sus_from_sharp_alias():
    result = normalize_chord("Bsus4")

    assert result.success is True
    assert result.chord is not None
    assert result.chord.symbol == "B:sus4"


def test_normalize_chord_accepts_chordonomicon_no_third_quality():
    result = normalize_chord("Csno3d")

    assert result.success is True
    assert result.chord is not None
    assert result.chord.symbol == "C#:no3"


def test_normalize_chord_accepts_common_chordonomicon_extensions():
    dominant_sus = normalize_chord("D7sus4")
    thirteenth = normalize_chord("Ab13")

    assert dominant_sus.chord is not None
    assert dominant_sus.chord.symbol == "D:7sus4"
    assert thirteenth.chord is not None
    assert thirteenth.chord.symbol == "Ab:13"


def test_normalize_chord_accepts_chordonomicon_extended_qualities():
    cases = {
        "Eminadd9": "E:minadd9",
        "Fmaj7sus2": "F:maj7sus2",
        "Fmaj911s": "F:maj9#11",
        "Csaugmaj7/A": "C#:augmaj7/A",
        "Gmin13/G": "G:min13/G",
        "Gminmaj7": "G:minmaj7",
        "Aminadd11": "A:minadd11",
        "C7sus2": "C:7sus2",
        "C13b": "C:13b",
        "Fmaj13": "F:maj13",
    }

    for raw_symbol, expected_symbol in cases.items():
        result = normalize_chord(raw_symbol)

        assert result.success is True
        assert result.chord is not None
        assert result.chord.symbol == expected_symbol
