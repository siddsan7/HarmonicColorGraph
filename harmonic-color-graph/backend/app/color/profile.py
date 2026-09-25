"""F43: a color profile for a "subject" identified only by Roman-token
labels -- a `Function` (one `RomanToken.core`), a global `Transition`
(`from_token>to_token`), or a frequent `Pattern` (a space-joined run of
core tokens) -- the three kinds of node/edge the corpus pipeline's
`aggregate`/`patterns` stages already produce.

None of those carry a real chord (no pitch classes, no key): F41's color
axes need both, so `realize_progression` rebuilds a concrete progression
from the core-token labels alone via F30's `realize()` (the documented
inverse of `romanize_chord` restricted to `.core`), in one caller-chosen
reference key. The reconstructed chords are then re-romanized in sequence
so every position gets correct previous/next-chord context (applied
dominants, cadence detection, ...) -- not just round-tripped labels.

`compute_color_profile` is the one entry point: F41's raw axes for the
subject's final (arrival) position, F41's norms-based [0, 1] normalization
when a norms table is supplied, and F42's perceptual axes for the whole
reconstructed progression.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.color.features import AXES, ChordColorRaw, compute_chord_color
from app.color.norms import NormsTable, normalize
from app.color.perceptual import PerceptualColor, compute_perceptual_color
from app.predict.realize import realize
from app.schemas.analysis_v2 import RomanToken
from app.schemas.harmony import CanonicalChord
from app.theory.roman import romanize_chord

PROFILE_SUBJECT_TYPES: tuple[str, ...] = ("function", "transition", "pattern")

# One stable reference key per mode: color axes are computed relative to
# real pitches/scale degrees, but a Function/Transition/Pattern subject is
# mode-relative only, so any key in that mode gives the same axis values
# (transposition-invariant by construction -- see `test_color_profile.py`).
REFERENCE_KEY = {"major": "C major", "minor": "A minor"}


def mode_of(core_token: str) -> Literal["major", "minor"]:
    prefix = core_token.split(":", 1)[0]
    if prefix == "M":
        return "major"
    if prefix == "m":
        return "minor"
    raise ValueError(f"Not a core token (expected 'M:...' or 'm:...'): {core_token!r}")


def transition_subject_id(from_token: str, to_token: str) -> str:
    """`>` never appears inside a core token (applied chords use `/`), so
    it is a safe, unambiguous separator for a transition's subject id."""
    return f"{from_token}>{to_token}"


def realize_progression(
    core_tokens: Sequence[str], key: str
) -> tuple[list[CanonicalChord], list[RomanToken]]:
    """Rebuild a concrete `(chords, tokens)` progression from a sequence of
    `RomanToken.core` labels alone, all in one reference `key`. Each chord
    is realized independently (F30's `realize()` is context-free per
    token), then re-romanized in sequence so every position's
    previous/next-chord context is real, not just relabeled."""
    if not core_tokens:
        raise ValueError("core_tokens must be non-empty")
    chords = [realize(token, key).chord for token in core_tokens]
    tokens: list[RomanToken] = []
    for index, chord in enumerate(chords):
        tokens.append(
            romanize_chord(
                chord,
                key,
                next_chord=chords[index + 1] if index + 1 < len(chords) else None,
                previous_chord=chords[index - 1] if index > 0 else None,
                chord_index=index,
            )
        )
    return chords, tokens


@dataclass(frozen=True)
class ColorProfile:
    subject_type: Literal["function", "transition", "pattern"]
    subject_id: str
    mode: Literal["major", "minor"]
    support: int
    raw: dict[str, float | None]
    raw_normalized: dict[str, float]
    perceptual: PerceptualColor


def _raw_axis_dict(raw: ChordColorRaw) -> dict[str, float | None]:
    return {axis: getattr(raw, axis) for axis in AXES}


def compute_color_profile(
    subject_type: Literal["function", "transition", "pattern"],
    subject_id: str,
    core_tokens: Sequence[str],
    *,
    support: int = 0,
    norms: NormsTable | None = None,
) -> ColorProfile:
    mode = mode_of(core_tokens[0])
    key = REFERENCE_KEY[mode]
    chords, tokens = realize_progression(core_tokens, key)

    raw = compute_chord_color(
        chords[-1],
        tokens[-1],
        key,
        previous_chord=chords[-2] if len(chords) > 1 else None,
        previous_token=tokens[-2] if len(tokens) > 1 else None,
    )
    raw_dict = _raw_axis_dict(raw)

    raw_normalized: dict[str, float] = {}
    if norms is not None:
        norm_subject_type = "chord" if len(chords) == 1 else "transition"
        for axis, value in raw_dict.items():
            if value is None:
                continue
            norm = norms.get((axis, norm_subject_type))
            if norm is not None:
                raw_normalized[axis] = normalize(value, norm)

    perceptual = compute_perceptual_color(chords, tokens, key)

    return ColorProfile(
        subject_type=subject_type,
        subject_id=subject_id,
        mode=mode,
        support=support,
        raw=raw_dict,
        raw_normalized=raw_normalized,
        perceptual=perceptual,
    )


__all__ = [
    "PROFILE_SUBJECT_TYPES",
    "REFERENCE_KEY",
    "ColorProfile",
    "compute_color_profile",
    "mode_of",
    "realize_progression",
    "transition_subject_id",
]
