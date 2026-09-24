"""`examples` stage: up to 5 example songs per pattern and top transition.
Scheduled for F22 (feature-specs/v2-implementation-plan.md)."""

from __future__ import annotations

from pathlib import Path

from pipeline.stages._unimplemented import StageNotImplementedError


def run_examples(sections_path: str | Path, output_path: str | Path) -> None:
    raise StageNotImplementedError("examples", "F22")
