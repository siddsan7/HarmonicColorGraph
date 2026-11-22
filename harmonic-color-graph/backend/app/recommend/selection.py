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


def single_strong_surprise(intent: dict[str, float] | None) -> bool:
    active = {axis: value for axis, value in (intent or {}).items() if value}
    return set(active) == {"common_surprising"} and active["common_surprising"] >= 0.7


def select_bounded_intent(
    ranked: list[ScoredCandidate],
    intent: dict[str, float] | None,
    *,
    preset: str = "balanced",
) -> list[ScoredCandidate]:
    """Add the frozen third-slot rotation only for single strong surprise.

    Selected utility slots rotate with the candidate priority; signed offsets
    retain every original score component and learned plausibility unchanged.
    Every other request keeps the independently validated adjacent policy.
    """
    if preset == "balanced" and len(ranked) >= 3 and single_strong_surprise(intent):
        target = (intent or {})["common_surprising"]

        def satisfies(row: ScoredCandidate) -> bool:
            return (
                intent_score(row.features.color_delta, {"common_surprising": 1.0}, row.features)
                - 0.5
            ) * target >= 0.025

        if not any(satisfies(row) for row in ranked[:2]) and satisfies(ranked[2]):
            return [
                replace(
                    row,
                    score=slot.score,
                    score_breakdown={
                        **row.score_breakdown,
                        "selection_constraint": slot.score - row.score,
                        "total": slot.score,
                    },
                )
                for row, slot in zip([ranked[2], ranked[0], ranked[1]], ranked[:3], strict=True)
            ] + ranked[3:]
    return select_strong_adjacent(ranked, intent, preset=preset)
