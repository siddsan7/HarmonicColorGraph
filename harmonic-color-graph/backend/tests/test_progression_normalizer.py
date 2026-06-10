from app.theory.progression_normalizer import normalize_progression


def test_normalize_progression_splits_dash_separated_string():
    result = normalize_progression("C - G - Am - F")

    assert result.success is True
    assert [chord.symbol for chord in result.chords] == [
        "C:maj",
        "G:maj",
        "A:min",
        "F:maj",
    ]
    assert result.skipped_tokens == []
    assert result.chord_parse_success_rate == 1.0


def test_normalize_progression_retains_valid_chords_and_reports_skips():
    result = normalize_progression(["C", "not a chord", "Gsus4"])

    assert result.success is False
    assert [chord.symbol for chord in result.chords] == ["C:maj", "G:sus4"]
    assert result.skipped_tokens == ["not a chord"]
    assert result.chord_parse_success_rate == 2 / 3
    assert [warning.code for warning in result.warnings] == ["unparseable_chord"]


def test_normalize_progression_handles_commas_and_empty_tokens():
    result = normalize_progression("C, G,, Am, F")

    assert result.success is True
    assert [chord.symbol for chord in result.chords] == [
        "C:maj",
        "G:maj",
        "A:min",
        "F:maj",
    ]
    assert result.skipped_tokens == []

