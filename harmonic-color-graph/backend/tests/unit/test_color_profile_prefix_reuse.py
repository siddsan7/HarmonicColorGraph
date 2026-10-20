"""Fresh contexts freeze output parity and eliminate repeated voice-leading work."""

from unittest.mock import patch

import pytest

from app.color import perceptual
from app.services import color_profile as profiles
from app.theory.roman import analyze_v2

DEV = [
    ("Bbmaj7 Dm7 Gm9 Cm7 F7 Bbmaj7", "Bb major"),
    ("F#m D E C#7 F#m", "F# minor"),
]
HELDOUT = [
    ("Abmaj7 Cm7 Fm9 Bbm7 Eb7 Abmaj7", "Ab major"),
    ("C#m9 F#m7 G#7 C#m9", "C# minor"),
    ("D/F# G A7 Dmaj7 Bm7 Em7 A7 Dmaj7", "D major"),
    ("Eb Cm Ab Bb7 Eb E C#m A B7 E", None),
]


def reference_arc(chords, tokens, key):
    """Pre-change implementation; do not route through the new aggregation path."""
    return [
        profiles.ArcPointData(
            position=index,
            chord=chord,
            token=tokens[index],
            raw=profiles.compute_chord_color(
                chord,
                tokens[index],
                key,
                previous_chord=chords[index - 1] if index else None,
                previous_token=tokens[index - 1] if index else None,
            ),
            perceptual=perceptual.compute_perceptual_color(
                chords[: index + 1],
                tokens[: index + 1],
                key,
            ),
        )
        for index, chord in enumerate(chords)
    ]


@pytest.mark.parametrize("progression,key", DEV + HELDOUT)
def test_full_color_profile_matches_reference_and_computes_raw_once(progression, key):
    with patch.object(profiles, "build_arc", reference_arc):
        expected = profiles.compute_color_profile(progression, key)
    analysis = analyze_v2(progression, key)
    with patch.object(profiles, "compute_chord_color", wraps=profiles.compute_chord_color) as raw:
        with patch.object(
            perceptual, "compute_chord_color", wraps=perceptual.compute_chord_color
        ) as repeated:
            actual = profiles.compute_color_profile(progression, key)
    assert actual == expected
    assert raw.call_count == len(analysis.chords)
    assert repeated.call_count == 0
    # Request-local prefixes must not retain prior key or position data.
    assert profiles.compute_color_profile(progression, key) == expected


def test_raw_prefix_aggregation_rejects_missing_or_misaligned_inputs():
    with pytest.raises(ValueError, match="same non-empty length"):
        perceptual._perceptual_from_raws([], [])
    analysis = analyze_v2("C G", "C major")
    with pytest.raises(ValueError, match="same non-empty length"):
        perceptual._perceptual_from_raws([], analysis.tokens)
