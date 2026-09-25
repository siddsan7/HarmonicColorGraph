"""F41 color/features.py: the Phase 2 §12.1 sanity suite plus targeted
coverage for each axis's raw-value formula.
"""

from app.color.features import (
    brightness,
    chromaticity,
    complexity,
    compute_chord_color,
    resolution,
    smoothness,
    stability,
    surprise,
    tension,
)
from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.theory.roman import analyze_v2


def _analyze(chords: str, key: str = "C major"):
    result = analyze_v2(chords, key)
    return result.chords, result.tokens


def test_resolution_authentic_beats_deceptive():
    chords, tokens = _analyze("G C Am")
    res_authentic = resolution(tokens[0], tokens[1])
    res_deceptive = resolution(tokens[0], tokens[2])
    assert res_authentic > res_deceptive


def test_brightness_major_iv_beats_borrowed_minor_iv():
    _, major_tokens = _analyze("F")  # IV in C major
    _, minor_tokens = _analyze("Fm")  # borrowed iv in C major
    assert brightness(minor_tokens[0], "C major") < brightness(major_tokens[0], "C major")


def test_tension_dominant_seventh_beats_tonic():
    _, tokens = _analyze("G7 C")
    assert tension(tokens[0], "C major") > tension(tokens[1], "C major")


def test_chromaticity_borrowed_progression_beats_diatonic_progression():
    chromatic_chords, chromatic_tokens = _analyze("Ab Bb C")  # bVI bVII I
    diatonic_chords, diatonic_tokens = _analyze("F G C")  # IV V I

    def _total(tokens):
        total = chromaticity(tokens[0], "C major")
        for index in range(1, len(tokens)):
            total += chromaticity(tokens[index], "C major", previous=tokens[index - 1])
        return total

    assert _total(chromatic_tokens) > _total(diatonic_tokens)


def test_smoothness_common_tone_progression_is_smooth():
    chords, tokens = _analyze("C Em Am")  # I iii vi
    smooth_values = [
        smoothness(chords[index], chords[index - 1]) for index in range(1, len(chords))
    ]
    assert all(value is not None for value in smooth_values)
    assert sum(smooth_values) / len(smooth_values) >= 0.7


def test_surprise_uses_predictor_and_ranks_rare_target_higher():
    store = InMemoryNgramStore()
    store.add_row(
        "global", 1, "", total=100, distinct_next=2, next={"M:I": 60, "M:vi": 40}, cont={}
    )
    store.add_row(
        "global",
        2,
        "M:V",
        total=100,
        distinct_next=2,
        next={"M:I": 90, "M:vi": 10},
        cont={"M:I": 1, "M:vi": 1},
    )
    predictor = KNPredictor(store=store)
    _, tokens = _analyze("G C")
    common = surprise(tokens[1], ["M:V"], predictor)
    _, deceptive_tokens = _analyze("G Am")
    rare = surprise(deceptive_tokens[1], ["M:V"], predictor)
    assert common is not None and rare is not None
    assert rare > common


def test_surprise_is_none_without_a_predictor():
    _, tokens = _analyze("G C")
    assert surprise(tokens[1], ["M:V"], None) is None


def test_complexity_grows_with_extensions_and_tone_count():
    _, triad = _analyze("C")
    _, seventh = _analyze("Cmaj7")
    assert complexity(seventh[0]) > complexity(triad[0])


def test_stability_tonic_root_position_beats_dominant_seventh():
    _, tokens = _analyze("G7 C")
    assert stability(tokens[1], "C major") > stability(tokens[0], "C major")


def test_compute_chord_color_first_position_has_no_transition_axes():
    chords, tokens = _analyze("C Am")
    raw = compute_chord_color(chords[0], tokens[0], "C major")
    assert raw.smoothness is None
    assert raw.resolution is None
    assert raw.finality is None
    assert raw.chromaticity == 0.0


def test_compute_chord_color_transition_populates_every_axis():
    chords, tokens = _analyze("G C")
    raw = compute_chord_color(
        chords[1],
        tokens[1],
        "C major",
        previous_chord=chords[0],
        previous_token=tokens[0],
    )
    assert raw.smoothness is not None
    assert raw.resolution is not None
    assert raw.finality is not None
    # Authentic cadence arriving on root-position I: finality should be high.
    assert raw.finality > 0.5
