"""Statistical next-chord recommendations shared by HTTP and future tools."""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.db.stores.graph import FactStore, NgramStore, PatternStore
from app.predict.ngram import KNPredictor, NgramHistory, PredictionResult
from app.predict.realize import realize
from app.schemas.recommend_v2 import (
    ContextUsed,
    Evidence,
    ExampleRef,
    Recommendation,
    RecommendData,
    RecommendMeta,
    RecommendRequest,
    RecommendResponse,
    RecommendWarning,
    ScoreBreakdown,
)
from app.theory.roman import analyze_v2, parse_key

_TOKEN = re.compile(r"^[Mm]:\S+$")
_COUNT_CACHE: OrderedDict[tuple[str, int, int], tuple[int, int]] = OrderedDict()
_COUNT_LOCK = Lock()
_COUNT_CACHE_SIZE = 128


class ExampleReader(Protocol):
    def transition_examples_many(
        self, pairs: list[tuple[str, str]], *, limit: int
    ) -> dict[tuple[str, str], list[dict[str, Any]]]: ...


class FactReader(Protocol):
    def existing_ids(self, fact_ids: list[str]) -> set[str]: ...


class SessionNgramReader:
    """Translate SQL rows into the predictor's store protocol."""

    def __init__(self, session: Session):
        self.store = NgramStore(session)

    def active_version(self) -> str | None:
        return self.store.active_version()

    def context_by_key(self, context: str) -> dict[str, Any] | None:
        return self.store.context_by_key(context)

    def histories(
        self, requests: list[tuple[int, int, str]]
    ) -> dict[tuple[int, int, str], NgramHistory]:
        return {
            (row["context_id"], row["ord"], row["history"]): NgramHistory(
                total=row["total"],
                distinct_next=row["distinct_next"],
                next=row["next"],
                cont=row["cont"],
            )
            for row in self.store.histories(requests)
        }

    def count_of_counts(
        self, requests: list[tuple[int, int]]
    ) -> dict[tuple[int, int], tuple[int, int]]:
        version = self.active_version() or ""
        result: dict[tuple[int, int], tuple[int, int]] = {}
        missing: list[tuple[int, int]] = []
        with _COUNT_LOCK:
            for pair in requests:
                key = (version, *pair)
                if key in _COUNT_CACHE:
                    result[pair] = _COUNT_CACHE[key]
                    _COUNT_CACHE.move_to_end(key)
                else:
                    missing.append(pair)
        if missing:
            rows = self.store.count_of_counts(missing)
            fresh = {(row["context_id"], row["ord"]): (row["n1"], row["n2"]) for row in rows}
            with _COUNT_LOCK:
                for pair in missing:
                    result[pair] = fresh.get(pair, (0, 0))
                    _COUNT_CACHE[(version, *pair)] = result[pair]
                    _COUNT_CACHE.move_to_end((version, *pair))
                while len(_COUNT_CACHE) > _COUNT_CACHE_SIZE:
                    _COUNT_CACHE.popitem(last=False)
        return result


class RecommendationService:
    def __init__(self, predictor: KNPredictor, examples: ExampleReader, facts: FactReader):
        self.predictor = predictor
        self.examples = examples
        self.facts = facts

    @classmethod
    def from_session(cls, session: Session) -> RecommendationService:
        return cls(
            KNPredictor(SessionNgramReader(session)), PatternStore(session), FactStore(session)
        )

    def recommend(self, request: RecommendRequest) -> RecommendResponse:
        started = time.perf_counter()
        version = self.predictor.store.active_version()
        if version is None:
            raise LookupError("No corpus version is active")
        tokens, key, warnings = _input_tokens(request.progression, request.key)
        genre = _context_value(request.genre)
        section = _context_value(request.section)
        prediction = self.predictor.predict(tokens, genre=genre, section=section, top_n=100)
        recommendations = self._items(
            prediction, tokens, key, request.limit, request.include_explanations
        )
        if not recommendations:
            warnings.append(
                RecommendWarning(
                    code="no_recommendations", message="No supported next chords were found."
                )
            )
        if genre and not any(
            context.startswith("genre:") or context.startswith("genre_section:")
            for context in prediction.context_chain
        ):
            warnings.append(
                RecommendWarning(
                    code="context_backoff",
                    message=(
                        "The requested genre has no retained corpus context; "
                        "global statistics were used."
                    ),
                )
            )
        if section and not any(
            context.startswith("section:") or context.startswith("genre_section:")
            for context in prediction.context_chain
        ):
            warnings.append(
                RecommendWarning(
                    code="context_backoff",
                    message=(
                        "The requested section has no retained corpus context; "
                        "broader statistics were used."
                    ),
                )
            )
        return RecommendResponse(
            data=RecommendData(input_tokens=tokens, key=key, recommendations=recommendations),
            meta=RecommendMeta(
                corpus_version=version,
                model_versions={"predictor": "interpolated-kn-v2"},
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                context_used=ContextUsed(
                    genre=genre, section=section, backoff=list(prediction.context_chain)
                ),
            ),
            warnings=warnings,
        )

    def _items(
        self, prediction: PredictionResult, history: list[str], key: str, limit: int, explain: bool
    ) -> list[Recommendation]:
        available = []
        for item in prediction.predictions:
            if len(available) >= limit:
                break
            if item.token[0] != history[-1][0]:
                continue
            try:
                available.append((item, realize(item.token, key)))
            except ValueError:
                continue
        examples_by_pair = self.examples.transition_examples_many(
            [(history[-1], item.token) for item, _ in available], limit=2
        )
        candidate_fact_ids = [
            f"transition:{history[-1]}->{item.token}:global" for item, _ in available
        ]
        existing_fact_ids = self.facts.existing_ids(candidate_fact_ids)
        items: list[Recommendation] = []
        for item, realized in available:
            specific = sum(part.contribution for part in item.breakdown if part.context != "global")
            global_mass = sum(
                part.contribution for part in item.breakdown if part.context == "global"
            )
            contexts = list(dict.fromkeys(part.context for part in item.breakdown))
            examples = examples_by_pair.get((history[-1], item.token), [])
            refs = [
                ExampleRef(
                    song_id=row["song_id"],
                    spotify_id=row.get("spotify_id"),
                    genre=row.get("genre"),
                    section=row.get("section"),
                    position=row.get("position"),
                )
                for row in examples
            ]
            fact_id = f"transition:{history[-1]}->{item.token}:global"
            fact_ids = [fact_id] if fact_id in existing_fact_ids else []
            explanation = None
            if explain:
                source = "the selected context" if specific > global_mass else "the broader corpus"
                evidence_text = (
                    f"The strongest matching history has {item.support} observed continuations."
                    if item.support
                    else (
                        "This candidate comes from smoothing rather than an "
                        "exact observed continuation."
                    )
                )
                explanation = (
                    f"{realized.chord.raw_symbol} may follow here: the model assigns "
                    f"{item.probability:.1%} probability. Most support comes from {source}. "
                    f"{evidence_text}"
                )
            items.append(
                Recommendation(
                    token=item.token,
                    figure=item.token.partition(":")[2],
                    chord=realized.chord.raw_symbol,
                    score=item.probability,
                    score_breakdown=ScoreBreakdown(
                        ngram=item.probability,
                        context=specific,
                        backoff=global_mass,
                    ),
                    labels=[
                        ("Context supported" if specific > global_mass else "Corpus supported")
                        if item.support
                        else "Smoothed estimate"
                    ],
                    fact_ids=fact_ids,
                    evidence=Evidence(count=item.support, contexts=contexts, example_refs=refs),
                    explanation=explanation,
                )
            )
        return items


def _context_value(value: str | None) -> str | None:
    if value is None or value.strip().lower() in {"", "unknown"}:
        return None
    return value.strip().lower()


def _input_tokens(
    progression: str | list[str], key: str | None
) -> tuple[list[str], str, list[RecommendWarning]]:
    if isinstance(progression, str):
        parts = [
            part for part in re.split(r"\s*(?:,|\s+-\s+|\n)\s*|\s+", progression.strip()) if part
        ]
    else:
        parts = progression
    if not 1 <= len(parts) <= 128 or any(not part or len(part) > 80 for part in parts):
        raise ValueError(
            "Provide 1–128 nonempty chords or core tokens (each at most 80 characters)."
        )
    if all(_TOKEN.fullmatch(part) for part in parts):
        if not key:
            raise ValueError("A key is required when progression contains core tokens.")
        _, mode, normalized_key = parse_key(key)
        if any(part[0] != ("M" if mode == "major" else "m") for part in parts):
            raise ValueError("All core tokens must match the key's mode.")
        for part in parts:
            realize(part, normalized_key)
        return list(parts), normalized_key, []
    if any(_TOKEN.fullmatch(part) for part in parts):
        raise ValueError("Use either all chords or all core tokens in one progression.")
    analysis = analyze_v2(parts, key)
    if len(analysis.tokens) != len(parts):
        raise ValueError("Every chord must parse before recommendations can be calculated.")
    warnings = (
        [
            RecommendWarning(
                code="key_ambiguous",
                message="The detected key is ambiguous; recommendations use its leading key.",
            )
        ]
        if analysis.ambiguous
        else []
    )
    return [token.core for token in analysis.tokens], analysis.song_key, warnings
