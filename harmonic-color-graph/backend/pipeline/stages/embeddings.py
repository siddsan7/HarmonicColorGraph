"""F50 offline Chord2Vec, FastRP, pattern embeddings and UMAP projections."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DIM = 64
SEED = 20260925
MIN_COUNT = 20
WINDOW = 4
TOP_PATTERNS = 5_000


@dataclass(frozen=True)
class EmbeddingsSummary:
    rows_written: int
    function_rows: int
    pattern_rows: int
    projection_rows: int
    train_sections: int
    model_vocab: int
    skipped_patterns: int


class TrainSentences:
    """Re-iterable, train-only stream of deduplicated section tokens."""

    def __init__(self, sections_path: str | Path):
        self.sections_path = Path(sections_path)

    def __iter__(self):
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(self.sections_path)
        for batch in parquet.iter_batches(columns=["split", "tokens"], batch_size=8192):
            for split, tokens in zip(
                batch.column("split").to_pylist(), batch.column("tokens").to_pylist(), strict=True
            ):
                if split == "train" and tokens:
                    yield tokens


def _stable_hash(value: str) -> int:
    return int.from_bytes(hashlib.blake2b(value.encode(), digest_size=8).digest(), "little")


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    return (vec / norm).astype(np.float32) if norm else vec.astype(np.float32)


def _theory_key(token: str) -> tuple[str, str, str] | None:
    if ":" not in token:
        return None
    mode, figure = token.split(":", 1)
    head, _, applied = figure.partition("/")
    match = re.match(r"([b#]*[ivIV]+)", head)
    return (mode, match.group(1), applied) if match else None


def _fastrp(transitions_path: Path, tokens: list[str]) -> dict[str, np.ndarray]:
    import polars as pl
    from scipy import sparse

    index = {token: i for i, token in enumerate(tokens)}
    edges: dict[tuple[int, int], float] = defaultdict(float)
    frame = pl.scan_parquet(transitions_path).filter(pl.col("context") == "global")
    for source, target, count in (
        frame.select("from_token", "to_token", "count").collect().iter_rows()
    ):
        if source in index and target in index and source != target:
            a, b = sorted((index[source], index[target]))
            edges[a, b] += float(np.log1p(count))
    families: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for token, i in index.items():
        key = _theory_key(token)
        if key is not None:
            families[key].append(i)
    for members in families.values():
        for left in range(len(members)):
            for right in range(left + 1, len(members)):
                a, b = sorted((members[left], members[right]))
                edges[a, b] += 3.0
    rows, cols, values = [], [], []
    for (a, b), weight in sorted(edges.items()):
        rows.extend((a, b))
        cols.extend((b, a))
        values.extend((weight, weight))
    size = len(tokens)
    adjacency = sparse.csr_matrix((values, (rows, cols)), shape=(size, size), dtype=np.float32)
    degrees = np.asarray(adjacency.sum(axis=1)).ravel()
    inverse = np.divide(1.0, degrees, out=np.zeros_like(degrees), where=degrees > 0)
    walk = sparse.diags(inverse) @ adjacency
    random = np.random.default_rng(SEED)
    state = random.choice(np.array([-1.0, 1.0], dtype=np.float32), size=(size, DIM))
    result = 0.2 * state
    for weight in (0.3, 0.3, 0.2):
        state = walk @ state
        result += weight * state
    return {token: _normalize(result[i]) for token, i in index.items()}


def _pattern_vector(
    pattern: str, vectors: dict[str, np.ndarray], counts: Counter[str]
) -> np.ndarray | None:
    tokens = pattern.split()
    available = [token for token in tokens if token in vectors]
    if not available:
        return None
    total = sum(counts.values())
    weights = np.array([0.001 / (0.001 + counts[token] / total) for token in available])
    mean = np.average(np.stack([vectors[token] for token in available]), axis=0, weights=weights)
    cadence = (vectors.get(tokens[-1], mean) - vectors.get(tokens[0], mean)) / 2
    return _normalize(0.85 * mean + 0.15 * cadence)


def _projection(rows: list[dict], output_path: Path, top_patterns: set[str]) -> int:
    import polars as pl

    selected = [
        row
        for row in rows
        if row["subject_type"] == "function"
        or (row["subject_type"] == "pattern" and row["subject_id"] in top_patterns)
    ]
    schema = {
        "subject_type": pl.Utf8,
        "subject_id": pl.Utf8,
        "model": pl.Utf8,
        "x": pl.Float32,
        "y": pl.Float32,
    }
    if not selected:
        pl.DataFrame(schema=schema).write_parquet(output_path)
        return 0
    import umap

    projected = []
    for model in sorted({row["model"] for row in selected}):
        model_rows = [row for row in selected if row["model"] == model]
        matrix = np.asarray([row["vec"] for row in model_rows], dtype=np.float32)
        if len(model_rows) >= 4:
            coordinates = umap.UMAP(
                n_components=2,
                n_neighbors=min(15, len(model_rows) - 1),
                metric="cosine",
                random_state=SEED,
                n_jobs=1,
            ).fit_transform(matrix)
        elif len(model_rows) >= 2:
            centered = matrix - matrix.mean(axis=0)
            u, s, _ = np.linalg.svd(centered, full_matrices=False)
            coordinates = np.zeros((len(model_rows), 2), dtype=np.float32)
            coordinates[:, : min(2, len(s))] = u[:, :2] * s[:2]
        else:
            coordinates = np.zeros((len(model_rows), 2), dtype=np.float32)
        for row, point in zip(model_rows, coordinates, strict=True):
            projected.append(
                {
                    "subject_type": row["subject_type"],
                    "subject_id": row["subject_id"],
                    "model": model,
                    "x": float(point[0]),
                    "y": float(point[1]),
                }
            )
    pl.DataFrame(projected, schema=schema).sort(
        "model", "subject_type", "subject_id"
    ).write_parquet(output_path)
    return len(projected)


def run_embeddings(
    sections_path: str | Path, output_dir: str | Path, *, min_count: int = MIN_COUNT
) -> EmbeddingsSummary:
    """Write loader-ready 64D vectors and 2D projections from train split."""
    import polars as pl
    from gensim.models import Word2Vec

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sentences = TrainSentences(sections_path)
    train_sections = sum(1 for _ in sentences)
    if not train_sections:
        raise ValueError("embeddings require train-split sections")
    model = Word2Vec(
        sentences=sentences,
        vector_size=DIM,
        window=WINDOW,
        min_count=min_count,
        sg=1,
        seed=SEED,
        workers=1,
        epochs=10,
        sorted_vocab=1,
        hashfxn=_stable_hash,
    )
    if not model.wv.index_to_key:
        raise ValueError(f"no function token reached min_count={min_count}")
    word_vectors = {token: _normalize(model.wv[token]) for token in model.wv.index_to_key}
    counts = Counter(
        {token: model.wv.get_vecattr(token, "count") for token in model.wv.index_to_key}
    )
    transitions = (
        pl.scan_parquet(output_dir / "transitions.parquet")
        .filter(pl.col("context") == "global")
        .select("from_token", "to_token")
        .collect()
    )
    graph_tokens = sorted(
        set(transitions["from_token"].to_list())
        | set(transitions["to_token"].to_list())
        | set(word_vectors)
    )
    graph_vectors = _fastrp(output_dir / "transitions.parquet", graph_tokens)
    rows = [
        {"subject_type": "function", "subject_id": token, "model": name, "vec": vector.tolist()}
        for name, vectors in (("chord2vec", word_vectors), ("fastrp", graph_vectors))
        for token, vector in sorted(vectors.items())
    ]
    patterns = pl.read_parquet(output_dir / "patterns.parquet", columns=["pattern", "support"])
    patterns = patterns.sort("support", descending=True)
    top_patterns = set(patterns.head(TOP_PATTERNS)["pattern"].to_list())
    skipped = 0
    for pattern in patterns["pattern"]:
        vector = _pattern_vector(pattern, word_vectors, counts)
        if vector is None:
            skipped += 1
        else:
            rows.append(
                {
                    "subject_type": "pattern",
                    "subject_id": pattern,
                    "model": "chord2vec",
                    "vec": vector.tolist(),
                }
            )
    rows.sort(key=lambda row: (row["subject_type"], row["model"], row["subject_id"]))
    schema = {
        "subject_type": pl.Utf8,
        "subject_id": pl.Utf8,
        "model": pl.Utf8,
        "vec": pl.List(pl.Float32),
    }
    pl.DataFrame(rows, schema=schema).write_parquet(output_dir / "embeddings.parquet")
    projection_rows = _projection(rows, output_dir / "embedding_projection.parquet", top_patterns)
    return EmbeddingsSummary(
        rows_written=len(rows),
        function_rows=len(word_vectors) + len(graph_vectors),
        pattern_rows=len(patterns) - skipped,
        projection_rows=projection_rows,
        train_sections=train_sections,
        model_vocab=len(word_vectors),
        skipped_patterns=skipped,
    )
