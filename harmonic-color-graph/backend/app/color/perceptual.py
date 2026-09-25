"""F42: perceptual color axes (nostalgia, dreaminess, melancholy, warmth,
openness, cinematic) derived from F41's measurable axes, blended with
curated progression rules, each carrying a `{value, confidence, source}`
per the plan.

`compute_perceptual_color` is the one entry point (mirrors F41's
`compute_chord_color`): given a whole progression's chords/tokens, it
aggregates F41's per-position raw axes plus a few token-metadata flags
(borrowed/chromatic/extension/cadence-fact flags, reusing F13's
`analyze_relationships` rather than re-detecting cadences) into a small
feature vector, then combines that feature vector into each perceptual
axis with a documented logistic (`perceptual_params.json`). When a curated
`color_rules.json` entry matches the progression's trailing core-token
n-gram, that rule's target value is blended in at its own confidence and
the axis's `source` becomes `"rule"`; otherwise the axis stays `"derived"`
and its explanation is generated from its top contributing features.
`"feedback"` is a reserved third `source` value for a future
user-feedback-adjusted axis; nothing here produces it yet.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.color.features import ChordColorRaw, SurprisePredictor, compute_chord_color
from app.schemas.analysis_v2 import RomanToken
from app.schemas.harmony import CanonicalChord
from app.theory.relationships_v2 import analyze_relationships

PERCEPTUAL_AXES: tuple[str, ...] = (
    "nostalgia",
    "dreaminess",
    "melancholy",
    "warmth",
    "openness",
    "cinematic",
)

_AXIS_ADJECTIVE = {
    "nostalgia": "nostalgic",
    "dreaminess": "dreamy",
    "melancholy": "melancholy",
    "warmth": "warm",
    "openness": "open-ended",
    "cinematic": "cinematic",
}

# Fact ids from `relationships_v2.RULES` that read as a "colorful" (borrowed
# or backdoor-style) cadence rather than a plain diatonic one -- used as a
# binary derived feature, not to re-implement cadence detection.
_MODAL_CADENCE_FACT_IDS = {
    "minor_plagal",
    "aeolian",
    "backdoor",
    "backdoor_three",
    "double_plagal",
}

# Hedged language the explanation generator must use, and absolute-claim
# words it must never use -- the "language lint" the plan's checks name.
_HEDGE_MARKERS = (
    "tends to",
    "commonly",
    "often",
    "typically",
    "can feel",
    "reads as",
    "associated with",
)
_FORBIDDEN_WORDS = (
    "always",
    "never",
    "definitely",
    "certainly",
    "guarantee",
    "guarantees",
    "proves",
    "undeniably",
    "fact",
    "must",
    "absolutely",
    "perfectly",
)


def lint_explanation(text: str) -> list[str]:
    """Return lint violations in `text`: empty means it passes. Every
    generated or curated explanation must hedge (`"tends to feel…"`,
    `"commonly associated with…"`, …) and never assert an absolute claim."""
    lowered = text.lower()
    violations = [
        f"forbidden_word:{word}"
        for word in _FORBIDDEN_WORDS
        if re.search(rf"\b{re.escape(word)}\b", lowered)
    ]
    if not any(marker in lowered for marker in _HEDGE_MARKERS):
        violations.append("missing_hedge")
    return violations


@dataclass(frozen=True)
class ColorRule:
    """One curated `color_rules.json` entry: a progression fingerprint
    (a contiguous run of `RomanToken.core` values) and the perceptual axis
    values it should push toward when matched."""

    pattern: tuple[str, ...]
    axes: dict[str, float]
    tags: tuple[str, ...]
    explanation: str
    confidence: float


@dataclass(frozen=True)
class PerceptualValue:
    value: float = field(metadata={"range": "[0, 1]"})
    confidence: float = field(metadata={"range": "[0, 1]"})
    source: Literal["rule", "derived", "feedback"]
    explanation: str


@dataclass(frozen=True)
class PerceptualColor:
    nostalgia: PerceptualValue
    dreaminess: PerceptualValue
    melancholy: PerceptualValue
    warmth: PerceptualValue
    openness: PerceptualValue
    cinematic: PerceptualValue

    def __getitem__(self, axis: str) -> PerceptualValue:
        return getattr(self, axis)


_RULES_PATH = Path(__file__).resolve().parent / "rules" / "color_rules.json"
_PARAMS_PATH = Path(__file__).resolve().parent / "perceptual_params.json"


def load_color_rules(path: Path = _RULES_PATH) -> tuple[ColorRule, ...]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    rules = tuple(
        ColorRule(
            pattern=tuple(row["pattern"]),
            axes=dict(row["axes"]),
            tags=tuple(row.get("tags", ())),
            explanation=row["explanation"],
            confidence=float(row["confidence"]),
        )
        for row in rows
    )
    for rule in rules:
        assert not set(rule.axes) - set(PERCEPTUAL_AXES), f"unknown axis in rule {rule.pattern}"
    return rules


def load_perceptual_params(path: Path = _PARAMS_PATH) -> dict[str, tuple[float, dict[str, float]]]:
    data = json.loads(path.read_text(encoding="utf-8"))["axes"]
    return {
        axis: (
            float(entry["bias"]),
            {feature: float(weighted["weight"]) for feature, weighted in entry["weights"].items()},
        )
        for axis, entry in data.items()
    }


_DEFAULT_RULES = load_color_rules()
_DEFAULT_PARAMS = load_perceptual_params()

# Human-readable phrases for the derived-feature names the logistic weights
# use, keyed the same as `_progression_features()`'s output -- used only to
# build the top-two-contributor explanation sentence.
_FEATURE_PHRASES = {
    "mean_chromaticity": "chromatic color outside the key",
    "mean_brightness01": "how bright the harmony leans",
    "mean_tension": "harmonic tension",
    "mean_stability": "tonic stability",
    "mean_smoothness": "smooth voice leading",
    "mean_complexity": "extended chord color",
    "mean_resolution": "how strongly it resolves",
    "max_finality": "how hard it lands on the tonic",
    "any_borrowed": "borrowed, modal-mixture color",
    "any_chromatic": "unexplained chromatic motion",
    "has_extension": "added chord extensions",
    "has_modal_cadence": "a modal-mixture cadence",
    "has_deceptive": "deceptive motion",
}


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _progression_features(
    raws: Sequence[ChordColorRaw],
    tokens: Sequence[RomanToken],
) -> dict[str, float]:
    """Aggregate F41's per-position raw axes (plus a few token-metadata
    flags) into one feature vector per progression. Position 0's own
    chord-in-context axes (chromaticity, brightness, tension, stability,
    complexity) are included; smoothness/resolution/finality only exist
    from position 1 onward (they describe a transition)."""

    def mean(values: Sequence[float | None]) -> float:
        present = [value for value in values if value is not None]
        return sum(present) / len(present) if present else 0.0

    transitions = raws[1:]
    fact_ids = {fact.id for fact in analyze_relationships(tokens)} if len(tokens) >= 2 else set()
    return {
        "mean_chromaticity": mean([raw.chromaticity for raw in raws]),
        "mean_brightness01": mean([(raw.brightness + 1.0) / 2.0 for raw in raws]),
        "mean_tension": mean([raw.tension for raw in raws]),
        "mean_stability": mean([raw.stability for raw in raws]),
        "mean_smoothness": mean([raw.smoothness for raw in transitions]) if transitions else 0.5,
        "mean_complexity": mean([raw.complexity for raw in raws]),
        "mean_resolution": mean([raw.resolution for raw in transitions]) if transitions else 0.0,
        "max_finality": max(
            (raw.finality for raw in transitions if raw.finality is not None), default=0.0
        ),
        "any_borrowed": 1.0 if any(token.is_borrowed for token in tokens) else 0.0,
        "any_chromatic": 1.0 if any(token.is_chromatic for token in tokens) else 0.0,
        "has_extension": 1.0 if any(token.extensions for token in tokens) else 0.0,
        "has_modal_cadence": 1.0 if fact_ids & _MODAL_CADENCE_FACT_IDS else 0.0,
        "has_deceptive": 1.0 if "deceptive" in fact_ids else 0.0,
    }


def _derived_axis(
    axis: str, features: dict[str, float], params: dict[str, tuple[float, dict[str, float]]]
) -> tuple[float, list[tuple[str, float]]]:
    """Return the axis's sigmoid value and its features ranked by
    contribution magnitude (`weight * feature_value`, signed)."""
    bias, weights = params[axis]
    contributions = [(feature, weights[feature] * features[feature]) for feature in weights]
    z = bias + sum(contribution for _, contribution in contributions)
    contributions.sort(key=lambda pair: abs(pair[1]), reverse=True)
    return _sigmoid(z), contributions


def _explain_derived(axis: str, contributions: list[tuple[str, float]]) -> str:
    """Hedged sentence from the axis's top two contributing features, by
    contribution magnitude (`_derived_axis` already sorted them)."""
    top_features = [feature for feature, contribution in contributions[:2] if contribution != 0]
    phrases = [_FEATURE_PHRASES.get(feature, feature) for feature in top_features]
    adjective = _AXIS_ADJECTIVE[axis]
    if len(phrases) >= 2:
        return (
            f"This progression tends to feel {adjective}, commonly associated with "
            f"{phrases[0]} and {phrases[1]}."
        )
    if phrases:
        return f"This progression tends to feel {adjective}, commonly associated with {phrases[0]}."
    return f"This progression can feel {adjective}, though no single feature drives it here."


def _match_rules(tokens: Sequence[RomanToken], rules: Sequence[ColorRule]) -> dict[str, ColorRule]:
    """For each perceptual axis, the highest-confidence rule whose pattern
    matches a trailing contiguous run of `tokens`' core values anywhere in
    the progression."""
    core = [token.core for token in tokens]
    best: dict[str, ColorRule] = {}
    for rule in rules:
        n = len(rule.pattern)
        matched = any(core[i : i + n] == list(rule.pattern) for i in range(len(core) - n + 1))
        if not matched:
            continue
        for axis in rule.axes:
            current = best.get(axis)
            if current is None or rule.confidence > current.confidence:
                best[axis] = rule
    return best


def compute_perceptual_color(
    chords: Sequence[CanonicalChord],
    tokens: Sequence[RomanToken],
    key: str,
    *,
    predictor: SurprisePredictor | None = None,
    genre: str | None = None,
    section: str | None = None,
    rules: Sequence[ColorRule] = _DEFAULT_RULES,
    params: dict[str, tuple[float, dict[str, float]]] = _DEFAULT_PARAMS,
) -> PerceptualColor:
    """Perceptual axes for a whole progression (`chords`/`tokens` from
    `app.theory.roman.analyze_v2`, same shapes as `compute_chord_color`'s
    inputs). Six axes, each `{value, confidence, source, explanation}`."""
    if len(chords) != len(tokens) or not tokens:
        raise ValueError("chords and tokens must be the same non-empty length")

    raws: list[ChordColorRaw] = []
    history: list[str] = []
    for index, (chord, token) in enumerate(zip(chords, tokens, strict=True)):
        previous_chord = chords[index - 1] if index > 0 else None
        previous_token = tokens[index - 1] if index > 0 else None
        raws.append(
            compute_chord_color(
                chord,
                token,
                key,
                previous_chord=previous_chord,
                previous_token=previous_token,
                predictor=predictor,
                history=tuple(history),
                genre=genre,
                section=section,
            )
        )
        history.append(token.core)

    features = _progression_features(raws, tokens)
    matched = _match_rules(tokens, rules)
    transition_count = max(len(tokens) - 1, 0)
    derived_confidence = _clip01(0.5 + 0.1 * min(transition_count, 2))

    values: dict[str, PerceptualValue] = {}
    for axis in PERCEPTUAL_AXES:
        derived_value, contributions = _derived_axis(axis, features, params)
        rule = matched.get(axis)
        if rule is not None:
            blended = rule.confidence * rule.axes[axis] + (1 - rule.confidence) * derived_value
            explanation = rule.explanation
            lint_errors = lint_explanation(explanation)
            assert not lint_errors, f"rule explanation fails lint: {explanation!r}"
            values[axis] = PerceptualValue(
                value=_clip01(blended),
                confidence=rule.confidence,
                source="rule",
                explanation=explanation,
            )
        else:
            explanation = _explain_derived(axis, contributions)
            values[axis] = PerceptualValue(
                value=_clip01(derived_value),
                confidence=derived_confidence,
                source="derived",
                explanation=explanation,
            )
    return PerceptualColor(**values)


__all__ = [
    "PERCEPTUAL_AXES",
    "ColorRule",
    "PerceptualColor",
    "PerceptualValue",
    "compute_perceptual_color",
    "lint_explanation",
    "load_color_rules",
    "load_perceptual_params",
]
