"""Offline-trained plausibility plus bounded user-intent ranking."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Literal

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


def intent_score(color_delta: dict[str, float], intent: dict[str, float] | None) -> float:
    """Orient every slider so positive values mean its right-hand label."""
    if not intent:
        return 0.0
    unknown = set(intent) - set(INTENT_AXES)
    if unknown or any(
        not -1 <= value <= 1 or not math.isfinite(value) for value in intent.values()
    ):
        raise ValueError("Intent axes must be known and lie in [-1, 1]")
    oriented = {
        "darker_brighter": color_delta["brightness"],
        "tense_relaxed": -color_delta["tension"],
        "common_surprising": color_delta["surprise"],
        "simple_complex": color_delta["complexity"],
        "resolved_open": -color_delta["resolution"],
        "smooth": color_delta["smoothness"],
    }
    magnitude = sum(abs(value) for value in intent.values())
    if magnitude == 0:
        return 0.0
    return sum(intent[name] * oriented[name] for name in intent) / magnitude


def score_candidates(
    candidates: list[CandidateFeatures],
    *,
    intent: dict[str, float] | None = None,
    preset: Preset = "balanced",
    weights: dict[str, float] | None = None,
    limit: int | None = None,
) -> list[ScoredCandidate]:
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
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
        intent_value = intent_score(item.color_delta, intent)
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
    results.sort(key=lambda item: (-item.score, item.token))
    return results[:limit]
