"""F43: build a progression's color arc, summary, and drivers for the
`POST /v2/color/profile` and `GET /v2/color/compare` endpoints.

DB-free, same split as F41/F42: a submitted progression is analyzed on the
fly (`analyze_v2`), and every axis is F41/F42's pure, predictor-free
computation -- no corpus lookup, no active-version dependency.

The "arc" (per-position color) is prefix-based: position `i`'s perceptual
axes come from `compute_perceptual_color` over `chords[:i+1]`/`tokens[:i+1]`
-- "how does the progression read up through this chord" -- so the arc
tracks color building up across the progression, and the final position's
perceptual axes are exactly the whole progression's F42 read (no separate
aggregation needed for the summary's perceptual half). The summary's raw
half is a genuinely weighted blend (not a plain mean): the final position
(cadence arrival) and any borrowed/chromatic chord get extra weight, per
the plan's "weighted toward the final cadence and rare borrowed chords"
-- see `_position_weight` and the bonus constants below for the exact
numbers and their rationale.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.color.features import AXES as RAW_AXES
from app.color.features import ChordColorRaw, compute_chord_color
from app.color.perceptual import PERCEPTUAL_AXES, PerceptualColor, compute_perceptual_color
from app.schemas.analysis_v2 import RomanToken
from app.schemas.color_v2 import (
    ArcPoint,
    ColorProfileResponse,
    ColorSummary,
    Driver,
    PerceptualAxisOut,
)
from app.schemas.harmony import CanonicalChord
from app.theory.roman import analyze_v2

# Bonus multipliers added to every position's base weight of 1.0 when
# building the raw-axis summary. A final-cadence arrival and a rare
# (borrowed/chromatic) chord are the two things Phase 2's design notes
# flagged as easy to wash out in a plain average across a progression --
# a four-chord loop with one striking borrowed chord should read as
# "driven by that chord", not diluted 1-in-4.
FINAL_POSITION_BONUS = 2.0
BORROWED_CHORD_BONUS = 1.5
CHROMATIC_CHORD_BONUS = 1.0


@dataclass(frozen=True)
class ArcPointData:
    position: int
    chord: CanonicalChord
    token: RomanToken
    raw: ChordColorRaw
    perceptual: PerceptualColor


def _perceptual_out(color: PerceptualColor) -> dict[str, PerceptualAxisOut]:
    return {
        axis: PerceptualAxisOut(
            value=color[axis].value,
            confidence=color[axis].confidence,
            source=color[axis].source,
            explanation=color[axis].explanation,
        )
        for axis in PERCEPTUAL_AXES
    }


def _raw_out(raw: ChordColorRaw) -> dict[str, float | None]:
    return {axis: getattr(raw, axis) for axis in RAW_AXES}


def build_arc(
    chords: Sequence[CanonicalChord], tokens: Sequence[RomanToken], key: str
) -> list[ArcPointData]:
    arc: list[ArcPointData] = []
    for index in range(len(chords)):
        raw = compute_chord_color(
            chords[index],
            tokens[index],
            key,
            previous_chord=chords[index - 1] if index > 0 else None,
            previous_token=tokens[index - 1] if index > 0 else None,
        )
        perceptual = compute_perceptual_color(chords[: index + 1], tokens[: index + 1], key)
        arc.append(
            ArcPointData(
                position=index,
                chord=chords[index],
                token=tokens[index],
                raw=raw,
                perceptual=perceptual,
            )
        )
    return arc


def _position_weight(index: int, last_index: int, token: RomanToken) -> float:
    weight = 1.0
    if index == last_index:
        weight += FINAL_POSITION_BONUS
    if token.is_borrowed:
        weight += BORROWED_CHORD_BONUS
    elif token.is_chromatic:
        weight += CHROMATIC_CHORD_BONUS
    return weight


def build_summary_and_drivers(
    arc: list[ArcPointData],
) -> tuple[dict[str, float], list[Driver]]:
    last_index = len(arc) - 1
    weights = [_position_weight(point.position, last_index, point.token) for point in arc]

    raw_summary: dict[str, float] = {}
    for axis in RAW_AXES:
        weighted_sum = 0.0
        weight_total = 0.0
        for point, weight in zip(arc, weights, strict=True):
            value = getattr(point.raw, axis)
            if value is None:
                continue
            weighted_sum += weight * value
            weight_total += weight
        if weight_total > 0:
            raw_summary[axis] = weighted_sum / weight_total

    drivers: list[Driver] = [
        Driver(
            position=last_index,
            chord=arc[last_index].chord.raw_symbol,
            reason="final_cadence",
            weight=FINAL_POSITION_BONUS,
        )
    ]
    for point in arc:
        if point.token.is_borrowed:
            drivers.append(
                Driver(
                    position=point.position,
                    chord=point.chord.raw_symbol,
                    reason="borrowed_chord",
                    weight=BORROWED_CHORD_BONUS,
                )
            )
        elif point.token.is_chromatic:
            drivers.append(
                Driver(
                    position=point.position,
                    chord=point.chord.raw_symbol,
                    reason="chromatic_chord",
                    weight=CHROMATIC_CHORD_BONUS,
                )
            )
    return raw_summary, drivers


def compute_color_profile(progression: str | list[str], key: str | None) -> ColorProfileResponse:
    analysis = analyze_v2(progression, key)
    arc_data = build_arc(analysis.chords, analysis.tokens, analysis.song_key)
    if not arc_data:
        raise ValueError("Progression has no chords to score")
    raw_summary, drivers = build_summary_and_drivers(arc_data)
    return ColorProfileResponse(
        key=analysis.song_key,
        arc=[
            ArcPoint(
                position=point.position,
                chord=point.chord.raw_symbol,
                token=point.token.core,
                raw=_raw_out(point.raw),
                perceptual=_perceptual_out(point.perceptual),
            )
            for point in arc_data
        ],
        summary=ColorSummary(raw=raw_summary, perceptual=_perceptual_out(arc_data[-1].perceptual)),
        drivers=drivers,
    )


def compute_color_compare(
    progression_a: str | list[str],
    key_a: str | None,
    progression_b: str | list[str],
    key_b: str | None,
) -> tuple[ColorProfileResponse, ColorProfileResponse, dict[str, float], dict[str, float]]:
    profile_a = compute_color_profile(progression_a, key_a)
    profile_b = compute_color_profile(progression_b, key_b)
    raw_deltas = {
        axis: profile_b.summary.raw[axis] - profile_a.summary.raw[axis]
        for axis in profile_a.summary.raw
        if axis in profile_b.summary.raw
    }
    perceptual_deltas = {
        axis: profile_b.summary.perceptual[axis].value - profile_a.summary.perceptual[axis].value
        for axis in PERCEPTUAL_AXES
    }
    return profile_a, profile_b, raw_deltas, perceptual_deltas
