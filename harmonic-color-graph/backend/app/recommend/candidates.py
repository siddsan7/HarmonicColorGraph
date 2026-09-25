"""Bounded, source-tagged union of statistical, graph, theory and vector candidates."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.predict.ngram import PredictionResult
from app.predict.realize import realize
from app.theory.roman import parse_key


@dataclass(frozen=True)
class Candidate:
    token: str
    generators: frozenset[str]
    ngram_probability: float = 0.0
    graph_probability: float = 0.0
    embedding_similarity: float | None = None


_BORROWED = {
    "M": ("iv", "bVI", "bVII", "bIII", "i", "iio", "bVImaj7"),
    "m": ("IV", "V7", "bVI", "bVII", "I", "II"),
}
_MEDIANTS = {"M": ("bIII", "bVI", "III", "VI"), "m": ("III", "VI", "bIII", "bVI")}
_TARGETS = {"M": ("I", "ii", "iii", "IV", "V", "vi"), "m": ("i", "ii", "III", "iv", "V", "VI")}
_BASIC = {
    "M": ("I", "ii", "iii", "IV", "V", "vi", "vii"),
    "m": ("i", "iio", "III", "iv", "V", "VI", "VII"),
}


def theory_expansions(history: Sequence[str], key: str) -> set[str]:
    """Finite theory vocabulary; every token must round-trip through realization."""
    mode = history[-1][0] if history else ("M" if parse_key(key)[1] == "major" else "m")
    if mode not in _BORROWED or any(not token.startswith(f"{mode}:") for token in history):
        raise ValueError("History tokens must share a mode")
    figures = {*_BASIC[mode], *_BORROWED[mode], *_MEDIANTS[mode]}
    for target in _TARGETS[mode]:
        figures.add(f"V7/{target}")
        figures.add(f"viio7/{target}")
        figures.add(f"subV7/{target}")
    return {token for figure in figures if _realizable(token := f"{mode}:{figure}", key)}


def _realizable(token: str, key: str) -> bool:
    try:
        realize(token, key)
    except ValueError:
        return False
    return True


def generate_candidates(
    history: Sequence[str],
    key: str,
    prediction: PredictionResult,
    *,
    graph_neighbors: Iterable[tuple[str, float]] = (),
    embedding_neighbors: Iterable[tuple[str, float]] = (),
    min_graph_prob: float = 0.005,
) -> list[Candidate]:
    """Union sources, retaining provenance and excluding unrealizable tokens.

    The caller queries graph neighbors of the last token and embedding neighbors
    of the top five n-gram tokens. Missing graph/vector data is an empty input.
    Each source is bounded to keep recommendation latency predictable.
    """
    if not 0 <= min_graph_prob <= 1:
        raise ValueError("min_graph_prob must be in [0, 1]")
    mode = history[-1][0] if history else ("M" if parse_key(key)[1] == "major" else "m")
    merged: dict[str, dict] = {}

    def add(token: str, source: str, value: float = 0.0) -> None:
        if not token.startswith(f"{mode}:") or not _realizable(token, key):
            return
        row = merged.setdefault(
            token,
            {
                "generators": set(),
                "ngram_probability": 0.0,
                "graph_probability": 0.0,
                "embedding_similarity": None,
            },
        )
        row["generators"].add(source)
        if source == "ngram":
            row["ngram_probability"] = max(row["ngram_probability"], value)
        elif source == "graph":
            row["graph_probability"] = max(row["graph_probability"], value)
        elif source == "embedding":
            current = row["embedding_similarity"]
            row["embedding_similarity"] = value if current is None else max(current, value)

    for item in prediction.predictions[:30]:
        add(item.token, "ngram", item.probability)
    for token, probability in list(graph_neighbors)[:100]:
        if probability >= min_graph_prob:
            add(token, "graph", probability)
    for token in sorted(theory_expansions(history, key)):
        add(token, "theory")
    for token, similarity in list(embedding_neighbors)[:50]:
        add(token, "embedding", similarity)
    ranked = sorted(merged.items(), key=lambda item: (-item[1]["ngram_probability"], item[0]))
    priority = {f"{mode}:{figure}" for figure in ("ii", "iv", "vi", "bVII")}
    first = ranked[:16]
    priority_rows = [row for row in ranked[16:] if row[0] in priority]
    rest = [row for row in ranked[16:] if row[0] not in priority]
    ordered = first + priority_rows + rest
    return [
        Candidate(
            token,
            frozenset(row["generators"]),
            row["ngram_probability"],
            row["graph_probability"],
            row["embedding_similarity"],
        )
        for token, row in ordered
    ]
