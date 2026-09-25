"""Intrinsic, reproducible evaluation of F50 function vectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Curated before model scoring. Each (anchor, positive, negative) asserts a
# theory-motivated ordering, not an absolute semantic equivalence.
TRIPLETS = (
    ("M:V7", "M:V", "M:iii"),
    ("M:V7/vi", "M:V7/ii", "M:IV"),
    ("M:Imaj7", "M:I", "M:V"),
    ("M:IVmaj7", "M:IV", "M:V"),
    ("M:ii7", "M:ii", "M:I"),
    ("M:vi7", "M:vi", "M:V"),
    ("M:iii7", "M:iii", "M:IV"),
    ("M:IV7", "M:IV", "M:I"),
    ("M:Vsus4", "M:V", "M:vi"),
    ("M:Vsus2", "M:V", "M:ii"),
    ("M:Isus4", "M:I", "M:V"),
    ("M:Isus2", "M:I", "M:IV"),
    ("M:IVsus2", "M:IV", "M:iii"),
    ("M:IVsus4", "M:IV", "M:vi"),
    ("M:V5", "M:V", "M:IV"),
    ("M:I5", "M:I", "M:ii"),
    ("M:IV5", "M:IV", "M:V"),
    ("M:V/V", "M:V7/V", "M:bVII"),
    ("M:V/vi", "M:V7/vi", "M:iii"),
    ("M:V/ii", "M:V7/ii", "M:I"),
    ("m:i7", "m:i", "m:V"),
    ("m:iv7", "m:iv", "m:III"),
    ("m:V7", "m:V", "m:VI"),
    ("m:VII7", "m:VII", "m:i"),
    ("m:VImaj7", "m:VI", "m:V"),
    ("m:IIImaj7", "m:III", "m:iv"),
    ("m:Vsus4", "m:V", "m:VI"),
    ("m:IVsus2", "m:IV", "m:i"),
    ("m:IVsus4", "m:IV", "m:III"),
    ("m:Isus4", "m:I", "m:V"),
    ("m:Isus2", "m:I", "m:iv"),
    ("m:V5", "m:V", "m:III"),
    ("m:VI5", "m:VI", "m:V"),
    ("m:III5", "m:III", "m:iv"),
    ("m:VII5", "m:VII", "m:i"),
    ("m:V/iv", "m:V7/iv", "m:III"),
    ("m:V7/v", "m:V/v", "m:i"),
    ("m:v7", "m:v", "m:VI"),
    ("m:ii7", "m:ii", "m:V"),
    ("m:IV7", "m:IV", "m:i"),
)
assert len(TRIPLETS) == 40


def _class(token: str) -> str:
    figure = token.partition(":")[2].split("/")[0].lstrip("b#")
    if figure.startswith(("V", "vii")):
        return "dominant"
    if figure.startswith(("ii", "IV", "iv")):
        return "predominant"
    if figure.startswith(("I", "i", "vi", "VI")):
        return "tonic"
    return "other"


@dataclass(frozen=True)
class ModelEvaluation:
    model: str
    passed: int
    evaluated: int
    purity_at_5: float
    neighbors: dict[str, list[str]]

    @property
    def score(self) -> float:
        return self.passed / self.evaluated if self.evaluated else 0.0


def evaluate_embeddings(path: str | Path) -> tuple[list[ModelEvaluation], str]:
    import polars as pl

    frame = pl.scan_parquet(path).filter(pl.col("subject_type") == "function").collect()
    evaluations = []
    for model in ("chord2vec", "fastrp"):
        rows = frame.filter(pl.col("model") == model).sort("subject_id")
        tokens = rows["subject_id"].to_list()
        matrix = np.asarray(rows["vec"].to_list(), dtype=np.float32)
        if not len(tokens):
            evaluations.append(ModelEvaluation(model, 0, 0, 0.0, {}))
            continue
        index = {token: i for i, token in enumerate(tokens)}
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.maximum(norms, 1e-12)
        passed = evaluated = 0
        for anchor, positive, negative in TRIPLETS:
            if not all(token in index for token in (anchor, positive, negative)):
                continue
            evaluated += 1
            a, p, n = (matrix[index[token]] for token in (anchor, positive, negative))
            passed += bool(np.dot(a, p) > np.dot(a, n))
        anchors = [token for token in ("M:I", "M:V7", "M:ii", "m:i", "m:V7") if token in index]
        neighbors = {}
        for token in anchors:
            scores = matrix @ matrix[index[token]]
            neighbors[token] = [tokens[i] for i in np.argsort(-scores) if tokens[i] != token][:5]
        purity_count = purity_total = 0
        # Exact all-pairs similarity is cheap for the vocabulary of core
        # functions; keep the diagnostic bounded if a future corpus grows.
        sample = np.linspace(0, len(tokens) - 1, min(500, len(tokens)), dtype=int)
        for i in sample:
            scores = matrix @ matrix[i]
            nearest = [j for j in np.argsort(-scores) if j != i][:5]
            purity_count += sum(_class(tokens[j]) == _class(tokens[i]) for j in nearest)
            purity_total += len(nearest)
        evaluations.append(
            ModelEvaluation(
                model,
                passed,
                evaluated,
                purity_count / purity_total if purity_total else 0.0,
                neighbors,
            )
        )
    default = max(evaluations, key=lambda item: (item.score, item.purity_at_5)).model
    return evaluations, default


def render_report(evaluations: list[ModelEvaluation], default: str, corpus: str) -> str:
    lines = [
        "# Embedding intrinsic evaluation",
        "",
        f"Corpus: `{corpus}`. Forty fixed, theory-motivated triplets are scored by cosine "
        "similarity.",
        "Only triplets whose three tokens appear in a model's vocabulary count as evaluated.",
        "",
        "| Model | Correct / evaluated | Pass rate | Class purity @ 5 |",
        "|---|---:|---:|---:|",
    ]
    for item in evaluations:
        lines.append(
            f"| {item.model} | {item.passed}/{item.evaluated} | "
            f"{item.score:.1%} | {item.purity_at_5:.1%} |"
        )
    lines.extend(["", f"Default model: `{default}`.", "", "## Nearest neighbors", ""])
    for item in evaluations:
        lines.extend([f"### {item.model}", "", "| Anchor | Top five neighbors |", "|---|---|"])
        lines.extend(
            f"| `{anchor}` | {', '.join(f'`{token}`' for token in neighbors)} |"
            for anchor, neighbors in item.neighbors.items()
        )
        lines.append("")
    lines.extend(
        [
            "## Curated triplets",
            "",
            "| # | Anchor | Expected closer | Expected farther |",
            "|---:|---|---|---|",
        ]
    )
    for i, (anchor, positive, negative) in enumerate(TRIPLETS, 1):
        lines.append(f"| {i} | `{anchor}` | `{positive}` | `{negative}` |")
    lines.append("")
    return "\n".join(lines)
