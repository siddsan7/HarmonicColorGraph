from app.theory.relationships import (
    label_progression_relationships,
    label_transition,
)
from app.theory.roman_analysis import analyze_progression


def labels_for(from_roman: str, to_roman: str, mode: str = "major") -> list[str]:
    return label_transition(from_roman, to_roman, mode).relationship_labels


def test_labels_required_cadences():
    assert "authentic cadence" in labels_for("V", "I")
    assert "dominant resolution" in labels_for("V", "I")
    assert "plagal cadence" in labels_for("IV", "I")
    assert "minor plagal cadence" in labels_for("iv", "I")
    assert "modal interchange" in labels_for("iv", "I")
    assert "deceptive cadence" in labels_for("V", "vi")


def test_labels_subv_like_resolution_from_analyzed_chords():
    analysis = analyze_progression(["Db7", "C"], key="C major")
    relationships = label_progression_relationships(
        analysis.roman_chords,
        mode_context=analysis.mode,
    )

    assert analysis.roman_chords == ["bII7", "I"]
    assert "tritone substitution" in relationships[0].relationship_labels
    assert "subV-like resolution" in relationships[0].relationship_labels


def test_labels_circle_motion_and_secondary_dominant():
    assert "circle-of-fifths motion" in labels_for("ii", "V")
    assert "secondary dominant" in labels_for("V/vi", "vi")


def test_transition_explanations_are_creator_safe():
    transition = label_transition("iv", "I", "major")

    assert transition.short_explanation is not None
    assert "borrowed minor iv" in transition.short_explanation
    assert transition.technical_explanation is not None
    assert "parallel minor" in transition.technical_explanation

