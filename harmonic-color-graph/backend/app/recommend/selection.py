"""Bounded selection priority for independently validated strong balanced requests."""

from __future__ import annotations

from dataclasses import replace

from app.recommend.scorer import ScoredCandidate, intent_score


def strong_balanced_request(intent: dict[str, float] | None, preset: str) -> bool:
    active = [value for value in (intent or {}).values() if value]
    return preset == "balanced" and bool(active) and all(abs(value) >= 0.7 for value in active)


def select_strong_adjacent(
    ranked: list[ScoredCandidate],
    intent: dict[str, float] | None,
    *,
    preset: str = "balanced",
) -> list[ScoredCandidate]:
    """Swap only the incumbent top two when the second meets every strong axis.

    The .025 predicate matches the frozen directional rubric. Exchange selected
    utility scores so downstream sorting preserves this bounded priority. Keep
    learned plausibility, feature terms and the original diversity terms intact;
    the signed selection_constraint term records the entire utility adjustment.
    The utility multiset, and therefore its softmax normalizer, is unchanged.
    """
    if len(ranked) < 2 or not strong_balanced_request(intent, preset):
        return ranked
    active = {axis: value for axis, value in (intent or {}).items() if value}

    def satisfies(row: ScoredCandidate) -> bool:
        return all(
            (
                intent_score(row.features.color_delta, {axis: 1.0}, row.features)
                - (0.5 if axis == "common_surprising" else 0)
            )
            * target
            >= 0.025
            for axis, target in active.items()
        )

    first, second = ranked[:2]
    if satisfies(first) or not satisfies(second):
        return ranked

    def adjusted(row: ScoredCandidate, score: float) -> ScoredCandidate:
        return replace(
            row,
            score=score,
            score_breakdown={
                **row.score_breakdown,
                "selection_constraint": score - row.score,
                "total": score,
            },
        )

    return [adjusted(second, first.score), adjusted(first, second.score), *ranked[2:]]
