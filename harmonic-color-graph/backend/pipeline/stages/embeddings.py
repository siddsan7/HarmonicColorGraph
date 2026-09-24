"""`embeddings` stage: Chord2Vec and graph embeddings for similarity.
Scheduled for F50 (feature-specs/v2-implementation-plan.md, M5)."""

from __future__ import annotations

from pathlib import Path

from pipeline.stages._unimplemented import StageNotImplementedError


def run_embeddings(sections_path: str | Path, output_path: str | Path) -> None:
    raise StageNotImplementedError("embeddings", "F50")
