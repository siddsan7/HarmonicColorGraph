"""Similarity ranking over stored embeddings and deterministic chord features."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from app.db.stores.embeddings import EmbeddingStore
from app.schemas.similar_v2 import (
    SimilarChordRequest,
    SimilarFunctionRequest,
    SimilarItem,
    SimilarProgressionRequest,
    SimilarResponse,
)
from app.theory.chord_normalizer import normalize_chord
from app.theory.roman import analyze_v2, parse_key

CORE = re.compile(r"^[Mm]:[b#]?[ivIV]+(?:[+oh]?7?|maj7)?(?:/[b#]?[ivIV]+)?$")
BARE_ROMAN = re.compile(r"^[b#]?[ivIV]+(?:[+oh]?7?|maj7)?(?:/[b#]?[ivIV]+)?$")


def _rotation_of(a: list[str], b: list[str]) -> bool:
    return (
        len(a) == len(b)
        and a != b
        and any(a[offset:] + a[:offset] == b for offset in range(1, len(a)))
    )


def _overlap(a: list[str], b: list[str]) -> float:
    left, right = Counter(a), Counter(b)
    intersection = sum((left & right).values())
    union = sum((left | right).values())
    return intersection / union if union else 0.0


def _cosine_counts(a: dict[str, int], b: dict[str, int]) -> float:
    dot = sum(value * b.get(token, 0) for token, value in a.items())
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def _parse_tokens(request: SimilarProgressionRequest) -> list[str]:
    value = request.tokens if request.tokens is not None else request.progression
    assert value is not None
    parts = value.split() if isinstance(value, str) else value
    if all(CORE.fullmatch(item) for item in parts):
        tokens = parts
    elif all(BARE_ROMAN.fullmatch(item) for item in parts):
        mode = parse_key(request.key)[1] if request.key else "major"
        prefix = "M" if mode == "major" else "m"
        tokens = [f"{prefix}:{item}" for item in parts]
    else:
        analysis = analyze_v2(value, request.key)
        tokens = [token.core for token in analysis.tokens]
    if not 3 <= len(tokens) <= 8:
        raise ValueError("Progression must contain 3 to 8 valid chords or core tokens")
    if len({token[0] for token in tokens}) != 1:
        raise ValueError("All core tokens must have the same mode")
    return tokens


class SimilarityService:
    def __init__(self, store: EmbeddingStore):
        self.store = store

    def _version(self) -> str:
        version = self.store.active_version()
        if version is None:
            raise LookupError("No corpus version is active")
        return version

    def functions(self, request: SimilarFunctionRequest) -> SimilarResponse:
        version = self._version()
        model = request.model or self.store.default_model()
        if not CORE.fullmatch(request.token):
            raise ValueError("token must be a mode-prefixed core token")
        if self.store.vector("function", request.token, model=model) is None:
            raise ValueError("No embedding exists for this function token")
        rows = self.store.neighbors("function", request.token, model=model, limit=request.k)
        return SimilarResponse(
            query=request.token,
            model=model,
            results=[
                SimilarItem(subject_id=row["subject_id"], similarity=row["similarity"])
                for row in rows
            ],
            corpus_version=version,
        )

    def chords(self, request: SimilarChordRequest) -> SimilarResponse:
        version = self._version()
        normalized = normalize_chord(request.chord.replace(":", "", 1)).chord
        if normalized is None:
            raise ValueError("Chord could not be parsed")
        rows = self.store.chord_candidates(normalized.symbol)
        usage: dict[str, dict[str, int]] = defaultdict(dict)
        for row in rows:
            usage[row["chord"]][row["token"]] = row["count"]
        seed_usage = usage.get(normalized.symbol)
        if not seed_usage:
            raise ValueError("Chord has no corpus usage")
        seed_pcs = set(normalized.pitch_classes)
        results = []
        for chord, counts in usage.items():
            if chord == normalized.symbol:
                continue
            other = normalize_chord(chord.replace(":", "", 1)).chord
            if other is None:
                continue
            pcs = set(other.pitch_classes)
            jaccard = len(seed_pcs & pcs) / len(seed_pcs | pcs)
            similarity = 0.6 * jaccard + 0.4 * _cosine_counts(seed_usage, counts)
            results.append(SimilarItem(subject_id=chord, similarity=similarity))
        results.sort(key=lambda item: (-item.similarity, item.subject_id))
        return SimilarResponse(
            query=normalized.symbol,
            model="pitch_jaccard+function_usage",
            results=results[: request.k],
            corpus_version=version,
        )

    def progressions(self, request: SimilarProgressionRequest) -> SimilarResponse:
        version = self._version()
        tokens = _parse_tokens(request)
        query = " ".join(tokens)
        model = self.store.default_model()
        if request.mode == "structural":
            vector = self.store.vector("pattern", query, model="chord2vec")
            if vector is None:
                vectors = [
                    self.store.vector("function", token, model="chord2vec") for token in tokens
                ]
                if any(item is None for item in vectors):
                    raise ValueError("One or more tokens have no function embedding")
                vector = [
                    sum(item[i] for item in vectors) / len(vectors)  # type: ignore[index]
                    for i in range(64)
                ]
            candidates = self.store.neighbors_by_vector(
                "pattern", vector, model="chord2vec", limit=160, exclude=query
            )
            metadata = self.store.pattern_metadata([row["subject_id"] for row in candidates])
        else:
            metadata = {row["subject_id"]: row for row in self.store.popular_patterns()}
            candidates = [
                {"subject_id": pattern, "similarity": _overlap(tokens, pattern.split())}
                for pattern in metadata
                if pattern != query
            ]
        color = request.filters.color
        colors = self.store.pattern_colors(list(metadata), color.axis) if color else {}
        results = []
        for row in candidates:
            pattern = row["subject_id"]
            info = metadata.get(pattern)
            if info is None:
                continue
            if request.filters.genre:
                lifts = info["context_lifts"] or {}
                if f"genre:{request.filters.genre.lower()}" not in lifts:
                    continue
            if color and not color.min <= colors.get(pattern, -1) <= color.max:
                continue
            other = pattern.split()
            results.append(
                SimilarItem(
                    subject_id=pattern,
                    similarity=max(-1.0, min(1.0, row["similarity"])),
                    shared_tokens=sorted(set(tokens) & set(other)),
                    rotation_of=query if _rotation_of(tokens, other) else None,
                    support=info["support"],
                )
            )
        results.sort(
            key=lambda item: (
                -item.similarity,
                item.rotation_of is not None,
                -(item.support or 0),
                item.subject_id,
            )
        )
        return SimilarResponse(
            query=query,
            model="chord2vec" if request.mode == "structural" else "token_overlap",
            results=results[: request.k],
            corpus_version=version,
            warnings=[] if model == "chord2vec" else ["Structural pattern search uses chord2vec."],
        )
