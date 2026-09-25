"""F43 color/profile.py: reconstructing a progression from Roman-token
labels alone, and computing a color profile for a Function/Transition/
Pattern subject."""

import pytest

from app.color.norms import AxisNorm
from app.color.profile import (
    ColorProfile,
    compute_color_profile,
    mode_of,
    realize_progression,
    transition_subject_id,
)


def test_mode_of_reads_the_core_token_prefix():
    assert mode_of("M:I") == "major"
    assert mode_of("m:i") == "minor"


def test_mode_of_rejects_a_non_core_token():
    with pytest.raises(ValueError):
        mode_of("F")


def test_transition_subject_id_is_unambiguous_against_applied_chord_slashes():
    subject_id = transition_subject_id("M:V7/vi", "M:vi")
    assert subject_id == "M:V7/vi>M:vi"
    # round-trips cleanly on the first top-level '>', not any '/'
    from_part, _, to_part = subject_id.partition(">")
    assert from_part == "M:V7/vi"
    assert to_part == "M:vi"


def test_realize_progression_round_trips_a_plagal_cadence():
    chords, tokens = realize_progression(["M:iv", "M:I"], "C major")
    assert [chord.raw_symbol for chord in chords] == ["Fm", "C"]
    assert [token.core for token in tokens] == ["M:iv", "M:I"]


def test_realize_progression_preserves_an_applied_dominant():
    chords, tokens = realize_progression(["M:V7/vi", "M:vi"], "C major")
    assert tokens[0].applied_to == "vi"
    assert tokens[0].core == "M:V7/vi"
    assert tokens[1].core == "M:vi"


def test_realize_progression_rejects_empty_input():
    with pytest.raises(ValueError):
        realize_progression([], "C major")


def test_raw_axes_are_transposition_invariant_across_reference_keys():
    from app.color.features import compute_chord_color

    reference = compute_color_profile("transition", "M:iv>M:I", ["M:iv", "M:I"])
    for other_key in ["D major", "F major", "G major"]:
        chords, tokens = realize_progression(["M:iv", "M:I"], other_key)
        raw = compute_chord_color(
            chords[-1],
            tokens[-1],
            other_key,
            previous_chord=chords[-2],
            previous_token=tokens[-2],
        )
        assert raw.chromaticity == reference.raw["chromaticity"]
        assert raw.brightness == pytest.approx(reference.raw["brightness"])
        assert raw.smoothness == pytest.approx(reference.raw["smoothness"])


def test_compute_color_profile_function_has_no_transition_axes():
    profile = compute_color_profile("function", "M:I", ["M:I"], support=100)
    assert isinstance(profile, ColorProfile)
    assert profile.subject_type == "function"
    assert profile.mode == "major"
    assert profile.support == 100
    assert profile.raw["smoothness"] is None
    assert profile.raw["resolution"] is None


def test_compute_color_profile_transition_populates_every_raw_axis():
    profile = compute_color_profile("transition", "M:V>M:I", ["M:V", "M:I"], support=40)
    assert profile.raw["smoothness"] is not None
    assert profile.raw["resolution"] is not None
    assert profile.raw["finality"] is not None


def test_compute_color_profile_pattern_uses_the_full_sequence_for_perceptual_axes():
    profile = compute_color_profile(
        "pattern", "M:bVI M:bVII M:I", ["M:bVI", "M:bVII", "M:I"], support=30
    )
    assert profile.subject_type == "pattern"
    # The curated Aeolian rule should fire over the full 3-token pattern.
    assert profile.perceptual.cinematic.source == "rule"


def test_compute_color_profile_minor_mode_function():
    profile = compute_color_profile("function", "m:i", ["m:i"], support=10)
    assert profile.mode == "minor"


def test_compute_color_profile_without_norms_leaves_raw_normalized_empty():
    profile = compute_color_profile("function", "M:I", ["M:I"])
    assert profile.raw_normalized == {}


def test_compute_color_profile_with_norms_populates_raw_normalized():
    norms = {
        ("brightness", "chord"): AxisNorm(
            axis="brightness",
            subject_type="chord",
            count=1000,
            p05=-1.0,
            p25=-0.3,
            p50=0.0,
            p75=0.3,
            p95=1.0,
            mean=0.0,
            std=0.4,
        )
    }
    profile = compute_color_profile("function", "M:I", ["M:I"], norms=norms)
    assert "brightness" in profile.raw_normalized
    assert 0.0 <= profile.raw_normalized["brightness"] <= 1.0
    # chromaticity has no matching norm entry, so it's simply absent
    assert "chromaticity" not in profile.raw_normalized
