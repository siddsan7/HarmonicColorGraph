import pytest
from pydantic import ValidationError

from app.schemas.harmony import (
    AnalyzeProgressionRequest,
    AnalyzeProgressionResponse,
    CanonicalChord,
    KeyAnalysis,
    NormalizedProgression,
    ParseWarning,
    RomanAnalysis,
    TransitionCandidate,
    TransitionRecord,
)


def test_phase_one_schemas_preserve_analysis_context():
    warning = ParseWarning(
        code="alias_normalized",
        message="Normalized CM7 to C:maj7.",
        raw_value="CM7",
    )
    chord = CanonicalChord(
        raw_symbol="CM7",
        symbol="C:maj7",
        root="C",
        quality="maj7",
        pitch_classes=[0, 4, 7, 11],
        intervals=[0, 4, 7, 11],
        bass=None,
        warnings=[warning],
    )
    progression = NormalizedProgression(
        raw_input="CM7 - G - Am - F",
        chords=[chord],
        skipped_tokens=[],
        warnings=[warning],
        success=True,
        chord_parse_success_rate=1.0,
    )
    alternate = KeyAnalysis(
        key="A minor",
        mode="minor",
        confidence=0.48,
        method="diatonic_fit",
        roman_chords=["IIImaj7", "VII", "i", "VI"],
    )
    roman = RomanAnalysis(
        key="C major",
        mode="major",
        confidence=0.92,
        method="provided_key",
        roman_chords=["Imaj7", "V", "vi", "IV"],
        alternate_analyses=[alternate],
        warnings=[],
    )
    transition = TransitionRecord(
        from_roman="V",
        to_roman="vi",
        mode_context="major",
        count=42,
        probability=0.21,
        genre="pop",
        section="chorus",
        relationship_labels=["deceptive cadence"],
    )
    response = AnalyzeProgressionResponse(
        absolute_chords=["C:maj7", "G:maj", "A:min", "F:maj"],
        roman_chords=["Imaj7", "V", "vi", "IV"],
        detected_key="C major",
        confidence=0.92,
        warnings=[warning],
        relationships=[transition],
    )

    assert progression.chords[0].symbol == "C:maj7"
    assert roman.alternate_analyses[0].key == "A minor"
    assert response.relationships[0].relationship_labels == ["deceptive cadence"]


def test_api_request_rejects_empty_chord_list():
    with pytest.raises(ValidationError):
        AnalyzeProgressionRequest(chords=[], key="C major")


def test_confidence_and_probability_are_bounded():
    with pytest.raises(ValidationError):
        RomanAnalysis(
            key="C major",
            mode="major",
            confidence=1.4,
            method="provided_key",
            roman_chords=["I"],
        )

    with pytest.raises(ValidationError):
        TransitionCandidate(
            chord="IV",
            probability=-0.1,
            relationship="common pop resolution",
        )


def test_canonical_chord_rejects_empty_symbol_and_invalid_root():
    with pytest.raises(ValidationError):
        CanonicalChord(
            raw_symbol="",
            symbol="",
            root="H",
            quality="maj",
            pitch_classes=[0, 4, 7],
            intervals=[0, 4, 7],
        )

