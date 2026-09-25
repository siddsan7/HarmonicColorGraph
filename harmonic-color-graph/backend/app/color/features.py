"""F41: measurable harmonic color features, raw (pre-normalization) values.

Every function here is pure and fast enough for the API hot path: no
database access except the optional `predictor` (surprise, resolution's
forward-looking term), which is dependency-injected via the `SurprisePredictor`
protocol so this module never imports `app.predict.ngram` (mirrors the
`NgramReader` protocol split in that module). `color/norms.py` maps these raw
values onto [0, 1] using corpus percentiles the `color` pipeline stage
computes; nothing here does that normalization itself.

`compute_chord_color` is the one entry point call sites use: given a chord's
`CanonicalChord` (for actual pitches -- voice leading needs real notes, not
scale degrees) and its `RomanToken` (for function/degree/inversion), plus the
previous chord's pair when there is one, it returns every axis at once. A
`previous_*` of `None` means "a chord in context" (the opening position of a
progression); given, it means "a transition" -- the same distinction F41's
plan draws for `chromaticity`, `smoothness`, `resolution`, and `finality`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.schemas.analysis_v2 import RomanToken
from app.schemas.harmony import CanonicalChord
from app.theory.relationships_v2 import analyze_relationships
from app.theory.spelling import (
    compute_interval_vector,
    diatonic_letters_and_pitch_classes,
    lof,
    spell_in_key,
)
from app.theory.voice_leading import transition_metrics, voice_lead

# Must match `pipeline/load.py`'s `COLOR_AXES` (same 9 names; the loader
# validates `hcg.color_norms` rows against that list).
AXES: tuple[str, ...] = (
    "chromaticity",
    "brightness",
    "tension",
    "stability",
    "surprise",
    "smoothness",
    "complexity",
    "resolution",
    "finality",
)


class SurprisePredictor(Protocol):
    def distribution(
        self, history: Sequence[str], *, genre: str | None = None, section: str | None = None
    ) -> dict[str, float]: ...


@dataclass(frozen=True)
class ChordColorRaw:
    """Raw (pre-normalization) axis values for one progression position.

    `smoothness`, `resolution`, and `finality` are `None` for a chord with no
    previous chord (nothing to transition from). `surprise` is `None` when no
    `predictor` was supplied.
    """

    chromaticity: float
    brightness: float
    tension: float
    stability: float
    surprise: float | None
    smoothness: float | None
    complexity: float
    resolution: float | None
    finality: float | None


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _tonic_root(key: str) -> str:
    root = key.strip().split()[0]
    return root[0].upper() + root[1:]


def _scale_pitch_classes(key: str) -> set[int]:
    return {pc for _, pc in diatonic_letters_and_pitch_classes(key)}


def chromaticity(token: RomanToken, key: str, *, previous: RomanToken | None = None) -> float:
    """Share of chord tones outside the local scale; for a transition, only
    the tones that are both out-of-scale and newly introduced (not already
    sounding in the previous chord)."""
    tones = token.pitch_classes
    if not tones:
        return 0.0
    scale = _scale_pitch_classes(key)
    out_of_scale = {pc for pc in tones if pc not in scale}
    if previous is not None:
        out_of_scale -= set(previous.pitch_classes)
    return len(out_of_scale) / len(tones)


# Third-quality brightness term: +1 major-third family, -1 minor/diminished
# family, 0 when there is no third to judge (sus, power).
_THIRD_QUALITY_TERM = {
    "maj": 1.0,
    "maj7": 1.0,
    "dom7": 1.0,
    "aug": 1.0,
    "min": -1.0,
    "min7": -1.0,
    "minmaj7": -1.0,
    "dim": -1.0,
    "dim7": -1.0,
    "hdim7": -1.0,
    "sus": 0.0,
    "power": 0.0,
}
# Fifths span used to squash the mean relative line-of-fifths index into
# [-1, 1] before blending with the third term: 7 fifths is one accidental's
# worth of chromatic distance beyond the 7-note diatonic collection, wide
# enough that ordinary diatonic and single-mixture chords land well inside
# the range while doubly-chromatic ones saturate rather than blow it up.
_LOF_NORM_SPAN = 7.0


def brightness(token: RomanToken, key: str) -> float:
    """0.6 * norm(mean line-of-fifths index of the chord tones, relative to
    the tonic) + 0.4 * third-quality term."""
    tonic_lof = lof(_tonic_root(key))
    relative = [lof(spell_in_key(pc, key)) - tonic_lof for pc in token.pitch_classes]
    mean_lof = sum(relative) / len(relative) if relative else 0.0
    lof_norm = max(-1.0, min(1.0, mean_lof / _LOF_NORM_SPAN))
    third_term = _THIRD_QUALITY_TERM.get(token.quality_class, 0.0)
    return 0.6 * lof_norm + 0.4 * third_term


# Interval-class-vector dissonance weights, ic1..ic6: m2/M7 1.0, M2/m7 0.4,
# m3/M6 and M3/m6 and P4/P5 consonant (0), tritone 0.8.
_DISSONANCE_WEIGHTS = (1.0, 0.4, 0.0, 0.0, 0.0, 0.8)


def _dissonance(pitch_classes: Sequence[int]) -> float:
    unique = sorted(set(pitch_classes))
    if len(unique) < 2:
        return 0.0
    vector = compute_interval_vector(unique)
    pair_count = len(unique) * (len(unique) - 1) // 2
    weighted = sum(
        count * weight for count, weight in zip(vector, _DISSONANCE_WEIGHTS, strict=True)
    )
    return _clip01(weighted / pair_count)


_FUNCTION_TENSION = {"D": 1.0, "PD": 0.5, "T": 0.0}
_FUNCTION_STABILITY = {"T": 1.0, "PD": 0.5, "D": 0.0}
_FUNCTION_OTHER_DEFAULT = 0.25  # chromatic/applied tokens: neither clearly resolved nor active


def tension(token: RomanToken, key: str) -> float:
    """0.4 * dissonance + 0.3 * function + 0.2 * chromaticity + 0.1 * (second
    inversion -> 1)."""
    function_term = _FUNCTION_TENSION.get(token.function, _FUNCTION_OTHER_DEFAULT)
    inversion_term = 1.0 if token.inversion == "second" else 0.0
    return (
        0.4 * _dissonance(token.pitch_classes)
        + 0.3 * function_term
        + 0.2 * chromaticity(token, key)
        + 0.1 * inversion_term
    )


def stability(token: RomanToken, key: str) -> float:
    """Weighted mean of tonic function, root position, diatonicism, and
    consonance."""
    function_term = _FUNCTION_STABILITY.get(token.function, _FUNCTION_OTHER_DEFAULT)
    root_term = 1.0 if token.inversion == "root" else 0.0
    diatonic_term = 1.0 - chromaticity(token, key)
    consonance_term = 1.0 - _dissonance(token.pitch_classes)
    return (function_term + root_term + diatonic_term + consonance_term) / 4.0


def surprise(
    token: RomanToken,
    history: Sequence[str],
    predictor: SurprisePredictor | None,
    *,
    genre: str | None = None,
    section: str | None = None,
    floor_probability: float = 1e-6,
) -> float | None:
    """-log2 P(token | history) from the F30 predictor; `None` without one."""
    if predictor is None:
        return None
    distribution = predictor.distribution(history, genre=genre, section=section)
    probability = max(distribution.get(token.core, 0.0), floor_probability)
    return -math.log2(probability)


# Total voice-leading motion (semitones, summed across 4 voices) beyond
# which smoothness bottoms out at 0: a full-voice contrary leap on every
# part is already an extreme outlier, so this is a generous ceiling, not a
# typical value.
_MAX_TOTAL_MOTION = 24


def smoothness(
    chord: CanonicalChord,
    previous_chord: CanonicalChord | None,
    *,
    max_motion: int = _MAX_TOTAL_MOTION,
) -> float | None:
    """1 - norm(total voice-leading motion from the previous chord)."""
    if previous_chord is None:
        return None
    source_voicing, target_voicing = voice_lead([previous_chord, chord])
    metrics = transition_metrics(source_voicing, target_voicing, previous_chord, chord)
    return 1.0 - _clip01(metrics.total_motion / max_motion)


def complexity(token: RomanToken) -> float:
    """clip((|distinct pitch classes| - 3) / 4 + 0.15 * |extensions|)."""
    raw = (len(set(token.pitch_classes)) - 3) / 4.0 + 0.15 * len(token.extensions)
    return _clip01(raw)


# F13 cadence strengths (relationships_v2.py rule ids).
_CADENCE_STRENGTH = {"authentic": 0.95, "plagal": 0.75, "half": 0.3, "deceptive": 0.45}

# Base-figure function classes for a `RomanToken.core`-style token
# ("M:vi", "m:V7/iv"), mirroring `app.theory.roman.romanize_chord`'s
# function assignment (kept as a separate small table, not an import, since
# that assignment is keyed off internal chord state this module doesn't
# have -- only the resulting core-token string).
_T_BASES = {"I", "i", "vi", "VI", "iii", "III"}
_PD_BASES = {"ii", "iio", "IV", "iv", "bII", "bVI"}
_D_BASES = {"V", "vii"}
_BASE_FIGURE_RE = re.compile(r"^[b#]*[ivIV]+")


def _function_of_core_token(token: str) -> str:
    figure = token.split(":", 1)[1] if ":" in token else token
    match = _BASE_FIGURE_RE.match(figure)
    base = match.group(0) if match else figure
    if base in _T_BASES:
        return "T"
    if base in _PD_BASES:
        return "PD"
    if base in _D_BASES:
        return "D"
    return "other"


def _cadence_strength(previous: RomanToken, current: RomanToken) -> float:
    facts = analyze_relationships([previous, current])
    matched = [_CADENCE_STRENGTH[fact.id] for fact in facts if fact.id in _CADENCE_STRENGTH]
    return max(matched, default=0.0)


def resolution(
    previous: RomanToken | None,
    current: RomanToken,
    *,
    predictor: SurprisePredictor | None = None,
    history: Sequence[str] = (),
    genre: str | None = None,
    section: str | None = None,
) -> float | None:
    """F13 cadence strength blended with P(next is T-class) when a predictor
    is available; cadence strength alone otherwise."""
    if previous is None:
        return None
    cadence = _cadence_strength(previous, current)
    if predictor is None:
        return cadence
    distribution = predictor.distribution((*history, current.core), genre=genre, section=section)
    p_tonic = sum(
        probability
        for candidate, probability in distribution.items()
        if _function_of_core_token(candidate) == "T"
    )
    return 0.7 * cadence + 0.3 * _clip01(p_tonic)


def finality(
    previous: RomanToken | None,
    current: RomanToken,
    *,
    predictor: SurprisePredictor | None = None,
    history: Sequence[str] = (),
    genre: str | None = None,
    section: str | None = None,
) -> float | None:
    """resolution * tonic-arrival * root-position."""
    res = resolution(
        previous, current, predictor=predictor, history=history, genre=genre, section=section
    )
    if res is None:
        return None
    is_tonic = current.degree == 1 and current.accidental == "" and current.applied_to is None
    tonic_arrival = 1.0 if is_tonic else 0.0
    root_term = 1.0 if current.inversion == "root" else 0.0
    return res * tonic_arrival * root_term


def compute_chord_color(
    chord: CanonicalChord,
    token: RomanToken,
    key: str,
    *,
    previous_chord: CanonicalChord | None = None,
    previous_token: RomanToken | None = None,
    predictor: SurprisePredictor | None = None,
    history: Sequence[str] = (),
    genre: str | None = None,
    section: str | None = None,
) -> ChordColorRaw:
    """Every raw color axis for `token` at one progression position.

    Pass `previous_chord`/`previous_token` for a transition (all 9 axes
    populated where the previous chord is defined for that axis); leave them
    `None` for "a chord in context" alone (chromaticity, brightness, tension,
    stability, surprise, and complexity are still defined; smoothness,
    resolution, and finality come back `None`, since they are inherently
    about the move into this chord).
    """
    return ChordColorRaw(
        chromaticity=chromaticity(token, key, previous=previous_token),
        brightness=brightness(token, key),
        tension=tension(token, key),
        stability=stability(token, key),
        surprise=surprise(token, history, predictor, genre=genre, section=section),
        smoothness=smoothness(chord, previous_chord),
        complexity=complexity(token),
        resolution=resolution(
            previous_token,
            token,
            predictor=predictor,
            history=history,
            genre=genre,
            section=section,
        ),
        finality=finality(
            previous_token,
            token,
            predictor=predictor,
            history=history,
            genre=genre,
            section=section,
        ),
    )
