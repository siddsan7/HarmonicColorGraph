"""`ngrams` stage: per-(context, order, history) rows for Kneser-Ney backoff.
Scheduled for F22 (feature-specs/v2-implementation-plan.md)."""

from __future__ import annotations

from pathlib import Path

from pipeline.stages._unimplemented import StageNotImplementedError


def run_ngrams(sections_path: str | Path, output_path: str | Path) -> None:
    raise StageNotImplementedError("ngrams", "F22")
