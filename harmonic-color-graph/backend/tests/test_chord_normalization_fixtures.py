import json
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "samples"
    / "chord_normalization_cases.json"
)


def test_chord_normalization_fixture_contains_required_cases():
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    by_raw_symbol = {case["raw_symbol"]: case for case in cases}

    required_symbols = {
        "Cmaj7",
        "CM7",
        "C major 7",
        "C Maj7",
        "C/E",
        "Gsus4",
        "F#m7b5",
        "not a chord",
    }

    assert required_symbols.issubset(by_raw_symbol.keys())
    assert by_raw_symbol["CM7"]["expected"]["symbol"] == "C:maj7"
    assert by_raw_symbol["C/E"]["expected"]["symbol"] == "C:maj/E"
    assert by_raw_symbol["F#m7b5"]["expected"]["symbol"] == "F#:min7b5"
    assert by_raw_symbol["not a chord"]["expected"] is None
    assert by_raw_symbol["not a chord"]["warnings"][0]["code"] == "unparseable_chord"


def test_chord_normalization_fixture_cases_are_self_describing():
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for case in cases:
        assert case["raw_symbol"]
        assert case["description"]
        assert "expected" in case
        assert "warnings" in case

