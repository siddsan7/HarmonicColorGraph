from app.theory.roman_analysis import analyze_progression


def test_analyze_progression_uses_provided_major_key():
    analysis = analyze_progression(["C", "G", "Am", "F"], key="C major")

    assert analysis.key == "C major"
    assert analysis.mode == "major"
    assert analysis.method == "provided_key"
    assert analysis.confidence == 1.0
    assert analysis.roman_chords == ["I", "V", "vi", "IV"]


def test_analyze_progression_handles_common_regression_cases():
    assert analyze_progression(["F", "G", "C"], key="C major").roman_chords == [
        "IV",
        "V",
        "I",
    ]
    assert analyze_progression(["Dm", "G", "C"], key="C major").roman_chords == [
        "ii",
        "V",
        "I",
    ]


def test_analyze_progression_preserves_ambiguity_when_key_is_missing():
    analysis = analyze_progression(["Am", "F", "C", "G"])

    assert analysis.key == "C major"
    assert analysis.method == "diatonic_fit_plus_terminal_chord"
    assert analysis.confidence < 1.0
    assert analysis.roman_chords == ["vi", "IV", "I", "V"]
    assert any(candidate.key == "A minor" for candidate in analysis.alternate_analyses)


def test_analyze_progression_marks_unparseable_chords_as_warnings():
    analysis = analyze_progression(["C", "not a chord", "G"], key="C major")

    assert analysis.roman_chords == ["I", "V"]
    assert analysis.confidence < 1.0
    assert [warning.code for warning in analysis.warnings] == ["unparseable_chord"]

