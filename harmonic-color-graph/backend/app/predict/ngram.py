"""F30: interpolated Kneser-Ney next-token prediction over core function
tokens, with context backoff across genre x section -> genre -> section ->
global.

The store owns SQL (and, for Postgres, context-key resolution). This module
owns the KN math: discounting, order backoff within one context, and
weighted mixing across the context chain. Mirrors the split in
`app/graph/service.py`.

Within one context, `order` follows n-gram convention (order 1 is the
unigram, order n has n-1 preceding tokens as history) -- the same
convention `pipeline/stages/ngrams.py` uses for the artifact this module
reads, at runtime, from `hcg.ngram_histories`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Protocol

# Reused, not duplicated: these constants and the history-string join
# convention are the pipeline's, and this module must read exactly what
# that pipeline wrote. Importing the module only pulls in these top-level
# constants -- `run_ngrams` itself lazy-imports polars, so this import does
# not pull polars into the FastAPI runtime.
from pipeline.stages.ngrams import HISTORY_SEP, MAX_ORDER_GLOBAL, MAX_ORDER_OTHER

# F30 plan: "K is tuned on the dev split." F31 (the leak-free evaluation
# harness) doesn't exist yet, so there is no dev split to tune against.
# 100 is a placeholder -- large enough that a context needs real repeated
# evidence (roughly 100+ observations of the exact history) before it
# dominates its backoff parent, small enough that a context with a few
# hundred observations still gets most of the weight. F31 should replace
# this with a tuned value and remove this comment.
DEFAULT_MIXING_K = 100.0


@dataclass(frozen=True)
class NgramHistory:
    total: int
    distinct_next: int
    next: dict[str, int]
    cont: dict[str, int]


@dataclass(frozen=True)
class OrderContribution:
    """How much of a predicted token's probability came from one
    (context, order) term in the backoff/mixing chain."""

    context: str
    order: int
    contribution: float


@dataclass(frozen=True)
class TokenPrediction:
    token: str
    probability: float
    support: int
    breakdown: tuple[OrderContribution, ...]


@dataclass(frozen=True)
class PredictionResult:
    history: tuple[str, ...]
    context_chain: tuple[str, ...]
    predictions: tuple[TokenPrediction, ...]
    # (context, order) pairs that actually had supporting data, most
    # specific first -- the evidence trail, not every chain step attempted.
    backoff_path: tuple[tuple[str, int], ...]


class NgramReader(Protocol):
    def active_version(self) -> str | None: ...

    def context_by_key(self, context: str) -> dict[str, Any] | None: ...

    def histories(
        self, requests: Sequence[tuple[int, int, str]]
    ) -> dict[tuple[int, int, str], NgramHistory]: ...

    def count_of_counts(
        self, requests: Sequence[tuple[int, int]]
    ) -> dict[tuple[int, int], tuple[int, int]]: ...


def _max_order(context_key: str) -> int:
    """Matches `pipeline/stages/ngrams.py`'s `_max_order`: every context
    except `global` was built with the same (lower) max order."""
    return MAX_ORDER_GLOBAL if context_key == "global" else MAX_ORDER_OTHER


def context_chain_keys(genre: str | None, section: str | None) -> list[str]:
    """The F30 backoff order: genre x section -> genre -> section -> global.
    Levels the caller didn't supply are simply absent from the chain."""
    chain: list[str] = []
    if genre and section:
        chain.append(f"genre_section:{genre}:{section}")
    if genre:
        chain.append(f"genre:{genre}")
    if section:
        chain.append(f"section:{section}")
    chain.append("global")
    return chain


def _discount(n1: int, n2: int) -> float:
    """Interpolated KN's single discount per order, `D = n1/(n1+2*n2)`
    (Chen & Goodman's `Y`), from count-of-counts pooled over every history
    at that (context, order). Always in [0, 1] for n1, n2 >= 0."""
    denominator = n1 + 2 * n2
    return n1 / denominator if denominator else 0.0


def _history_suffix(history_tokens: Sequence[str], hist_len: int) -> str:
    if hist_len == 0:
        return ""
    return HISTORY_SEP.join(history_tokens[len(history_tokens) - hist_len :])


def _order_chain(history_len: int, max_order: int) -> list[int]:
    """Orders to try within one context, from the highest usable order
    (bounded by both the available history and that context's own max
    order) down to 1, the unigram floor."""
    top = min(history_len, max_order - 1) + 1
    return list(range(top, 0, -1))


def _within_context_requests(
    context_id: int, history_tokens: Sequence[str], max_order: int
) -> list[tuple[int, int, str]]:
    return [
        (context_id, order, _history_suffix(history_tokens, order - 1))
        for order in _order_chain(len(history_tokens), max_order)
    ]


@dataclass
class _ChainResolution:
    """One resolved (chain-order-preserved) context, from most specific to
    `global`."""

    key: str
    context_id: int
    max_order: int


@dataclass
class _Computed:
    """Everything `predict()` and `distribution()` share: the full mixed
    distribution plus enough bookkeeping to explain any token in it."""

    history_tokens: tuple[str, ...]
    context_ids: list[int]
    id_to_key: dict[int, str]
    distribution: dict[str, float]
    contributions: dict[tuple[int, int], dict[str, float]]
    backoff_path_ids: list[tuple[int, int]]
    rows_by_context_order: dict[tuple[int, int], NgramHistory]


@dataclass
class KNPredictor:
    store: NgramReader
    mixing_k: float = DEFAULT_MIXING_K
    # F31's baseline ablations ("KN orders 2-5, with and without context
    # backoff") need a lower max order than the pipeline actually built --
    # e.g. evaluating "order 3" means never using order 4/5 evidence even
    # though it exists in the store. None (the default) uses each
    # context's own real max order, exactly as production does.
    max_order_cap: int | None = None
    # Corpus-wide, changes only when the active version changes -- unlike
    # the per-request history fetch, safe (and worth it) to cache like
    # `graph/service.py`'s `_ADJACENCY_CACHE`.
    discount_cache_size: int = 64

    _discount_cache: dict[tuple[str, int, int], float] = field(
        default_factory=dict, init=False, repr=False
    )
    _discount_cache_order: list[tuple[str, int, int]] = field(
        default_factory=list, init=False, repr=False
    )
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def distribution(
        self, history: Sequence[str], *, genre: str | None = None, section: str | None = None
    ) -> dict[str, float]:
        """The full probability distribution over every token the corpus
        has ever seen in this position, not just the top-N. F31's
        perplexity/NDCG metrics need the probability the model assigned to
        the *actual* next token, which usually isn't in the top-N."""
        return self._compute(history, genre, section).distribution

    def predict(
        self,
        history: Sequence[str],
        *,
        genre: str | None = None,
        section: str | None = None,
        top_n: int = 10,
    ) -> PredictionResult:
        if not 1 <= top_n <= 100:
            raise ValueError("top_n must be between 1 and 100")
        computed = self._compute(history, genre, section)
        ranked = sorted(computed.distribution.items(), key=lambda item: (-item[1], item[0]))[:top_n]
        predictions = tuple(
            self._token_prediction(
                token,
                probability,
                computed.contributions,
                computed.backoff_path_ids,
                computed.rows_by_context_order,
                computed.id_to_key,
            )
            for token, probability in ranked
        )
        return PredictionResult(
            history=computed.history_tokens,
            context_chain=tuple(computed.id_to_key[cid] for cid in computed.context_ids),
            predictions=predictions,
            backoff_path=tuple(
                (computed.id_to_key[cid], order) for cid, order in computed.backoff_path_ids
            ),
        )

    def _compute(self, history: Sequence[str], genre: str | None, section: str | None) -> _Computed:
        history_tokens = tuple(history)
        resolved = self._resolve_chain(genre, section)
        if not resolved:
            raise LookupError("No graph context available for prediction (no active corpus)")

        requests: list[tuple[int, int, str]] = []
        co_requests: set[tuple[int, int]] = set()
        for level in resolved:
            requests.extend(
                _within_context_requests(level.context_id, history_tokens, level.max_order)
            )
            for order in _order_chain(len(history_tokens), level.max_order):
                if order > 1:  # order 1 uses continuation counts, not a discount
                    co_requests.add((level.context_id, order))

        rows = self.store.histories(requests)  # one SQL round trip for this request
        discounts = self._discounts(co_requests)

        contributions: dict[tuple[int, int], dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        dist, backoff_path_ids = self._mix_chain(
            [level.context_id for level in resolved],
            [level.max_order for level in resolved],
            history_tokens,
            rows,
            discounts,
            contributions,
        )
        dist = _renormalize(dist)

        # Exactly one row per (context_id, order) within a single request
        # (one history per order in each context's own backoff chain), so
        # this drops the (unused) history string with no ambiguity.
        rows_by_context_order = {(cid, order): row for (cid, order, _history), row in rows.items()}
        return _Computed(
            history_tokens=history_tokens,
            context_ids=[level.context_id for level in resolved],
            id_to_key={level.context_id: level.key for level in resolved},
            distribution=dist,
            contributions=contributions,
            backoff_path_ids=backoff_path_ids,
            rows_by_context_order=rows_by_context_order,
        )

    def _resolve_chain(self, genre: str | None, section: str | None) -> list[_ChainResolution]:
        resolved: list[_ChainResolution] = []
        for key in context_chain_keys(genre, section):
            row = self.store.context_by_key(key)
            if row is None:
                # Not an error: this context simply wasn't kept by the
                # pipeline (too few observations) or was never requested at
                # all (e.g. no genre given) -- drop it from the chain, same
                # net effect as giving it zero support (beta = 0 below).
                continue
            max_order = _max_order(key)
            if self.max_order_cap is not None:
                max_order = min(max_order, self.max_order_cap)
            resolved.append(
                _ChainResolution(key=key, context_id=int(row["id"]), max_order=max_order)
            )
        return resolved

    def _discounts(self, requests: set[tuple[int, int]]) -> dict[tuple[int, int], float]:
        version = self.store.active_version() or ""
        cached: dict[tuple[int, int], float] = {}
        missing: list[tuple[int, int]] = []
        with self._lock:
            for context_id, order in requests:
                key = (version, context_id, order)
                if key in self._discount_cache:
                    cached[(context_id, order)] = self._discount_cache[key]
                else:
                    missing.append((context_id, order))
        if missing:
            counts = self.store.count_of_counts(missing)
            with self._lock:
                for pair in missing:
                    n1, n2 = counts.get(pair, (0, 0))
                    discount = _discount(n1, n2)
                    cached[pair] = discount
                    cache_key = (version, *pair)
                    self._discount_cache[cache_key] = discount
                    self._discount_cache_order.append(cache_key)
                    if len(self._discount_cache_order) > self.discount_cache_size:
                        stale = self._discount_cache_order.pop(0)
                        self._discount_cache.pop(stale, None)
        return cached

    def _mix_chain(
        self,
        context_ids: list[int],
        max_orders: list[int],
        history_tokens: tuple[str, ...],
        rows: dict[tuple[int, int, str], NgramHistory],
        discounts: dict[tuple[int, int], float],
        contributions: dict[tuple[int, int], dict[str, float]],
    ) -> tuple[dict[str, float], list[tuple[int, int]]]:
        context_id, max_order = context_ids[0], max_orders[0]
        dist_here, backoff_here = _context_distribution(
            context_id, max_order, history_tokens, rows, discounts, contributions
        )
        if len(context_ids) == 1:
            return dist_here, backoff_here

        top_order = _order_chain(len(history_tokens), max_order)[0]
        top_key = (context_id, top_order, _history_suffix(history_tokens, top_order - 1))
        n_ctx_h = rows[top_key].total if top_key in rows else 0
        beta = n_ctx_h / (n_ctx_h + self.mixing_k) if (n_ctx_h + self.mixing_k) > 0 else 0.0

        dist_rest, backoff_rest = self._mix_chain(
            context_ids[1:], max_orders[1:], history_tokens, rows, discounts, contributions
        )

        for key in backoff_here:
            contributions[key] = {
                token: amount * beta for token, amount in contributions[key].items()
            }
        for key in backoff_rest:
            contributions[key] = {
                token: amount * (1 - beta) for token, amount in contributions[key].items()
            }

        merged: dict[str, float] = defaultdict(float)
        for token, probability in dist_here.items():
            merged[token] += beta * probability
        for token, probability in dist_rest.items():
            merged[token] += (1 - beta) * probability
        return dict(merged), backoff_here + backoff_rest

    @staticmethod
    def _token_prediction(
        token: str,
        probability: float,
        contributions: dict[tuple[int, int], dict[str, float]],
        backoff_path_ids: list[tuple[int, int]],
        rows_by_context_order: dict[tuple[int, int], NgramHistory],
        id_to_key: dict[int, str],
    ) -> TokenPrediction:
        breakdown = tuple(
            OrderContribution(context=id_to_key[context_id], order=order, contribution=amount)
            for context_id, order in backoff_path_ids
            if (amount := contributions.get((context_id, order), {}).get(token, 0.0)) > 0
        )
        # "support (counts)": the raw observed count backing this token,
        # from the most specific (context, order) step whose *raw* next
        # counts actually include it (the unigram's counts are
        # continuation counts, not raw observations, so it's excluded here
        # even when it's on the backoff path).
        support = 0
        for context_id, order in backoff_path_ids:
            if order == 1:
                continue
            row = rows_by_context_order.get((context_id, order))
            if row is not None and token in row.next:
                support = row.next[token]
                break
        return TokenPrediction(
            token=token, probability=probability, support=support, breakdown=breakdown
        )


def _context_distribution(
    context_id: int,
    max_order: int,
    history_tokens: tuple[str, ...],
    rows: dict[tuple[int, int, str], NgramHistory],
    discounts: dict[tuple[int, int], float],
    contributions: dict[tuple[int, int], dict[str, float]],
) -> tuple[dict[str, float], list[tuple[int, int]]]:
    """Interpolated KN within a single context: `P = own_term(order) +
    lambda(order) * P(order - 1)`, recursing down to the unigram, which
    (per the plan) uses continuation counts instead of raw counts.

    Implemented top-down as a loop, tracking `path_weight` (the product of
    every lambda consumed so far) instead of recursing bottom-up, so the
    per-(context, order) contribution recorded at each step already carries
    its true final weight -- no second pass to rescale it afterward.
    """
    dist: dict[str, float] = {}
    backoff_path: list[tuple[int, int]] = []
    path_weight = 1.0
    for order in _order_chain(len(history_tokens), max_order):
        history = _history_suffix(history_tokens, order - 1)
        row = rows.get((context_id, order, history))
        if order == 1:
            total_cont = sum(row.cont.values()) if row is not None else 0
            if total_cont > 0:
                backoff_path.append((context_id, 1))
                bucket = contributions[(context_id, 1)]
                for token, count in row.cont.items():
                    amount = path_weight * (count / total_cont)
                    dist[token] = dist.get(token, 0.0) + amount
                    bucket[token] += amount
            break
        if row is None or row.total == 0:
            continue  # no evidence at this order: pure backoff, weight unchanged
        backoff_path.append((context_id, order))
        discount = discounts.get((context_id, order), 0.0)
        bucket = contributions[(context_id, order)]
        for token, count in row.next.items():
            amount = path_weight * (max(count - discount, 0.0) / row.total)
            dist[token] = dist.get(token, 0.0) + amount
            bucket[token] += amount
        path_weight *= discount * row.distinct_next / row.total
    return dist, backoff_path


def _renormalize(dist: dict[str, float]) -> dict[str, float]:
    """Safety net, not the common path: with real corpus data every
    context's order-1 row always has continuation counts (see
    `pipeline/stages/ngrams.py` -- order 1 is never pruned, and any kept
    context has order >= 2 data feeding its continuations), so mass sums to
    1 already. Guards a fixture or edge case where it doesn't, by spreading
    any missing mass uniformly over the tokens already seen, rather than
    silently returning a distribution that doesn't sum to 1.
    """
    total = sum(dist.values())
    if total <= 0.0 or not dist:
        return dist
    remainder = 1.0 - total
    if abs(remainder) < 1e-9:
        return dist
    if remainder > 0:
        bonus = remainder / len(dist)
        return {token: probability + bonus for token, probability in dist.items()}
    scale = 1.0 / total
    return {token: probability * scale for token, probability in dist.items()}


class InMemoryNgramStore:
    """F30: an `NgramReader` built directly from the `ngrams` pipeline
    artifact (or hand-written rows with the same shape), for tests and for
    F31's leak-free evaluation harness -- no Postgres involved.
    """

    def __init__(self, version: str = "test") -> None:
        self._version = version
        self._context_ids: dict[str, int] = {}
        self._context_keys: dict[int, str] = {}
        self._rows: dict[tuple[int, int, str], NgramHistory] = {}

    def active_version(self) -> str | None:
        return self._version

    def context_by_key(self, context: str) -> dict[str, Any] | None:
        context_id = self._context_ids.get(context)
        if context_id is None:
            return None
        return {"id": context_id, "type": context.split(":", 1)[0], "value": context}

    def histories(
        self, requests: Sequence[tuple[int, int, str]]
    ) -> dict[tuple[int, int, str], NgramHistory]:
        return {key: self._rows[key] for key in requests if key in self._rows}

    def count_of_counts(
        self, requests: Sequence[tuple[int, int]]
    ) -> dict[tuple[int, int], tuple[int, int]]:
        result: dict[tuple[int, int], tuple[int, int]] = {}
        for context_id, order in requests:
            n1 = n2 = 0
            for (row_context, row_order, _history), row in self._rows.items():
                if row_context != context_id or row_order != order:
                    continue
                for count in row.next.values():
                    if count == 1:
                        n1 += 1
                    elif count == 2:
                        n2 += 1
            result[(context_id, order)] = (n1, n2)
        return result

    def add_row(
        self,
        context: str,
        order: int,
        history: str,
        *,
        total: int,
        distinct_next: int,
        next: dict[str, int],
        cont: dict[str, int] | None = None,
    ) -> None:
        context_id = self._context_ids.setdefault(context, len(self._context_ids))
        self._context_keys[context_id] = context
        self._rows[(context_id, order, history)] = NgramHistory(
            total=total, distinct_next=distinct_next, next=dict(next), cont=dict(cont or {})
        )

    @classmethod
    def from_rows(
        cls, rows: Iterable[dict[str, Any]], *, version: str = "test"
    ) -> InMemoryNgramStore:
        """Each row has the `ngrams` artifact's shape: `context`, `order`,
        `history`, `total`, `distinct_next`, `next`, `cont` -- with `next`
        and `cont` either already-parsed dicts or JSON strings (as the
        parquet artifact and the Postgres `jsonb` columns both store them).
        """
        import json

        store = cls(version=version)
        for row in rows:
            next_counts = row["next"]
            if isinstance(next_counts, str):
                next_counts = json.loads(next_counts)
            cont_counts = row.get("cont", {})
            if isinstance(cont_counts, str):
                cont_counts = json.loads(cont_counts)
            store.add_row(
                row["context"],
                int(row["order"]),
                row["history"],
                total=int(row["total"]),
                distinct_next=int(row["distinct_next"]),
                next=next_counts,
                cont=cont_counts,
            )
        return store

    @classmethod
    def from_parquet(cls, path: str, *, version: str = "test") -> InMemoryNgramStore:
        """Load the real `ngrams` pipeline stage's parquet output -- the
        artifact F31's evaluation harness (and offline experimentation)
        runs against."""
        import polars as pl

        return cls.from_rows(pl.read_parquet(path).to_dicts(), version=version)
