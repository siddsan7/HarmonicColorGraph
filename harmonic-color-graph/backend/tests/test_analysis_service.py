from app.services.analysis import analyze_progression_service


def test_analysis_service_returns_analyze_progression_response_shape():
    response = analyze_progression_service(["C", "G", "Am", "F"], key="C major")

    assert response.absolute_chords == ["C:maj", "G:maj", "A:min", "F:maj"]
    assert response.roman_chords == ["I", "V", "vi", "IV"]
    assert response.detected_key == "C major"
    assert response.confidence == 1.0
    assert [(item.from_roman, item.to_roman) for item in response.relationships] == [
        ("I", "V"),
        ("V", "vi"),
        ("vi", "IV"),
    ]
    assert "deceptive cadence" in response.relationships[1].relationship_labels


def test_analysis_service_covers_phase_one_regression_cases():
    assert analyze_progression_service(["F", "G", "C"], key="C major").roman_chords == [
        "IV",
        "V",
        "I",
    ]
    assert analyze_progression_service(["Dm", "G", "C"], key="C major").roman_chords == [
        "ii",
        "V",
        "I",
    ]
    assert analyze_progression_service(["Fm", "C"], key="C major").roman_chords == [
        "iv",
        "I",
    ]
    assert analyze_progression_service(["G", "Am"], key="C major").roman_chords == [
        "V",
        "vi",
    ]


def test_analysis_service_propagates_warnings_and_confidence():
    response = analyze_progression_service(["C", "not a chord", "G"], key="C major")

    assert response.absolute_chords == ["C:maj", "G:maj"]
    assert response.roman_chords == ["I", "V"]
    assert response.confidence < 1.0
    assert [warning.code for warning in response.warnings] == ["unparseable_chord"]

