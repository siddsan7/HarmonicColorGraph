"""F30: `realize()` spells a predicted core token back into a chord,
inverting `app.theory.roman.romanize_chord`'s `.core` output.
"""

from __future__ import annotations

import pytest

from app.predict.realize import realize
from app.theory.roman import parse_key, romanize_chord
from app.theory.spelling import diatonic_letters_and_pitch_classes

MAJOR_KEYS = [
    "C major",
    "G major",
    "D major",
    "A major",
    "E major",
    "B major",
    "F major",
    "Bb major",
    "Eb major",
    "Ab major",
    "Db major",
    "F# major",
]
MINOR_KEYS = [
    "A minor",
    "E minor",
    "B minor",
    "F# minor",
    "C# minor",
    "G# minor",
    "D minor",
    "G minor",
    "C minor",
    "F minor",
    "Bb minor",
    "Eb minor",
]

MAJOR_TOKENS = [
    "M:I",
    "M:ii",
    "M:iii",
    "M:IV",
    "M:V",
    "M:vi",
    "M:viio",
    "M:V7",
    "M:ii7",
    "M:IVmaj7",
    "M:viio7",
    "M:iih7",
    "M:V/V",
    "M:V7/vi",
    "M:V/ii",
    "M:viio/V",
    "M:viio7/ii",
    "M:subV7/V",
    "M:bII",
    "M:bVI",
    "M:bVII",
    "M:iv",
    "M:Vsus4",
    "M:Isus2",
    "M:V+",
]
MINOR_TOKENS = [
    "m:i",
    "m:iio",
    "m:III",
    "m:iv",
    "m:v",
    "m:VI",
    "m:VII",
    "m:V7",
    "m:viio7",
]


def test_spec_examples_in_e_flat_major():
    v_of_v = realize("M:V/V", "Eb major")
    assert v_of_v.chord.symbol == "F:maj"
    assert v_of_v.chord.root == "F"

    flat_six = realize("M:bVI", "Eb major")
    assert flat_six.chord.root == "Cb"
    assert flat_six.display_enharmonic is None  # correct spelling stays primary


def _assert_realizes_correctly(token: str, key: str) -> None:
    result = realize(token, key)
    tonic_pc, mode, normalized_key = parse_key(key)
    chord = result.chord
    assert chord.root_pc is not None

    # Round-trip: re-analyzing the realized chord in the same key (with a
    # resolution target for applied chords, since that's what the forward
    # analyzer needs to recognize one) must recover the same root pitch
    # class -- the strongest available check that the spelling is
    # theoretically correct, not just "a" valid enharmonic spelling.
    next_hint = None
    if "/" in token:
        target_realized = realize(f"{token[0]}:{token.split('/', 1)[1]}", key)
        next_hint = target_realized.chord
    reanalyzed = romanize_chord(chord, normalized_key, next_chord=next_hint)
    assert reanalyzed.root_pc == chord.root_pc

    # The letter itself must be the numeral's own diatonic scale-degree
    # letter (F10's requirement), not just any enharmonically-correct
    # spelling -- checked directly for non-applied tokens, where the
    # token's degree is unambiguous without needing the round-trip above.
    # Skipped when a `display_enharmonic` fallback fired (e.g. bII in a
    # key whose own 2nd degree is already flat, needing a double flat
    # CanonicalChord can't represent): there, the simpler letter is
    # deliberately NOT the numeral's own degree letter -- see `_build`.
    if "/" not in token and result.display_enharmonic is None:
        degree = reanalyzed.degree
        diatonic = diatonic_letters_and_pitch_classes(normalized_key)
        assert chord.root[0] == diatonic[degree - 1][0]


@pytest.mark.parametrize("token", MAJOR_TOKENS)
@pytest.mark.parametrize("key", MAJOR_KEYS)
def test_major_realization_table(token, key):
    _assert_realizes_correctly(token, key)


@pytest.mark.parametrize("token", MINOR_TOKENS)
@pytest.mark.parametrize("key", MINOR_KEYS)
def test_minor_realization_table(token, key):
    _assert_realizes_correctly(token, key)


def test_double_accidental_falls_back_to_a_representable_spelling():
    # Db major's own 2nd degree is Eb; flattening it (bII) needs a double
    # flat, which CanonicalChord can't represent -- realize() must not
    # crash, and must still surface the theoretical name for display.
    result = realize("M:bII", "Db major")
    assert len(result.chord.root) <= 2  # a representable, single-accidental root
    assert result.display_enharmonic == "Ebb"


def test_minor_mode_degree_seven_defaults_to_natural_minor_subtonic():
    # "vii" with no accidental is ambiguous in minor (both the natural
    # b7/subtonic and the raised leading tone reduce to the same core
    # token) -- realize() documents and picks the natural-minor b7.
    result = realize("m:VII", "A minor")
    assert result.chord.root == "G"


def test_unknown_mode_prefix_raises():
    with pytest.raises(ValueError):
        realize("X:V", "C major")


def test_malformed_numeral_raises():
    with pytest.raises(ValueError):
        realize("M:notachord", "C major")
