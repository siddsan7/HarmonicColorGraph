"""Offline-trained plausibility plus bounded user-intent ranking."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from statistics import mean, pstdev
from typing import Literal

from app.predict.realize import realize
from app.recommend.features import FEATURE_NAMES, CandidateFeatures

WEIGHTS_FILE = Path(__file__).with_name("weights") / "plausibility_v1.json"
Preset = Literal["plausible", "balanced", "adventurous"]
PRESETS: dict[str, tuple[float, float, float]] = {
    "plausible": (0.85, 0.15, 0.02),
    "balanced": (0.60, 0.40, 0.04),
    "adventurous": (0.35, 0.65, 0.07),
}
INTENT_AXES = (
    "darker_brighter",
    "tense_relaxed",
    "common_surprising",
    "simple_complex",
    "resolved_open",
    "smooth",
    "dreamy",
)


@dataclass(frozen=True)
class ScoredCandidate:
    token: str
    score: float
    plausibility: float
    score_breakdown: dict[str, float | dict[str, float]]
    features: CandidateFeatures


def load_weights(path: Path = WEIGHTS_FILE) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    weights = payload["weights"]
    if set(weights) != set(FEATURE_NAMES):
        raise ValueError("Plausibility weights do not match runtime features")
    return {name: float(weights[name]) for name in FEATURE_NAMES}


def intent_score(
    color_delta: dict[str, float],
    intent: dict[str, float] | None,
    candidate: CandidateFeatures | None = None,
) -> float:
    """Orient sliders toward their right-hand labels.

    The optional dreamy direction uses a transparent theory/perceptual
    heuristic: a smooth borrowed major-seventh mediant tends to sound more
    dreamlike than an equally smooth diatonic triad. Modal mixture also
    informs perceived darkness; raw line-of-fifths brightness remains intact
    in the returned color deltas.
    """
    if not intent:
        return 0.0
    unknown = set(intent) - set(INTENT_AXES)
    if unknown or any(
        not -1 <= value <= 1 or not math.isfinite(value) for value in intent.values()
    ):
        raise ValueError("Intent axes must be known and lie in [-1, 1]")
    borrowed = candidate.values["borrowed"] if candidate else 0.0
    mediant = candidate.values["chromatic_mediant"] if candidate else 0.0
    major_seventh = (
        float(candidate.token.partition(":")[2].split("/", 1)[0].endswith("maj7"))
        if candidate
        else 0.0
    )
    dreamy = (
        0.75 * borrowed * mediant * major_seventh
        + 0.15 * max(0.0, color_delta["smoothness"])
        + 0.10 * max(0.0, -color_delta["tension"])
    )
    oriented = {
        "darker_brighter": color_delta["brightness"] - 0.4 * borrowed * (1.0 + mediant),
        "tense_relaxed": -color_delta["tension"],
        "common_surprising": color_delta["surprise"],
        "simple_complex": color_delta["complexity"],
        "resolved_open": -color_delta["resolution"],
        "smooth": color_delta["smoothness"],
        "dreamy": dreamy,
    }
    magnitude = sum(abs(value) for value in intent.values())
    if magnitude == 0:
        return 0.0
    return sum(intent[name] * oriented[name] for name in intent) / magnitude


@lru_cache(maxsize=4096)
def _pitch_classes(token: str) -> frozenset[int]:
    key = "C minor" if token.startswith("m:") else "C major"
    return frozenset(realize(token, key).chord.pitch_classes)


def score_candidates(
    candidates: list[CandidateFeatures],
    *,
    intent: dict[str, float] | None = None,
    preset: Preset = "balanced",
    weights: dict[str, float] | None = None,
    limit: int | None = None,
    selection_diversity: float = 0.8,
) -> list[ScoredCandidate]:
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if not math.isfinite(selection_diversity) or selection_diversity < 0:
        raise ValueError("selection_diversity must be finite and nonnegative")
    if not candidates:
        return []
    coefficients = weights or load_weights()
    if set(coefficients) != set(FEATURE_NAMES):
        raise ValueError("Weights do not match runtime features")
    logits = [
        sum(coefficients[name] * item.values[name] for name in FEATURE_NAMES) for item in candidates
    ]
    center = max(logits)
    exponentials = [math.exp(value - center) for value in logits]
    denominator = sum(exponentials)
    probabilities = [value / denominator for value in exponentials]
    # Remove the lowest 5% of the candidate plausibility distribution.
    floor_index = max(0, math.ceil(len(probabilities) * 0.05) - 1)
    floor = sorted(probabilities)[floor_index]
    average, spread = mean(logits), pstdev(logits) or 1.0
    w_p, w_i, w_d = PRESETS[preset]
    results = []
    for item, logit, probability in zip(candidates, logits, probabilities, strict=True):
        if probability < floor:
            continue
        parts = {name: coefficients[name] * item.values[name] for name in FEATURE_NAMES}
        intent_value = intent_score(item.color_delta, intent, item)
        diversity = (1.0 - item.values["common_tones"]) * 0.5 + item.values["tonal_distance"] * 0.5
        plaus_term = w_p * (logit - average) / spread
        # Color deltas are bounded by one while candidate-set z-scores span
        # several units. Scale an explicit creative request accordingly.
        intent_term = 6.0 * w_i * intent_value
        diversity_term = w_d * diversity
        surprise_bonus = 0.08 * item.values["surprise"] if preset == "adventurous" else 0.0
        score = plaus_term + intent_term + diversity_term + surprise_bonus
        results.append(
            ScoredCandidate(
                item.token,
                score,
                probability,
                {
                    "feature_contributions": parts,
                    "plausibility_logit": logit,
                    "plausibility_z": plaus_term,
                    "intent": intent_term,
                    "diversity": diversity_term,
                    "surprise_bonus": surprise_bonus,
                    "plausibility_floor": floor,
                    "total": score,
                },
                item,
            )
        )
    # Penalize redundancy within the returned list, not just similarity to
    # the previous chord. The first choice retains its original utility.
    selected: list[ScoredCandidate] = []
    while results and (limit is None or len(selected) < limit):

        def penalty(item: ScoredCandidate) -> float:
            if not selection_diversity or not selected:
                return 0.0
            pitches = _pitch_classes(item.token)
            return selection_diversity * max(
                len(pitches & _pitch_classes(other.token))
                / max(1, len(pitches | _pitch_classes(other.token)))
                for other in selected
            )

        penalties = {item.token: penalty(item) for item in results}
        choice = min(results, key=lambda item: (-(item.score - penalties[item.token]), item.token))
        adjustment = -penalties[choice.token]
        score = choice.score + adjustment
        selected.append(
            replace(
                choice,
                score=score,
                score_breakdown={
                    **choice.score_breakdown,
                    "selection_diversity": adjustment,
                    "total": score,
                },
            )
        )
        results.remove(choice)
    return selected
