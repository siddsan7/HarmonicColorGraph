"""F43 app/services/color_profile.py: the progression arc, the weighted
raw-axis summary, and drivers."""

import pytest

from app.services.color_profile import (
    BORROWED_CHORD_BONUS,
    FINAL_POSITION_BONUS,
    build_arc,
    build_summary_and_drivers,
    compute_color_compare,
    compute_color_profile,
)
from app.theory.roman import analyze_v2


def test_build_arc_one_point_per_chord():
    result = analyze_v2("C Am F G", "C major")
    arc = build_arc(result.chords, result.tokens, "C major")
    assert [point.position for point in arc] == [0, 1, 2, 3]
    assert arc[0].raw.smoothness is None  # nothing to transition from
    assert arc[1].raw.smoothness is not None


def test_build_arc_perceptual_axes_are_prefix_based():
    """Position i's perceptual read should match compute_perceptual_color
    over just the prefix up to i, not the whole progression."""
    from app.color.perceptual import compute_perceptual_color

    result = analyze_v2("Fm C G", "C major")
    arc = build_arc(result.chords, result.tokens, "C major")
    prefix_only = compute_perceptual_color(result.chords[:2], result.tokens[:2], "C major")
    assert arc[1].perceptual.nostalgia.value == prefix_only.nostalgia.value


def test_summary_final_position_and_borrowed_chord_are_upweighted():
    result = analyze_v2("Fm C Am F", "C major")  # Fm (borrowed) is position 0
    arc = build_arc(result.chords, result.tokens, "C major")
    raw_summary, drivers = build_summary_and_drivers(arc)

    reasons = {(d.position, d.reason) for d in drivers}
    assert (3, "final_cadence") in reasons
    assert (0, "borrowed_chord") in reasons
    assert any(d.weight == FINAL_POSITION_BONUS for d in drivers)
    assert any(d.weight == BORROWED_CHORD_BONUS for d in drivers)


def test_summary_raw_axis_skips_positions_where_it_is_undefined():
    result = analyze_v2("C Am", "C major")
    arc = build_arc(result.chords, result.tokens, "C major")
    raw_summary, _ = build_summary_and_drivers(arc)
    # smoothness only exists at position 1 (a transition); the weighted
    # average must not be dragged toward 0 by position 0's missing value.
    assert raw_summary["smoothness"] == pytest.approx(arc[1].raw.smoothness)


def test_compute_color_profile_summary_perceptual_equals_last_arc_point():
    profile = compute_color_profile("Cmaj7 Em7 Am7", "C major")
    last = profile.arc[-1]
    assert profile.summary.perceptual["dreaminess"].value == last.perceptual["dreaminess"].value


def test_compute_color_profile_rejects_an_unparseable_progression():
    with pytest.raises(ValueError):
        compute_color_profile("zzz qqq", "C major")


def test_compute_color_compare_deltas_are_b_minus_a():
    profile_a, profile_b, raw_deltas, perceptual_deltas = compute_color_compare(
        "Fm C", "C major", "F C", "C major"
    )
    assert perceptual_deltas["nostalgia"] == pytest.approx(
        profile_b.summary.perceptual["nostalgia"].value
        - profile_a.summary.perceptual["nostalgia"].value
    )
    assert perceptual_deltas["nostalgia"] < 0
