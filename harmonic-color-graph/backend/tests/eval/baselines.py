"""F31 baselines compared against v2 (the full F30 predictor): a global
unigram floor, the v1 hard-backoff bigram, and v2 itself ablated to each
order 2-5 with and without context mixing.

Every baseline shares one `Baseline` protocol so the harness can loop over
them uniformly; each wraps the *same* `NgramReader` (built once from the
train-only artifact) so every comparison is apples-to-apples on identical
underlying counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.predict.ngram import KNPredictor, NgramReader, context_chain_keys


class Baseline(Protocol):
    name: str

    def distribution(
        self, history: tuple[str, ...], genre: str | None, section: str | None
    ) -> dict[str, float]: ...


@dataclass
class GlobalUnigramBaseline:
    """Ignores history and context entirely: always the corpus-wide
    continuation-count unigram. The floor every other model should beat."""

    store: NgramReader
    name: str = "global_unigram"
    _cached: dict[str, float] | None = field(default=None, init=False, repr=False)

    def distribution(self, history, genre, section) -> dict[str, float]:
        if self._cached is None:
            context = self.store.context_by_key("global")
            if context is None:
                self._cached = {}
            else:
                rows = self.store.histories([(context["id"], 1, "")])
                row = rows.get((context["id"], 1, ""))
                total = sum(row.cont.values()) if row else 0
                self._cached = (
                    {token: count / total for token, count in row.cont.items()} if total else {}
                )
        return self._cached


@dataclass
class V1HardBackoffBaseline:
    """F04's v1 algorithm, re-implemented against v2's own bigram (order-2)
    counts for a fair comparison: raw MLE (`count/total`, no smoothing)
    within the first context in the chain that has any data for the last
    token, with no interpolation across contexts or orders. See
    `app/services/transition_lookup.py` for the original v1 implementation
    this mirrors (same chain order, same "first non-empty bucket wins"
    rule) -- not reused directly because v1 operates on its own
    differently-encoded Roman-numeral vocabulary and Postgres tables,
    which would make a "same underlying data" comparison impossible.
    """

    store: NgramReader
    name: str = "v1_hard_backoff_bigram"

    def distribution(self, history, genre, section) -> dict[str, float]:
        if not history:
            return {}
        last_token = history[-1]
        for key in context_chain_keys(genre, section):
            context = self.store.context_by_key(key)
            if context is None:
                continue
            rows = self.store.histories([(context["id"], 2, last_token)])
            row = rows.get((context["id"], 2, last_token))
            if row and row.total > 0:
                return {token: count / row.total for token, count in row.next.items()}
        return {}


@dataclass
class KNOrderBaseline:
    """v2 itself, ablated to a fixed max order and with context mixing on
    or off -- isolates how much each order and context contribute on top
    of the unigram/v1 floors."""

    predictor: KNPredictor
    use_context: bool
    name: str

    def distribution(self, history, genre, section) -> dict[str, float]:
        if self.use_context:
            return self.predictor.distribution(history, genre=genre, section=section)
        return self.predictor.distribution(history, genre=None, section=None)


def build_baselines(store: NgramReader) -> dict[str, Baseline]:
    baselines: dict[str, Baseline] = {
        "global_unigram": GlobalUnigramBaseline(store),
        "v1_hard_backoff_bigram": V1HardBackoffBaseline(store),
    }
    for order in (2, 3, 4, 5):
        predictor = KNPredictor(store, max_order_cap=order)
        baselines[f"kn_order{order}_no_context"] = KNOrderBaseline(
            predictor, use_context=False, name=f"kn_order{order}_no_context"
        )
        baselines[f"kn_order{order}_context"] = KNOrderBaseline(
            predictor, use_context=True, name=f"kn_order{order}_context"
        )
    return baselines


# v2's headline configuration per the plan's checks: order 5 (each
# context's real max order, uncapped) with full context mixing.
V2_FULL_NAME = "kn_order5_context"
