"""F10 checks: spelling tables (24 keys x 7 degrees), inversion detection,
and interval vectors for reference chords.
"""

import pytest

from app.theory.chord_normalizer import normalize_chord
from app.theory.spelling import (
    classify_chord_intervals,
    compute_interval_vector,
    compute_pc_set_mask,
    detect_inversion,
    diatonic_letters_and_pitch_classes,
    lof,
    spell,
    spell_chord_tones,
    spell_in_key,
)

# Standard textbook scales for all 12 major and 12 natural-minor keys, authored
# independently of `spelling.py` as the ground truth this module is checked
# against (one canonical spelling per pitch class per the circle of fifths).
MAJOR_SCALES = {
    "C major": ["C", "D", "E", "F", "G", "A", "B"],
    "G major": ["G", "A", "B", "C", "D", "E", "F#"],
    "D major": ["D", "E", "F#", "G", "A", "B", "C#"],
    "A major": ["A", "B", "C#", "D", "E", "F#", "G#"],
    "E major": ["E", "F#", "G#", "A", "B", "C#", "D#"],
    "B major": ["B", "C#", "D#", "E", "F#", "G#", "A#"],
    "F# major": ["F#", "G#", "A#", "B", "C#", "D#", "E#"],
    "Db major": ["Db", "Eb", "F", "Gb", "Ab", "Bb", "C"],
    "Ab major": ["Ab", "Bb", "C", "Db", "Eb", "F", "G"],
    "Eb major": ["Eb", "F", "G", "Ab", "Bb", "C", "D"],
    "Bb major": ["Bb", "C", "D", "Eb", "F", "G", "A"],
    "F major": ["F", "G", "A", "Bb", "C", "D", "E"],
}

MINOR_SCALES = {
    "A minor": ["A", "B", "C", "D", "E", "F", "G"],
    "E minor": ["E", "F#", "G", "A", "B", "C", "D"],
    "B minor": ["B", "C#", "D", "E", "F#", "G", "A"],
    "F# minor": ["F#", "G#", "A", "B", "C#", "D", "E"],
    "C# minor": ["C#", "D#", "E", "F#", "G#", "A", "B"],
    "G# minor": ["G#", "A#", "B", "C#", "D#", "E", "F#"],
    "D# minor": ["D#", "E#", "F#", "G#", "A#", "B", "C#"],
    "Bb minor": ["Bb", "C", "Db", "Eb", "F", "Gb", "Ab"],
    "F minor": ["F", "G", "Ab", "Bb", "C", "Db", "Eb"],
    "C minor": ["C", "D", "Eb", "F", "G", "Ab", "Bb"],
    "G minor": ["G", "A", "Bb", "C", "D", "Eb", "F"],
    "D minor": ["D", "E", "F", "G", "A", "Bb", "C"],
}


ALL_24_KEYS = sorted(MAJOR_SCALES.items()) + sorted(MINOR_SCALES.items())


@pytest.mark.parametrize("key,expected_scale", ALL_24_KEYS)
def test_diatonic_scale_spelling_all_24_keys_7_degrees(key, expected_scale):
    diatonic = diatonic_letters_and_pitch_classes(key)
    assert len(diatonic) == 7
    spelled = [spell(pc, letter) for letter, pc in diatonic]
    assert spelled == expected_scale
    # Every degree also round-trips through spell_in_key (the public API).
    for note, (_letter, pc) in zip(expected_scale, diatonic, strict=True):
        assert spell_in_key(pc, key) == note


def test_lof_reference_values():
    assert lof("C") == 0
    assert lof("G#") == 8
    assert lof("Ab") == -4
    assert lof("F#") == 6
    assert lof("Bb") == -2


def test_ab_major_triad_spells_flats_never_sharps():
    tones = spell_chord_tones("Ab", [0, 4, 7])
    assert tones == ["Ab", "C", "Eb"]


def test_leading_tone_prefers_sharp_over_flat_tonic():
    assert spell_in_key(8, "A minor") == "G#"


@pytest.mark.parametrize(
    "raw_symbol,expected_inversion",
    [
        ("C", "root"),
        ("C/C", "root"),
        ("C/E", "first"),
        ("C/G", "second"),
        ("C7/Bb", "third"),
        ("C/D", "other"),
    ],
)
def test_inversion_detection(raw_symbol, expected_inversion):
    result = normalize_chord(raw_symbol)
    assert result.chord is not None
    assert result.chord.inversion == expected_inversion


def test_detect_inversion_directly():
    assert detect_inversion(root_pc=0, bass_pc=0, pitch_classes=[0, 4, 7]) == "root"
    assert detect_inversion(root_pc=0, bass_pc=4, pitch_classes=[0, 4, 7]) == "first"
    assert detect_inversion(root_pc=0, bass_pc=7, pitch_classes=[0, 4, 7]) == "second"
    assert detect_inversion(root_pc=0, bass_pc=10, pitch_classes=[0, 4, 7, 10]) == "third"
    assert detect_inversion(root_pc=0, bass_pc=2, pitch_classes=[0, 4, 7]) == "other"


# <ic1, ic2, ic3, ic4, ic5, ic6> vectors for 10 reference chords, cross-checked
# by hand against the pairwise pitch-class-interval counts (see spelling.py's
# compute_interval_vector docstring for the definition).
REFERENCE_INTERVAL_VECTORS = {
    "major_triad": ([0, 4, 7], [0, 0, 1, 1, 1, 0]),
    "minor_triad": ([0, 3, 7], [0, 0, 1, 1, 1, 0]),
    "diminished_triad": ([0, 3, 6], [0, 0, 2, 0, 0, 1]),
    "augmented_triad": ([0, 4, 8], [0, 0, 0, 3, 0, 0]),
    "dominant_seventh": ([0, 4, 7, 10], [0, 1, 2, 1, 1, 1]),
    "major_seventh": ([0, 4, 7, 11], [1, 0, 1, 2, 2, 0]),
    "minor_seventh": ([0, 3, 7, 10], [0, 1, 2, 1, 2, 0]),
    "diminished_seventh": ([0, 3, 6, 9], [0, 0, 4, 0, 0, 2]),
    "half_diminished_seventh": ([0, 3, 6, 10], [0, 1, 2, 1, 1, 1]),
    "sus4_triad": ([0, 5, 7], [0, 1, 0, 0, 2, 0]),
}


@pytest.mark.parametrize(
    "pitch_classes,expected_vector",
    REFERENCE_INTERVAL_VECTORS.values(),
    ids=REFERENCE_INTERVAL_VECTORS.keys(),
)
def test_interval_vector_reference_chords(pitch_classes, expected_vector):
    assert compute_interval_vector(pitch_classes) == expected_vector
    assert sum(expected_vector) == len(pitch_classes) * (len(pitch_classes) - 1) // 2


def test_pc_set_mask_is_a_12_bit_bitmask():
    assert compute_pc_set_mask([0, 4, 7]) == 0b0000_1001_0001
    assert compute_pc_set_mask([]) == 0
    assert compute_pc_set_mask(list(range(12))) == 0xFFF


@pytest.mark.parametrize(
    "quality,intervals,expected_class,expected_extensions",
    [
        ("maj", [0, 4, 7], "maj", []),
        ("min", [0, 3, 7], "min", []),
        ("dim", [0, 3, 6], "dim", []),
        ("aug", [0, 4, 8], "aug", []),
        ("7", [0, 4, 7, 10], "dom7", []),
        ("maj7", [0, 4, 7, 11], "maj7", []),
        ("min7", [0, 3, 7, 10], "min7", []),
        ("min7b5", [0, 3, 6, 10], "hdim7", []),
        ("dim7", [0, 3, 6, 9], "dim7", []),
        ("minmaj7", [0, 3, 7, 11], "minmaj7", []),
        ("sus2", [0, 2, 7], "sus", []),
        ("sus4", [0, 5, 7], "sus", []),
        ("no3", [0, 7], "power", []),
        ("9", [0, 4, 7, 10, 2], "dom7", ["9"]),
        ("maj9", [0, 4, 7, 11, 2], "maj7", ["9"]),
        ("min9", [0, 3, 7, 10, 2], "min7", ["9"]),
        ("add9", [0, 4, 7, 2], "maj", ["9"]),
        ("add13", [0, 4, 7, 9], "maj", ["13"]),
        ("minadd13", [0, 3, 7, 9], "min", ["13"]),
        ("13", [0, 4, 7, 10, 2, 5, 9], "dom7", ["9", "11", "13"]),
        ("maj9#11", [0, 4, 7, 11, 2, 6], "maj7", ["9", "#11"]),
    ],
)
def test_classify_chord_intervals(quality, intervals, expected_class, expected_extensions):
    info = classify_chord_intervals(intervals)
    assert info.quality_class == expected_class
    assert info.extensions == expected_extensions
