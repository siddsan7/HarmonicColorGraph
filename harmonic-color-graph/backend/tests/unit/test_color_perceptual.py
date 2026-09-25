"""F42 color/perceptual.py: the plan's rule-ordering sanity suite, plus
targeted coverage for rule loading, blending, and the language lint."""

import pytest

from app.color.perceptual import (
    PERCEPTUAL_AXES,
    ColorRule,
    compute_perceptual_color,
    lint_explanation,
    load_color_rules,
    load_perceptual_params,
)
from app.theory.roman import analyze_v2


def _analyze(chords: str, key: str = "C major"):
    result = analyze_v2(chords, key)
    return result.chords, result.tokens


def _color(chords: str, key: str = "C major"):
    chs, toks = _analyze(chords, key)
    return compute_perceptual_color(chs, toks, key)


# --- Phase 2 §6.1-style rule orderings named in the plan's checks --------


def test_nostalgia_borrowed_iv_beats_diatonic_iv():
    borrowed = _color("Fm C")  # iv -> I
    diatonic = _color("F C")  # IV -> I
    assert borrowed.nostalgia.value > diatonic.nostalgia.value


def test_cinematic_aeolian_climb_beats_plain_authentic_approach():
    aeolian = _color("Ab Bb C")  # bVI -> bVII -> I
    plain = _color("F G C")  # IV -> V -> I
    assert aeolian.cinematic.value > plain.cinematic.value


def test_dreaminess_extended_mediant_chain_beats_plain_triads():
    extended = _color("Cmaj7 Em7 Am7")  # Imaj7 -> iii7 -> vi7
    plain = _color("C G Am")  # I -> V -> vi
    assert extended.dreaminess.value > plain.dreaminess.value


# --- Every value carries confidence and source ----------------------------


def test_every_axis_carries_confidence_and_source():
    color = _color("F G C")
    for axis in PERCEPTUAL_AXES:
        value = color[axis]
        assert 0.0 <= value.value <= 1.0
        assert 0.0 <= value.confidence <= 1.0
        assert value.source in {"rule", "derived", "feedback"}
        assert value.explanation


def test_matched_rule_axis_reports_rule_source_and_high_confidence():
    color = _color("Fm C")  # matches the M:iv -> M:I rule
    assert color.nostalgia.source == "rule"
    assert color.nostalgia.confidence >= 0.8


def test_unmatched_axis_on_a_matched_progression_stays_derived():
    color = _color("Fm C")  # the M:iv -> M:I rule sets nostalgia/warmth/melancholy only
    assert color.openness.source == "derived"


def test_no_rule_match_is_fully_derived():
    color = _color("C F")  # I -> IV: not a curated rule pattern
    for axis in PERCEPTUAL_AXES:
        assert color[axis].source == "derived"


# --- Language lint ----------------------------------------------------------


def test_lint_rejects_absolute_claims():
    assert lint_explanation("This progression always feels nostalgic.")


def test_lint_rejects_unhedged_sentences_even_without_forbidden_words():
    assert lint_explanation("This progression feels nostalgic.")


def test_lint_accepts_hedged_sentences():
    assert lint_explanation("This progression tends to feel nostalgic.") == []
    assert lint_explanation("This commonly reads as a warm, settled arrival.") == []


def test_every_curated_rule_explanation_passes_lint():
    for rule in load_color_rules():
        assert lint_explanation(rule.explanation) == []


def test_every_derived_explanation_passes_lint():
    for chords in ["C F", "C Dm", "G Am F", "Cmaj7 Fmaj7"]:
        color = _color(chords)
        for axis in PERCEPTUAL_AXES:
            value = color[axis]
            if value.source == "derived":
                assert lint_explanation(value.explanation) == []


# --- Rule loading and matching ---------------------------------------------


def test_load_color_rules_returns_at_least_twenty_entries():
    rules = load_color_rules()
    assert len(rules) >= 20
    for rule in rules:
        assert rule.pattern
        assert rule.axes
        assert set(rule.axes) <= set(PERCEPTUAL_AXES)
        assert 0.0 < rule.confidence <= 1.0


def test_every_curated_rule_pattern_is_reachable():
    """Guards against a dead rule: every pattern must be producible by the
    real analyzer, not just a hand-typed guess at core-token spelling."""
    fixtures = {
        ("M:iv", "M:I"): ("Fm C", "C major"),
        ("M:bVI", "M:bVII", "M:I"): ("Ab Bb C", "C major"),
        ("M:V", "M:vi"): ("G Am", "C major"),
        ("M:V", "M:I"): ("G C", "C major"),
        ("M:I", "M:iii"): ("C Em", "C major"),
        ("M:Imaj7", "M:iii7"): ("Cmaj7 Em7", "C major"),
        ("M:vi", "M:IV"): ("Am F", "C major"),
        ("m:V7", "m:i"): ("E7 Am", "A minor"),
        ("M:bVII", "M:IV", "M:I"): ("Bb F C", "C major"),
        ("M:ii", "M:V", "M:I"): ("Dm G C", "C major"),
        ("M:bVI", "M:V"): ("Ab G", "C major"),
        ("M:V7/V", "M:V"): ("D7 G", "C major"),
        ("m:i", "m:bII"): ("Am Bb", "A minor"),
        ("m:bII", "m:III"): ("Bb C", "A minor"),
        ("m:iv", "m:i"): ("Dm Am", "A minor"),
        ("m:V7", "m:VI"): ("E7 F", "A minor"),
        ("M:I", "M:bVI"): ("C Ab", "C major"),
        ("M:I", "M:III"): ("C E", "C major"),
        ("M:ii7", "M:V7", "M:Imaj7"): ("Dm7 G7 Cmaj7", "C major"),
        ("m:V", "m:i"): ("E Am", "A minor"),
        ("M:iv", "M:bVII7", "M:I"): ("Fm Bb7 C", "C major"),
    }
    rules = load_color_rules()
    assert {rule.pattern for rule in rules} <= set(fixtures)
    for pattern, (chords, key) in fixtures.items():
        _, tokens = _analyze(chords, key)
        core = [token.core for token in tokens]
        n = len(pattern)
        assert any(core[i : i + n] == list(pattern) for i in range(len(core) - n + 1)), (
            f"{pattern} not reachable from {chords!r} in {key}"
        )


def test_load_perceptual_params_covers_every_axis_with_a_rationale():
    data = load_perceptual_params()
    assert set(data) == set(PERCEPTUAL_AXES)
    import json
    from pathlib import Path

    raw = json.loads(
        (Path(__file__).resolve().parents[2] / "app/color/perceptual_params.json").read_text(
            encoding="utf-8"
        )
    )["axes"]
    for axis, entry in raw.items():
        for feature, weighted in entry["weights"].items():
            assert weighted["rationale"], f"{axis}.{feature} is missing a rationale"


# --- Compute API shape -------------------------------------------------------


def test_compute_perceptual_color_rejects_mismatched_lengths():
    chords, tokens = _analyze("C F")
    with pytest.raises(ValueError):
        compute_perceptual_color(chords, tokens[:1], "C major")


def test_compute_perceptual_color_rejects_empty_progression():
    with pytest.raises(ValueError):
        compute_perceptual_color([], [], "C major")


def test_custom_rules_and_params_override_the_defaults():
    chords, tokens = _analyze("C F")
    custom_rule = ColorRule(
        pattern=("M:I", "M:IV"),
        axes={"warmth": 0.99},
        tags=("test",),
        explanation="This tends to feel deliberately warm for this test.",
        confidence=0.9,
    )
    params = load_perceptual_params()
    color = compute_perceptual_color(chords, tokens, "C major", rules=[custom_rule], params=params)
    assert color.warmth.source == "rule"
    # blended = 0.9 * 0.99 + 0.1 * derived, and derived in [0, 1]
    assert 0.9 * 0.99 <= color.warmth.value <= 0.9 * 0.99 + 0.1
    assert color.warmth.confidence == 0.9
